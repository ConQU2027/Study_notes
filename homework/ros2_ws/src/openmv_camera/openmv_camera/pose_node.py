"""ROS 2 planar PnP and timestamped TF; no smoothing or unique square heading."""

import json
import time

from geometry_msgs.msg import PoseStamped, TransformStamped
import numpy as np
from rcl_interfaces.msg import SetParametersResult
import rclpy
from rclpy.duration import Duration
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.time import Time
from sensor_msgs.msg import CameraInfo
from std_msgs.msg import String
from tf2_ros import TransformException
from tf2_ros.buffer import Buffer
from tf2_ros.static_transform_broadcaster import StaticTransformBroadcaster
from tf2_ros.transform_broadcaster import TransformBroadcaster
from tf2_ros.transform_listener import TransformListener

from .pose import (
    compose_transform, estimate_square_pose, quaternion_to_rotation_matrix,
    rotation_matrix_to_quaternion, rpy_to_quaternion, square_object_points,
    validate_mount_tf_mode,
)

DEFAULTS = {
    "target_size_m": 0.099,
    "max_reprojection_error_px": 8.0,
    "min_positive_depth_m": 0.02,
    "tf_timeout_sec": 0.05,
    "previous_pose_timeout_sec": 0.5,
    "base_frame": "base_link",
    "camera_frame": "camera_optical_frame",
    "target_frame": "target",
    "mount_tf_mode": "assumed_static",
    "base_to_camera_translation_m": [0.20, 0.0, 0.10],
    "base_to_camera_rpy_deg": [-90.0, 0.0, -90.0],
}


def validate_node_settings(values: dict) -> None:
    square_object_points(values["target_size_m"])
    validate_mount_tf_mode(values["mount_tf_mode"])
    for key in (
        "max_reprojection_error_px", "min_positive_depth_m",
        "tf_timeout_sec", "previous_pose_timeout_sec",
    ):
        if not np.isfinite(values[key]) or values[key] <= 0:
            raise ValueError(f"{key} must be positive and finite")
    for key in ("base_frame", "camera_frame", "target_frame"):
        if not isinstance(values[key], str) or not values[key].strip():
            raise ValueError(f"{key} must be a non-empty string")
    if len({values["base_frame"], values["camera_frame"], values["target_frame"]}) != 3:
        raise ValueError("base, camera and target frames must be distinct")
    if len(values["base_to_camera_translation_m"]) != 3 or not np.all(
        np.isfinite(values["base_to_camera_translation_m"])
    ):
        raise ValueError("base_to_camera_translation_m must contain three finite values")
    if len(values["base_to_camera_rpy_deg"]) != 3 or not np.all(
        np.isfinite(values["base_to_camera_rpy_deg"])
    ):
        raise ValueError("base_to_camera_rpy_deg must contain three finite values")


