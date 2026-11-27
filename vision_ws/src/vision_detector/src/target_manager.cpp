#include <rclcpp/rclcpp.hpp>

#include <geometry_msgs/msg/pose_stamped.hpp>
#include <vision_interfaces/msg/target_spec.hpp>

#include <chrono>
#include <functional>

class TargetManager : public rclcpp::Node
{
public:
  TargetManager() : Node("target_manager")
  {
    // 宽、高和 HSV 范围。
    declare_parameter<double>("width", 0.07);
    declare_parameter<double>("height", 0.05);
    declare_parameter<int>("h_min", 0);
    declare_parameter<int>("h_max", 10);
    declare_parameter<int>("s_min", 90);
    declare_parameter<int>("s_max", 255);
    declare_parameter<int>("v_min", 50);
    declare_parameter<int>("v_max", 255);

    spec_pub_ = create_publisher<vision_interfaces::msg::TargetSpec>("/target_spec", 10);
    pose_sub_ = create_subscription<geometry_msgs::msg::PoseStamped>(
      "/target_pose", 10,
      std::bind(&TargetManager::poseCallback, this, std::placeholders::_1));

    timer_ = create_wall_timer(std::chrono::milliseconds(1000),std::bind(&TargetManager::publishSpec, this));

    RCLCPP_INFO(get_logger(), "目标参数节点已启动");
  }

private:
  void publishSpec()
  {
    vision_interfaces::msg::TargetSpec msg;
    msg.header.stamp = now();
    msg.width = get_parameter("width").as_double();
    msg.height = get_parameter("height").as_double();
    msg.h_min = get_parameter("h_min").as_int();
    msg.h_max = get_parameter("h_max").as_int();
    msg.s_min = get_parameter("s_min").as_int();
    msg.s_max = get_parameter("s_max").as_int();
    msg.v_min = get_parameter("v_min").as_int();
    msg.v_max = get_parameter("v_max").as_int();
    spec_pub_->publish(msg);
  }

  void poseCallback(const geometry_msgs::msg::PoseStamped::SharedPtr msg)
  {
    RCLCPP_INFO_THROTTLE(
      get_logger(), *get_clock(), 1000,
      "收到位姿：x=%.3f, y=%.3f, z=%.3f",
      msg->pose.position.x, msg->pose.position.y, msg->pose.position.z);
  }

  rclcpp::Publisher<vision_interfaces::msg::TargetSpec>::SharedPtr spec_pub_;
  rclcpp::Subscription<geometry_msgs::msg::PoseStamped>::SharedPtr pose_sub_;
  rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<TargetManager>());
  rclcpp::shutdown();
  return 0;
}
