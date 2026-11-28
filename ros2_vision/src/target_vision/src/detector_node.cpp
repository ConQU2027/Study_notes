// ============================================================
// detector_node.cpp  （改进版 v2）
// 作用：订阅 /image_raw，检测带缺口的彩色矩形，用 solvePnP 估计位姿，
//       发布 /target_vision/pose、调试图 /target_vision/debug_image、
//       TF camera_optical_frame -> target
//
// 算法链路（全部传统视觉，无神经网络）：
//   BGR -> HSV 颜色分割 -> 形态学开运算 -> 最大轮廓
//   -> approxPolyDP 扫描得到 5 个顶点（多则裁剪）
//   -> cornerSubPix 亚像素精化
//   -> 顶点规范化（定绕向 + 最大内角 = 缺口起点）
//   -> solvePnP(IPPE) + solvePnPRefineLM -> 位姿
//   -> 时序滤波（跳变剔除 + 位置低通 + 四元数 slerp）   <-- v2 新增
//
// v2 相比 v1 的改动（都在文件里标了 v2）：
//   1) 时序平滑：位姿不再逐帧抖动/翻转（任务书③）
//   2) 调试图限频，默认 5Hz，降低 DDS 负载提高帧率（任务书④）
//   3) 目标被画面边缘裁切时给出明确原因
//   4) 畸变系数可配置（dist_coeffs），标定结果可以直接用
// ============================================================
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
    // ---------- 颜色阈值 ----------
    h_min_ = declare_parameter<int>("h_min", 33);
    h_max_ = declare_parameter<int>("h_max", 95);
    s_min_ = declare_parameter<int>("s_min", 90);
    v_min_ = declare_parameter<int>("v_min", 50);

    // ---------- 形态学核大小（3/5/7，0 表示不做）----------
    morph_open_ = declare_parameter<int>("morph_open", 5);

    // ---------- 轮廓过滤 ----------
    min_area_ratio_ = declare_parameter<double>("min_area_ratio", 0.002);

    // ---------- 多边形逼近参数 ----------
    expected_vertices_ = declare_parameter<int>("expected_vertices", 5);
    eps_min_ = declare_parameter<double>("eps_min_ratio", 0.004);
    eps_max_ = declare_parameter<double>("eps_max_ratio", 0.20);
    eps_step_ = declare_parameter<double>("eps_step_ratio", 0.002);

    // ---------- 靶标实际尺寸（毫米，必须与实物量出来的一致）----------
    target_w_ = declare_parameter<double>("target_width_mm", 220.0);
    target_h_ = declare_parameter<double>("target_height_mm", 160.0);
    chamfer_long_ = declare_parameter<double>("chamfer_long_mm", 60.0);
    chamfer_short_ = declare_parameter<double>("chamfer_short_mm", 40.0);

    // ---------- 位姿筛选 ----------
    max_reproj_rms_ = declare_parameter<double>("max_reproj_rms_px", 3.0);

    // ---------- v2: 时序滤波参数 ----------
    // smooth_tau_s：低通时间常数。越小越跟手但越抖；0.08~0.15 比较合适
    smooth_tau_ = declare_parameter<double>("smooth_tau_s", 0.10);
    // 单帧跳变超过这个阈值就当作误检丢弃（防止 180° 翻转和飞到远处的假解）
    max_jump_m_ = declare_parameter<double>("max_jump_m", 0.25);
    max_jump_deg_ = declare_parameter<double>("max_jump_deg", 60.0);
    // 连续被丢弃这么多次后，认为目标真的换了，重置滤波器
    max_reject_streak_ = declare_parameter<int>("max_reject_streak", 8);

    // ---------- 坐标系 ----------
    camera_frame_ = declare_parameter<std::string>("camera_frame", "camera_optical_frame");
    base_frame_ = declare_parameter<std::string>("base_frame", "base_link");
    target_frame_ = declare_parameter<std::string>("target_frame", "target");

    // ---------- 相机内参（标定后填这里）----------
    fx_ = declare_parameter<double>("fx", 550.0);
    fy_ = declare_parameter<double>("fy", 550.0);
    cx_ = declare_parameter<double>("cx", 320.0);
    cy_ = declare_parameter<double>("cy", 240.0);
    // v2: 畸变系数 [k1,k2,p1,p2,k3]，不给就全 0（等价于不处理畸变）
    dist_coeffs_ = declare_parameter<std::vector<double>>(
      "dist_coeffs", std::vector<double>{0.0, 0.0, 0.0, 0.0, 0.0});

    // ---------- 调试图 ----------
    publish_debug_ = declare_parameter<bool>("publish_debug_image", true);
    // v2: 调试图最大发布频率（Hz）
    debug_hz_ = declare_parameter<double>("debug_publish_hz", 5.0);

    updateCameraMatrix();

    // ---------- 靶标模型点（必须与顶点规范化顺序一致）----------
    // 顺序：缺口起点 A -> 右上 -> 右下 -> 左下 -> 缺口另一端 B
    model_3d_.clear();
    model_3d_.emplace_back(static_cast<float>(chamfer_long_), 0.0f, 0.0f);
    model_3d_.emplace_back(static_cast<float>(target_w_), 0.0f, 0.0f);
    model_3d_.emplace_back(static_cast<float>(target_w_), static_cast<float>(target_h_), 0.0f);
    model_3d_.emplace_back(0.0f, static_cast<float>(target_h_), 0.0f);
    model_3d_.emplace_back(0.0f, static_cast<float>(chamfer_short_), 0.0f);

    // ---------- 话题 ----------
    image_sub_ = create_subscription<sensor_msgs::msg::Image>(
      "image_raw", rclcpp::SensorDataQoS(),
      [this](const sensor_msgs::msg::Image::SharedPtr msg) { this->onImage(msg); });

    pose_pub_ = create_publisher<geometry_msgs::msg::PoseStamped>("/target_vision/pose", 10);
    debug_pub_ = create_publisher<sensor_msgs::msg::Image>("/target_vision/debug_image", 10);

    tf_broadcaster_ = std::make_unique<tf2_ros::TransformBroadcaster>(*this);
    tf_buffer_ = std::make_shared<tf2_ros::Buffer>(this->get_clock());
    tf_listener_ = std::make_shared<tf2_ros::TransformListener>(*tf_buffer_);

    RCLCPP_INFO(get_logger(),
                "检测节点就绪(v2): 靶标 %.0fx%.0fmm 切角(%.0f, %.0f)mm, 内参 fx=%.1f fy=%.1f cx=%.1f cy=%.1f",
                target_w_, target_h_, chamfer_long_, chamfer_short_, fx_, fy_, cx_, cy_);
    RCLCPP_INFO(get_logger(),
                "时序滤波: tau=%.2fs 跳变阈值 %.2fm/%.0f° 调试图 %.1fHz",
                smooth_tau_, max_jump_m_, max_jump_deg_, debug_hz_);
  }