class PoseEstimatorNode(Node):
    def __init__(self) -> None:
        super().__init__("pose_estimator", namespace="/camera")
        for key, value in DEFAULTS.items():
            self.declare_parameter(key, value)
        self._settings = self._read_settings()
        validate_node_settings(self._settings)
        self.add_on_set_parameters_callback(self._validate_parameter_update)

        self._camera_info = None
        self._previous_rvec = None
        self._previous_track_id = None
        self._previous_pose_monotonic = 0.0
        self._tf_buffer = Buffer()
        self._tf_listener = TransformListener(self._tf_buffer, self)
        self._tf_broadcaster = TransformBroadcaster(self)
        self._static_tf_broadcaster = StaticTransformBroadcaster(self)
        if self._settings["mount_tf_mode"] == "assumed_static":
            self._static_tf_broadcaster.sendTransform(self._mount_transform())

        self._info_sub = self.create_subscription(CameraInfo, "camera_info", self._on_info, 10)
        self._square_sub = self.create_subscription(String, "tracking/stats", self._on_square, 10)
        self._camera_pose_pub = self.create_publisher(PoseStamped, "target_pose_camera", 10)
        self._base_pose_pub = self.create_publisher(PoseStamped, "target_pose_base", 10)
        self._stats_pub = self.create_publisher(String, "pose/stats", 10)
        if self._settings["mount_tf_mode"] == "assumed_static":
            self.get_logger().warning(
                "Publishing ASSUMED base-to-camera static TF; it is not measured extrinsics."
            )
        else:
            self.get_logger().info(
                "External mount TF mode: publishing no base-to-camera transform; "
                "robot TF is looked up at each image timestamp."
            )
        self.get_logger().info(
            "PnP uses configured square size and temporally associated targets; "
            "no temporal smoothing is applied."
        )

    def _read_settings(self) -> dict:
        return {key: self.get_parameter(key).value for key in DEFAULTS}

    def _validate_parameter_update(self, parameters) -> SetParametersResult:
        values = self._read_settings()
        for parameter in parameters:
            if (
                parameter.name == "mount_tf_mode"
                and parameter.value != self._settings["mount_tf_mode"]
            ):
                return SetParametersResult(
                    successful=False,
                    reason="mount_tf_mode changes require editing YAML and restarting the node",
                )
            if parameter.name in values:
                values[parameter.name] = parameter.value
        try:
            validate_node_settings(values)
        except (TypeError, ValueError) as error:
            return SetParametersResult(successful=False, reason=str(error))
        return SetParametersResult(successful=True)

    def _mount_transform(self) -> TransformStamped:
        settings = self._read_settings()
        transform = TransformStamped()
        transform.header.stamp = self.get_clock().now().to_msg()
        transform.header.frame_id = settings["base_frame"]
        transform.child_frame_id = settings["camera_frame"]
        translation = settings["base_to_camera_translation_m"]
        transform.transform.translation.x = float(translation[0])
        transform.transform.translation.y = float(translation[1])
        transform.transform.translation.z = float(translation[2])
        quaternion = rpy_to_quaternion(*np.radians(settings["base_to_camera_rpy_deg"]))
        transform.transform.rotation.x = float(quaternion[0])
        transform.transform.rotation.y = float(quaternion[1])
        transform.transform.rotation.z = float(quaternion[2])
        transform.transform.rotation.w = float(quaternion[3])
        return transform

    def _on_info(self, message: CameraInfo) -> None:
        if len(message.k) == 9 and message.k[0] > 0 and message.k[4] > 0:
            self._camera_info = message

    @staticmethod
    def _pose_message(frame_id: str, stamp, rotation: np.ndarray, translation: np.ndarray):
        message = PoseStamped()
        message.header.frame_id = frame_id
        message.header.stamp = stamp
        message.pose.position.x = float(translation[0])
        message.pose.position.y = float(translation[1])
        message.pose.position.z = float(translation[2])
        quaternion = rotation_matrix_to_quaternion(rotation)
        message.pose.orientation.x = float(quaternion[0])
        message.pose.orientation.y = float(quaternion[1])
        message.pose.orientation.z = float(quaternion[2])
        message.pose.orientation.w = float(quaternion[3])
        return message

    def _publish_status(self, source: dict, valid: bool, reason: str, **extra) -> None:
        settings = self._read_settings()
        message = String()
        message.data = json.dumps({
            "valid": valid,
            "reason": reason,
            "stamp": source.get("stamp"),
            "frame_id": source.get("frame_id"),
            "target_size_m": settings["target_size_m"],
            "mount_tf_mode": settings["mount_tf_mode"],
            "mount_is_assumed": settings["mount_tf_mode"] == "assumed_static",
            **extra,
        }, sort_keys=True)
        self._stats_pub.publish(message)

    def _on_square(self, message: String) -> None:
        try:
            source = json.loads(message.data)
        except json.JSONDecodeError as error:
            self.get_logger().error(f"Invalid square stats JSON: {error}")
            return
        tracking = source.get("tracking", {})
        if tracking.get("valid") is False:
            self._publish_status(
                source, False, "invalid_tracking_input", detail=tracking.get("detail")
            )
            return
        if not source.get("detected") or not source.get("targets"):
            reason = {
                "occluded": "target_occluded",
                "tentative": "target_not_confirmed",
            }.get(source.get("tracking_state"), "no_square_target")
            self._publish_status(source, False, reason)
            return
        if self._camera_info is None:
            self._publish_status(source, False, "invalid_or_missing_camera_info")
            return
        settings = self._read_settings()
        if source.get("frame_id") != settings["camera_frame"]:
            self._publish_status(source, False, "square_frame_does_not_match_camera_frame")
            return
        stamp_data = source.get("stamp")
        if not isinstance(stamp_data, dict) or not {"sec", "nanosec"}.issubset(stamp_data):
            self._publish_status(source, False, "missing_image_timestamp")
            return

        selected_target = source["targets"][0]
        selected_track_id = selected_target.get("track_id")
        now = time.monotonic()
        previous = self._previous_rvec
        if (
            selected_track_id != self._previous_track_id
            or now - self._previous_pose_monotonic > settings["previous_pose_timeout_sec"]
        ):
            previous = None
        try:
            pose, pnp_info = estimate_square_pose(
                selected_target["vertices"], settings["target_size_m"],
                self._camera_info.k, self._camera_info.d,
                settings["max_reprojection_error_px"], settings["min_positive_depth_m"],
                previous,
            )
        except (KeyError, TypeError, ValueError) as error:
            self._publish_status(source, False, "invalid_pnp_input", detail=str(error))
            return
        if pose is None:
            self._publish_status(source, False, "no_valid_pnp_candidate", pnp=pnp_info)
            return

        stamp = Time(seconds=stamp_data["sec"], nanoseconds=stamp_data["nanosec"])
        try:
            mount = self._tf_buffer.lookup_transform(
                settings["base_frame"], settings["camera_frame"], stamp,
                timeout=Duration(seconds=settings["tf_timeout_sec"]),
            )
        except TransformException as error:
            self._publish_status(source, False, "tf_lookup_failed", pnp=pnp_info, detail=str(error))
            return

        mount_rotation = quaternion_to_rotation_matrix([
            mount.transform.rotation.x, mount.transform.rotation.y,
            mount.transform.rotation.z, mount.transform.rotation.w,
        ])
        mount_translation = np.array([
            mount.transform.translation.x, mount.transform.translation.y,
            mount.transform.translation.z,
        ], dtype=np.float64)
        base_rotation, base_translation = compose_transform(
            mount_rotation, mount_translation, pose["rotation_matrix"], pose["translation_m"]
        )
        ros_stamp = stamp.to_msg()
        camera_pose = self._pose_message(
            settings["camera_frame"], ros_stamp, pose["rotation_matrix"], pose["translation_m"]
        )
        base_pose = self._pose_message(
            settings["base_frame"], ros_stamp, base_rotation, base_translation
        )
        self._camera_pose_pub.publish(camera_pose)
        self._base_pose_pub.publish(base_pose)

        target_tf = TransformStamped()
        target_tf.header.stamp = ros_stamp
        target_tf.header.frame_id = settings["camera_frame"]
        target_tf.child_frame_id = settings["target_frame"]
        target_tf.transform.translation.x = float(pose["translation_m"][0])
        target_tf.transform.translation.y = float(pose["translation_m"][1])
        target_tf.transform.translation.z = float(pose["translation_m"][2])
        target_tf.transform.rotation = camera_pose.pose.orientation
        self._tf_broadcaster.sendTransform(target_tf)

        self._previous_rvec = pose["rvec"].copy()
        self._previous_track_id = selected_track_id
        self._previous_pose_monotonic = now
        self._publish_status(
            source, True, "ok", pnp=pnp_info,
            tracking_state=source.get("tracking_state"),
            selected_track_id=selected_track_id,
            selected_square_area_px=selected_target["area_px"],
            camera_translation_m=[round(float(value), 6) for value in pose["translation_m"]],
            camera_quaternion_xyzw=[round(float(value), 8) for value in pose["quaternion_xyzw"]],
            base_translation_m=[round(float(value), 6) for value in base_translation],
            base_quaternion_xyzw=[
                round(float(value), 8)
                for value in rotation_matrix_to_quaternion(base_rotation)
            ],
            reprojection_error_px=round(pose["reprojection_error_px"], 5),
        )


def main(args=None) -> None:
    rclpy.init(args=args)
    node = None
    try:
        node = PoseEstimatorNode()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
