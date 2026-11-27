"""位姿解算节点：PnP + slerp 滤波 + TF 广播 + 抖动统计"""
import math
from collections import deque
import numpy as np
import cv2
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped, TransformStamped
from sensor_msgs.msg import CameraInfo
from tf2_ros import TransformBroadcaster
from vision_interfaces.msg import TargetDetection
from target_pose.rotation_utils import (
    matrix_to_quaternion, quaternion_to_rpy, quaternion_to_matrix)
def slerp(q0, q1, t):
    """球面线性插值，q = (x, y, z, w)"""
    q0 = np.asarray(q0, dtype=np.float64)
    q1 = np.asarray(q1, dtype=np.float64)
    dot = float(np.dot(q0, q1))
    if dot < 0.0:
        q1 = -q1
        dot = -dot
    dot = min(1.0, dot)
    if dot > 0.9995:                       # 夹角极小，退化为线性插值
        r = q0 + t * (q1 - q0)
        n = np.linalg.norm(r)
        return r / n if n > 1e-9 else q1
    theta_0 = math.acos(dot)
    sin_theta_0 = math.sin(theta_0)
    s0 = math.sin((1.0 - t) * theta_0) / sin_theta_0
    s1 = math.sin(t * theta_0) / sin_theta_0
    return s0 * q0 + s1 * q1