private:
  // ------------------- 相机内参矩阵 -------------------
  void updateCameraMatrix()
  {
    K_ = (cv::Mat_<double>(3, 3) << fx_, 0.0, cx_, 0.0, fy_, cy_, 0.0, 0.0, 1.0);
    if (dist_coeffs_.size() >= 5) {
      D_ = (cv::Mat_<double>(1, 5) << dist_coeffs_[0], dist_coeffs_[1], dist_coeffs_[2],
            dist_coeffs_[3], dist_coeffs_[4]);
    } else {
      D_ = cv::Mat::zeros(5, 1, CV_64F);
    }
  }

  // ------------------- 多边形有向面积 -------------------
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

  // ------------------- 某个顶点的内角（度）-------------------
  static double interiorAngleDeg(
    const cv::Point2f & prev, const cv::Point2f & cur, const cv::Point2f & next)
  {
    const cv::Point2f v1 = prev - cur;
    const cv::Point2f v2 = next - cur;
    const double cross = v1.x * v2.y - v1.y * v2.x;
    const double dot = v1.x * v2.x + v1.y * v2.y;
    return std::atan2(std::abs(cross), dot) * 180.0 / CV_PI;
  }

  // ------------------- 顶点规范化 -------------------
  static void canonicalize(std::vector<cv::Point2f> & p)
  {
    if (signedArea(p) < 0) {
      std::reverse(p.begin() + 1, p.end());
    }
    const size_t n = p.size();
    size_t best = 0;
    double best_angle = -1.0;
    for (size_t i = 0; i < n; ++i) {
      const double a =
        interiorAngleDeg(p[(i + n - 1) % n], p[i], p[(i + 1) % n]);
      if (a > best_angle) {
        best_angle = a;
        best = i;
      }
    }
    std::rotate(p.begin(), p.begin() + best, p.end());
  }

  // ------------------- 顶点裁剪 -------------------
  static void pruneToSize(std::vector<cv::Point2f> & p, int target)
  {
    while (static_cast<int>(p.size()) > target) {
      const int n = static_cast<int>(p.size());
      int worst = 0;
      double worst_dev = 1e9;
      for (int i = 0; i < n; ++i) {
        const double a = interiorAngleDeg(p[(i + n - 1) % n], p[i], p[(i + 1) % n]);
        const double dev = std::abs(180.0 - a);
        if (dev < worst_dev) {
          worst_dev = dev;
          worst = i;
        }
      }
      p.erase(p.begin() + worst);
    }
  }

  // ------------------- 检测：颜色分割 + 多边形逼近 -------------------
  bool detect(const cv::Mat & bgr, std::vector<cv::Point2f> & corners, std::string & reason)
  {
    cv::Mat hsv, mask, gray;
    cv::cvtColor(bgr, hsv, cv::COLOR_BGR2HSV);
    cv::cvtColor(bgr, gray, cv::COLOR_BGR2GRAY);
    cv::inRange(hsv,
                cv::Scalar(h_min_, s_min_, v_min_),
                cv::Scalar(h_max_, 255, 255),
                mask);

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

    // 取面积最大的轮廓
    auto biggest = std::max_element(
      contours.begin(), contours.end(),
      [](const std::vector<cv::Point> & a, const std::vector<cv::Point> & b) {
        return cv::contourArea(a) < cv::contourArea(b);
      });

    const double area = cv::contourArea(*biggest);
    const double frame_area = static_cast<double>(bgr.cols) * static_cast<double>(bgr.rows);
    if (area < min_area_ratio_ * frame_area) {
      reason = "目标太小（颜色块面积不足）";
      return false;
    }

    // v2: 目标贴边/出画时轮廓会被画面边界切平，顶点数必然不对
    const cv::Rect br = cv::boundingRect(*biggest);
    if (br.x <= 1 || br.y <= 1 ||
        br.x + br.width >= bgr.cols - 1 || br.y + br.height >= bgr.rows - 1) {
      reason = "目标被画面边缘裁切（请拉远或移正）";
      return false;
    }

    // 收尾：亚像素精化 -> 规范化
    auto finish = [&](std::vector<cv::Point2f> & pts, double eps) {
      try {
        cv::cornerSubPix(
          gray, pts, cv::Size(5, 5), cv::Size(-1, -1),
          cv::TermCriteria(
            cv::TermCriteria::EPS + cv::TermCriteria::COUNT, 20, 0.01));
      } catch (const cv::Exception &) {
      }
      corners = pts;
      canonicalize(corners);
      last_contour_ = *biggest;
      last_epsilon_ = eps;
      return true;
    };

    // 第一遍：找「恰好 expected 个顶点」的最精细逼近
    const double perimeter = cv::arcLength(*biggest, true);
    std::vector<cv::Point> over;
    double over_eps = 0.0;
    for (double eps = eps_min_; eps <= eps_max_; eps += eps_step_) {
      std::vector<cv::Point> approx;
      cv::approxPolyDP(*biggest, approx, perimeter * eps, true);
      const int n = static_cast<int>(approx.size());

      if (n == expected_vertices_) {
        std::vector<cv::Point2f> pts;
        pts.reserve(approx.size());
        for (const auto & p : approx) {
          pts.emplace_back(static_cast<float>(p.x), static_cast<float>(p.y));
        }
        return finish(pts, eps);
      }
      if (n > expected_vertices_ && (over.empty() || n < static_cast<int>(over.size()))) {
        over = approx;
        over_eps = eps;
      }
      if (n < expected_vertices_) {break;}
    }

    // 第二遍（兜底）：把最接近的那次裁剪到 5 个
    if (!over.empty()) {
      std::vector<cv::Point2f> pts;
      pts.reserve(over.size());
      for (const auto & p : over) {
        pts.emplace_back(static_cast<float>(p.x), static_cast<float>(p.y));
      }
      pruneToSize(pts, expected_vertices_);
      return finish(pts, over_eps);
    }

    reason = "多边形顶点数不是 " + std::to_string(expected_vertices_) +
      "（可能是距离、光照或阈值不合适）";
    return false;
  }

  // ------------------- 每帧回调 -------------------
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
      // v2: 丢失超过 1 秒就重置滤波器
      if (has_last_ && (rclcpp::Time(msg->header.stamp) - last_stamp_).seconds() > 1.0) {
        has_last_ = false;
      }
      if (found_) {
        found_ = false;
        RCLCPP_WARN(get_logger(), "目标丢失: %s", reason.c_str());
      }
      return;
    }

    // ---------- 位姿求解：IPPE + LM 精化 ----------
    cv::Mat rvec, tvec;
    if (!cv::solvePnP(model_3d_, corners, K_, D_, rvec, tvec, false, cv::SOLVEPNP_IPPE)) {
      return;
    }
    cv::solvePnPRefineLM(model_3d_, corners, K_, D_, rvec, tvec);

    // ---------- 重投影误差 ----------
    std::vector<cv::Point2f> projected;
    cv::projectPoints(model_3d_, rvec, tvec, K_, D_, projected);
    double sq_sum = 0.0;
    for (size_t i = 0; i < corners.size() && i < projected.size(); ++i) {
      const cv::Point2f d = corners[i] - projected[i];
      sq_sum += d.x * d.x + d.y * d.y;
    }
    const double rms = std::sqrt(sq_sum / static_cast<double>(corners.size()));
    if (rms > max_reproj_rms_) {
      RCLCPP_WARN_THROTTLE(get_logger(), *get_clock(), 2000,
                           "重投影误差太大(%.2fpx)，丢弃该帧", rms);
      return;
    }

    // ---------- 旋转矩阵 -> 四元数 ----------
    cv::Mat R;
    cv::Rodrigues(rvec, R);
    tf2::Matrix3x3 m(
      R.at<double>(0, 0), R.at<double>(0, 1), R.at<double>(0, 2),
      R.at<double>(1, 0), R.at<double>(1, 1), R.at<double>(1, 2),
      R.at<double>(2, 0), R.at<double>(2, 1), R.at<double>(2, 2));
    tf2::Quaternion q_raw;
    m.getRotation(q_raw);

    // ================= v2: 时序滤波 =================
    // 1) 跳变剔除  2) 低通平滑
    // alpha = 1 - exp(-dt/tau) 让平滑程度与帧率无关
    const rclcpp::Time stamp(msg->header.stamp);
    const double dt = has_last_ ? (stamp - last_stamp_).seconds() : 1e9;
    const cv::Vec3d t_raw(tvec.at<double>(0), tvec.at<double>(1), tvec.at<double>(2));

    if (has_last_ && dt < 1.0) {
      const double dpos_m = cv::norm(t_raw - last_t_) / 1000.0;
      const double dang_deg =
        std::abs(q_raw.angleShortestPath(last_q_)) * 180.0 / CV_PI;

      if (dpos_m > max_jump_m_ || dang_deg > max_jump_deg_) {
        if (++reject_streak_ < max_reject_streak_) {
          RCLCPP_WARN_THROTTLE(get_logger(), *get_clock(), 1000,
                               "位姿跳变过大(%.2fm / %.0f°)，丢弃该帧", dpos_m, dang_deg);
          return;
        }
        RCLCPP_WARN(get_logger(), "连续跳变，重置滤波器重新捕获目标");
        has_last_ = false;
      }
      reject_streak_ = 0;
    }

    cv::Vec3d t_f = t_raw;
    tf2::Quaternion q_f = q_raw;
    if (has_last_ && dt < 1.0) {
      const double alpha = 1.0 - std::exp(-dt / std::max(1e-3, smooth_tau_));
      t_f = t_raw * alpha + last_t_ * (1.0 - alpha);
      q_f = last_q_.slerp(q_raw, alpha);
      q_f.normalize();
    }
    last_t_ = t_f;
    last_q_ = q_f;
    last_stamp_ = stamp;
    has_last_ = true;
    // ================= v2 时序滤波结束 =================

    // ---------- 组装位姿（用平滑后的值）----------
    geometry_msgs::msg::PoseStamped pose_cam;
    pose_cam.header.stamp = msg->header.stamp;
    pose_cam.header.frame_id = camera_frame_;
    pose_cam.pose.position.x = t_f[0] / 1000.0;
    pose_cam.pose.position.y = t_f[1] / 1000.0;
    pose_cam.pose.position.z = t_f[2] / 1000.0;
    pose_cam.pose.orientation = tf2::toMsg(q_f);

    // ---------- 发布位姿：换算到 base_link ----------
    geometry_msgs::msg::PoseStamped pose_out = pose_cam;
    if (base_frame_ != camera_frame_) {
      try {
        pose_out = tf_buffer_->transform(pose_cam, base_frame_, tf2::durationFromSec(0.1));
      } catch (const tf2::TransformException & ex) {
        RCLCPP_WARN_THROTTLE(get_logger(), *get_clock(), 5000,
                             "没有 base_link<-camera 的 TF，先发相机系位姿: %s", ex.what());
      }
    }
    pose_pub_->publish(pose_out);

    // ---------- 发布 TF ----------
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

    // ---------- v2: 调试图（限频发布）----------
    if (publish_debug_) {
      const rclcpp::Time now_t = this->now();
      const double period = 1.0 / std::max(0.5, debug_hz_);
      if (debug_stamp_.nanoseconds() == 0 || (now_t - debug_stamp_).seconds() >= period) {
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

        // 坐标轴：红=X 绿=Y 蓝=Z（50mm，用原始解投影）
        const std::vector<cv::Point3f> axes{
          {0.0f, 0.0f, 0.0f},
          {50.0f, 0.0f, 0.0f},
          {0.0f, 50.0f, 0.0f},
          {0.0f, 0.0f, 50.0f}};
        std::vector<cv::Point2f> axes_2d;
        cv::projectPoints(axes, rvec, tvec, K_, D_, axes_2d);
        if (axes_2d.size() == 4) {
          cv::line(dbg, axes_2d[0], axes_2d[1], cv::Scalar(0, 0, 255), 2);
          cv::line(dbg, axes_2d[0], axes_2d[2], cv::Scalar(0, 255, 0), 2);
          cv::line(dbg, axes_2d[0], axes_2d[3], cv::Scalar(255, 0, 0), 2);
        }

        char text[160];
        std::snprintf(text, sizeof(text), "TRACKING z=%.2fm rms=%.2fpx",
                      pose_cam.pose.position.z, rms);
        cv::putText(dbg, text, cv::Point(8, 24), cv::FONT_HERSHEY_SIMPLEX, 0.6,
                    cv::Scalar(0, 255, 0), 2);

        debug_pub_->publish(*cv_bridge::CvImage(msg->header, "bgr8", dbg).toImageMsg());
        debug_stamp_ = now_t;
      }
    }
  }

  // ---------- 参数 ----------
  int h_min_ = 33, h_max_ = 95, s_min_ = 90, v_min_ = 50;
  int morph_open_ = 5;
  int expected_vertices_ = 5;
  double min_area_ratio_ = 0.002;
  double eps_min_ = 0.004, eps_max_ = 0.20, eps_step_ = 0.002;
  double target_w_ = 220.0, target_h_ = 160.0;
  double chamfer_long_ = 60.0, chamfer_short_ = 40.0;
  double max_reproj_rms_ = 3.0;
  double fx_ = 550.0, fy_ = 550.0, cx_ = 320.0, cy_ = 240.0;
  std::vector<double> dist_coeffs_{0.0, 0.0, 0.0, 0.0, 0.0};
  bool publish_debug_ = true;
  // v2 参数
  double smooth_tau_ = 0.10;
  double max_jump_m_ = 0.25;
  double max_jump_deg_ = 60.0;
  int max_reject_streak_ = 8;
  double debug_hz_ = 5.0;
  std::string camera_frame_, base_frame_, target_frame_;

  // ---------- 数据 ----------
  cv::Mat K_, D_;
  std::vector<cv::Point3f> model_3d_;
  std::vector<cv::Point> last_contour_;
  double last_epsilon_ = 0.0;
  bool found_ = false;

  // v2: 时序滤波状态
  bool has_last_ = false;
  cv::Vec3d last_t_{0.0, 0.0, 0.0};
  tf2::Quaternion last_q_;
  rclcpp::Time last_stamp_{0, 0, RCL_ROS_TIME};
  int reject_streak_ = 0;
  rclcpp::Time debug_stamp_{0, 0, RCL_ROS_TIME};

  // ---------- ROS ----------
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
