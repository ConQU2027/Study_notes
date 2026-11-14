#include <chrono>
#include <cmath>
#include <functional>
#include <iomanip>
#include <memory>
#include <sstream>
#include <string>
#include "geometry_msgs/msg/point.hpp"
#include "lr_interfaces/action/move_to.hpp"
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_action/rclcpp_action.hpp"
namespace
{

std::string uuid_to_string(const rclcpp_action::GoalUUID & uuid)
{
  std::ostringstream oss;
  oss << std::hex << std::setfill('0');
  for (const auto byte : uuid) {
    oss << std::setw(2) << static_cast<int>(byte);
  }
  return oss.str();
}

std::string result_code_to_string(rclcpp_action::ResultCode code)
{
  switch (code) {
    case rclcpp_action::ResultCode::SUCCEEDED:
      return "SUCCEEDED";
    case rclcpp_action::ResultCode::CANCELED:
      return "CANCELED";
    case rclcpp_action::ResultCode::ABORTED:
      return "ABORTED";
    case rclcpp_action::ResultCode::UNKNOWN:
      return "UNKNOWN";
  }
  return "UNKNOWN";
}

} 

class ControlCenter : public rclcpp::Node
{
public:
  using MoveTo = lr_interfaces::action::MoveTo;
  using GoalHandleMoveTo = rclcpp_action::ClientGoalHandle<MoveTo>;

  ControlCenter()
  : rclcpp::Node("control_center")
  {
    target_x_ = this->declare_parameter<double>("target_x", 10.0);
    target_y_ = this->declare_parameter<double>("target_y", 5.0);
    seconds_per_day_ = this->declare_parameter<double>("seconds_per_day", 60.0);
    if (seconds_per_day_ <= 0.0) {
      seconds_per_day_ = 60.0;
    }

    client_ = rclcpp_action::create_client<MoveTo>(this, "lr_move_to");
  }

  void send_goal()
  {
    if (!client_->wait_for_action_server(std::chrono::seconds(5))) {
      RCLCPP_ERROR(
        this->get_logger(),
        "等待服务端超时，请先启动");
      rclcpp::shutdown();
      return;
    }

    MoveTo::Goal goal;
    goal.target_position.x = target_x_;
    goal.target_position.y = target_y_;
    goal.target_position.z = 0.0;

    RCLCPP_INFO(
      this->get_logger(), "向小车发送目标: (%.2f, %.2f)", target_x_, target_y_);

    rclcpp_action::Client<MoveTo>::SendGoalOptions options;
    options.goal_response_callback =
      std::bind(&ControlCenter::goal_response_callback, this, std::placeholders::_1);
    options.feedback_callback =
      std::bind(
      &ControlCenter::feedback_callback, this,
      std::placeholders::_1, std::placeholders::_2);
    options.result_callback =
      std::bind(&ControlCenter::result_callback, this, std::placeholders::_1);

    client_->async_send_goal(goal, options);
  }

private:
  void goal_response_callback(GoalHandleMoveTo::SharedPtr goal_handle)
  {
    if (!goal_handle) {
      RCLCPP_ERROR(this->get_logger(), "目标被小车拒绝（REJECT）");
      rclcpp::shutdown();
      return;
    }

    RCLCPP_INFO(
      this->get_logger(), "目标已被接受，目标=%s",
      uuid_to_string(goal_handle->get_goal_id()).c_str());
  }

  void feedback_callback(
    GoalHandleMoveTo::SharedPtr goal_handle,
    const std::shared_ptr<const MoveTo::Feedback> feedback)
  {
    (void)goal_handle;
    last_distance_ = feedback->distance_to_target;

    RCLCPP_INFO(
      this->get_logger(),
      "[feedback] pos=(%.2f, %.2f) vel=(%.2f, %.2f) 剩余=%.2f m",
      feedback->current_position.x, feedback->current_position.y,
      feedback->current_velocity.x, feedback->current_velocity.y,
      feedback->distance_to_target);
  }

  void result_callback(const GoalHandleMoveTo::WrappedResult & wrapped_result)
  {
    if (!wrapped_result.result) {
      RCLCPP_ERROR(this->get_logger(), "收到空回复");
      rclcpp::shutdown();
      return;
    }

    const auto & result = *wrapped_result.result;
    const double remaining = std::hypot(
      target_x_ - result.final_position.x,
      target_y_ - result.final_position.y);
    const std::string status = result_code_to_string(wrapped_result.code);

    RCLCPP_INFO(
      this->get_logger(),
      "末状态=%s 最终点=(%.2f, %.2f) 总时间消耗=%.2f "
      "剩余距离=%.2fm",
      status.c_str(), result.final_position.x, result.final_position.y,
      result.total_time_sec, remaining);

    if (wrapped_result.code == rclcpp_action::ResultCode::SUCCEEDED) {
      RCLCPP_INFO(
        this->get_logger(),
        "任务完成：总耗时 %.2f s，约 %.2f 天（按 %.1f 秒/天）",
        result.total_time_sec,
        result.total_time_sec / seconds_per_day_, seconds_per_day_);
    } else if (wrapped_result.code == rclcpp_action::ResultCode::CANCELED) {
      RCLCPP_WARN(
        this->get_logger(),
        "任务已取消：停在(%.2f, %.2f)，距目标还剩 %.2fm",
       // "（服务端最后一条Feedback上报%.2fm）",
        result.final_position.x, result.final_position.y,
        remaining);//, last_distance_
    } else if (wrapped_result.code == rclcpp_action::ResultCode::ABORTED) {
      RCLCPP_WARN(
        this->get_logger(),
        "任务中止：停在(%.2f, %.2f)，距原目标还剩%.2fm",
        result.final_position.x, result.final_position.y, remaining);
    }

    // 收到 Result 后退出
    rclcpp::shutdown();
  }

  rclcpp_action::Client<MoveTo>::SharedPtr client_;

  double target_x_{10.0};
  double target_y_{5.0};
  double seconds_per_day_{60.0};
  double last_distance_{0.0};
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<ControlCenter>();
  node->send_goal();
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}