class PoseNode(Node):
    def __init__(self):
        super().__init__('target_pose')
        self.declare_parameter('target_width', 0.20)
        self.declare_parameter('target_height', 0.12)
        self.declare_parameter('notch_width', 0.025)
        self.declare_parameter('pnp_method', 'IPPE')
        self.declare_parameter('use_refine_lm', True)
        self.declare_parameter('assume_undistorted', True)
        self.declare_parameter('filter_type', 'lowpass')
        self.declare_parameter('alpha_position', 0.22)
        self.declare_parameter('alpha_rotation', 0.22)
        self.declare_parameter('max_position_jump', 0.30)
        self.declare_parameter('parent_frame', 'camera_link')
        self.declare_parameter('child_frame', 'target')
        self.declare_parameter('log_interval', 50)
        gp = self.get_parameter
        self.parent_frame = gp('parent_frame').value
        self.child_frame = gp('child_frame').value
        self.max_jump = float(gp('max_position_jump').value)
        self.use_refine = bool(gp('use_refine_lm').value)
        self.log_interval = int(gp('log_interval').value)
        W = float(gp('target_width').value)
        H = float(gp('target_height').value)
        # 完整正方形的 4 个角：图像上对应外接矩形的 4 角
        # 缺口角是两条边延长线的交点，与外接矩形的角在几何上一致
        self.obj_pts = np.array([
            [-W / 2, -H / 2, 0.0],
            [W / 2, -H / 2, 0.0],
            [W / 2, H / 2, 0.0],
            [-W / 2, H / 2, 0.0],
        ], dtype=np.float64)
        self.K = None
        self.D = np.zeros(5, dtype=np.float64)
        self.last_pose = None
        self.gt_pose = None
        self.pnp_count = 0
        self.err_pos_sum = 0.0
        self.err_rot_sum = 0.0
        self.err_count = 0
        self.px_err_sum = 0.0
        self.px_err_count = 0
        # 抖动统计缓冲
        self.raw_hist = deque(maxlen=60)
        self.filt_hist = deque(maxlen=60)
        self.raw_q_hist = deque(maxlen=60)
        self.filt_q_hist = deque(maxlen=60)
        self.pub_raw = self.create_publisher(PoseStamped, '/target/pose_raw', 10)
        self.pub_filt = self.create_publisher(PoseStamped, '/target/pose', 10)
        self.tf_br = TransformBroadcaster(self)
        self.sub_info = self.create_subscription(
            CameraInfo, '/camera_info', self.on_camera_info, 10)
        self.sub_det = self.create_subscription(
            TargetDetection, '/target/detection', self.on_detection, 10)
        self.sub_gt = self.create_subscription(
            PoseStamped, '/target_pose_gt', self.on_gt, 10)
        self.get_logger().info(
            f'位姿节点已启动 | 目标 {W*1000:.0f}x{H*1000:.0f} mm | '
            f'{self.parent_frame} -> {self.child_frame} | slerp=on'
        )
    # ==================================================================
    def on_camera_info(self, msg: CameraInfo):
        if self.K is None:
            self.K = np.array(msg.k, dtype=np.float64).reshape(3, 3)
            d = np.array(msg.d, dtype=np.float64)
            if self.get_parameter('assume_undistorted').value:
                self.D = np.zeros(5, dtype=np.float64)
            else:
                self.D = d if d.size else np.zeros(5, dtype=np.float64)
            self.get_logger().info(
                f'相机内参: fx={self.K[0,0]:.1f} fy={self.K[1,1]:.1f} '
                f'cx={self.K[0,2]:.1f} cy={self.K[1,2]:.1f} | '
                f'assume_undistorted={self.get_parameter("assume_undistorted").value}'
            )
    def on_gt(self, msg: PoseStamped):
        self.gt_pose = msg
    # ==================================================================
    def on_detection(self, msg: TargetDetection):
        if self.K is None:
            return
        img_pts = np.array([[c.x, c.y] for c in msg.corners], dtype=np.float64)
        if img_pts.shape != (4, 2):
            return
        self.diagnose_corners(img_pts)
        try:
            ok, rvec, tvec = cv2.solvePnP(
                self.obj_pts, img_pts, self.K, self.D,
                flags=cv2.SOLVEPNP_IPPE)
        except cv2.error:
            return
        if not ok:
            return
        if self.use_refine:
            try:
                rvec, tvec = cv2.solvePnPRefineLM(
                    self.obj_pts, img_pts, self.K, self.D, rvec, tvec)
            except cv2.error:
                pass
        R, _ = cv2.Rodrigues(rvec)
        q = matrix_to_quaternion(R)
        x, y, z = [float(v) for v in tvec.flatten()]
        self.pnp_count += 1
        self.publish_pose(x, y, z, q, msg.header.stamp, filtered=False)
        filtered = self.apply_filter(np.array([x, y, z, q[0], q[1], q[2], q[3]]))
        self.publish_pose(filtered[0], filtered[1], filtered[2],
                          filtered[3:7], msg.header.stamp, filtered=True)
        # 抖动采样
        self.raw_hist.append(np.array([x, y, z]))
        self.filt_hist.append(filtered[0:3].copy())
        self.raw_q_hist.append(np.array(q, dtype=np.float64))
        self.filt_q_hist.append(np.array(filtered[3:7], dtype=np.float64))
        self.compare_with_gt(x, y, z, q)
    # ==================================================================
    def diagnose_corners(self, img_pts):
        if self.gt_pose is None:
            return
        gt = self.gt_pose.pose
        q_gt = np.array([gt.orientation.x, gt.orientation.y,
                         gt.orientation.z, gt.orientation.w], dtype=np.float64)
        R_gt = quaternion_to_matrix(q_gt)
        t_gt = np.array([gt.position.x, gt.position.y, gt.position.z],
                        dtype=np.float64).reshape(3, 1)
        rvec_gt, _ = cv2.Rodrigues(R_gt)
        try:
            proj, _ = cv2.projectPoints(self.obj_pts, rvec_gt, t_gt, self.K, self.D)
        except cv2.error:
            return
        err = float(np.mean(np.linalg.norm(proj.reshape(4, 2) - img_pts, axis=1)))
        self.px_err_sum += err
        self.px_err_count += 1
    # ==================================================================
    def apply_filter(self, new_pose):
        """一阶低通：位置线性插值，姿态 slerp"""
        a_p = float(self.get_parameter('alpha_position').value)
        a_r = float(self.get_parameter('alpha_rotation').value)
        if self.last_pose is None:
            self.last_pose = new_pose.copy()
            return new_pose.copy()
        if self.max_jump > 0:
            jump = float(np.linalg.norm(new_pose[0:3] - self.last_pose[0:3]))
            if jump > self.max_jump:
                self.get_logger().warn(
                    f'位置跳变 {jump*1000:.0f} mm 超阈值，丢弃该帧',
                    throttle_duration_sec=1.0)
                return self.last_pose.copy()
        out = new_pose.copy()
        out[0:3] = self.last_pose[0:3] * (1.0 - a_p) + new_pose[0:3] * a_p
        out[3:7] = slerp(self.last_pose[3:7], new_pose[3:7], a_r)
        self.last_pose = out.copy()
        return out
    # ==================================================================
    def publish_pose(self, x, y, z, q, stamp, filtered):
        msg = PoseStamped()
        msg.header.stamp = stamp
        msg.header.frame_id = self.parent_frame
        msg.pose.position.x = float(x)
        msg.pose.position.y = float(y)
        msg.pose.position.z = float(z)
        q = np.array(q, dtype=np.float64)
        if q[3] < 0.0:
            q = -q        
        msg.pose.orientation.x = float(q[0])
        msg.pose.orientation.y = float(q[1])
        msg.pose.orientation.z = float(q[2])
        msg.pose.orientation.w = float(q[3])
        if filtered:
            self.pub_filt.publish(msg)
            tf = TransformStamped()
            tf.header = msg.header
            tf.child_frame_id = self.child_frame
            tf.transform.translation.x = msg.pose.position.x
            tf.transform.translation.y = msg.pose.position.y
            tf.transform.translation.z = msg.pose.position.z
            tf.transform.rotation = msg.pose.orientation
            self.tf_br.sendTransform(tf)
        else:
            self.pub_raw.publish(msg)
    # ==================================================================
    @staticmethod
    def _jitter_pos(hist):
        """位置二阶差分均值，单位 mm"""
        if len(hist) < 10:
            return 0.0
        arr = np.stack(list(hist))
        d2 = np.diff(arr, n=2, axis=0)
        return float(np.mean(np.linalg.norm(d2, axis=1))) * 1000.0
    @staticmethod
    def _jitter_rot(hist):
        """相邻帧转角序列的标准差，单位 deg"""
        if len(hist) < 10:
            return 0.0
        qs = list(hist)
        angs = []
        for i in range(1, len(qs)):
            d = abs(float(np.dot(qs[i], qs[i - 1])))
            d = min(1.0, max(-1.0, d))
            angs.append(math.degrees(2.0 * math.acos(d)))
        if len(angs) < 3:
            return 0.0
        return float(np.std(np.diff(angs)))
    # ==================================================================
    def compare_with_gt(self, x, y, z, q):
        if self.gt_pose is None:
            return
        gt = self.gt_pose.pose
        est_p = np.array([x, y, z])
        gt_p = np.array([gt.position.x, gt.position.y, gt.position.z])
        pos_err = float(np.linalg.norm(est_p - gt_p)) * 1000.0
        q_est = np.array([q[0], q[1], q[2], q[3]], dtype=np.float64)
        q_gt = np.array([gt.orientation.x, gt.orientation.y,
                         gt.orientation.z, gt.orientation.w], dtype=np.float64)
        dot = min(1.0, max(-1.0, abs(float(np.dot(q_est, q_gt)))))
        rot_err = math.degrees(2.0 * math.acos(dot))
        self.err_pos_sum += pos_err
        self.err_rot_sum += rot_err
        self.err_count += 1
        if self.err_count % self.log_interval != 0:
            return
        n = float(self.err_count)
        jr_p = self._jitter_pos(self.raw_hist)
        jf_p = self._jitter_pos(self.filt_hist)
        jr_r = self._jitter_rot(self.raw_q_hist)
        jf_r = self._jitter_rot(self.filt_q_hist)
        red_p = (1.0 - jf_p / jr_p) * 100.0 if jr_p > 1e-6 else 0.0
        red_r = (1.0 - jf_r / jr_r) * 100.0 if jr_r > 1e-6 else 0.0
        px = self.px_err_sum / max(self.px_err_count, 1)
        a_p = float(self.get_parameter('alpha_position').value)
        a_r = float(self.get_parameter('alpha_rotation').value)
        self.get_logger().info(
            f'GT #{self.err_count} | 位置 {self.err_pos_sum/n:.2f} mm | '
            f'姿态 {self.err_rot_sum/n:.2f} deg | 角点 {px:.2f} px'
        )
        self.get_logger().info(
            f'  抖动(位置) raw {jr_p:.2f} mm -> filt {jf_p:.2f} mm  (-{red_p:.0f}%) | '
            f'抖动(姿态) raw {jr_r:.2f} deg -> filt {jf_r:.2f} deg  (-{red_r:.0f}%)'
        )
        self.get_logger().info(
            f'  alpha_pos={a_p:.2f} alpha_rot={a_r:.2f}'
        )
def main():
    rclpy.init()
    node = PoseNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
if __name__ == '__main__':
    main()