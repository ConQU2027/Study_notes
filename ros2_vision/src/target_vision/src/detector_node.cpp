#include <algorithm>
#include <cmath>
#include <cstdio>
#include <memory>
#include <string>
#include <vector>

#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/image.hpp>
#include <geometry_msgs/msg/pose_stamped.hpp>
#include <geometry_msgs/msg/transform_stamped.hpp>

#include <cv_bridge/cv_bridge.h>
#include <opencv2/opencv.hpp>

#include <tf2/LinearMath/Matrix3x3.h>
#include <tf2/LinearMath/Quaternion.h>
#include <tf2_geometry_msgs/tf2_geometry_msgs.hpp>
#include <tf2_ros/buffer.h>
#include <tf2_ros/transform_broadcaster.h>
#include <tf2_ros/transform_listener.h>

class DetectorNode : public rclcpp::Node
{
public:
  DetectorNode() : Node("detector_node")
  {
    h_min_ = declare_parameter<int>("h_min", 33);
    h_max_ = declare_parameter<int>("h_max", 95);
    s_min_ = declare_parameter<int>("s_min", 90);
    v_min_ = declare_parameter<int>("v_min", 50);
    morph_open_ = declare_parameter<int>("morph_open", 5);
    min_area_ratio_ = declare_parameter<double>("min_area_ratio", 0.002);
    expected_vertices_ = declare_parameter<int>("expected_vertices", 5);
    eps_min_ = declare_parameter<double>("eps_min_ratio", 0.004);
    eps_max_ = declare_parameter<double>("eps_max_ratio", 0.20);
    eps_step_ = declare_parameter<double>("eps_step_ratio", 0.002);
    target_w_ = declare_parameter<double>("target_width_mm", 220.0);
    target_h_ = declare_parameter<double>("target_height_mm", 160.0);
    chamfer_long_ = declare_parameter<double>("chamfer_long_mm", 60.0);
    chamfer_short_ = declare_parameter<double>("chamfer_short_mm", 40.0);
    max_reproj_rms_ = declare_parameter<double>("max_reproj_rms_px", 3.0);
    camera_frame_ = declare_parameter<std::string>("camera_frame", "camera_optical_frame");
    base_frame_ = declare_parameter<std::string>("base_frame", "base_link");
    target_frame_ = declare_parameter<std::string>("target_frame", "target");
    fx_ = declare_parameter<double>("fx", 550.0);
    fy_ = declare_parameter<double>("fy", 550.0);
    cx_ = declare_parameter<double>("cx", 320.0);
    cy_ = declare_parameter<double>("cy", 240.0);
    publish_debug_ = declare_parameter<bool>("publish_debug_image", true);

    updateCameraMatrix();

    model_3d_.clear();
    model_3d_.emplace_back(static_cast<float>(chamfer_long_), 0.0f, 0.0f);
    model_3d_.emplace_back(static_cast<float>(target_w_), 0.0f, 0.0f);
    model_3d_.emplace_back(static_cast<float>(target_w_), static_cast<float>(target_h_), 0.0f);
    model_3d_.emplace_back(0.0f, static_cast<float>(target_h_), 0.0f);
    model_3d_.emplace_back(0.0f, static_cast<float>(chamfer_short_), 0.0f);

    image_sub_ = create_subscription<sensor_msgs::msg::Image>(
      "image_raw", rclcpp::SensorDataQoS(),
      [this](const sensor_msgs::msg::Image::SharedPtr msg) { this->onImage(msg); });

    pose_pub_ = create_publisher<geometry_msgs::msg::PoseStamped>("/target_vision/pose", 10);
    debug_pub_ = create_publisher<sensor_msgs::msg::Image>("/target_vision/debug_image", 10);

    tf_broadcaster_ = std::make_unique<tf2_ros::TransformBroadcaster>(*this);
    tf_buffer_ = std::make_shared<tf2_ros::Buffer>(this->get_clock());
    tf_listener_ = std::make_shared<tf2_ros::TransformListener>(*tf_buffer_);

    RCLCPP_INFO(get_logger(),
                "检测节点就绪: 靶标 %.0fx%.0fmm 切角(%.0f,%.0f)mm 内参 fx=%.1f fy=%.1f cx=%.1f cy=%.1f",
                target_w_, target_h_, chamfer_long_, chamfer_short_, fx_, fy_, cx_, cy_);
  }

private:
  void updateCameraMatrix()
  {
    K_ = (cv::Mat_<double>(3, 3) << fx_, 0.0, cx_, 0.0, fy_, cy_, 0.0, 0.0, 1.0);
    D_ = cv::Mat::zeros(5, 1, CV_64F);
  }

