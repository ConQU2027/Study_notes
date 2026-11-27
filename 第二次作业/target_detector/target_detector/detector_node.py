#!/usr/bin/env python3
"""目标检测节点：正方形切角目标

形状假设：边长 88mm 的正方形，在一个角上切去直角三角形缺口。
识别依据：5 顶点多边形的内角——两个缺口端点内角明显小于 90°。
输出：4 个真实点（缺口上端点 + 三个完整角），供 PnP 使用。
"""
import time
import numpy as np
import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from geometry_msgs.msg import Point32
from cv_bridge import CvBridge

from vision_interfaces.msg import TargetDetection


class DetectorNode(Node):
    def __init__(self):
        super().__init__('target_detector')

        self.declare_parameter('target_width', 0.088)
        self.declare_parameter('target_height', 0.088)
        self.declare_parameter('notch_width', 0.025)
        self.declare_parameter('notch_depth', 0.036)

        self.declare_parameter('detect_mode', 'dark')
        self.declare_parameter('use_otsu', True)
        self.declare_parameter('dark_thresh', 80)
        self.declare_parameter('invert', True)
        self.declare_parameter('use_neutral_filter', True)
        self.declare_parameter('max_saturation', 60)
        self.declare_parameter('exclude_green', True)
        self.declare_parameter('green_hue_lo', 35)
        self.declare_parameter('green_hue_hi', 95)
        self.declare_parameter('green_sat_min', 70)

        self.declare_parameter('hsv_lower', [0, 100, 60])
        self.declare_parameter('hsv_upper', [40, 255, 255])

        self.declare_parameter('morph_kernel', 7)
        self.declare_parameter('morph_iterations', 2)

        self.declare_parameter('min_area_ratio', 0.004)
        self.declare_parameter('max_area_ratio', 0.70)
        self.declare_parameter('min_solidity', 0.85)
        self.declare_parameter('aspect_tolerance', 0.3)
        self.declare_parameter('corner_max_angle', 80.0)
        self.declare_parameter('notch_prominence', 2.0)
        self.declare_parameter('min_side_px', 80.0)
        self.declare_parameter('max_side_px', 500.0)

        self.declare_parameter('process_scale', 1.0)
        self.declare_parameter('use_edge_refine', True)
        self.declare_parameter('edge_band_ratio', 0.04)

        self.declare_parameter('undistort_image', True)
        self.declare_parameter('publish_debug_image', True)
        self.declare_parameter('log_interval', 100)

        gp = self.get_parameter
        self.mode = gp('detect_mode').value
        self.use_otsu = bool(gp('use_otsu').value)
        self.dark_thresh = int(gp('dark_thresh').value)
        self.invert = bool(gp('invert').value)
        self.use_neutral_filter = bool(gp('use_neutral_filter').value)
        self.max_saturation = int(gp('max_saturation').value)
        self.exclude_green = bool(gp('exclude_green').value)
        self.green_hue_lo = int(gp('green_hue_lo').value)
        self.green_hue_hi = int(gp('green_hue_hi').value)
        self.green_sat_min = int(gp('green_sat_min').value)
        self.hsv_lower = np.array(gp('hsv_lower').value, dtype=np.uint8)
        self.hsv_upper = np.array(gp('hsv_upper').value, dtype=np.uint8)

        self.morph_k = int(gp('morph_kernel').value)
        self.morph_iter = int(gp('morph_iterations').value)
        self.min_area_ratio = gp('min_area_ratio').value
        self.max_area_ratio = gp('max_area_ratio').value
        self.min_solidity = float(gp('min_solidity').value)
        self.aspect_tol = float(gp('aspect_tolerance').value)
        self.corner_max_angle = float(gp('corner_max_angle').value)
        self.notch_prominence = float(gp('notch_prominence').value)
        self.min_side_px = float(gp('min_side_px').value)
        self.max_side_px = float(gp('max_side_px').value)

        W = float(gp('target_width').value)
        H = float(gp('target_height').value)
        self.expected_aspect = max(W, H) / min(W, H)

        self.scale = float(gp('process_scale').value)
        self.use_refine = bool(gp('use_edge_refine').value)
        self.band_ratio = float(gp('edge_band_ratio').value)
        self.do_undistort = bool(gp('undistort_image').value)
        self.publish_debug = gp('publish_debug_image').value
        self.log_interval = int(gp('log_interval').value)

        self.bridge = CvBridge()
        self.map1 = None
        self.map2 = None
        self.map_size = None
        self.last_thresh = 0

        self.pub = self.create_publisher(TargetDetection, '/target/detection', 10)
        self.pub_dbg = self.create_publisher(Image, '/target/debug_image', 10)
        self.sub = self.create_subscription(Image, '/image_raw', self.on_image, 10)
        self.sub_info = self.create_subscription(
            CameraInfo, '/camera_info', self.on_camera_info, 10)

        self.frame_count = 0
        self.detect_count = 0
        self.total_time = 0.0
        self.reason = {'no_contour': 0, 'no_area': 0, 'no_shape': 0,
                       'no_pentagon': 0, 'no_notch': 0, 'ok': 0}

        self.get_logger().info(
            f'检测节点 | 模式={self.mode} | 目标 '
            f'{W*1000:.0f}x{H*1000:.0f} mm | '
            f'缺口 {gp("notch_width").value*1000:.0f}x'
            f'{gp("notch_depth").value*1000:.0f} mm'
        )

    # ==================================================================
    def on_camera_info(self, msg: CameraInfo):
        if not self.do_undistort:
            return
        K = np.array(msg.k, dtype=np.float64).reshape(3, 3)
        D = np.array(msg.d, dtype=np.float64)
        if D.size == 0:
            D = np.zeros(5, dtype=np.float64)
        size = (int(msg.width), int(msg.height))
        if self.map1 is not None and self.map_size == size:
            return
        self.map1, self.map2 = cv2.initUndistortRectifyMap(
            K, D, None, K, size, cv2.CV_16SC2)
        self.map_size = size
        self.get_logger().info(
            f'去畸变映射已建立 {size[0]}x{size[1]} | k1={D[0]:.3f}')

    # ==================================================================
    def build_mask(self, frame):
        """目标 = 暗区，并可选地剔除绿色背景
        两种剔除策略：
          use_neutral_filter=True  —— 只保留低饱和（适合纯黑目标 + 彩色背景）
          exclude_green=True       —— 只剔除高饱和绿色（适合黑目标带反光/色偏）
        经验上「排除法」更宽容，误杀风险更低。
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        if self.use_otsu:
            t, mask = cv2.threshold(gray, 0, 255,
                                    cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
            self.last_thresh = int(t)
        else:
            _, mask = cv2.threshold(gray, self.dark_thresh, 255,
                                    cv2.THRESH_BINARY_INV)
            self.last_thresh = self.dark_thresh
        hue = hsv[:, :, 0].astype(np.int16)
        sat = hsv[:, :, 1].astype(np.int16)
        if self.use_neutral_filter:
            neutral = (sat < self.max_saturation).astype(np.uint8) * 255
            mask = cv2.bitwise_and(mask, neutral)
        if self.exclude_green:
            green = ((hue >= self.green_hue_lo) & (hue <= self.green_hue_hi)
                     & (sat >= self.green_sat_min))
            mask[green] = 0
        return mask
    # ==================================================================
    def on_image(self, msg: Image):
        self.frame_count += 1
        t_start = time.perf_counter()

        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:
            self.get_logger().error(f'图像转换失败: {e}')
            return

        if self.map1 is not None:
            frame = cv2.remap(frame, self.map1, self.map2, cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_REPLICATE)

        proc = cv2.resize(frame, None, fx=self.scale, fy=self.scale,
                          interpolation=cv2.INTER_LINEAR) if self.scale != 1.0 else frame

        mask = self.build_mask(proc)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (self.morph_k, self.morph_k))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=self.morph_iter)

        result = self.detect(proc, mask)

        if result is not None:
            corners, notch_idx = result
            corners = corners / self.scale
            self.detect_count += 1
            self.reason['ok'] += 1

            det = TargetDetection()
            det.header = msg.header
            det.corners = [Point32(x=float(u), y=float(v), z=0.0) for u, v in corners]
            det.notch_edge = int(notch_idx)
            det.confidence = 1.0
            self.pub.publish(det)
        else:
            corners, notch_idx = None, -1

        if self.publish_debug:
            self.publish_debug_image(frame, mask, corners, notch_idx)

        self.total_time += time.perf_counter() - t_start

        if self.frame_count % self.log_interval == 0:
            avg_ms = self.total_time / self.log_interval * 1000.0
            self.total_time = 0.0
            rate = 100.0 * self.detect_count / self.frame_count
            self.get_logger().info(
                f'帧 {self.frame_count} | 成功 {self.detect_count} ({rate:.0f}%) | '
                f'{avg_ms:.1f} ms | T={self.last_thresh} | {self.reason}'
            )

    # ==================================================================
    def detect(self, proc, mask):
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if not contours:
            self.reason['no_contour'] += 1
            return None

        h, w = proc.shape[:2]
        area_img = float(h * w)

        best, best_area = None, 0.0
        for c in contours:
            a = cv2.contourArea(c)
            if a < self.min_area_ratio * area_img or a > self.max_area_ratio * area_img:
                continue
            if not self.shape_ok(c):
                continue
            if a > best_area:
                best_area, best = a, c

        if best is None:
            self.reason['no_area'] += 1
            return None
        if self.frame_count % 60 == 0:
            _rw, _rh = cv2.minAreaRect(best)[1]
            _ar = max(_rw, _rh) / max(min(_rw, _rh), 1e-6)
            _sol = best_area / max(_rw * _rh, 1e-6)
            _x, _y, _w, _h = cv2.boundingRect(best)
            self.get_logger().info(
                f'  best: 面积={best_area:.0f}, 外接={_rw:.0f}x{_rh:.0f}, '
                f'长宽比={_ar:.2f}, 填充率={_sol:.3f}, bbox=({_x},{_y},{_w},{_h}), '
                f'轮廓数={len(contours)}')

        # ---- 先判断缺口在哪个外接角上（最近点距离法）----
        rect = cv2.minAreaRect(best)
        box4 = self.order_poly(cv2.boxPoints(rect))
        pts_all = best.reshape(-1, 2).astype(np.float64)
        corner_gap = [float(np.min(np.linalg.norm(pts_all - box4[k], axis=1)))
                      for k in range(4)]
        notch_corner = int(np.argmax(corner_gap))
        if self.frame_count % 60 == 0:
            self.get_logger().info(
                '  4 角缺口距离: ' + ', '.join(f'{d:.0f}' for d in corner_gap)
                + f'  -> 缺口角={notch_corner}')
        # ---- 外接矩形 4 角 + 缺口角定位 ----
        rect = cv2.minAreaRect(best)
        box = self.order_poly(cv2.boxPoints(rect))
        pts_all = best.reshape(-1, 2).astype(np.float64)
        gaps = [float(np.min(np.linalg.norm(pts_all - box[k], axis=1)))
                for k in range(4)]
        notch_corner = int(np.argmax(gaps))
        # 缺口显著性：真目标有一个角明显远离轮廓，其余三个几乎贴着
        # 背景中的规则暗区没有这种单角偏移，比值会接近 1
        g_sorted = sorted(gaps, reverse=True)
        if g_sorted[0] < self.notch_prominence * max(g_sorted[1], 1.0):
            self.reason['no_notch'] += 1
            if self.frame_count % 60 == 0:
                self.get_logger().info(
                    '  缺口不显著，丢弃: ' + ', '.join(f'{d:.0f}' for d in g_sorted)
                    + f'  比值={g_sorted[0]/max(g_sorted[1],1e-6):.2f}')
            return None
        # 缺口角应对应 3D 的 P0（左上角），据此决定起点
        box = np.roll(box, -notch_corner, axis=0)
        # 可选：对 3 条完整边做直线拟合精修
        if self.use_refine:
            refined = self.refine_quad_by_edges(best, box, notch_corner)
            if refined is not None:
                box = refined
        if self.frame_count % 60 == 0:
            self.get_logger().info(
                '  4 角缺口距离: ' + ', '.join(f'{d:.0f}' for d in gaps)
                + f'  -> 缺口角={notch_corner}')
        # 尺寸合理性：外接矩形的长边像素数应在合理范围内
        _rw, _rh = cv2.minAreaRect(best)[1]
        _side = 0.5 * (_rw + _rh)
        if _side < self.min_side_px or _side > self.max_side_px:
            self.reason['no_area'] += 1
            return None
        return box, notch_corner


    # ==================================================================
    def refine_quad_by_edges(self, contour, box, notch_corner):
        """用轮廓点拟合四条边求交点；缺口所在边的拟合精度较低，仍参与计算"""
        pts = contour.reshape(-1, 2).astype(np.float64)
        if len(pts) < 20:
            return None
        lines = []
        for i in range(4):
            p0 = box[i]
            p1 = box[(i + 1) % 4]
            ev = p1 - p0
            el = float(np.linalg.norm(ev))
            if el < 8.0:
                return None
            nrm = np.array([-ev[1], ev[0]], dtype=np.float64) / el
            rel = pts - p0
            d = np.abs(rel @ nrm)
            t = (rel @ ev) / (el * el)
            m = (d < el * self.band_ratio) & (t > 0.10) & (t < 0.90)
            if int(m.sum()) < 6:
                return None
            vx, vy, x0, y0 = cv2.fitLine(
                pts[m].astype(np.float32), cv2.DIST_L2, 0, 0.01, 0.01).flatten()
            lines.append((np.array([x0, y0], dtype=np.float64),
                          np.array([vx, vy], dtype=np.float64)))
        out = []
        for i in range(4):
            pa, da = lines[(i - 1) % 4]
            pb, db = lines[i]
            pt = self._intersect(pa, da, pb, db)
            if pt is None:
                return None
            out.append(pt)
        out = np.array(out, dtype=np.float64)
        if np.max(np.linalg.norm(out - box, axis=1)) > 0.25 * np.linalg.norm(box[0] - box[2]):
            return None
        return out
    # ==================================================================
    def shape_ok(self, c):
        area = cv2.contourArea(c)
        rw, rh = cv2.minAreaRect(c)[1]
        if rw < 5.0 or rh < 5.0:
            return False
        rect_area = rw * rh
        if rect_area < 1e-6:
            return False
        if area / rect_area < self.min_solidity:
            return False
        ar = max(rw, rh) / min(rw, rh)
        if abs(ar / self.expected_aspect - 1.0) > self.aspect_tol:
            return False
        return True

    # ==================================================================
    @staticmethod
    def order_poly(pts):
        pts = np.asarray(pts, dtype=np.float64).reshape(-1, 2)
        c = pts.mean(axis=0)
        ang = np.arctan2(pts[:, 1] - c[1], pts[:, 0] - c[0])
        return pts[np.argsort(ang)]

    # ==================================================================
    @staticmethod
    def inner_angles(pts):
        """按顺序计算多边形每个顶点的内角（度）"""
        n = len(pts)
        out = []
        for i in range(n):
            p_prev = pts[(i - 1) % n]
            p = pts[i]
            p_next = pts[(i + 1) % n]
            v1 = p_prev - p
            v2 = p_next - p
            n1 = float(np.linalg.norm(v1))
            n2 = float(np.linalg.norm(v2))
            if n1 < 1e-9 or n2 < 1e-9:
                out.append(180.0)
                continue
            cosv = float(np.clip(v1 @ v2 / (n1 * n2), -1.0, 1.0))
            out.append(float(np.degrees(np.arccos(cosv))))
        return out

    # ==================================================================
    def refine_poly(self, contour, ordered, idx):
        """对 4 条边（P0-P1, P1-P2, P2-P3, P3-P4）做直线拟合，求交点"""
        pts = contour.reshape(-1, 2).astype(np.float64)
        if len(pts) < 20:
            return None

        n = len(ordered)
        edges = [(idx[0], idx[1]), (idx[1], idx[2]),
                 (idx[2], idx[3]), (idx[3], (idx[3] + 1) % n)]

        lines = []
        for a_i, b_i in edges:
            p0 = ordered[a_i]
            p1 = ordered[b_i]
            ev = p1 - p0
            el = float(np.linalg.norm(ev))
            if el < 8.0:
                return None
            nrm = np.array([-ev[1], ev[0]], dtype=np.float64) / el
            rel = pts - p0
            d = np.abs(rel @ nrm)
            t = (rel @ ev) / (el * el)
            m = (d < el * self.band_ratio) & (t > 0.08) & (t < 0.92)
            if int(m.sum()) < 6:
                return None
            vx, vy, x0, y0 = cv2.fitLine(
                pts[m].astype(np.float32), cv2.DIST_L2, 0, 0.01, 0.01).flatten()
            lines.append((np.array([x0, y0], dtype=np.float64),
                          np.array([vx, vy], dtype=np.float64)))

        out = []
        for i in range(4):
            pa, da = lines[(i - 1) % 4]
            pb, db = lines[i]
            pt = self._intersect(pa, da, pb, db)
            if pt is None:
                return None
            out.append(pt)

        out = np.array(out, dtype=np.float64)
        base = ordered[idx]
        if np.max(np.linalg.norm(out - base, axis=1)) > 0.25 * np.linalg.norm(base[0] - base[2]):
            return None
        return out

    # ==================================================================
    @staticmethod
    def _intersect(p1, d1, p2, d2):
        A = np.array([[d1[0], -d2[0]], [d1[1], -d2[1]]], dtype=np.float64)
        det = float(np.linalg.det(A))
        if abs(det) < 1e-9:
            return None
        t = np.linalg.solve(A, p2 - p1)
        return p1 + t[0] * d1

    # ==================================================================
    def publish_debug_image(self, frame, mask, corners, notch_idx):
        vis = frame.copy()

        mh, mw = max(1, vis.shape[0] // 4), max(1, vis.shape[1] // 4)
        small = cv2.resize(mask, (mw, mh), interpolation=cv2.INTER_NEAREST)
        vis[0:mh, 0:mw] = cv2.cvtColor(small, cv2.COLOR_GRAY2BGR)
        cv2.rectangle(vis, (0, 0), (mw, mh), (0, 255, 0), 1)
        cv2.putText(vis, f'T={self.last_thresh}', (4, mh - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)

        if corners is None:
            cv2.putText(vis, 'NO TARGET', (mw + 10, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
        else:
            pts_i = np.round(corners).astype(np.int32)
            cv2.polylines(vis, [pts_i.reshape(-1, 1, 2)], True, (0, 255, 0), 2)
            for i, (x, y) in enumerate(pts_i):
                color = (0, 0, 255) if i == 0 else (255, 0, 255)
                cv2.circle(vis, (int(x), int(y)), 5, color, -1)
                cv2.putText(vis, f'P{i}', (int(x) + 6, int(y) - 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            cv2.line(vis, tuple(pts_i[0]), tuple(pts_i[1]), (0, 165, 255), 3)
            cv2.putText(vis, f'notch={notch_idx}', (mw + 10, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)

        m = self.bridge.cv2_to_imgmsg(vis, encoding='bgr8')
        m.header.stamp = self.get_clock().now().to_msg()
        self.pub_dbg.publish(m)


def main():
    rclpy.init()
    node = DetectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
