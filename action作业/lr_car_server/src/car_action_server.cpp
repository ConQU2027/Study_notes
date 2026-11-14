#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <functional>
#include <iomanip>
#include <memory>
#include <mutex>
#include <sstream>
#include <string>
#include <thread>
#include "geometry_msgs/msg/point.hpp"
#include "geometry_msgs/msg/vector3.hpp"
#include "lr_interfaces/action/move_to.hpp"
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_action/rclcpp_action.hpp"

namespace
{
//没招了，只能让deepseek帮我写了，然后它两个节点都写的又臭又长
// 判断是否到达的精确度
//constexpr暂时感觉就像是能写个表达式的const
constexpr double kEpsilon = 1e-6;

double elapsed_seconds(const std::chrono::steady_clock::time_point & start)
{
  return std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
}

std::string uuid_to_string(const rclcpp_action::GoalUUID & uuid)
{
  std::ostringstream oss;
  oss << std::hex << std::setfill('0');
  for (const auto byte : uuid) {
    oss << std::setw(2) << static_cast<int>(byte);
  }
  return oss.str();
}

}  // namespace

class CarActionServer : public rclcpp::Node
{
public:
  using MoveTo = lr_interfaces::action::MoveTo;
  using GoalHandleMoveTo = rclcpp_action::ServerGoalHandle<MoveTo>;

  CarActionServer()
  : rclcpp::Node("car_action_server")
  {
    // 这里用了参数，然而我看不懂
    speed_ = this->declare_parameter<double>("speed", 1.0);            // m/s
    tick_sec_ = this->declare_parameter<double>("tick_sec", 0.5);      // 控制周期 s
    start_x_ = this->declare_parameter<double>("start_x", 0.0);        // 初始位置 x
    start_y_ = this->declare_parameter<double>("start_y", 0.0);        // 初始位置 y
    seconds_per_day_ = this->declare_parameter<double>("seconds_per_day", 60.0);


    //这里把“速度自己定义”理解为客户端自己输入速度,同时反馈周期一类的也能自己
    if (speed_ <= 0.0) {
      RCLCPP_WARN(this->get_logger(), "速度必须为正数，已重置为1.0 m/s");
      speed_ = 1.0;
    }
    if (tick_sec_ <= 0.0) {
      RCLCPP_WARN(this->get_logger(), "反馈周期必须为正数，已重置为0.5 s");
      tick_sec_ = 0.5;
    }
    if (tick_sec_ < 0.02) {
      RCLCPP_WARN(this->get_logger(), "反馈周期太小，已提升为0.02 s");
      tick_sec_ = 0.02;
    }
    if (seconds_per_day_ <= 0.0) {
      seconds_per_day_ = 60.0;
    }

    pose_x_ = start_x_;
    pose_y_ = start_y_;

    // ---------------- Action 服务端 ----------------
    action_server_ = rclcpp_action::create_server<MoveTo>(
      this, kActionName,
      std::bind(
        &CarActionServer::handle_goal, this,
        std::placeholders::_1, std::placeholders::_2),
      std::bind(&CarActionServer::handle_cancel, this, std::placeholders::_1),
      std::bind(&CarActionServer::handle_accepted, this, std::placeholders::_1));

    RCLCPP_INFO(
      this->get_logger(),
      "小车服务端已启动: action名称为 %s, 初始位置为(%.2f, %.2f), "
      "速度为%.2f m/s, 控制周期为%.2f s",
      kActionName, pose_x_, pose_y_, speed_, tick_sec_);
  }