  static double signedArea(const std::vector<cv::Point2f> & p)
  {
    double s = 0.0;
    const size_t n = p.size();
    for (size_t i = 0; i < n; ++i) {
      const cv::Point2f & a = p[i];
      const cv::Point2f & b = p[(i + 1) % n];
      s += a.x * b.y - b.x * a.y;
    }
    return 0.5 * s;
  }

  static double interiorAngleDeg(
    const cv::Point2f & prev, const cv::Point2f & cur, const cv::Point2f & next)
  {
    const cv::Point2f v1 = prev - cur;
    const cv::Point2f v2 = next - cur;
    const double cross = v1.x * v2.y - v1.y * v2.x;
    const double dot = v1.x * v2.x + v1.y * v2.y;
    return std::atan2(std::abs(cross), dot) * 180.0 / CV_PI;
  }

  static void canonicalize(std::vector<cv::Point2f> & p)
  {
    if (signedArea(p) < 0) {
      std::reverse(p.begin() + 1, p.end());
    }
    const size_t n = p.size();
    size_t best = 0;
    double best_angle = -1.0;
    for (size_t i = 0; i < n; ++i) {
      const double a = interiorAngleDeg(p[(i + n - 1) % n], p[i], p[(i + 1) % n]);
      if (a > best_angle) {
        best_angle = a;
        best = i;
      }
    }
    std::rotate(p.begin(), p.begin() + best, p.end());
  }

  bool detect(const cv::Mat & bgr, std::vector<cv::Point2f> & corners, std::string & reason)
  {
    cv::Mat hsv, mask;
    cv::cvtColor(bgr, hsv, cv::COLOR_BGR2HSV);
    cv::inRange(hsv, cv::Scalar(h_min_, s_min_, v_min_), cv::Scalar(h_max_, 255, 255), mask);

    if (morph_open_ >= 3) {
      const cv::Mat kernel = cv::getStructuringElement(
        cv::MORPH_ELLIPSE, cv::Size(morph_open_, morph_open_));
      cv::morphologyEx(mask, mask, cv::MORPH_OPEN, kernel);
    }

    std::vector<std::vector<cv::Point>> contours;
    cv::findContours(mask, contours, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_SIMPLE);
    if (contours.empty()) {
      reason = "没有找到目标颜色";
      return false;
    }

    auto biggest = std::max_element(
      contours.begin(), contours.end(),
      [](const std::vector<cv::Point> & a, const std::vector<cv::Point> & b) {
        return cv::contourArea(a) < cv::contourArea(b);
      });

    const double area = cv::contourArea(*biggest);
    const double frame_area = static_cast<double>(bgr.cols) * static_cast<double>(bgr.rows);
    if (area < min_area_ratio_ * frame_area) {
      reason = "目标太小";
      return false;
    }

    const double perimeter = cv::arcLength(*biggest, true);
    for (double eps = eps_min_; eps <= eps_max_; eps += eps_step_) {
      std::vector<cv::Point> approx;
      cv::approxPolyDP(*biggest, approx, perimeter * eps, true);
      if (static_cast<int>(approx.size()) != expected_vertices_) {continue;}

      corners.clear();
      corners.reserve(approx.size());
      for (const auto & p : approx) {
        corners.emplace_back(static_cast<float>(p.x), static_cast<float>(p.y));
      }
      canonicalize(corners);
      last_contour_ = *biggest;
      return true;
    }

    reason = "多边形顶点数不是 " + std::to_string(expected_vertices_);
    return false;
  }

