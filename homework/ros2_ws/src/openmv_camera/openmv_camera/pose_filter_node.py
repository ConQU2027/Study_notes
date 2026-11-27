"""ROS 2 filtered base-frame pose and TF; never republishes stale measurements."""

import json
import time

from geometry_msgs.msg import PoseStamped, TransformStamped
import numpy as np
from rcl_interfaces.msg import SetParametersResult
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String
from tf2_ros.transform_broadcaster import TransformBroadcaster

from .pose_filter import FilterRejection, PoseFilter, validate_filter_settings

DEFAULTS = {
    "position_min_cutoff_hz": 1.0,
    "position_beta": 0.02,
    "position_derivative_cutoff_hz": 1.0,
    "orientation_tau_sec": 0.12,
    "max_position_jump_m": 0.30,
    "max_rotation_jump_deg": 80.0,
    "reacquire_timeout_sec": 0.5,
    "base_frame": "base_link",
    "target_frame": "target_filtered",
}


def validate_node_settings(values: dict) -> None:
    validate_filter_settings(values)
    for key in ("base_frame", "target_frame"):
        if not isinstance(values[key], str) or not values[key].strip():
            raise ValueError(f"{key} must be a non-empty string")
    if values["base_frame"] == values["target_frame"]:
        raise ValueError("base_frame and target_frame must differ")


class PoseFilterNode(Node):
    def __init__(self) -> None:
        super().__init__("pose_filter", namespace="/camera")
        for key, value in DEFAULTS.items():
            self.declare_parameter(key, value)
        validate_node_settings(self._read_settings())
        self.add_on_set_parameters_callback(self._validate_parameter_update)

        self._filter = PoseFilter(self._read_settings())
        self._active = False
        self._ever_active = False
        self._accepted_total = 0
        self._outliers_total = 0
        self._lost_total = 0
        self._reacquired_total = 0

        self._pose_sub = self.create_subscription(
            PoseStamped, "target_pose_base", self._on_pose, 10
        )
        self._status_sub = self.create_subscription(
            String, "pose/stats", self._on_pose_status, 10
        )
        self._pose_pub = self.create_publisher(PoseStamped, "target_pose_filtered", 10)
        self._stats_pub = self.create_publisher(String, "filter/stats", 10)
        self._tf_broadcaster = TransformBroadcaster(self)
        self.get_logger().info(
            "Filtering new base-frame poses with One Euro and quaternion SLERP; "
            "no stale pose republishing."
        )

    def _read_settings(self) -> dict:
        return {key: self.get_parameter(key).value for key in DEFAULTS}

    def _validate_parameter_update(self, parameters) -> SetParametersResult:
        values = self._read_settings()
        for parameter in parameters:
            if parameter.name in values:
                values[parameter.name] = parameter.value
        try:
            validate_node_settings(values)
        except (TypeError, ValueError) as error:
            return SetParametersResult(successful=False, reason=str(error))
        return SetParametersResult(successful=True)

    def _counts(self) -> dict:
        return {
            "accepted_poses_total": self._accepted_total,
            "outliers_rejected_total": self._outliers_total,
            "lost_events_total": self._lost_total,
            "reacquisitions_total": self._reacquired_total,
        }

    def _publish_status(self, source: dict, valid: bool, reason: str, **extra) -> None:
        message = String()
        message.data = json.dumps({
            "valid": valid,
            "reason": reason,
            "stamp": source.get("stamp"),
            "frame_id": self.get_parameter("base_frame").value,
            "parameters": self._read_settings(),
            **self._counts(),
            **extra,
        }, sort_keys=True)
        self._stats_pub.publish(message)

    def _on_pose_status(self, message: String) -> None:
        try:
            source = json.loads(message.data)
        except json.JSONDecodeError:
            return
        if not source.get("valid"):
            if self._active:
                self._lost_total += 1
            self._active = False
            self._filter.reset()
            self._publish_status(source, False, source.get("reason", "upstream_pose_invalid"))

    @staticmethod
    def _source_from_pose(message: PoseStamped) -> dict:
        return {"stamp": {
            "sec": message.header.stamp.sec,
            "nanosec": message.header.stamp.nanosec,
        }}

    def _on_pose(self, message: PoseStamped) -> None:
        source = self._source_from_pose(message)
        settings = self._read_settings()
        if message.header.frame_id != settings["base_frame"]:
            self._publish_status(source, False, "unexpected_base_frame")
            return
        self._filter.settings = settings
        stamp_sec = message.header.stamp.sec + message.header.stamp.nanosec * 1e-9
        translation = np.array([
            message.pose.position.x, message.pose.position.y, message.pose.position.z,
        ], dtype=np.float64)
        quaternion = np.array([
            message.pose.orientation.x, message.pose.orientation.y,
            message.pose.orientation.z, message.pose.orientation.w,
        ], dtype=np.float64)
        started = time.perf_counter()
        try:
            filtered, info = self._filter.process(translation, quaternion, stamp_sec)
        except FilterRejection as error:
            if error.reason in ("position_outlier", "orientation_outlier"):
                self._outliers_total += 1
            self._publish_status(source, False, error.reason, metrics=error.metrics)
            return
        except (TypeError, ValueError) as error:
            self._publish_status(source, False, "invalid_filter_input", detail=str(error))
            return

        if self._ever_active and (not self._active or info["reacquired"]):
            self._reacquired_total += 1
        self._active = True
        self._ever_active = True
        self._accepted_total += 1

        output = PoseStamped()
        output.header = message.header
        output.pose.position.x = float(filtered["translation_m"][0])
        output.pose.position.y = float(filtered["translation_m"][1])
        output.pose.position.z = float(filtered["translation_m"][2])
        output.pose.orientation.x = float(filtered["quaternion_xyzw"][0])
        output.pose.orientation.y = float(filtered["quaternion_xyzw"][1])
        output.pose.orientation.z = float(filtered["quaternion_xyzw"][2])
        output.pose.orientation.w = float(filtered["quaternion_xyzw"][3])
        self._pose_pub.publish(output)

        transform = TransformStamped()
        transform.header = message.header
        transform.child_frame_id = settings["target_frame"]
        transform.transform.translation.x = output.pose.position.x
        transform.transform.translation.y = output.pose.position.y
        transform.transform.translation.z = output.pose.position.z
        transform.transform.rotation = output.pose.orientation
        self._tf_broadcaster.sendTransform(transform)

        elapsed_ms = (time.perf_counter() - started) * 1000.0
        self._publish_status(
            source, True, "ok", metrics=info, processing_ms=round(elapsed_ms, 3),
            filtered_translation_m=[
                round(float(value), 6) for value in filtered["translation_m"]
            ],
            filtered_quaternion_xyzw=[
                round(float(value), 8) for value in filtered["quaternion_xyzw"]
            ],
        )


def main(args=None) -> None:
    rclpy.init(args=args)
    node = None
    try:
        node = PoseFilterNode()
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
