"""ROS 2 temporal target association; occluded tracks never emit stale detections."""

import json
import time

import numpy as np
from rcl_interfaces.msg import SetParametersResult
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String

from .tracking import TemporalTracker, validate_tracking_settings

DEFAULTS = {
    "max_association_distance_px": 60.0,
    "max_area_ratio": 2.0,
    "velocity_alpha": 0.5,
    "min_hits": 2,
    "max_missed_frames": 5,
    "track_timeout_sec": 0.5,
}


class TemporalTrackerNode(Node):
    def __init__(self) -> None:
        super().__init__("target_tracker", namespace="/camera")
        for key, value in DEFAULTS.items():
            self.declare_parameter(key, value)
        validate_tracking_settings(self._read_settings())
        self.add_on_set_parameters_callback(self._validate_parameter_update)
        self._tracker = TemporalTracker(self._read_settings())

        self._square_sub = self.create_subscription(
            String, "square/stats", self._on_square, 10
        )
        self._tracking_pub = self.create_publisher(String, "tracking/stats", 10)
        self.get_logger().info(
            "Associating square detections by image timestamp; occluded tracks emit no target."
        )

    def _read_settings(self) -> dict:
        return {key: self.get_parameter(key).value for key in DEFAULTS}

    def _validate_parameter_update(self, parameters) -> SetParametersResult:
        values = self._read_settings()
        for parameter in parameters:
            if parameter.name in values:
                values[parameter.name] = parameter.value
        try:
            validate_tracking_settings(values)
        except (TypeError, ValueError) as error:
            return SetParametersResult(successful=False, reason=str(error))
        return SetParametersResult(successful=True)

    def _publish_invalid(self, source: dict, reason: str, detail: str) -> None:
        message = String()
        message.data = json.dumps({
            "detected": False,
            "target_count": 0,
            "targets": [],
            "stamp": source.get("stamp"),
            "frame_id": source.get("frame_id"),
            "tracking_state": "invalid_input",
            "tracking": {"valid": False, "reason": reason, "detail": detail},
        }, sort_keys=True)
        self._tracking_pub.publish(message)

    def _on_square(self, message: String) -> None:
        started = time.perf_counter()
        source = {}
        try:
            source = json.loads(message.data)
            if not isinstance(source, dict):
                raise ValueError("square stats must be a JSON object")
            stamp = source.get("stamp")
            if not isinstance(stamp, dict) or not {"sec", "nanosec"}.issubset(stamp):
                raise ValueError("missing image timestamp")
            stamp_sec = float(stamp["sec"]) + float(stamp["nanosec"]) * 1e-9
            if not np.isfinite(stamp_sec):
                raise ValueError("image timestamp must be finite")
            targets = source.get("targets", []) if source.get("detected") else []
            self._tracker.settings = self._read_settings()
            tracked = self._tracker.update(targets, stamp_sec)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            self._publish_invalid(
                source if isinstance(source, dict) else {}, "invalid_tracking_input", str(error)
            )
            return

        output = dict(source)
        output["input_detected"] = bool(source.get("detected"))
        output["detected"] = bool(tracked["targets"])
        output["target_count"] = len(tracked["targets"])
        output["targets"] = tracked["targets"]
        output["tracking_state"] = tracked["tracking_state"]
        output["tracking"] = {
            "valid": True,
            "reason": "ok",
            **{key: value for key, value in tracked.items() if key != "targets"},
            "parameters": self._read_settings(),
            "processing_ms": round((time.perf_counter() - started) * 1000.0, 3),
        }
        message = String()
        message.data = json.dumps(output, sort_keys=True)
        self._tracking_pub.publish(message)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = None
    try:
        node = TemporalTrackerNode()
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
