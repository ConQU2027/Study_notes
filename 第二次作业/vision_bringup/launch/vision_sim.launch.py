import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    bringup_dir = get_package_share_directory('vision_bringup')
    params = os.path.join(bringup_dir, 'config', 'params.yaml')

    use_sim = LaunchConfiguration('use_sim')
    sim_arg = DeclareLaunchArgument('use_sim', default_value='true')

    synthetic = Node(
        package='target_detector',
        executable='synthetic_target',
        name='synthetic_target',
        parameters=[params],
        output='screen',
    )

    detector = Node(
        package='target_detector',
        executable='detector_node',
        name='target_detector',
        parameters=[params],
        remappings=[('/image_raw', '/camera/image_raw')],
        output='screen',
    )

    pose = Node(
        package='target_pose',
        executable='pose_node',
        name='target_pose',
        parameters=[params],
        output='screen',
    )

    return LaunchDescription([sim_arg, synthetic, detector, pose])
