#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/image.hpp>
#include <sensor_msgs/msg/compressed_image.hpp>
#include <sensor_msgs/msg/camera_info.hpp>
#include <geometry_msgs/msg/pose_stamped.hpp>
#include <cv_bridge/cv_bridge.h>
#include <opencv2/opencv.hpp>

#include <tf2/LinearMath/Matrix3x3.h>
#include <tf2/LinearMath/Quaternion.h>

#include <algorithm>
#include <chrono>
#include <cstdio>

#include "vision_core/square_detector.hpp"

// 不要写 using namespace rclcpp; 避免和 cv::Node 冲突！
using namespace cv;
using namespace std;

const double AXIS_LEN = 0.04;  // 坐标轴绘制长度(米)

// ============================================================
// ROS 节点：只负责"收图像 → 交给算法库 → 发布结果"，
// 检测和跟随逻辑全在 vision_core 包里，两边互不干扰。
// ============================================================
class SquareDetectorNode : public rclcpp::Node
{
public:
    SquareDetectorNode() : rclcpp::Node("square_detector_node")
    {
        // ---- 检测参数：全部可以由 launch 覆盖，现场调参不用重编译 ----
        vision_core::Params p;
        p.white_min = declare_parameter("white_min", p.white_min);
        p.white_max = declare_parameter("white_max", p.white_max);
        p.sat_max = declare_parameter("sat_max", p.sat_max);
        p.min_area = declare_parameter("min_area", p.min_area);
        p.max_reproj = declare_parameter("max_reproj", p.max_reproj);
        p.max_track_dist = declare_parameter("max_track_dist", p.max_track_dist);
        p.min_cutoff = declare_parameter("smooth_min_cutoff", p.min_cutoff);
        p.beta = declare_parameter("smooth_beta", p.beta);
        detector_ = vision_core::SquareDetector(p);

        // 调试图每 debug_every 帧发一次：640x480 原图 900KB，20Hz 就是 18MB/s，会吃满 DDS
        debug_every_ = std::max(1, static_cast<int>(declare_parameter("debug_every", 2)));

        // 标定兜底：camera_info 没到时用近似内参先跑，调试图标 NO CALIB，不会静默不动
        K_ = (Mat_<double>(3, 3) << 444.82, 0.0, 294.51, 0.0, 446.20, 244.07, 0.0, 0.0, 1.0);
        D_ = Mat::zeros(1, 5, CV_64F);

        // 深度 3：留一点缓冲吸收偶发抖动。reliable 保证不丢帧——
        // 位姿稳定比低延迟更重要，代价是最多几帧(百毫秒级)的延迟。
        auto qos = rclcpp::QoS(3).reliable();

        img_sub_ = create_subscription<sensor_msgs::msg::Image>(
            "/camera/image_raw", qos,
            std::bind(&SquareDetectorNode::imageCallback, this, std::placeholders::_1));
        info_sub_ = create_subscription<sensor_msgs::msg::CameraInfo>(
            "/camera/camera_info", qos,
            std::bind(&SquareDetectorNode::infoCallback, this, std::placeholders::_1));

        pose_pub_ = create_publisher<geometry_msgs::msg::PoseStamped>("/target_pose_camera", 10);
        debug_pub_ = create_publisher<sensor_msgs::msg::Image>("/debug_image", 10);
        // JPEG 压缩调试图：一张 60KB，比原始图小 15 倍，才能和 20Hz 共存
        comp_pub_ = create_publisher<sensor_msgs::msg::CompressedImage>(
            "/debug_image/compressed", 10);

        RCLCPP_INFO(get_logger(), "square_detector_node start (white_min=%d min_area=%.0f)",
                    p.white_min, p.min_area);
    }

private:
    rclcpp::Subscription<sensor_msgs::msg::Image>::SharedPtr img_sub_;
    rclcpp::Subscription<sensor_msgs::msg::CameraInfo>::SharedPtr info_sub_;
    rclcpp::Publisher<geometry_msgs::msg::PoseStamped>::SharedPtr pose_pub_;
    rclcpp::Publisher<sensor_msgs::msg::Image>::SharedPtr debug_pub_;
    rclcpp::Publisher<sensor_msgs::msg::CompressedImage>::SharedPtr comp_pub_;

    vision_core::SquareDetector detector_;  // 算法库，跟随/滤波状态都存在它里面

    Mat K_;
    Mat D_;
    bool have_calib_ = false;

    rclcpp::Time last_stamp_;
    bool have_last_stamp_ = false;
    double in_hz_ = 0.0;     // 输入帧率(相机给多快)
    double proc_ms_ = 0.0;   // 整条回调耗时(解码+检测+发布)，20fps 要求 < 50ms
    double last_wall_ = 0.0; // 上一次处理的系统时间(秒)
    double win_t0_ = 0.0;    // 帧率统计窗口起点
    int win_cnt_ = 0;        // 窗口内帧数
    int frame_cnt_ = 0;      // 处理帧计数，每 100 帧打一条日志
    int debug_every_ = 2;    // 调试图隔帧发布

