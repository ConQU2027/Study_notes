#include <chrono>
#include <filesystem>
#include <string>
#include <vector>

#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/image.hpp>
#include <std_msgs/msg/header.hpp>

#include <cv_bridge/cv_bridge.h>
#include <opencv2/opencv.hpp>

class ImageSourceNode : public rclcpp::Node
{
public:
  ImageSourceNode() : Node("image_source_node")
  {
    source_type_ = declare_parameter<std::string>("source_type", "camera");
    device_      = declare_parameter<std::string>("device", "/dev/video0");
    image_dir_   = declare_parameter<std::string>("image_dir", "");
    fps_         = declare_parameter<double>("fps", 20.0);

    image_pub_ = create_publisher<sensor_msgs::msg::Image>("image_raw", rclcpp::SensorDataQoS());

    if (source_type_ == "image_dir") {
      loadImageList();
    } else {
      openCamera();
    }

    const auto period = std::chrono::duration<double>(1.0 / std::max(1.0, fps_));
    timer_ = create_wall_timer(period, [this]() { this->onTimer(); });
  }

private:
  void openCamera()
  {
    if (!cap_.open(device_, cv::CAP_V4L2)) {
      return;
    }
  }

  void loadImageList()
  {
    namespace fs = std::filesystem;
    if (image_dir_.empty() || !fs::exists(image_dir_)) {
      return;
    }
    for (const auto & entry : fs::directory_iterator(image_dir_)) {
      if (!entry.is_regular_file()) {continue;}
      const std::string ext = entry.path().extension().string();
      if (ext == ".png" || ext == ".jpg" || ext == ".jpeg" || ext == ".bmp") {
        files_.push_back(entry.path().string());
      }
    }
    std::sort(files_.begin(), files_.end());
  }

  void onTimer()
  {
    cv::Mat frame;

    if (source_type_ == "image_dir") {
      if (files_.empty()) {return;}
      frame = cv::imread(files_[index_ % files_.size()], cv::IMREAD_COLOR);
      index_++;
      if (frame.empty()) {
        return;
      }
    } else {
      if (!cap_.isOpened()) {
        return;
      }
      if (!cap_.read(frame) || frame.empty()) {
        return;
      }
    }

    std_msgs::msg::Header header;
    header.stamp = now();
    image_pub_->publish(*cv_bridge::CvImage(header, "bgr8", frame).toImageMsg());
  }

  std::string source_type_, device_, image_dir_;
  double fps_ = 20.0;

  cv::VideoCapture cap_;
  std::vector<std::string> files_;
  size_t index_ = 0;

  rclcpp::Publisher<sensor_msgs::msg::Image>::SharedPtr image_pub_;
  rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char **argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<ImageSourceNode>());
  rclcpp::shutdown();
  return 0;
}
