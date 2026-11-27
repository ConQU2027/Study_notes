"""Real-size RViz markers for raw and filtered poses, with deletion on loss."""

import json

from geometry_msgs.msg import PoseStamped
from rcl_interfaces.msg import SetParametersResult
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String
from visualization_msgs.msg import Marker

from .visualization import (
    square_outline_points, validate_target_size, validate_visualization_settings,
)

DEFAULTS = {
    "display_thickness_m": 0.001,
    "line_width_m": 0.002,
    "base_frame": "base_link",
}


class TargetVisualizerNode(Node):
    def __init__(self) -> None:
        super().__init__("target_visualizer", namespace="/camera")
        for key, value in DEFAULTS.items():
            self.declare_parameter(key, value)
        validate_visualization_settings(self._settings())
        self.add_on_set_parameters_callback(self._validate_parameter_update)
        self._target_size_m = 0.099

        self._raw_pose_sub = self.create_subscription(
            PoseStamped, "target_pose_base", self._on_raw_pose, 10
        )
        self._filtered_pose_sub = self.create_subscription(
            PoseStamped, "target_pose_filtered", self._on_filtered_pose, 10
        )
        self._pose_status_sub = self.create_subscription(
            String, "pose/stats", self._on_pose_status, 10
        )
        self._filter_status_sub = self.create_subscription(
            String, "filter/stats", self._on_filter_status, 10
        )
        self._raw_pub = self.create_publisher(Marker, "target_marker_raw", 10)
        self._filtered_pub = self.create_publisher(Marker, "target_marker_filtered", 10)
        self.get_logger().info(
            "Publishing real-size raw square and filtered outline; markers are deleted on loss."
        )

    def _settings(self) -> dict:
        return {key: self.get_parameter(key).value for key in DEFAULTS}

    def _validate_parameter_update(self, parameters) -> SetParametersResult:
        values = self._settings()
        for parameter in parameters:
            if parameter.name in values:
                values[parameter.name] = parameter.value
        try:
            validate_visualization_settings(values)
        except (TypeError, ValueError) as error:
            return SetParametersResult(successful=False, reason=str(error))
        return SetParametersResult(successful=True)

    def _marker(self, header, namespace: str, marker_type: int) -> Marker:
        marker = Marker()
        marker.header = header
        marker.ns = namespace
        marker.id = 0
        marker.type = marker_type
        marker.action = Marker.ADD
        return marker

    def _delete(self, publisher, namespace: str) -> None:
        marker = Marker()
        marker.header.frame_id = self.get_parameter("base_frame").value
        marker.header.stamp = self.get_clock().now().to_msg()
        marker.ns = namespace
        marker.id = 0
        marker.action = Marker.DELETE
        publisher.publish(marker)

    def _on_raw_pose(self, message: PoseStamped) -> None:
        settings = self._settings()
        marker = self._marker(message.header, "openmv_raw_square", Marker.CUBE)
        marker.pose = message.pose
        marker.scale.x = self._target_size_m
        marker.scale.y = self._target_size_m
        marker.scale.z = settings["display_thickness_m"]
        marker.color.r = 0.1
        marker.color.g = 0.9
        marker.color.b = 0.2
        marker.color.a = 0.30
        self._raw_pub.publish(marker)

    def _on_filtered_pose(self, message: PoseStamped) -> None:
        settings = self._settings()
        marker = self._marker(message.header, "openmv_filtered_outline", Marker.LINE_LIST)
        marker.pose = message.pose
        marker.scale.x = settings["line_width_m"]
        marker.color.r = 0.1
        marker.color.g = 0.7
        marker.color.b = 1.0
        marker.color.a = 1.0
        for x, y, z in square_outline_points(self._target_size_m):
            from geometry_msgs.msg import Point
            point = Point()
            point.x = x
            point.y = y
            point.z = z
            marker.points.append(point)
        self._filtered_pub.publish(marker)

    def _on_pose_status(self, message: String) -> None:
        try:
            source = json.loads(message.data)
            size = validate_target_size(source.get("target_size_m", self._target_size_m))
            self._target_size_m = size
        except (json.JSONDecodeError, TypeError, ValueError):
            return
        if not source.get("valid"):
            self._delete(self._raw_pub, "openmv_raw_square")

    def _on_filter_status(self, message: String) -> None:
        try:
            source = json.loads(message.data)
        except json.JSONDecodeError:
            return
        if not source.get("valid"):
            self._delete(self._filtered_pub, "openmv_filtered_outline")


def main(args=None) -> None:
    rclpy.init(args=args)
    node = None
    try:
        node = TargetVisualizerNode()
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