    void infoCallback(const sensor_msgs::msg::CameraInfo::SharedPtr msg)
    {
        // 没标定时 d 是空的，直接拿去构造 Mat 会指针越界崩溃，先拦一下
        if (msg->d.size() < 4) {
            RCLCPP_WARN(get_logger(), "camera_info.d is empty, please load a calibration file"); return;
        }
        K_ = (Mat_<double>(3, 3) << msg->k[0], msg->k[1], msg->k[2], msg->k[3], msg->k[4], msg->k[5], msg->k[6], msg->k[7], msg->k[8]);
        // 畸变系数个数不一定刚好 5 个，按实际长度拷
        D_ = Mat(1, static_cast<int>(msg->d.size()), CV_64F);
        for (size_t i = 0; i < msg->d.size(); ++i) {
            D_.at<double>(static_cast<int>(i)) = msg->d[i];
        }
        if (!have_calib_) {
            RCLCPP_INFO(get_logger(), "camera_info loaded: fx=%.2f fy=%.2f", msg->k[0], msg->k[4]);
        }
        have_calib_ = true;
    }

    // 把检测结果画到调试图上：绿框、蓝色角点、坐标轴、黄色中心点
    void drawResult(Mat &img, const vision_core::Result &r)
    {
        if (r.found && r.quad.size() == 4) {
            vector<Point> poly;
            for (auto &p : r.quad) poly.emplace_back((int)p.x, (int)p.y);
            drawContours(img, vector<vector<Point>>{poly}, -1, Scalar(0,255,0), 2);
            for (auto &p : r.quad) circle(img, p, 4, Scalar(255,0,0), -1);
            drawFrameAxes(img, K_, D_, r.rvec, r.tvec, AXIS_LEN);
            circle(img, r.center, 4, Scalar(0,255,255), -1);
        }
        // TRACK=正在跟随同一个目标，SEARCH=还没锁定；cand=候选数，thr=本帧白度阈值，
        // in=输入帧率，ms=整条回调耗时(20fps 要求 < 50ms)
        char buf[160];
        snprintf(buf, sizeof(buf), "%s cand=%d thr=%d in=%.1fHz %.1fms %s",
                 r.tracking ? "TRACK" : "SEARCH", r.candidates, detector_.whiteThr(),
                 in_hz_, proc_ms_, have_calib_ ? "" : "NO CALIB");
        putText(img, buf, Point(10, 30), FONT_HERSHEY_SIMPLEX, 0.6, Scalar(0,255,255), 2);
        // 没框出来时看这两行：white=白色占比(≈0=阈值太高/画面全黑)，maxA=最大白块面积，
        // rej 是各道门槛各挡掉几个(面积够大却没框 = 形状门槛挡的)
        const auto & dg = detector_.diag();
        snprintf(buf, sizeof(buf), "white=%.1f%% cnt=%d maxA=%d e=%d", dg.white_ratio * 100.0, dg.contours, dg.max_cnt_area, dg.rej_edge);
        putText(img, buf, Point(10, 56), FONT_HERSHEY_SIMPLEX, 0.4, Scalar(0, 255, 0), 1);
        snprintf(buf, sizeof(buf), "rej a=%d q=%d r=%d c=%d p=%d z=%d rp=%d", dg.rej_area, dg.rej_approx + dg.rej_convex,
                 dg.rej_ratio, dg.rej_corner, dg.rej_pnp, dg.rej_z, dg.rej_reproj);
        putText(img, buf, Point(10, 78), FONT_HERSHEY_SIMPLEX, 0.4, Scalar(0, 255, 0), 1);
        // 一个候选都没有、而白色轮廓又贴在画面边缘：目标被切掉了(太近/没拍全)，退远就能框住
        if (r.candidates == 0 && dg.rej_edge > 0) {
            putText(img, "TARGET CUT BY FRAME - MOVE BACK", Point(10, 112), FONT_HERSHEY_SIMPLEX, 0.6, Scalar(0, 0, 255), 2);
        }
    }

