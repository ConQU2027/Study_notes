"""
一键启动视觉链路：相机 (usb_cam) + 白方块识别 (vision/view)

用法：
    ros2 launch vision vision.launch.py
    ros2 launch vision vision.launch.py framerate:=15.0
    ros2 launch vision vision.launch.py white_min:=100          # 环境偏暗，识别不出时调
    ros2 launch vision vision.launch.py smooth_min_cutoff:=2.5  # 抖动明显时调大

设计说明：
    1. 关键参数全部用 DeclareLaunchArgument 声明，命令行可覆盖，不写死在节点里；
    2. 相机输出的 image_raw / camera_info 通过 remappings 改到 /camera/... 下，
       view 节点订阅的正好是这两个名字，两边一对就通；
    3. 数值参数用 ParameterValue 指定类型，否则会被当成字符串传进去，
       usb_cam 声明 int/double 参数时会报 "invalid type"。
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    # ---- 先把所有可调参数取出来，下面统一引用 ----
    video_device = LaunchConfiguration('video_device')
    pixel_format = LaunchConfiguration('pixel_format')
    image_width = LaunchConfiguration('image_width')
    image_height = LaunchConfiguration('image_height')
    framerate = LaunchConfiguration('framerate')
    camera_name = LaunchConfiguration('camera_name')
    camera_info_url = LaunchConfiguration('camera_info_url')
    image_topic = LaunchConfiguration('image_topic')
    camera_info_topic = LaunchConfiguration('camera_info_topic')
    # 识别参数
    white_min = LaunchConfiguration('white_min')
    white_max = LaunchConfiguration('white_max')
    sat_max = LaunchConfiguration('sat_max')
    min_area = LaunchConfiguration('min_area')
    max_reproj = LaunchConfiguration('max_reproj')
    max_track_dist = LaunchConfiguration('max_track_dist')
    smooth_min_cutoff = LaunchConfiguration('smooth_min_cutoff')
    smooth_beta = LaunchConfiguration('smooth_beta')
    debug_every = LaunchConfiguration('debug_every')

    return LaunchDescription([
        # ========== 相机采集参数 ==========
        DeclareLaunchArgument(
            'video_device',
            default_value='/dev/video0',
            description='摄像头设备节点，插拔后编号可能变化',
        ),
        DeclareLaunchArgument(
            'pixel_format',
            default_value='yuyv2rgb',
            description='像素格式。不要用 mjpeg2rgb：这台相机会让 usb_cam 抛异常退出',
        ),
        DeclareLaunchArgument(
            'image_width',
            default_value='640',
            description='图像宽度，必须和标定文件一致',
        ),
        DeclareLaunchArgument(
            'image_height',
            default_value='480',
            description='图像高度，必须和标定文件一致',
        ),
        DeclareLaunchArgument(
            'framerate',
            default_value='20.0',
            description='相机采集帧率(Hz)，目标 20fps',
        ),

        # ========== 标定文件 ==========
        DeclareLaunchArgument(
            'camera_name',
            default_value='camera',
            description='必须和标定 yaml 里的 camera_name 一致，否则静默不加载',
        ),
        DeclareLaunchArgument(
            'camera_info_url',
            default_value='file:///home/an/ros2_learning/task2_ws/config/camera_calib.yaml',
            description='标定文件路径；d 为空时检测节点会拒绝工作',
        ),

        # ========== 话题名 ==========
        DeclareLaunchArgument(
            'image_topic',
            default_value='/camera/image_raw',
            description='图像话题名，发布端和订阅端共用',
        ),
        DeclareLaunchArgument(
            'camera_info_topic',
            default_value='/camera/camera_info',
            description='相机内参话题名，发布端和订阅端共用',
        ),

        # ========== 识别参数（现场调参不用改代码）==========
        DeclareLaunchArgument(
            'white_min',
            default_value='100',
            description='白度下限(0~255)。整块识别不出就往小调：90 / 80 / 70',
        ),
        DeclareLaunchArgument(
            'white_max',
            default_value='165',
            description='白度上限(阈值封顶)。框不住白块调小 150，框住整片桌面调大 180',
        ),
        DeclareLaunchArgument(
            'sat_max',
            default_value='25',
            description='饱和度上限：白纸几乎无颜色(S≈0~10)。框住木桌/纸箱调小 15，白块在暖光下偏黄调大 35',
        ),
        DeclareLaunchArgument(
            'min_area',
            default_value='500',
            description='最小面积(像素)。目标放得很远、框出不来时调小',
        ),
        DeclareLaunchArgument(
            'max_reproj',
            default_value='6.0',
            description='重投影误差上限(像素)，调大能多检出、但假解也变多',
        ),
        DeclareLaunchArgument(
            'max_track_dist',
            default_value='200.0',
            description='跟随允许的单帧最大移动(像素)，快速挥动时跟丢就调大',
        ),
        DeclareLaunchArgument(
            'smooth_min_cutoff',
            default_value='1.6',
            description='静止时滤波截止频率(Hz)，越大越跟手、越小越稳',
        ),
        DeclareLaunchArgument(
            'smooth_beta',
            default_value='0.02',
            description='速度增益，快速移动时的跟手程度',
        ),
        DeclareLaunchArgument(
            'debug_every',
            default_value='2',
            description='调试图每 N 帧发一次(2=10Hz)；想看 20Hz 调试图设 1',
        ),

        # ========== 节点 1：相机 ==========
        Node(
            package='usb_cam',
            executable='usb_cam_node_exe',
            name='usb_cam',
            output='screen',
            parameters=[{
                'video_device': ParameterValue(video_device, value_type=str),
                'pixel_format': ParameterValue(pixel_format, value_type=str),
                'image_width': ParameterValue(image_width, value_type=int),
                'image_height': ParameterValue(image_height, value_type=int),
                'framerate': ParameterValue(framerate, value_type=float),
                'camera_name': ParameterValue(camera_name, value_type=str),
                'camera_info_url': ParameterValue(camera_info_url, value_type=str),
            }],
            remappings=[
                ('image_raw', image_topic),
                ('camera_info', camera_info_topic),
            ],
        ),

        # ========== 节点 2：识别 ==========
        # view 节点内部订阅的是绝对名 /camera/image_raw，所以这里也按绝对名重映射，
        # 这样改 image_topic 参数时两个节点会一起跟着变。
        Node(
            package='vision',
            executable='view',
            name='square_detector_node',
            output='screen',
            parameters=[{
                'white_min': ParameterValue(white_min, value_type=int),
                'white_max': ParameterValue(white_max, value_type=int),
                'sat_max': ParameterValue(sat_max, value_type=int),
                'min_area': ParameterValue(min_area, value_type=float),
                'max_reproj': ParameterValue(max_reproj, value_type=float),
                'max_track_dist': ParameterValue(max_track_dist, value_type=float),
                'smooth_min_cutoff': ParameterValue(smooth_min_cutoff, value_type=float),
                'smooth_beta': ParameterValue(smooth_beta, value_type=float),
                'debug_every': ParameterValue(debug_every, value_type=int),
            }],
            remappings=[
                ('/camera/image_raw', image_topic),
                ('/camera/camera_info', camera_info_topic),
            ],
        ),
    ])
