import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from geometry_msgs.msg import PoseStamped
from cv_bridge import CvBridge
import cv2
import numpy as np
from collections import deque

class DetectorNode(Node):
    def __init__(self):
        super().__init__('detector_node')
        self.sub_img = self.create_subscription(Image, '/image_raw', self.image_callback, 10)
        self.sub_info = self.create_subscription(CameraInfo, '/camera_info', self.info_callback, 10)
        self.pub_pose = self.create_publisher(PoseStamped, '/target_pose', 10)
        self.pub_debug = self.create_publisher(Image, '/debug_image', 10)
        self.bridge = CvBridge()
        
        # 估测内参，先跑通逻辑再说
        self.camera_matrix = np.array([
            [800.0, 0.0, 320.0],
            [0.0, 800.0, 240.0],
            [0.0, 0.0, 1.0]
        ], dtype=np.float64)

# 畸变系数直接用 0（假装没有畸变）
        self.dist_coeffs = np.zeros((5, 1))
        
        # 物理尺寸 (单位：米)  0.2米长(20cm)，0.1米宽(10cm)
        self.obj_points = np.array([
            [-0.1, -0.05, 0.0], # 左下
            [ 0.1, -0.05, 0.0], # 右下
            [ 0.1,  0.05, 0.0], # 右上
            [-0.1,  0.05, 0.0]  # 左上
        ], dtype=np.float32)
        
        self.pose_history = deque(maxlen=20)
        self.get_logger().info("视觉检测节点已启动！")

    def info_callback(self, msg):
        if self.camera_matrix is None:
            self.camera_matrix = np.array(msg.k).reshape((3, 3))
            self.dist_coeffs = np.array(msg.d)
            self.get_logger().info("收到相机内参！")

    def image_callback(self, msg):
        if self.camera_matrix is None:
            return
            
        cv_img = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        #gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        # 二值化反转：让红色区域变白，背景变黑
        #_, mask = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY_INV)
        # 转换到 HSV 色彩空间
        hsv = cv2.cvtColor(cv_img, cv2.COLOR_BGR2HSV)

# 设定红色的范围（红色在 HSV 里分布在两头，这里给个大概的）
        lower_red1 = np.array([0, 70, 50])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([170, 70, 50])
        upper_red2 = np.array([180, 255, 255])

# 提取红色掩码
        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        mask = mask1 + mask2
                
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        debug_img = cv_img.copy()
        
        if contours:
            c = max(contours, key=cv2.contourArea)
            if cv2.contourArea(c) > 1000:
                
                # 1. 先用凸包把缺口“填平”
                hull = cv2.convexHull(c)
                
                # 2. 用 approxPolyDP 提取 4 个真实的角点（这样能贴合梯形）
                peri = cv2.arcLength(hull, True)
                approx = cv2.approxPolyDP(hull, 0.02 * peri, True)
                
                if len(approx) == 4:
                    cv2.drawContours(debug_img, [approx], -1, (0, 255, 0), 2)
                    
                    # 3. 超级稳定的角点排序法（求和找左上/右下，求差找右上/左下）
                    pts = approx.reshape(4, 2).astype(np.float32)
                    
                    rect = np.zeros((4, 2), dtype=np.float32)
                    s = pts.sum(axis=1)
                    rect[0] = pts[np.argmin(s)] # 左上角（x+y最小）
                    rect[2] = pts[np.argmax(s)] # 右下角（x+y最大）
                    
                    diff = np.diff(pts, axis=1)
                    rect[1] = pts[np.argmin(diff)] # 右上角（y-x最小）
                    rect[3] = pts[np.argmax(diff)] # 左下角（y-x最大）
                    
                    img_points = rect
                else:
                    return

                # PnP 解算
                success, rvec, tvec = cv2.solvePnP(self.obj_points, img_points, self.camera_matrix, self.dist_coeffs)
                
                if success:
                    # 滑动平均
                    self.pose_history.append((tvec[0][0], tvec[1][0], tvec[2][0]))
                    avg_x = np.mean([p[0] for p in self.pose_history])
                    avg_y = np.mean([p[1] for p in self.pose_history])
                    avg_z = np.mean([p[2] for p in self.pose_history])
                    
                    # 发布位姿
                    pose_msg = PoseStamped() # 带有时间戳
                    pose_msg.header.stamp = self.get_clock().now().to_msg() # 获取当前时间，转成ROS消息格式
                    pose_msg.header.frame_id = "camera_link"# 相对于camera_link的位姿
                    pose_msg.pose.position.x = float(avg_x)
                    pose_msg.pose.position.y = float(avg_y)
                    pose_msg.pose.position.z = float(avg_z)
                    pose_msg.pose.orientation.w = 1.0
                    self.pub_pose.publish(pose_msg)
                    
                    # 画坐标轴
                    cv2.drawFrameAxes(debug_img, self.camera_matrix, self.dist_coeffs, rvec, tvec, 0.05)

        cv2.imwrite('/home/lianghaoyi/ros2-ws/final_result.jpg',debug_img)
        self.pub_debug.publish(self.bridge.cv2_to_imgmsg(debug_img, "bgr8"))

def main(args=None):
    rclpy.init(args=args)
    node = DetectorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()