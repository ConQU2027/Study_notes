#include "rclcpp/rclcpp.hpp"
#include "rclcpp_action/rclcpp_action.hpp"
#include "lr_interfaces/action/move_to_target.hpp"
#include "geometry_msgs/msg/point.hpp"


class ActionControl01 : public rclcpp::Node{
public:
    using MoveToTarget = lr_interfaces::action::MoveToTarget;
    using GoalHandleMoveToTarget = rclcpp_action::ClientGoalHandle<MoveToTarget>;

    explicit ActionControl01(std::string name) : Node(name){
        double target_y = 5.0,target_x = 5.0;
        this->declare_parameter<double>("target_x",target_x);
        this->declare_parameter<double>("target_y",target_y);
        
        target_x = this->get_parameter("target_x",target_x);
        target_y = this->get_parameter("target_y",target_y);
        RCLCPP_INFO(this->get_logger(),"the node is starting%s.",name.c_str());

        this->client_ptr =rclcpp_action::create_client<MoveToTarget>(this,"move_to_target");

        this->timer = this->create_wall_timer(std::chrono::milliseconds(500),std::bind(&ActionControl01::send_goal,this));
    }

    void send_goal(){
        using namespace std::placeholders;

        this->timer->cancel();

        if (!this->client_ptr->wait_for_action_server(std::chrono::seconds(10))) {
            RCLCPP_ERROR(this->get_logger(),"Action server not available after waiting");
            rclcpp::shutdown();
            return;
        }

        auto goal_msg = MoveToTarget::Goal();
        goal_msg.target_position.x = target_x;   
        goal_msg.target_position.y = target_y;   
        goal_msg.target_position.z = 0.0;

        RCLCPP_INFO(this->get_logger(),"Sending goal: target_position=(%.2f, %.2f)",goal_msg.target_position.x, goal_msg.target_position.y);

        auto send_goal_options =rclcpp_action::Client<MoveToTarget>::SendGoalOptions();
        send_goal_options.goal_response_callback = std::bind(&ActionControl01::goal_response_callback,this,_1);
        send_goal_options.feedback_callback = std::bind(&ActionControl01::feedback_callback,this,_1,_2);
        send_goal_options.result_callback = std::bind(&ActionControl01::result_callback,this,_1);

        this->client_ptr->async_send_goal(goal_msg,send_goal_options);
    }

private:
    rclcpp_action::Client<MoveToTarget>::SharedPtr client_ptr;
    rclcpp::TimerBase::SharedPtr timer;

    double target_x;
    double target_y;

    void goal_response_callback(GoalHandleMoveToTarget::SharedPtr goal_handle){
        if (!goal_handle)RCLCPP_ERROR(this->get_logger(),"Goal was rejected by server");
        else RCLCPP_INFO(this->get_logger(),"Goal accepted by server, waiting for result");
        
    }

    
    void feedback_callback(GoalHandleMoveToTarget::SharedPtr,const std::shared_ptr<const MoveToTarget::Feedback> feedback){
        RCLCPP_INFO(this->get_logger(),"Feedback: pos=(%.2f, %.2f) V=(%.2f, %.2f) remain=%.2f",feedback->current_position.x,feedback->current_position.y,feedback->current_velocity.x,feedback->current_velocity.y,feedback->distance_to_target);
    }

   
    void result_callback(const GoalHandleMoveToTarget::WrappedResult & result){
        switch (result.code) {
            case rclcpp_action::ResultCode::SUCCEEDED:break;
            case rclcpp_action::ResultCode::ABORTED:
                RCLCPP_ERROR(this->get_logger(),"Goal was aborted");
                return;
            case rclcpp_action::ResultCode::CANCELED:
                RCLCPP_ERROR(this->get_logger(),"Goal was canceled");
                RCLCPP_INFO(this->get_logger(),"Canceled: final=(%.2f,%.2f) remain=%.2f time=%.2fs",result.result->final_position.x,result.result->final_position.y,result.result->distance_to_target,result.result->total_time_sec);
                return;
            default:
                RCLCPP_ERROR(this->get_logger(),"Unknown result code");
                return;
        }
        RCLCPP_INFO(this->get_logger(),"Result received: final=(%.2f,%.2f) time=%.2fs",result.result->final_position.x,result.result->final_position.y,result.result->total_time_sec);
    }
};

int main(int argc, char ** argv)
{
    rclcpp::init(argc, argv);
    auto action_client = std::make_shared<ActionControl01>("action_robot_cpp");
    rclcpp::spin(action_client);
    rclcpp::shutdown();
    return 0;
}