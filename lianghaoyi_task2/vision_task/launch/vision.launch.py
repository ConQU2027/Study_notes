from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        # 1. 静态TF,建立连接
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            arguments=['--x', '0.1', '--y', '0', '--z', '0', '--roll', '0', '--pitch', '0', '--yaw', '0', '--frame-id', 'base_link', '--child-frame-id', 'camera_link']
            # base_link是父坐标系，camera是子坐标系
        ),
        # 2. 假相机
        #Node(
            #package='vision_task',
            #executable='fake_camera',
            #name='fake_camera'
        #),
          # 2. 真实 USB 摄像头节点 (替换了原来的 fake_camera)
        Node(
            package='usb_cam',
            executable='usb_cam_node_exe',
            name='usb_cam',
            # 把刚才命令行里成功的参数写到这里
            parameters=[{
                'video_device': '/dev/video0',
                'pixel_format': 'mjpeg2rgb',
                'image_width': 640,
                'image_height': 480,
                'framerate': 30.0
            }]
        ),
        
        # 3. 视觉节点
        Node(
            package='vision_task',
            executable='detector_node',
            name='detector_node'
        )
    ])