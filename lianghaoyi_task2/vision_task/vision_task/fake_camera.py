import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
import cv2
import numpy as np
from cv_bridge import CvBridge

class FakeCamera(Node):
    def __init__(self):
        super().__init__('fake_camera')
        self.pub_img = self.create_publisher(Image, '/image_raw', 10)
        self.pub_info = self.create_publisher(CameraInfo, '/camera_info', 10)
        self.bridge = CvBridge()
        
        # 【修改这里】读取你的本地图片
        # 请确保 test_image.jpg 真的在这个路径下！
        self.img = cv2.imread('/home/lianghaoyi/ros2-ws/src/vision_task/test_image2.jpg')
        
        if self.img is None:
            self.get_logger().error("找不到图片！请检查路径！")
            # 如果找不到图，画个红的防报错
            self.img = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.rectangle(self.img, (200, 150), (400, 300), (0, 0, 255), -1) 
        else:
            # 防止图片太大或太小，统一 resize 到 640x480
            self.img = cv2.resize(self.img, (640, 480))

        # 假相机内参
        self.camera_info = CameraInfo()
        self.camera_info.width = 640
        self.camera_info.height = 480
        self.camera_info.k = [500.0, 0.0, 320.0, 0.0, 500.0, 240.0, 0.0, 0.0, 1.0]

        # 20Hz 定时器
        self.timer = self.create_timer(0.05, self.timer_callback)
        self.get_logger().info('假相机节点已启动（读取本地图片模式）！')

    def timer_callback(self):
        # 发布图像和相机信息
        self.pub_img.publish(self.bridge.cv2_to_imgmsg(self.img, "bgr8"))
        self.pub_info.publish(self.camera_info)

def main(args=None):
    rclpy.init(args=args)
    node = FakeCamera()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()