  void onImage(const sensor_msgs::msg::Image::SharedPtr msg)
  {
    cv_bridge::CvImageConstPtr cv_ptr;
    try {
      cv_ptr = cv_bridge::toCvShare(msg, "bgr8");
    } catch (const cv_bridge::Exception & e) {
      RCLCPP_ERROR(get_logger(), "cv_bridge 转换失败: %s", e.what());
      return;
    }
    const cv::Mat & bgr = cv_ptr->image;

    std::vector<cv::Point2f> corners;
    std::string reason;
    if (!detect(bgr, corners, reason)) {
      if (found_) {
        found_ = false;
        RCLCPP_WARN(get_logger(), "目标丢失: %s", reason.c_str());
      }
      return;
    }

    cv::Mat rvec, tvec;
    if (!cv::solvePnP(model_3d_, corners, K_, D_, rvec, tvec, false, cv::SOLVEPNP_IPPE)) {
      return;
    }
    cv::solvePnPRefineLM(model_3d_, corners, K_, D_, rvec, tvec);

    std::vector<cv::Point2f> projected;
    cv::projectPoints(model_3d_, rvec, tvec, K_, D_, projected);
    double sq_sum = 0.0;
    for (size_t i = 0; i < corners.size() && i < projected.size(); ++i) {
      const cv::Point2f d = corners[i] - projected[i];
      sq_sum += d.x * d.x + d.y * d.y;
    }
    const double rms = std::sqrt(sq_sum / static_cast<double>(corners.size()));
    if (rms > max_reproj_rms_) {
      RCLCPP_WARN_THROTTLE(get_logger(), *get_clock(), 2000, "重投影误差太大(%.2fpx)", rms);
      return;
    }

    cv::Mat R;
    cv::Rodrigues(rvec, R);
    tf2::Matrix3x3 m(
      R.at<double>(0, 0), R.at<double>(0, 1), R.at<double>(0, 2),
      R.at<double>(1, 0), R.at<double>(1, 1), R.at<double>(1, 2),
      R.at<double>(2, 0), R.at<double>(2, 1), R.at<double>(2, 2));
    tf2::Quaternion q;
    m.getRotation(q);

    geometry_msgs::msg::PoseStamped pose_cam;
    pose_cam.header.stamp = msg->header.stamp;
    pose_cam.header.frame_id = camera_frame_;
    pose_cam.pose.position.x = tvec.at<double>(0) / 1000.0;
    pose_cam.pose.position.y = tvec.at<double>(1) / 1000.0;
    pose_cam.pose.position.z = tvec.at<double>(2) / 1000.0;
    pose_cam.pose.orientation = tf2::toMsg(q);

    geometry_msgs::msg::PoseStamped pose_out = pose_cam;
    if (base_frame_ != camera_frame_) {
      try {
        pose_out = tf_buffer_->transform(pose_cam, base_frame_, tf2::durationFromSec(0.1));
      } catch (const tf2::TransformException & ex) {
        RCLCPP_WARN_THROTTLE(get_logger(), *get_clock(), 5000,
                             "没有 base_link<-camera 的 TF: %s", ex.what());
      }
    }
    pose_pub_->publish(pose_out);

    geometry_msgs::msg::TransformStamped ts;
    ts.header.stamp = msg->header.stamp;
    ts.header.frame_id = camera_frame_;
    ts.child_frame_id = target_frame_;
    ts.transform.translation.x = pose_cam.pose.position.x;
    ts.transform.translation.y = pose_cam.pose.position.y;
    ts.transform.translation.z = pose_cam.pose.position.z;
    ts.transform.rotation = pose_cam.pose.orientation;
    tf_broadcaster_->sendTransform(ts);

    if (!found_) {
      found_ = true;
      RCLCPP_INFO(get_logger(), "目标已锁定: 距离 %.2f m, 重投影 %.2f px",
                  pose_cam.pose.position.z, rms);
    }

    if (publish_debug_) {
      cv::Mat dbg = bgr.clone();
      std::vector<std::vector<cv::Point>> contour_list{last_contour_};
      cv::drawContours(dbg, contour_list, -1, cv::Scalar(255, 0, 255), 2);

      for (size_t i = 0; i < corners.size(); ++i) {
        const cv::Point pt(cvRound(corners[i].x), cvRound(corners[i].y));
        const cv::Scalar color = (i == 0) ? cv::Scalar(0, 0, 255) : cv::Scalar(0, 165, 255);
        cv::circle(dbg, pt, 4, color, -1);
        cv::putText(dbg, std::to_string(i), pt + cv::Point(6, -4),
                    cv::FONT_HERSHEY_SIMPLEX, 0.5, cv::Scalar(0, 255, 0), 1);
      }

      const std::vector<cv::Point3f> axes{
        {0.0f, 0.0f, 0.0f}, {50.0f, 0.0f, 0.0f},
        {0.0f, 50.0f, 0.0f}, {0.0f, 0.0f, 50.0f}};
      std::vector<cv::Point2f> axes_2d;
      cv::projectPoints(axes, rvec, tvec, K_, D_, axes_2d);
      if (axes_2d.size() == 4) {
        cv::line(dbg, axes_2d[0], axes_2d[1], cv::Scalar(0, 0, 255), 2);
        cv::line(dbg, axes_2d[0], axes_2d[2], cv::Scalar(0, 255, 0), 2);
        cv::line(dbg, axes_2d[0], axes_2d[3], cv::Scalar(255, 0, 0), 2);
      }

      char text[128];
      std::snprintf(text, sizeof(text), "TRACKING  z=%.2fm  rms=%.2fpx",
                    pose_cam.pose.position.z, rms);
      cv::putText(dbg, text, cv::Point(8, 24), cv::FONT_HERSHEY_SIMPLEX, 0.6,
                  cv::Scalar(0, 255, 0), 2);

      debug_pub_->publish(*cv_bridge::CvImage(msg->header, "bgr8", dbg).toImageMsg());
    }
  }

