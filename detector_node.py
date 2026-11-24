import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import PoseStamped, TransformStamped
from cv_bridge import CvBridge
import cv2
import numpy as np
from scipy.spatial.transform import Rotation as R
import tf2_ros
import tf2_geometry_msgs
from tf2_ros import TransformBroadcaster


class DetectorNode(Node):
    def __init__(self):
        super().__init__('detector_node')
        #声明可调参数
        self.declare_parameter("detect_threshold", 1000.0)
        self.declare_parameter("marker_size",0.05)
        self.declare_parameter("publish_rate",30.0)
        self.declare_parameter("frame_id","camera_link")
        self.declare_parameter("target_frame","target")

        #读取参数（改用 .value）
        self.detect_threshold = self.get_parameter("detect_threshold").value
        self.marker_size = self.get_parameter("marker_size").value
        self.publish_rate = self.get_parameter("publish_rate").value
        self.frame_id = self.get_parameter("frame_id").value
        self.target_frame = self.get_parameter("target_frame").value

        self.tf_broadcaster = TransformBroadcaster(self)
        self.bridge = CvBridge()
        
        self.subscription = self.create_subscription(Image, '/camera/image_raw', self.image_callback, 10)
        self.debug_pub = self.create_publisher(Image, '/debug_image', 10)
        self.target_pub = self.create_publisher(PoseStamped, '/vision/target', 10)
        
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)
        
        self.camera_matrix = np.array([[600.0, 0.0, 320.0], [0.0, 600.0, 240.0], [0.0, 0.0, 1.0]], dtype=np.float32)
        self.dist_coeffs = np.zeros((5, 1))
        
        self.prev_rvec = None
        self.prev_tvec = None
        self.alpha = 0.4

    def image_callback(self, msg):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except:
            return

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array([0, 120, 70]), np.array([10, 255, 255]))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        target_corners = None
        for cnt in contours:
            # 使用参数阈值，不再写死1000
            if cv2.contourArea(cnt) < self.detect_threshold:
                continue
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.04 * peri, True)
            if len(approx) >= 5:
                rect = cv2.minAreaRect(cnt)
                target_corners = cv2.boxPoints(rect)
                break
                
        if target_corners is not None:
            cv2.drawContours(frame, [np.int0(target_corners)], 0, (0, 255, 0), 2)
            # 使用marker_size参数生成物体坐标，不再硬编码0.05
            half = self.marker_size / 2.0
            obj_points = np.array([
                [-half, -half, 0],
                [ half, -half, 0],
                [ half,  half, 0],
                [-half,  half, 0]
            ], dtype=np.float32)
            
            success, rvec, tvec = cv2.solvePnP(obj_points, target_corners, self.camera_matrix, self.dist_coeffs, flags=cv2.SOLVEPNP_IPPE_SQUARE)
                
            if success:
                if self.prev_rvec is None:
                    self.prev_rvec, self.prev_tvec = rvec, tvec
                else:
                    rvec = self.alpha * rvec + (1 - self.alpha) * self.prev_rvec
                    tvec = self.alpha * tvec + (1 - self.alpha) * self.prev_tvec
                    self.prev_rvec, self.prev_tvec = rvec, tvec
                    
                cv2.drawFrameAxes(frame, self.camera_matrix, self.dist_coeffs, rvec, tvec, self.marker_size)
                
                pose_cam = PoseStamped()
                pose_cam.header.stamp = self.get_clock().now().to_msg()
                # 使用参数frame_id
                pose_cam.header.frame_id = self.frame_id
                pose_cam.pose.position.x = float(tvec[0])
                pose_cam.pose.position.y = float(tvec[1])
                pose_cam.pose.position.z = float(tvec[2])
                
                rmat, _ = cv2.Rodrigues(rvec)
                quat = R.from_matrix(rmat).as_quat()
                pose_cam.pose.orientation.x = quat[0]
                pose_cam.pose.orientation.y = quat[1]
                pose_cam.pose.orientation.z = quat[2]
                pose_cam.pose.orientation.w = quat[3]

                # TF广播
                t=TransformStamped()
                t.header.stamp=pose_cam.header.stamp
                t.header.frame_id=self.frame_id
                t.child_frame_id=self.target_frame
                t.transform.translation.x = pose_cam.pose.position.x
                t.transform.translation.y = pose_cam.pose.position.y
                t.transform.translation.z = pose_cam.pose.position.z
                t.transform.rotation.w = pose_cam.pose.orientation.w
                t.transform.rotation.x = pose_cam.pose.orientation.x
                t.transform.rotation.y = pose_cam.pose.orientation.y
                t.transform.rotation.z = pose_cam.pose.orientation.z
                self.tf_broadcaster.sendTransform(t)
                
                try:
                    transform = self.tf_buffer.lookup_transform('base_link', pose_cam.header.frame_id, rclpy.time.Time())
                    pose_base = tf2_geometry_msgs.do_transform_pose_stamped(pose_cam, transform)
                    pose_base.header.frame_id = 'base_link'
                    self.target_pub.publish(pose_base)
                except Exception as e:
                    self.get_logger().warn(f"TF 转换失败: {e}", throttle_duration_sec=2.0)

        try:
            self.debug_pub.publish(self.bridge.cv2_to_imgmsg(frame, encoding="bgr8"))
        except:
            pass


def main(args=None):
    rclpy.init(args=args)
    node = DetectorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()