  ~CarActionServer() override
  {
    // 通知所有工作线程退出，并等它们真正结束，避免线程访问已销毁的成员
    shutting_down_.store(true);
    while (running_workers_.load() > 0) {
      std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
  }

private:
  // --------------------------------------------------------------------------
  //  给“正在执行的线程”做计数，仅供析构函数等待使用
  // --------------------------------------------------------------------------
  class WorkerCounter
  {
  public:
    explicit WorkerCounter(std::atomic<int> & counter)
    : counter_(counter) { ++counter_; }

    ~WorkerCounter() { --counter_; }

    WorkerCounter(const WorkerCounter &) = delete;
    WorkerCounter & operator=(const WorkerCounter &) = delete;

  private:
    std::atomic<int> & counter_;
  };

  // --------------------------------------------------------------------------
  //  收到新 Goal：只做合法性检查，真正的抢占在 handle_accepted 里完成
  // --------------------------------------------------------------------------
  rclcpp_action::GoalResponse handle_goal(
    const rclcpp_action::GoalUUID & uuid,
    std::shared_ptr<const MoveTo::Goal> goal)
  {
    if (shutting_down_.load()) {
      RCLCPP_WARN(this->get_logger(), "节点正在关闭，拒绝新目标");
      return rclcpp_action::GoalResponse::REJECT;
    }

    if (!std::isfinite(goal->target_position.x) ||
      !std::isfinite(goal->target_position.y))
    {
      RCLCPP_ERROR(
        this->get_logger(), "目标点非法，拒绝。goal_id=%s",
        uuid_to_string(uuid).c_str());
      return rclcpp_action::GoalResponse::REJECT;
    }

    RCLCPP_INFO(
      this->get_logger(), "收到新目标请求，goal_id=%s target=(%.2f, %.2f)",
      uuid_to_string(uuid).c_str(),
      goal->target_position.x, goal->target_position.y);
    return rclcpp_action::GoalResponse::ACCEPT_AND_EXECUTE;
  }

  // --------------------------------------------------------------------------
  //  收到取消请求：返回 ACCEPT 后，执行线程会在下一个检查点停止并调用 canceled()
  // --------------------------------------------------------------------------
  rclcpp_action::CancelResponse handle_cancel(
    const std::shared_ptr<GoalHandleMoveTo> goal_handle)
  {
    if (!goal_handle || !goal_handle->is_active()) {
      return rclcpp_action::CancelResponse::REJECT;
    }

    RCLCPP_WARN(
      this->get_logger(), "收到取消请求，goal_id=%s，执行线程将在下一个控制周期停止",
      uuid_to_string(goal_handle->get_goal_id()).c_str());
    return rclcpp_action::CancelResponse::ACCEPT;
  }

  // --------------------------------------------------------------------------
  //  Goal 被接受：登记为“最新目标”（旧目标因此被标记为抢占），再开线程执行
  // --------------------------------------------------------------------------
  void handle_accepted(const std::shared_ptr<GoalHandleMoveTo> goal_handle)
  {
    if (shutting_down_.load()) {
      RCLCPP_WARN(this->get_logger(), "节点正在关闭，忽略新目标");
      return;
    }

    {
      std::lock_guard<std::mutex> lock(state_mutex_);
      // 关键点：latest_goal_ 指向最新被接受的 Goal。
      // 旧 Goal 的执行线程发现 latest_goal_ != 自己，就立即 abort 退出 —— 这就是抢占。
      latest_goal_ = goal_handle;
    }

    RCLCPP_INFO(
      this->get_logger(), "接受目标=%s，启动执行线程",
      uuid_to_string(goal_handle->get_goal_id()).c_str());

    std::thread(&CarActionServer::execute_wrapper, this, goal_handle).detach();
  }

  // --------------------------------------------------------------------------
  //  线程入口：捕获异常，避免 detach 线程里的异常把整个进程 terminate
  // --------------------------------------------------------------------------
  void execute_wrapper(const std::shared_ptr<GoalHandleMoveTo> goal_handle)
  {
    try {
      execute(goal_handle);
    } catch (const std::exception & e) {
      RCLCPP_ERROR(this->get_logger(), "执行线程捕获异常: %s", e.what());
    } catch (...) {
      RCLCPP_ERROR(this->get_logger(), "执行线程捕获未知异常");
    }
  }

  // --------------------------------------------------------------------------
  //  执行线程：模拟运动 + 发布 Feedback + 处理 到达 / 取消 / 抢占
  // --------------------------------------------------------------------------
  void execute(const std::shared_ptr<GoalHandleMoveTo> goal_handle)
  {
    WorkerCounter counter(running_workers_);

    const auto goal = goal_handle->get_goal();
    auto result = std::make_shared<MoveTo::Result>();

    const std::string goal_id = uuid_to_string(goal_handle->get_goal_id());
    const auto start_time = std::chrono::steady_clock::now();

    const double target_x = goal->target_position.x;
    const double target_y = goal->target_position.y;

    // 从“小车当前真实位置”出发：这样抢占后新目标会从旧目标停下的地方继续，
    // 与物理小车的行为一致。
    double cur_x = 0.0;
    double cur_y = 0.0;
    {
      std::lock_guard<std::mutex> lock(state_mutex_);
      cur_x = pose_x_;
      cur_y = pose_y_;
    }

    RCLCPP_INFO(
      this->get_logger(), "[goal %s] 开始执行: 当前位置为(%.2f, %.2f)，目标为(%.2f, %.2f)",
      goal_id.c_str(), cur_x, cur_y, target_x, target_y);

    const std::chrono::milliseconds tick_ms(
      static_cast<long long>(std::llround(tick_sec_ * 1000.0)));

    while (rclcpp::ok() && !shutting_down_.load()) {
      // ---------- 1) 抢占检查：有更新的 Goal 顶替了自己 ----------
      if (is_preempted(goal_handle)) {
        const double elapsed = elapsed_seconds(start_time);
        result->final_position.x = cur_x;
        result->final_position.y = cur_y;
        result->final_position.z = 0.0;
        result->total_time_sec = elapsed;
        if (goal_handle->is_active()) {
          goal_handle->abort(result);
        }
        clear_latest_goal(goal_handle);
        RCLCPP_WARN(
          this->get_logger(),
          "[goal %s] 被新目标抢占，停止于(%.2f, %.2f), 已用时%.2f s",
          goal_id.c_str(), cur_x, cur_y, elapsed);
        return;
      }

      // ---------- 2) 取消检查：handle_cancel 返回 ACCEPT 后这里变为 true ----------
      if (goal_handle->is_canceling()) {
        const double elapsed = elapsed_seconds(start_time);
        result->final_position.x = cur_x;
        result->final_position.y = cur_y;
        result->final_position.z = 0.0;
        result->total_time_sec = elapsed;
        if (goal_handle->is_active()) {
          goal_handle->canceled(result);
        }
        clear_latest_goal(goal_handle);
        RCLCPP_WARN(
          this->get_logger(),
          "[goal %s] 已取消 , 停止于(%.2f, %.2f),已用时 %.2f s, 剩余 %.2f m",
          goal_id.c_str(), cur_x, cur_y, elapsed,
          std::hypot(target_x - cur_x, target_y - cur_y));
        return;
      }

      // ---------- 3) 前进一个控制周期 ----------
      const double dx = target_x - cur_x;
      const double dy = target_y - cur_y;
      const double remaining_before = std::hypot(dx, dy);

      double vx = 0.0;
      double vy = 0.0;

      if (remaining_before > kEpsilon) {
        const double max_step = speed_ * tick_sec_;
        if (remaining_before <= max_step) {
          // 本周期就能到达，直接落到目标点，速度归零（避免“冲过头”）
          cur_x = target_x;
          cur_y = target_y;
        } else {
          vx = speed_ * dx / remaining_before;
          vy = speed_ * dy / remaining_before;
          cur_x += vx * tick_sec_;
          cur_y += vy * tick_sec_;
        }

        std::lock_guard<std::mutex> lock(state_mutex_);
        pose_x_ = cur_x;
        pose_y_ = cur_y;
      }

      const double remaining = std::hypot(target_x - cur_x, target_y - cur_y);

      // ---------- 4) 发布 Feedback ----------
      auto feedback = std::make_shared<MoveTo::Feedback>();
      feedback->current_position.x = cur_x;
      feedback->current_position.y = cur_y;
      feedback->current_position.z = 0.0;
      feedback->current_velocity.x = vx;
      feedback->current_velocity.y = vy;
      feedback->current_velocity.z = 0.0;
      feedback->distance_to_target = remaining;
      goal_handle->publish_feedback(feedback);

      RCLCPP_INFO(
        this->get_logger(),
        "[goal %s] feedback: pos=(%.2f, %.2f) vel=(%.2f, %.2f) 剩余=%.2f m",
        goal_id.c_str(), cur_x, cur_y, vx, vy, remaining);

      // ---------- 5) 到达目标 ----------
      if (remaining <= kEpsilon) {
        const double elapsed = elapsed_seconds(start_time);
        result->final_position.x = cur_x;
        result->final_position.y = cur_y;
        result->final_position.z = 0.0;
        result->total_time_sec = elapsed;
        if (goal_handle->is_active()) {
          goal_handle->succeed(result);
        }
        clear_latest_goal(goal_handle);
        RCLCPP_INFO(
          this->get_logger(),
          "[goal %s]到达目标, 总耗时 %.2f s ",
          goal_id.c_str(), elapsed);
        return;
      }

      // ---------- 6) 等待下一个周期（切片休眠，抢占/取消可快速响应） ----------
      sleep_interruptible(goal_handle, tick_ms);
    }

    // 节点正在关闭
    const double elapsed = elapsed_seconds(start_time);
    result->final_position.x = cur_x;
    result->final_position.y = cur_y;
    result->final_position.z = 0.0;
    result->total_time_sec = elapsed;
    if (goal_handle->is_active()) {
      goal_handle->abort(result);
    }
    clear_latest_goal(goal_handle);
    RCLCPP_WARN(
      this->get_logger(), "[goal %s]节点关闭，任务中止于(%.2f, %.2f)",
      goal_id.c_str(), cur_x, cur_y);
  }

  // --------------------------------------------------------------------------
  //  辅助函数
  // --------------------------------------------------------------------------
  bool is_preempted(const std::shared_ptr<GoalHandleMoveTo> & goal_handle)
  {
    std::lock_guard<std::mutex> lock(state_mutex_);
    return latest_goal_ && latest_goal_ != goal_handle;
  }

  void clear_latest_goal(const std::shared_ptr<GoalHandleMoveTo> & goal_handle)
  {
    std::lock_guard<std::mutex> lock(state_mutex_);
    if (latest_goal_ == goal_handle) {
      latest_goal_.reset();
    }
  }

  void sleep_interruptible(
    const std::shared_ptr<GoalHandleMoveTo> & goal_handle,
    std::chrono::milliseconds duration)
  {
    const auto deadline = std::chrono::steady_clock::now() + duration;
    while (rclcpp::ok() && !shutting_down_.load() &&
      std::chrono::steady_clock::now() < deadline)
    {
      std::this_thread::sleep_for(std::chrono::milliseconds(20));
      if (is_preempted(goal_handle) || goal_handle->is_canceling()) {
        return;
      }
    }
  }

  // --------------------------------------------------------------------------
  //  成员
  // --------------------------------------------------------------------------
  static constexpr const char * kActionName = "lr_move_to";

  double speed_{1.0};             // 模拟速度 m/s
  double tick_sec_{0.5};          // 控制周期 s
  double start_x_{0.0};           // 初始位置
  double start_y_{0.0};
  double seconds_per_day_{60.0};  // 用于把秒折算成“天”打印

  double pose_x_{0.0};            // 小车当前真实位置（所有 Goal 共享）
  double pose_y_{0.0};

  std::mutex state_mutex_;        // 保护 pose_x_/pose_y_/latest_goal_
  std::shared_ptr<GoalHandleMoveTo> latest_goal_;

  std::atomic<bool> shutting_down_{false};
  std::atomic<int> running_workers_{0};

  rclcpp_action::Server<MoveTo>::SharedPtr action_server_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<CarActionServer>();
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}