  int h_min_ = 33, h_max_ = 95, s_min_ = 90, v_min_ = 50;
  int morph_open_ = 5;
  int expected_vertices_ = 5;
  double min_area_ratio_ = 0.002;
  double eps_min_ = 0.004, eps_max_ = 0.20, eps_step_ = 0.002;
  double target_w_ = 220.0, target_h_ = 160.0;
  double chamfer_long_ = 60.0, chamfer_short_ = 40.0;
  double max_reproj_rms_ = 3.0;
  double fx_ = 550.0, fy_ = 550.0, cx_ = 320.0, cy_ = 240.0;
  bool publish_debug_ = true;
  std::string camera_frame_, base_frame_, target_frame_;

  cv::Mat K_, D_;
  std::vector<cv::Point3f> model_3d_;
  std::vector<cv::Point> last_contour_;
  bool found_ = false;

  rclcpp::Subscription<sensor_msgs::msg::Image>::SharedPtr image_sub_;
  rclcpp::Publisher<geometry_msgs::msg::PoseStamped>::SharedPtr pose_pub_;
  rclcpp::Publisher<sensor_msgs::msg::Image>::SharedPtr debug_pub_;
  std::unique_ptr<tf2_ros::TransformBroadcaster> tf_broadcaster_;
  std::shared_ptr<tf2_ros::Buffer> tf_buffer_;
  std::shared_ptr<tf2_ros::TransformListener> tf_listener_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<DetectorNode>());
  rclcpp::shutdown();
  return 0;
}
