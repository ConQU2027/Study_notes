#include <rclcpp/rclcpp.hpp>

#include <cv_bridge/cv_bridge.h>
#include <geometry_msgs/msg/pose_stamped.hpp>
#include <image_transport/image_transport.hpp>
#include <std_msgs/msg/header.hpp>
#include <tf2/LinearMath/Matrix3x3.h>
#include <tf2/LinearMath/Quaternion.h>
#include <tf2/time.h>
#include <tf2_geometry_msgs/tf2_geometry_msgs.hpp>
#include <tf2_ros/buffer.h>
#include <tf2_ros/transform_broadcaster.h>
#include <tf2_ros/transform_listener.h>
#include <vision_interfaces/msg/target_spec.hpp>

#include <opencv2/calib3d.hpp>
#include <opencv2/highgui.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/videoio.hpp>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <memory>
#include <vector>

namespace
{
constexpr char kBaseFrame[] = "base_link";
constexpr char kCameraFrame[] = "camera_optical_frame";
constexpr char kTargetFrame[] = "target_object";
constexpr double kMinArea = 800.0;
constexpr double kNotchMinDepth = 4.0;
constexpr int kBlurKernel = 5;
constexpr int kMorphKernel = 3;

// 缺口在物理目标的哪个角：0 左上，1 右上，2 右下，3 左下。
constexpr int kNotchCorner = 0;

// 位姿平滑和有效性过滤。
constexpr double kAlpha = 0.35;
constexpr double kResetJump = 0.15;       // 米
constexpr double kResetAngle = 0.5;       // 弧度
constexpr double kMaxReprojection = 3.0;  // 像素
constexpr double kMinDistance = 0.05;     // 米
constexpr double kMaxDistance = 3.0;      // 米

// 只用于显示框的 2D 角点平滑。
constexpr double kCornerAlpha = 0.35;
constexpr double kCornerResetPx = 30.0;

struct TargetSpecData
{
  double width{0.22};
  double height{0.14};
  int h_min{0};
  int h_max{10};
  int s_min{90};
  int s_max{255};
  int v_min{50};
  int v_max{255};
};
}

class VisionDetectorNode : public rclcpp::Node
{
public:
  VisionDetectorNode() : Node("vision_detector")
  {
    // 直接打开 USB 相机；采集模式设为 640x480、MJPG、20 帧。
    cap_.open(0, cv::CAP_V4L2);
    if (!cap_.isOpened()) {
      RCLCPP_ERROR(get_logger(), "无法打开 USB 相机");
      return;
    }

    cap_.set(cv::CAP_PROP_FOURCC, cv::VideoWriter::fourcc('M', 'J', 'P', 'G'));
    cap_.set(cv::CAP_PROP_FRAME_WIDTH, 640);
    cap_.set(cv::CAP_PROP_FRAME_HEIGHT, 480);
    cap_.set(cv::CAP_PROP_FPS, 20);
    cap_.set(cv::CAP_PROP_BUFFERSIZE, 1);
    RCLCPP_INFO(
      get_logger(), "USB 相机已打开：%dx%d, %.1f fps",
      static_cast<int>(cap_.get(cv::CAP_PROP_FRAME_WIDTH)),
      static_cast<int>(cap_.get(cv::CAP_PROP_FRAME_HEIGHT)),
      cap_.get(cv::CAP_PROP_FPS));

    // TF：查询 base_link -> camera_optical_frame，发布 target_object。
    tf_buffer_ = std::make_shared<tf2_ros::Buffer>(get_clock());
    tf_listener_ = std::make_shared<tf2_ros::TransformListener>(*tf_buffer_);
    tf_broadcaster_ = std::make_shared<tf2_ros::TransformBroadcaster>(*this);

    // 给 rqt / rviz2 看的调试图像。
    debug_pub_ = image_transport::create_publisher(this, "/vision/debug_image");

    spec_sub_ = create_subscription<vision_interfaces::msg::TargetSpec>(
      "/target_spec", 10,
      std::bind(&VisionDetectorNode::specCallback, this, std::placeholders::_1));

    pose_pub_ = create_publisher<geometry_msgs::msg::PoseStamped>("/target_pose", 10);

    timer_ = create_wall_timer(
      std::chrono::milliseconds(50),
      std::bind(&VisionDetectorNode::timerCallback, this));
  }

private:
  // 接收目标宽高和 HSV 范围。
  void specCallback(const vision_interfaces::msg::TargetSpec::SharedPtr msg)
  {
    const bool changed =
      spec_.width != msg->width ||
      spec_.height != msg->height ||
      spec_.h_min != msg->h_min ||
      spec_.h_max != msg->h_max ||
      spec_.s_min != msg->s_min ||
      spec_.s_max != msg->s_max ||
      spec_.v_min != msg->v_min ||
      spec_.v_max != msg->v_max;

    spec_.width = msg->width;
    spec_.height = msg->height;
    spec_.h_min = msg->h_min;
    spec_.h_max = msg->h_max;
    spec_.s_min = msg->s_min;
    spec_.s_max = msg->s_max;
    spec_.v_min = msg->v_min;
    spec_.v_max = msg->v_max;

    // 只有目标参数变化时才重置，避免 1 Hz 重复发布把平滑一直打断。
    if (changed) {
      has_last_pose_ = false;
      has_last_corners_ = false;
    }
  }

