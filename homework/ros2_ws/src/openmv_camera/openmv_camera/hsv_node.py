"""ROS 2 HSV mask and preview publisher; no contour or pose estimation."""

import json
import time

import cv2
import numpy as np
from rcl_interfaces.msg import SetParametersResult
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import String

from .hsv import HSV_LIMITS, hsv_mask_bgr, validate_thresholds

WHITE_DEFAULTS = {
    "h_min": 0,
    "h_max": 179,
    "s_min": 0,
    "s_max": 70,
    "v_min": 180,
    "v_max": 255,
}


class HsvSegmenterNode(Node):
    def __init__(self) -> None:
        super().__init__("hsv_segmenter", namespace="/camera")
        for key, value in WHITE_DEFAULTS.items():
            self.declare_parameter(key, value)
        validate_thresholds(self._thresholds())
        self.add_on_set_parameters_callback(self._validate_parameter_update)

        self._image_sub = self.create_subscription(
            Image,
            "image_raw",
            self._on_image,
            qos_profile_sensor_data,
        )
        self._mask_pub = self.create_publisher(Image, "hsv/mask", qos_profile_sensor_data)
        self._preview_pub = self.create_publisher(Image, "hsv/preview", qos_profile_sensor_data)
        self._stats_pub = self.create_publisher(String, "hsv/stats", 10)
        self.get_logger().info(
            "Publishing raw HSV mask and preview; tune thresholds under the actual lighting."
        )

    def _thresholds(self) -> dict:
        return {key: int(self.get_parameter(key).value) for key in HSV_LIMITS}

    def _validate_parameter_update(self, parameters) -> SetParametersResult:
        values = self._thresholds()
        for parameter in parameters:
            if parameter.name in values:
                values[parameter.name] = int(parameter.value)
        try:
            validate_thresholds(values)
        except ValueError as error:
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

    def _on_image(self, message: Image) -> None:
        if message.encoding != "bgr8" or message.step != message.width * 3:
            self.get_logger().error("HSV node expects tightly packed bgr8 input")
            return
        expected_bytes = message.step * message.height
        if len(message.data) != expected_bytes:
            self.get_logger().error("Input image byte count does not match its dimensions")
            return

        started = time.perf_counter()
        bgr = np.frombuffer(message.data, dtype=np.uint8).reshape(
            message.height, message.width, 3
        )
        thresholds = self._thresholds()
        mask = hsv_mask_bgr(bgr, thresholds)
        preview = bgr.copy()
        preview[mask > 0] = (0, 255, 0)
        elapsed_ms = (time.perf_counter() - started) * 1000.0

        self._mask_pub.publish(self._image_message(message.header, "mono8", mask))
        self._preview_pub.publish(self._image_message(message.header, "bgr8", preview))
        stats = String()
        stats.data = json.dumps({
            "hsv_ms": round(elapsed_ms, 3),
            "mask_pixels": int(cv2.countNonZero(mask)),
            "mask_ratio": round(float(cv2.countNonZero(mask)) / mask.size, 6),
            "thresholds": thresholds,
        }, sort_keys=True)
        self._stats_pub.publish(stats)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = None
    try:
        node = HsvSegmenterNode()
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
