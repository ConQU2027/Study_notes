#!/usr/bin/env python3
"""合成目标数据源：渲染带缺口的彩色矩形，并发布真值位姿

用途：在真实相机/样品到位前，为检测与位姿算法提供可控输入。
     因为位姿是我们自己指定的，所以同时提供 ground truth，
     可用于定量评估 PnP 精度。
"""
import math
import numpy as np
import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from geometry_msgs.msg import PoseStamped
from cv_bridge import CvBridge

from target_detector.rotation_utils import matrix_to_quaternion, rpy_to_matrix


class SyntheticTarget(Node):
    def __init__(self):
        super().__init__('synthetic_target')

        # ---- 目标几何（与 detector 保持一致，从 params.yaml 注入）----
        self.declare_parameter('target_width', 0.200)
        self.declare_parameter('target_height', 0.120)
        self.declare_parameter('notch_width', 0.030)
        self.declare_parameter('notch_depth', 0.020)
        self.declare_parameter('notch_edge_ref', 0)

        # ---- 图像与内参 ----
        self.declare_parameter('width_px', 1280)
        self.declare_parameter('height_px', 720)
        self.declare_parameter('fps', 20.0)
        self.declare_parameter('fx', 800.0)
        self.declare_parameter('fy', 800.0)
        self.declare_parameter('cx', 640.0)
        self.declare_parameter('cy', 360.0)
        self.declare_parameter('dist_k1', 0.0)
        self.declare_parameter('dist_k2', 0.0)

        # ---- 运动与噪声 ----
        self.declare_parameter('motion_amplitude', 0.03)
        self.declare_parameter('motion_period', 6.0)
        self.declare_parameter('add_noise', True)
        self.declare_parameter('noise_sigma', 4.0)
        self.declare_parameter('background_gray', 40)

        gp = self.get_parameter
        self.W = gp('target_width').value
        self.H = gp('target_height').value
        self.NW = gp('notch_width').value
        self.ND = gp('notch_depth').value
        self.notch_edge = gp('notch_edge_ref').value

        self.Wpx = gp('width_px').value
        self.Hpx = gp('height_px').value
        self.fps = gp('fps').value

        self.K = np.array([
            [gp('fx').value, 0.0, gp('cx').value],
            [0.0, gp('fy').value, gp('cy').value],
            [0.0, 0.0, 1.0],
        ], dtype=np.float64)
        self.dist = np.array([gp('dist_k1').value, gp('dist_k2').value, 0.0, 0.0, 0.0],
                             dtype=np.float64)

        self.amp = gp('motion_amplitude').value
        self.period = gp('motion_period').value
        self.add_noise = gp('add_noise').value
        self.noise_sigma = gp('noise_sigma').value
        self.bg = int(gp('background_gray').value)

        self.bridge = CvBridge()
        self.pub_img = self.create_publisher(Image, '/camera/image_raw', 10)
        self.pub_info = self.create_publisher(CameraInfo, '/camera_info', 10)
        self.pub_gt = self.create_publisher(PoseStamped, '/target_pose_gt', 10)

        self.t0 = self.get_clock().now()
        self.timer = self.create_timer(1.0 / self.fps, self.tick)
        self.get_logger().info(
            f'合成目标已启动 | 目标 {self.W*1000:.0f}x{self.H*1000:.0f} mm | '
            f'图像 {self.Wpx}x{self.Hpx} @ {self.fps} Hz'
        )

    # ------------------------------------------------------------------
    def outline_points_3d(self):
        """目标平面上的 3D 轮廓点（z=0），按 notch_edge 把缺口放在指定边

        坐标系与 OpenCV 相机系一致：x 向右、y 向下、z 向前
        """
        W, H, nw, nd = self.W, self.H, self.NW, self.ND

        if self.notch_edge == 0:      # 缺口在上边（y = -H/2）
            xg = W * 0.25
            return np.array([
                [-W/2, -H/2, 0], [xg-nw/2, -H/2, 0], [xg-nw/2, -H/2+nd, 0],
                [xg+nw/2, -H/2+nd, 0], [xg+nw/2, -H/2, 0],
                [W/2, -H/2, 0], [W/2, H/2, 0], [-W/2, H/2, 0],
            ], dtype=np.float64)

        if self.notch_edge == 1:      # 缺口在右边（x = +W/2）
            yg = -H * 0.25
            return np.array([
                [-W/2, -H/2, 0], [W/2, -H/2, 0], [W/2, yg-nw/2, 0],
                [W/2-nd, yg-nw/2, 0], [W/2-nd, yg+nw/2, 0],
                [W/2, yg+nw/2, 0], [W/2, H/2, 0], [-W/2, H/2, 0],
            ], dtype=np.float64)

        if self.notch_edge == 2:      # 缺口在下边（y = +H/2）
            xg = -W * 0.25
            return np.array([
                [-W/2, -H/2, 0], [W/2, -H/2, 0], [W/2, H/2, 0],
                [xg+nw/2, H/2, 0], [xg+nw/2, H/2-nd, 0],
                [xg-nw/2, H/2-nd, 0], [xg-nw/2, H/2, 0], [-W/2, H/2, 0],
            ], dtype=np.float64)

        # notch_edge == 3: 缺口在左边（x = -W/2）
        yg = H * 0.25
        return np.array([
            [-W/2, -H/2, 0], [W/2, -H/2, 0], [W/2, H/2, 0], [-W/2, H/2, 0],
            [-W/2, yg+nw/2, 0], [-W/2+nd, yg+nw/2, 0],
            [-W/2+nd, yg-nw/2, 0], [-W/2, yg-nw/2, 0],
        ], dtype=np.float64)

    # ------------------------------------------------------------------
    def tick(self):
        now = self.get_clock().now()
        t = (now - self.t0).nanoseconds * 1e-9

        # ---- 目标位姿轨迹：绕中心做正弦摆动，模拟"动态变换" ----
        w = 2.0 * math.pi / max(self.period, 1e-3)
        x = self.amp * math.sin(w * t)
        y = self.amp * 0.7 * math.sin(1.3 * w * t)
        z = 0.60 + 0.05 * math.sin(0.7 * w * t)
        yaw = 0.5 * math.sin(0.9 * w * t)
        pitch = 0.15 * math.sin(1.1 * w * t)
        roll = 0.08 * math.sin(1.7 * w * t)

        R = rpy_to_matrix(roll, pitch, yaw)
        tvec = np.array([[x], [y], [z]], dtype=np.float64)

        # ---- 投影到图像平面 ----
        pts3d = self.outline_points_3d()
        pts2d, _ = cv2.projectPoints(pts3d, R, tvec, self.K, self.dist)
        pts2d = pts2d.reshape(-1, 2).astype(np.int32)

        # ---- 渲染 ----
        img = np.full((self.Hpx, self.Wpx, 3), self.bg, dtype=np.uint8)
        cv2.fillPoly(img, [pts2d], (40, 200, 240))          # 橙色（BGR）

        if self.add_noise:
            noise = np.random.normal(0, self.noise_sigma, img.shape)
            img = np.clip(img.astype(np.float64) + noise, 0, 255).astype(np.uint8)

        stamp = now.to_msg()

        # ---- 发布图像 ----
        img_msg = self.bridge.cv2_to_imgmsg(img, encoding='bgr8')
        img_msg.header.stamp = stamp
        img_msg.header.frame_id = 'camera_link'
        self.pub_img.publish(img_msg)

        # ---- 发布相机内参 ----
        info = CameraInfo()
        info.header.stamp = stamp
        info.header.frame_id = 'camera_link'
        info.height = self.Hpx
        info.width = self.Wpx
        info.distortion_model = 'plumb_bob'
        info.d = [float(v) for v in self.dist]
        info.k = [float(v) for v in self.K.flatten()]
        info.r = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
        info.p = [
            self.K[0, 0], 0.0, self.K[0, 2], 0.0,
            0.0, self.K[1, 1], self.K[1, 2], 0.0,
            0.0, 0.0, 1.0, 0.0,
        ]
        self.pub_info.publish(info)

        # ---- 发布真值位姿 ----
        qx, qy, qz, qw = matrix_to_quaternion(R)
        gt = PoseStamped()
        gt.header.stamp = stamp
        gt.header.frame_id = 'camera_link'
        gt.pose.position.x = float(x)
        gt.pose.position.y = float(y)
        gt.pose.position.z = float(z)
        gt.pose.orientation.x = float(qx)
        gt.pose.orientation.y = float(qy)
        gt.pose.orientation.z = float(qz)
        gt.pose.orientation.w = float(qw)
        self.pub_gt.publish(gt)


def main():
    rclpy.init()
    node = SyntheticTarget()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()