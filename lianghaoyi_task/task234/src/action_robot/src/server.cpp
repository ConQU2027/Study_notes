#include "rclcpp/rclcpp.hpp"
#include "rclcpp_action/rclcpp_action.hpp"
#include "lr_interfaces/action/move_robot.hpp"
#include "action_robot/robot.h"

using MoveRobot=lr_interfaces::action::MoveRobot;
using GoalHandleMoveRobot=rclcpp_action::ServerGoalHandle<MoveRobot>;
class ActionRobot01:public rclcpp::Node{
public:
    explicit ActionRobot01(std::string name):Node(name){
        RCLCPP_INFO(this->get_logger(),"节点 %s 已启动",name.c_str());
        this->declare_parameter("target_x",5.0);
        this->declare_parameter("target_y",5.0);
        this->declare_parameter("speed",1.0);
        double tx=this->get_parameter("target_x").as_double();
        double ty=this->get_parameter("target_y").as_double();
        double sp=this->get_parameter("speed").as_double();
        robot_.set_goal(tx, ty);
        robot_.set_speed(sp);

        param_callback_handle_ = this->add_on_set_parameters_callback(
            std::bind(&ActionRobot01::param_callback, this, std::placeholders::_1));

        this->action_server_ = rclcpp_action::create_server<MoveRobot>(
            this, "move_robot",
            std::bind(&ActionRobot01::handle_goal, this, std::placeholders::_1, std::placeholders::_2),
            std::bind(&ActionRobot01::handle_cancel, this, std::placeholders::_1),
            std::bind(&ActionRobot01::handle_accepted, this, std::placeholders::_1));
    }

private:
    Robot robot_;
    rclcpp_action::Server<MoveRobot>::SharedPtr action_server_;
    rclcpp::node_interfaces::OnSetParametersCallbackHandle::SharedPtr param_callback_handle_;

    rcl_interfaces::msg::SetParametersResult param_callback(const std::vector<rclcpp::Parameter> & parameters) {
        rcl_interfaces::msg::SetParametersResult result;
        result.successful = true;

        for(const auto&param:parameters){
            if(param.get_name()=="target_x"||param.get_name()=="target_y"){
                double tx=this->get_parameter("target_x").as_double();
                double ty=this->get_parameter("target_y").as_double();
                robot_.set_goal(tx,ty);
                RCLCPP_INFO(this->get_logger(),"收到新参数->目标位置更新为:(%.1f,%.1f)",tx,ty);
            }else if(param.get_name()=="speed"){
                double sp=param.as_double();
                robot_.set_speed(sp);
                RCLCPP_INFO(this->get_logger(),"收到新参数->速度更新为:%.1f",sp);
            }
        }
        return result;
    }

    rclcpp_action::GoalResponse handle_goal(const  rclcpp_action::GoalUUID&uuid,std::shared_ptr<const MoveRobot::Goal>goal){
        (void)uuid;(void)goal;
        double tx=this->get_parameter("target_x").as_double();
        double ty =this->get_parameter("target_y").as_double();
        robot_.set_goal(tx,ty);
        RCLCPP_INFO(this->get_logger(),"收到 Action 发车指令，以参数 (%.1f, %.1f) 为目标开始移动",tx,ty);
        return rclcpp_action::GoalResponse::ACCEPT_AND_EXECUTE;
    }

    rclcpp_action::CancelResponse handle_cancel(const std::shared_ptr<GoalHandleMoveRobot>goal_handle){
        (void)goal_handle;
        RCLCPP_INFO(this->get_logger(),"收到取消请求，小车停止");
        robot_.stop_move();
        return rclcpp_action::CancelResponse::ACCEPT;
    }

    void handle_accepted(const std::shared_ptr<GoalHandleMoveRobot> goal_handle) {
        std::thread{std::bind(&ActionRobot01::execute_move, this, goal_handle)}.detach();
    }
    void execute_move(const std::shared_ptr<GoalHandleMoveRobot> goal_handle) {
        auto feedback = std::make_shared<MoveRobot::Feedback>();
        auto result = std::make_shared<MoveRobot::Result>();
        rclcpp::Rate rate(1);
        double time_sec = 0.0;

        while (rclcpp::ok() && !robot_.close_goal()) {
            if (goal_handle->is_canceling()) {
                result->final_position.x=robot_.get_x();
                result->final_position.y=robot_.get_y();
                result->total_time_sec=time_sec;
                goal_handle->canceled(result);
                RCLCPP_INFO(this->get_logger(),"任务已被取消");
                return;
            }
            feedback->current_position.x=robot_.get_x();
            feedback->current_position.y=robot_.get_y();
            feedback->distance_to_target=robot_.get_distance();
            goal_handle->publish_feedback(feedback);

            robot_.move_step();
            time_sec += 1.0;
            rate.sleep();
        }

        result->final_position.x=robot_.get_x();
        result->final_position.y=robot_.get_y();
        result->total_time_sec=time_sec;
        goal_handle->succeed(result);
        RCLCPP_INFO(this->get_logger(),"成功到达目标点！");
    }
};

int main(int argc, char **argv) {
    rclcpp::init(argc, argv);
    auto action_server = std::make_shared<ActionRobot01>("action_robot_server");
    rclcpp::spin(action_server);
    rclcpp::shutdown();
    return 0;
}