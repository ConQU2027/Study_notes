import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('target_vision')
    default_params = os.path.join(pkg_share, 'config', 'vision_params.yaml')

    params_file = LaunchConfiguration('params_file')
    source_type = LaunchConfiguration('source_type')
    device = LaunchConfiguration('device')
    image_dir = LaunchConfiguration('image_dir')
    use_rviz = LaunchConfiguration('use_rviz')

    declare_args = [
        DeclareLaunchArgument('params_file', default_value=default_params),
        DeclareLaunchArgument('source_type', default_value='camera'),
        DeclareLaunchArgument('device', default_value='/dev/video0'),
        DeclareLaunchArgument('image_dir', default_value=''),
        DeclareLaunchArgument('use_rviz', default_value='false'),
    ]

    image_source = Node(
        package='target_vision',
        executable='image_source_node',
        name='image_source_node',
        parameters=[params_file, {
            'source_type': source_type,
            'device': device,
            'image_dir': image_dir,
        }],
        output='screen',
    )

    detector = Node(
        package='target_vision',
        executable='detector_node',
        name='detector_node',
        parameters=[params_file],
        output='screen',
    )

    camera_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='camera_tf',
        arguments=[
            '--x', '0.15', '--y', '0.0', '--z', '0.25',
            '--roll', '-1.5707963', '--pitch', '0.0', '--yaw', '-1.5707963',
            '--frame-id', 'base_link',
            '--child-frame-id', 'camera_optical_frame',
        ],
    )

    rviz2 = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        condition=IfCondition(use_rviz),
    )

    return LaunchDescription(declare_args + [image_source, detector, camera_tf, rviz2])
