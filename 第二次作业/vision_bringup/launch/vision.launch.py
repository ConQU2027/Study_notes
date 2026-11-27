import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
def generate_launch_description():
    params = os.path.join(
        get_package_share_directory('vision_bringup'), 'config', 'params.yaml')
    camera = Node(
        package='hf687_camera',
        executable='camera_node',
        name='hf687_camera',
        parameters=[params],
        output='screen',
    )
    detector = Node(
        package='target_detector',
        executable='detector_node',
        name='target_detector',
        parameters=[params],
        remappings=[('/image_raw', '/camera/image_raw'),
                    ('/camera_info', '/camera/camera_info')],
        output='screen',
    )
    pose = Node(
        package='target_pose',
        executable='pose_node',
        name='target_pose',
        parameters=[params],
        remappings=[('/camera_info', '/camera/camera_info')],
        output='screen',
    )
    return LaunchDescription([camera, detector, pose])