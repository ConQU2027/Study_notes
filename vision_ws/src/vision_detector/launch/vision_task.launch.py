from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    params_file = LaunchConfiguration("params_file")

    return LaunchDescription([
        DeclareLaunchArgument(
            "params_file",
            default_value=PathJoinSubstitution([
                FindPackageShare("vision_detector"), "config", "params.yaml"
            ]),
            description="目标尺寸和 HSV 参数文件",
        ),
        DeclareLaunchArgument(
            "camera_x", default_value="0.0",
            description="相机相对 base_link 的 x，单位米",
        ),
        DeclareLaunchArgument(
            "camera_y", default_value="0.0",
            description="相机相对 base_link 的 y，单位米",
        ),
        DeclareLaunchArgument(
            "camera_z", default_value="2.0",
            description="相机相对 base_link 的 z，单位米",
        ),
        DeclareLaunchArgument(
            "camera_roll", default_value="0.0",
            description="相机安装 roll，弧度",
        ),
        DeclareLaunchArgument(
            "camera_pitch", default_value="0.0",
            description="相机安装 pitch，弧度",
        ),
        DeclareLaunchArgument(
            "camera_yaw", default_value="0.0",
            description="相机安装 yaw，弧度",
        ),
        DeclareLaunchArgument(
            "use_rviz", default_value="true",
            description="是否启动 RViz",
        ),

        # base_link -> camera_link：按实际安装位置修改 launch 参数。
        Node(
            package="tf2_ros",
            executable="static_transform_publisher",
            name="base_to_camera_tf",
            arguments=[
                "--x", LaunchConfiguration("camera_x"),
                "--y", LaunchConfiguration("camera_y"),
                "--z", LaunchConfiguration("camera_z"),
                "--roll", LaunchConfiguration("camera_roll"),
                "--pitch", LaunchConfiguration("camera_pitch"),
                "--yaw", LaunchConfiguration("camera_yaw"),
                "--frame-id", "base_link",
                "--child-frame-id", "camera_link",
            ],
            output="screen",
        ),

        # 标准相机光学坐标系：z 向前，x 向右，y 向下。
        Node(
            package="tf2_ros",
            executable="static_transform_publisher",
            name="camera_to_optical_tf",
            arguments=[
                "--x", "0", "--y", "0", "--z", "0",
                "--roll", "-1.5708", "--pitch", "0", "--yaw", "-1.5708",
                "--frame-id", "camera_link",
                "--child-frame-id", "camera_optical_frame",
            ],
            output="screen",
        ),

        Node(
            package="vision_detector",
            executable="target_manager",
            name="target_manager",
            output="screen",
            parameters=[params_file],
        ),
        Node(
            package="vision_detector",
            executable="vision_detector_node",
            name="vision_detector",
            output="screen",
        ),
        Node(
            package="rviz2",
            executable="rviz2",
            name="rviz2",
            arguments=[
                "-d",
                PathJoinSubstitution([
                    FindPackageShare("vision_detector"), "rviz", "vision.rviz"
                ]),
            ],
            condition=IfCondition(LaunchConfiguration("use_rviz")),
            output="screen",
        ),
    ])
