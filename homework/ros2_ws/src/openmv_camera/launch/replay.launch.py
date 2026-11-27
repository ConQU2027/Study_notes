"""Run algorithms and optional RViz from recorded inputs with simulated time.

Start ``ros2 bag play --clock`` separately. Play only image_raw and camera_info
when regenerating outputs; this launch intentionally creates new PnP and TF.
"""

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

    def processing_node(executable, name, config_name):
        return Node(
            package="openmv_camera",
            executable=executable,
            name=name,
            namespace="camera",
            parameters=[config(config_name), {"use_sim_time": True}],
            output="screen",
            emulate_tty=True,
        )

    return LaunchDescription([
        DeclareLaunchArgument(
            "rviz", default_value="false",
            description="Open RViz2 with the target marker configuration",
        ),
        processing_node("openmv_hsv_node", "hsv_segmenter", "hsv.yaml"),
        processing_node("openmv_square_node", "square_detector", "square.yaml"),
        processing_node("openmv_tracking_node", "target_tracker", "tracking.yaml"),
        processing_node("openmv_pose_node", "pose_estimator", "pose.yaml"),
        processing_node("openmv_pose_filter_node", "pose_filter", "filter.yaml"),
        processing_node("openmv_visualization_node", "target_visualizer", "visualization.yaml"),
        Node(
            package="rviz2", executable="rviz2", name="rviz2",
            arguments=["-d", PathJoinSubstitution([package_share, "rviz", "target.rviz"])],
            parameters=[{"use_sim_time": True}],
            condition=IfCondition(LaunchConfiguration("rviz")),
            output="screen", emulate_tty=True,
        ),
    ])
