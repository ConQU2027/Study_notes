#!/usr/bin/env python3
"""相机节点：用 OpenCV 直接读取 UVC 摄像头并发布 ROS 图像

对比 usb_cam 的好处：
  - 参数完全自己掌控，不受 usb_cam 版本差异影响
  - 便于后续加入图像预处理（如自动曝光补偿）
缺点：没有 usb_cam 那么成熟的错误处理

P6 阶段二选一：
  A. 用本节点（推荐，可控）
  B. 用 usb_cam 节点 + camera_info_url 加载标定 yaml
"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from cv_bridge import CvBridge


class CameraNode(Node):
    def __init__(self):
        super().__init__('hf687_camera')

        self.declare_parameter('video_device', '/dev/video0')
        self.declare_parameter('image_width', 1280)
        self.declare_parameter('image_height', 720)
        self.declare_parameter('framerate', 30.0)
        self.declare_parameter('use_mjpeg', True)
        self.declare_parameter('frame_id', 'camera_link')

        # 内参（标定后从 yaml 覆盖）
        self.declare_parameter('fx', 800.0)
        self.declare_parameter('fy', 800.0)
        self.declare_parameter('cx', 640.0)
        self.declare_parameter('cy', 360.0)
        self.declare_parameter('dist_k1', 0.0)
        self.declare_parameter('dist_k2', 0.0)
        self.declare_parameter('dist_p1', 0.0)
        self.declare_parameter('dist_p2', 0.0)

        gp = self.get_parameter
        self.device = gp('video_device').value
        self.W = gp('image_width').value
        self.H = gp('image_height').value
        self.fps = gp('framerate').value
        self.frame_id = gp('frame_id').value

        self.bridge = CvBridge()
        self.pub_img = self.create_publisher(Image, '/camera/image_raw', 10)
        self.pub_info = self.create_publisher(CameraInfo, '/camera/camera_info', 10)

        self.cap = None
        self.open_camera()

        import threading
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self.get_logger().info(
            f'相机节点已启动 | {self.device} | {self.W}x{self.H} @ {self.fps} Hz'
        )

    # ------------------------------------------------------------------
    def open_camera(self):
        import cv2
        self.cap = cv2.VideoCapture(self.device, cv2.CAP_V4L2)
        if not self.cap.isOpened():
            self.get_logger().error(f'无法打开 {self.device}，检查设备与权限')
            self.cap = None
            return

        # 关键：MJPG 必须在设置分辨率前指定，否则走 YUYV 会严重掉帧
        if self.get_parameter('use_mjpeg').value:
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.W)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.H)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)   # 降低延迟

        real_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        real_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        real_fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.get_logger().info(
            f'相机实际参数: {real_w}x{real_h} @ {real_fps:.1f} Hz'
        )

    # ------------------------------------------------------------------
    def _loop(self):
        while self._running and rclpy.ok():
            self.tick()
    def tick(self):
        if self.cap is None:
            return

        ok, frame = self.cap.read()
        if not ok:
            self.get_logger().warn('读帧失败', throttle_duration_sec=2.0)
            return

        stamp = self.get_clock().now().to_msg()

        img_msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        img_msg.header.stamp = stamp
        img_msg.header.frame_id = self.frame_id
        self.pub_img.publish(img_msg)

        gp = self.get_parameter
        info = CameraInfo()
        info.header.stamp = stamp
        info.header.frame_id = self.frame_id
        info.height = frame.shape[0]
        info.width = frame.shape[1]
        info.distortion_model = 'plumb_bob'
        info.d = [
            gp('dist_k1').value, gp('dist_k2').value,
            gp('dist_p1').value, gp('dist_p2').value, 0.0,
        ]
        fx, fy = gp('fx').value, gp('fy').value
        cx, cy = gp('cx').value, gp('cy').value
        info.k = [fx, 0.0, cx, 0.0, fy, cy, 0.0, 0.0, 1.0]
        info.p = [fx, 0.0, cx, 0.0, 0.0, fy, cy, 0.0, 0.0, 0.0, 1.0, 0.0]
        self.pub_info.publish(info)

    def destroy_node(self):
        self._running = False
        if self.cap is not None:
            self.cap.release()
        super().destroy_node()


def main():
    rclpy.init()
    node = CameraNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()