  void timerCallback()
  {
    cv::Mat frame;
    cap_ >> frame;
    if (frame.empty()) {
      return;
    }
    RCLCPP_INFO_ONCE(get_logger(), "已读取第一帧图像");

    cv::Mat display = frame.clone();
    std::vector<cv::Point2f> corners;
    const bool found = detect(frame, corners, display);

    // 显示识别结果。
    cv::imshow("vision_detector", display);
    cv::waitKey(1);

    // 发布给 rqt / rviz2 / rosbag 的调试图像。
    std_msgs::msg::Header header;
    header.stamp = now();
    header.frame_id = kCameraFrame;
    debug_pub_.publish(*cv_bridge::CvImage(header, "bgr8", display).toImageMsg());

    if (!found) {
      return;
    }

    cv::Vec3d rvec;
    cv::Vec3d tvec;
    if (!solvePose(corners, rvec, tvec)) {
      return;
    }

    publishPose(rvec, tvec);
  }

  // 颜色分割、找轮廓、最小外接矩形。
  bool detect(const cv::Mat & frame,std::vector<cv::Point2f> & corners,cv::Mat & display){
    cv::Mat blurred;
    //高斯模糊
    cv::GaussianBlur(frame, blurred, cv::Size(kBlurKernel, kBlurKernel), 0.0);
    //转hsv图像
    cv::Mat hsv;
    cv::cvtColor(blurred, hsv, cv::COLOR_BGR2HSV);
    //二值化
    cv::Mat mask;
    cv::inRange(hsv,cv::Scalar(spec_.h_min, spec_.s_min, spec_.v_min),
      cv::Scalar(spec_.h_max, spec_.s_max, spec_.v_max),mask);
    //形态学操作 构造核 开闭运算
    const cv::Mat kernel = cv::getStructuringElement(cv::MORPH_RECT, cv::Size(kMorphKernel, kMorphKernel));
    cv::morphologyEx(mask, mask, cv::MORPH_OPEN, kernel);
    cv::morphologyEx(mask, mask, cv::MORPH_CLOSE, kernel);
    //找轮廓
    std::vector<std::vector<cv::Point>> contours;
    cv::findContours(mask, contours, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_SIMPLE);
    if (contours.empty()) {
      return false;
    }
    //取最大轮廓
    const auto largest = std::max_element(
      contours.begin(), contours.end(),
      [](const std::vector<cv::Point> & a, const std::vector<cv::Point> & b) {
        return cv::contourArea(a) < cv::contourArea(b);
      });

    if (cv::contourArea(*largest) < kMinArea) {
      return false;
    }
    //拟合最小外接矩形 得到四个角点
    const cv::RotatedRect rect = cv::minAreaRect(*largest);
    cv::Point2f points[4];
    rect.points(points);
    corners.assign(points, points + 4);

    // 按顺时针排序，后面再从缺口角开始。
    cv::Point2f center(0.0F, 0.0F);
    for (const auto & p : corners) {
      center += p;
    }
    center *= 0.25F;
    std::sort(
      corners.begin(), corners.end(),
      [center](const cv::Point2f & a, const cv::Point2f & b) {
        return std::atan2(a.y - center.y, a.x - center.x) <
               std::atan2(b.y - center.y, b.x - center.x);
      });

    // 凸包 + 凸包缺陷找缺口。
    std::vector<int> hull;
    cv::convexHull(*largest, hull, true, true);
    std::vector<cv::Vec4i> defects;
    cv::convexityDefects(*largest, hull, defects);
    if (defects.empty()) {
      return false;
    }

    double max_depth = 0.0;
    cv::Point2f notch;
    for (const auto & defect : defects) {
      const double depth = static_cast<double>(defect[3]) / 256.0;
      if (depth > max_depth) {
        max_depth = depth;
        const cv::Point & p = (*largest)[defect[2]];
        notch = cv::Point2f(static_cast<float>(p.x), static_cast<float>(p.y));
      }
    }
    if (max_depth < kNotchMinDepth) {
      return false;
    }

    // 缺口最近的角作为 0 号角点。
    size_t start = 0;
    double best = 1e9;
    for (size_t i = 0; i < corners.size(); ++i) {
      const double d = cv::norm(corners[i] - notch);
      if (d < best) {
        best = d;
        start = i;
      }
    }
    std::rotate(corners.begin(), corners.begin() + start, corners.end());

    // 对显示用的四个角做低通，避免绿色框逐帧抖动。
    // PnP 仍然使用上面的原始 corners。
    std::vector<cv::Point2f> display_corners = corners;
    bool reset_corners = !has_last_corners_;
    if (!reset_corners) {
      for (size_t i = 0; i < display_corners.size(); ++i) {
        if (cv::norm(display_corners[i] - last_corners_[i]) > kCornerResetPx) {
          reset_corners = true;
          break;
        }
      }
    }

    if (reset_corners) {
      last_corners_ = corners;
      has_last_corners_ = true;
    } else {
      for (size_t i = 0; i < display_corners.size(); ++i) {
        display_corners[i] =
          static_cast<float>(kCornerAlpha) * display_corners[i] +
          static_cast<float>(1.0 - kCornerAlpha) * last_corners_[i];
      }
      last_corners_ = display_corners;
    }

    // 画平滑后的框
    cv::circle(display, notch, 6, cv::Scalar(255, 0, 0), -1);
    for (size_t i = 0; i < display_corners.size(); ++i) {
      cv::circle(display, display_corners[i], 5, cv::Scalar(0, 0, 255), -1);
      cv::line(
        display, display_corners[i], display_corners[(i + 1) % 4],
        cv::Scalar(0, 255, 0), 2);
    }

    return true;
  }

