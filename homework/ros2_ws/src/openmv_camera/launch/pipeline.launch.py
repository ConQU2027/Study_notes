"""Start camera, detection, tracking, PnP/TF, filtering and visualization."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    package_share = FindPackageShare("openmv_camera")

    def config(name):
        return PathJoinSubstitution([package_share, "config", name])

    return LaunchDescription([
        DeclareLaunchArgument(
            "serial_port", default_value="/dev/ttyACM0",
            description="OpenMV VCP device; overrides live_calibrated.yaml",
        ),
        DeclareLaunchArgument(
            "rviz", default_value="false",
            description="Open RViz2 with the target marker configuration",
        ),
        Node(
            package="openmv_camera", executable="openmv_camera_node",
            name="openmv_camera", namespace="camera",
            parameters=[config("live_calibrated.yaml"), {
                "serial_port": LaunchConfiguration("serial_port"),
            }],
            output="screen", emulate_tty=True,
        ),
        Node(
            package="openmv_camera", executable="openmv_hsv_node",
            name="hsv_segmenter", namespace="camera",
            parameters=[config("hsv.yaml")], output="screen", emulate_tty=True,
        ),
        Node(
            package="openmv_camera", executable="openmv_square_node",
            name="square_detector", namespace="camera",
            parameters=[config("square.yaml")], output="screen", emulate_tty=True,
        ),
        Node(
            package="openmv_camera", executable="openmv_tracking_node",
            name="target_tracker", namespace="camera",
            parameters=[config("tracking.yaml")], output="screen", emulate_tty=True,
        ),
        Node(
            package="openmv_camera", executable="openmv_pose_node",
            name="pose_estimator", namespace="camera",
            parameters=[config("pose.yaml")], output="screen", emulate_tty=True,
        ),
        Node(
            package="openmv_camera", executable="openmv_pose_filter_node",
            name="pose_filter", namespace="camera",
            parameters=[config("filter.yaml")], output="screen", emulate_tty=True,
        ),
        Node(
            package="openmv_camera", executable="openmv_visualization_node",
            name="target_visualizer", namespace="camera",
            parameters=[config("visualization.yaml")], output="screen", emulate_tty=True,
        ),
        Node(
            package="rviz2", executable="rviz2", name="rviz2",
            arguments=["-d", PathJoinSubstitution([package_share, "rviz", "target.rviz"])],
            parameters=[{"use_sim_time": False}],
            condition=IfCondition(LaunchConfiguration("rviz")),
            output="screen", emulate_tty=True,
        ),
    ])
