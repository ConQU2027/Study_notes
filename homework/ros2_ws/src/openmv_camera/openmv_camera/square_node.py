"""ROS 2 single-frame square confirmation; no PnP, TF or tracking."""

import json
import time

import cv2
from message_filters import Subscriber, TimeSynchronizer
import numpy as np
from rcl_interfaces.msg import SetParametersResult
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import String

from .square import detect_squares, validate_settings

DEFAULT_SETTINGS = {
    "morph_kernel_size": 3,
    "morph_open_iterations": 1,
    "morph_close_iterations": 1,
    "min_area_px": 300.0,
    "max_area_ratio": 0.9,
    "approx_epsilon_ratio": 0.04,
    "aspect_ratio_max": 1.4,
    "min_angle_deg": 70.0,
    "max_angle_deg": 110.0,
}


class SquareDetectorNode(Node):
    def __init__(self) -> None:
        super().__init__("square_detector", namespace="/camera")
        for key, value in DEFAULT_SETTINGS.items():
            self.declare_parameter(key, value)
        validate_settings(self._settings())
        self.add_on_set_parameters_callback(self._validate_parameter_update)

        self._raw_sub = Subscriber(self, Image, "image_raw", qos_profile=qos_profile_sensor_data)
        self._mask_sub = Subscriber(self, Image, "hsv/mask", qos_profile=qos_profile_sensor_data)
        self._sync = TimeSynchronizer([self._raw_sub, self._mask_sub], queue_size=10)
        self._sync.registerCallback(self._on_images)

        self._mask_pub = self.create_publisher(Image, "square/mask", qos_profile_sensor_data)
        self._overlay_pub = self.create_publisher(Image, "square/overlay", qos_profile_sensor_data)
        self._stats_pub = self.create_publisher(String, "square/stats", 10)
        self.get_logger().info(
            "Publishing single-frame square confirmation; no PnP, TF or temporal tracking."
        )

    def _settings(self) -> dict:
        return {key: self.get_parameter(key).value for key in DEFAULT_SETTINGS}

    def _validate_parameter_update(self, parameters) -> SetParametersResult:
        values = self._settings()
        for parameter in parameters:
            if parameter.name in values:
                values[parameter.name] = parameter.value
        try:
            validate_settings(values)
        except (TypeError, ValueError) as error:
            return SetParametersResult(successful=False, reason=str(error))
        return SetParametersResult(successful=True)

    @staticmethod
    def _image_message(header, encoding: str, data: np.ndarray) -> Image:
        height, width = data.shape[:2]
        message = Image()
        message.header = header
        message.height = height
        message.width = width
        message.encoding = encoding
        message.is_bigendian = False
        message.step = width * (1 if encoding == "mono8" else 3)
        message.data = np.ascontiguousarray(data).tobytes()
        return message

    @staticmethod
    def _decode_image(message: Image, encoding: str) -> np.ndarray:
        channels = 1 if encoding == "mono8" else 3
        if message.encoding != encoding or message.step != message.width * channels:
            raise ValueError(f"Expected tightly packed {encoding} input")
        if message.width == 0 or message.height == 0:
            raise ValueError("Input image dimensions must be non-zero")
        if len(message.data) != message.step * message.height:
            raise ValueError("Input image byte count does not match its dimensions")
        return np.frombuffer(message.data, dtype=np.uint8).reshape(
            message.height, message.width, channels
        ) if channels == 3 else np.frombuffer(message.data, dtype=np.uint8).reshape(
            message.height, message.width
        )

    def _on_images(self, raw_message: Image, mask_message: Image) -> None:
        try:
            bgr = self._decode_image(raw_message, "bgr8")
            mask = self._decode_image(mask_message, "mono8")
        except ValueError as error:
            self.get_logger().error(str(error))
            return
        if bgr.shape[:2] != mask.shape:
            self.get_logger().error("Raw image and HSV mask dimensions differ")
            return

        started = time.perf_counter()
        settings = self._settings()
        filtered, targets, info = detect_squares(mask, settings)
        elapsed_ms = (time.perf_counter() - started) * 1000.0

        overlay = bgr.copy()
        for index, target in enumerate(targets):
            vertices = np.asarray(target["vertices"], dtype=np.int32)
            cv2.polylines(overlay, [vertices], True, (0, 255, 0), 2)
            center = tuple(int(round(value)) for value in target["center_px"])
            cv2.drawMarker(overlay, center, (0, 0, 255), cv2.MARKER_CROSS, 12, 2)
            cv2.putText(
                overlay, f"SQUARE {index}", (center[0] + 6, center[1] - 6),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1, cv2.LINE_AA,
            )

        self._mask_pub.publish(self._image_message(mask_message.header, "mono8", filtered))
        self._overlay_pub.publish(self._image_message(raw_message.header, "bgr8", overlay))
        stats = String()
        stats.data = json.dumps({
            "detected": bool(targets),
            "stamp": {
                "sec": raw_message.header.stamp.sec,
                "nanosec": raw_message.header.stamp.nanosec,
            },
            "frame_id": raw_message.header.frame_id,
            "processing_ms": round(elapsed_ms, 3),
            "filtered_mask_ratio": round(float(cv2.countNonZero(filtered)) / filtered.size, 6),
            "parameters": settings,
            **info,
            "targets": targets,
        }, sort_keys=True)
        self._stats_pub.publish(stats)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = None
    try:
        node = SquareDetectorNode()
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