  // 已知宽高 + 四个图像角点，求位姿。
  bool solvePose(
    const std::vector<cv::Point2f> & corners,
    cv::Vec3d & rvec,
    cv::Vec3d & tvec)
  {
    const float half_w = static_cast<float>(spec_.width * 0.5);
    const float half_h = static_cast<float>(spec_.height * 0.5);

    // 左上、右上、右下、左下。
    std::vector<cv::Point3f> object_points = {
      {-half_w, half_h, 0.0F},
      {half_w, half_h, 0.0F},
      {half_w, -half_h, 0.0F},
      {-half_w, -half_h, 0.0F}};

    // 缺口在哪个物理角，模型点就从哪个角开始。
    std::rotate(
      object_points.begin(),
      object_points.begin() + kNotchCorner,
      object_points.end());

    if (!cv::solvePnP(
        object_points, corners, camera_matrix_, dist_coeffs_, rvec, tvec,
        false, cv::SOLVEPNP_IPPE))
    {
      return false;
    }

    // 非线性优化，减小角点噪声造成的抖动。
    try {
      cv::solvePnPRefineLM(
        object_points, corners, camera_matrix_, dist_coeffs_, rvec, tvec);
    } catch (const cv::Exception &) {
      // 优化失败时保留 IPPE 的解。
    }

    if (tvec[2] < kMinDistance || tvec[2] > kMaxDistance) {
      return false;
    }

    // 重投影误差过大说明角点或 PnP 解不可信，直接丢弃。
    std::vector<cv::Point2f> projected;
    cv::projectPoints(object_points, rvec, tvec, camera_matrix_, dist_coeffs_, projected);

    double sum_squared = 0.0;
    for (size_t i = 0; i < projected.size(); ++i) {
      const double dx = projected[i].x - corners[i].x;
      const double dy = projected[i].y - corners[i].y;
      sum_squared += dx * dx + dy * dy;
    }
    const double rms = std::sqrt(sum_squared / static_cast<double>(projected.size()));
    if (rms > kMaxReprojection) {
      return false;
    }

    return true;
  }