    void imageCallback(const sensor_msgs::msg::Image::SharedPtr img_msg)
    {
        auto t_beg = std::chrono::steady_clock::now();

        // 用图像时间戳算帧间隔，One Euro 靠它判断"动得快不快"
        rclcpp::Time stamp(img_msg->header.stamp);
        double dt = 1.0 / 20.0;
        if (have_last_stamp_) {
            dt = (stamp - last_stamp_).seconds();
        }
        if (dt <= 0.0 || dt > 1.0) dt = 1.0 / 20.0;  // 时间戳乱跳时兜底
        last_stamp_ = stamp;
        have_last_stamp_ = true;

        // 输入帧率：按整秒统计帧数，比"帧间时间取倒数"稳，也不会被单次卡顿带偏
        double now_s = this->now().seconds();
        if (win_t0_ <= 0.0) {win_t0_ = now_s;}
        ++win_cnt_;
        if (now_s - win_t0_ >= 1.0) {
            in_hz_ = win_cnt_ / (now_s - win_t0_);
            win_cnt_ = 0;
            win_t0_ = now_s;
        }
        last_wall_ = now_s;

        cv_bridge::CvImagePtr cv_ptr;
        try {
            cv_ptr = cv_bridge::toCvCopy(img_msg, sensor_msgs::image_encodings::BGR8);
        } catch (cv_bridge::Exception &e) {
            RCLCPP_ERROR(get_logger(), "cv_bridge err: %s", e.what());
            return;
        }

        // 一行拿到检测+跟随结果，节点本身不需要知道内部怎么实现的
        vision_core::Result res = detector_.detect(cv_ptr->image, K_, D_, dt);
        ++frame_cnt_;

        // 调试图：JPEG 版小 15 倍，和 20Hz 共存；原始图留给调参看细节。都按 debug_every 隔帧发，
        // 因为发布动作本身会抢接收线程，20Hz 全速发会把输入帧率从 20Hz 削到 12Hz。
        if (frame_cnt_ % debug_every_ == 0) {
            Mat debug_img = cv_ptr->image.clone();
            drawResult(debug_img, res);

            std::vector<uchar> jpg;
            cv::imencode(".jpg", debug_img, jpg, std::vector<int>{cv::IMWRITE_JPEG_QUALITY, 75});
            sensor_msgs::msg::CompressedImage cmsg;
            cmsg.header = img_msg->header;
            cmsg.format = "jpeg";
            cmsg.data = jpg;
            comp_pub_->publish(cmsg);

            cv_bridge::CvImage debug_msg;
            debug_msg.header = img_msg->header;
            debug_msg.encoding = sensor_msgs::image_encodings::BGR8;
            debug_msg.image = debug_img;
            debug_pub_->publish(*debug_msg.toImageMsg());
        }

        // 整条回调的总耗时：解码 + 检测 + 画图 + 发布，这才是能不能跑 20fps 的判据
        double proc = std::chrono::duration<double, std::milli>(
            std::chrono::steady_clock::now() - t_beg).count();
        proc_ms_ = 0.9 * proc_ms_ + 0.1 * proc;
        // 每 50 帧(约 2.5 秒)打一条，终端里就能判断 cand=0 是阈值、形状还是位姿挡的
        if (frame_cnt_ % 50 == 0) {
            const auto & g = detector_.diag();
            RCLCPP_INFO(get_logger(), "in=%.1fHz proc=%.1fms cand=%d thr=%d white=%.1f%% maxA=%d "
                        "rej[a%d q%d r%d c%d p%d z%d rp%d]", in_hz_, proc_ms_, res.candidates,
                        detector_.whiteThr(), g.white_ratio * 100.0, g.max_cnt_area, g.rej_area,
                        g.rej_approx + g.rej_convex, g.rej_ratio, g.rej_corner, g.rej_pnp, g.rej_z, g.rej_reproj);
        }

        if (!res.found) return;  // 这帧没锁定目标，位姿不发布

        // 构造 PoseStamped
        geometry_msgs::msg::PoseStamped pose_stamped;
        pose_stamped.header = img_msg->header;  // 时间戳、frame_id 和相机一致
        pose_stamped.pose.position.x = res.tvec.at<double>(0);
        pose_stamped.pose.position.y = res.tvec.at<double>(1);
        pose_stamped.pose.position.z = res.tvec.at<double>(2);

        // 旋转向量 → 四元数
        Mat R;
        Rodrigues(res.rvec, R);
        tf2::Matrix3x3 rot_mat(
            R.at<double>(0,0), R.at<double>(0,1), R.at<double>(0,2),
            R.at<double>(1,0), R.at<double>(1,1), R.at<double>(1,2),
            R.at<double>(2,0), R.at<double>(2,1), R.at<double>(2,2));
        tf2::Quaternion q;
        rot_mat.getRotation(q);
        pose_stamped.pose.orientation.x = q.x();
        pose_stamped.pose.orientation.y = q.y();
        pose_stamped.pose.orientation.z = q.z();
        pose_stamped.pose.orientation.w = q.w();

        pose_pub_->publish(pose_stamped);
    }
};

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<SquareDetectorNode>());
    rclcpp::shutdown();
    return 0;
}