  void publishPose(const cv::Vec3d & rvec, const cv::Vec3d & tvec)
  {
    // PoseStamped 的姿态字段是四元数，所以这里必须转换。
    cv::Mat rotation;
    cv::Rodrigues(rvec, rotation);
    const tf2::Matrix3x3 matrix(
      rotation.at<double>(0, 0), rotation.at<double>(0, 1), rotation.at<double>(0, 2),
      rotation.at<double>(1, 0), rotation.at<double>(1, 1), rotation.at<double>(1, 2),
      rotation.at<double>(2, 0), rotation.at<double>(2, 1), rotation.at<double>(2, 2));

    tf2::Quaternion q;
    matrix.getRotation(q);
    q.normalize();

    const rclcpp::Time stamp = now();

    // 跳变、断档时重置；否则做位置低通和姿态 slerp。
    const bool gap =
      last_stamp_.nanoseconds() > 0 && (stamp - last_stamp_).seconds() > 0.5;
    const double jump = cv::norm(tvec - last_tvec_);

    const double dot = std::abs(
      q.x() * last_q_.x() + q.y() * last_q_.y() +
      q.z() * last_q_.z() + q.w() * last_q_.w());
    const double angle = 2.0 * std::acos(std::min(1.0, dot));

    if (!has_last_pose_ || gap || jump > kResetJump || angle > kResetAngle) {
      last_tvec_ = tvec;
      last_q_ = q;
      has_last_pose_ = true;
    } else {
      last_tvec_ = kAlpha * tvec + (1.0 - kAlpha) * last_tvec_;
      last_q_ = last_q_.slerp(q, kAlpha);
      last_q_.normalize();
    }
    last_stamp_ = stamp;

    // 相机坐标系下的平滑位姿。
    geometry_msgs::msg::PoseStamped camera_pose;
    camera_pose.header.stamp = stamp;
    camera_pose.header.frame_id = kCameraFrame;
    camera_pose.pose.position.x = last_tvec_[0];
    camera_pose.pose.position.y = last_tvec_[1];
    camera_pose.pose.position.z = last_tvec_[2];
    camera_pose.pose.orientation.x = last_q_.x();
    camera_pose.pose.orientation.y = last_q_.y();
    camera_pose.pose.orientation.z = last_q_.z();
    camera_pose.pose.orientation.w = last_q_.w();

    // 发布平滑后的 camera_optical_frame -> target_object TF。
    geometry_msgs::msg::TransformStamped tf_msg;
    tf_msg.header.stamp = stamp;
    tf_msg.header.frame_id = kCameraFrame;
    tf_msg.child_frame_id = kTargetFrame;
    tf_msg.transform.translation.x = last_tvec_[0];
    tf_msg.transform.translation.y = last_tvec_[1];
    tf_msg.transform.translation.z = last_tvec_[2];
    tf_msg.transform.rotation = camera_pose.pose.orientation;
    tf_broadcaster_->sendTransform(tf_msg);

    // 用 TF 把位姿变换到 base_link。
    geometry_msgs::msg::PoseStamped base_pose;
    try {
      const geometry_msgs::msg::TransformStamped transform =
        tf_buffer_->lookupTransform(kBaseFrame, kCameraFrame, tf2::TimePointZero);
      tf2::doTransform(camera_pose, base_pose, transform);
      base_pose.header.stamp = stamp;
      base_pose.header.frame_id = kBaseFrame;
    } catch (const tf2::TransformException & ex) {
      RCLCPP_WARN_THROTTLE(
        get_logger(), *get_clock(), 2000, "TF 查询失败：%s", ex.what());
      return;
    }

    pose_pub_->publish(base_pose);

    RCLCPP_INFO_THROTTLE(
      get_logger(), *get_clock(), 1000,
      "目标位姿 base_link：x=%.3f, y=%.3f, z=%.3f",
      base_pose.pose.position.x, base_pose.pose.position.y, base_pose.pose.position.z);
  }

  TargetSpecData spec_;

  cv::VideoCapture cap_;
  //内参和畸变系数
  cv::Mat camera_matrix_ = (cv::Mat_<double>(3, 3) <<
    687.5317091908014, 0.0, 297.1336070206084,
    0.0, 687.3486375867584, 250.4347773180092,
    0.0, 0.0, 1.0);

cv::Mat dist_coeffs_ = (cv::Mat_<double>(1, 5) <<
    -0.4294605200479273, 0.5223008810846906, 0.0008544169944606501, -0.0004179638989459173, -0.9492596199013797);

  rclcpp::Subscription<vision_interfaces::msg::TargetSpec>::SharedPtr spec_sub_;
  rclcpp::Publisher<geometry_msgs::msg::PoseStamped>::SharedPtr pose_pub_;
  rclcpp::TimerBase::SharedPtr timer_;

  std::shared_ptr<tf2_ros::Buffer> tf_buffer_;
  std::shared_ptr<tf2_ros::TransformListener> tf_listener_;
  std::shared_ptr<tf2_ros::TransformBroadcaster> tf_broadcaster_;
  image_transport::Publisher debug_pub_;

  cv::Vec3d last_tvec_{0.0, 0.0, 0.0};
  tf2::Quaternion last_q_;
  rclcpp::Time last_stamp_{0, 0, RCL_ROS_TIME};
  bool has_last_pose_{false};

  std::vector<cv::Point2f> last_corners_;
  bool has_last_corners_{false};
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<VisionDetectorNode>());
  rclcpp::shutdown();
  return 0;
}
