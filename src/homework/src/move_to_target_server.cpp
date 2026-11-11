#include "homework/robot.h"
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_action/rclcpp_action.hpp"
#include "lr_interfaces/action/move_to_target.hpp"

class ActionRobot01 : public rclcpp::Node{
public:

    
   
    using MoveToTarget = lr_interfaces::action::MoveToTarget;
    using GoalHandleMoveToTarget = rclcpp_action::ServerGoalHandle<MoveToTarget>;

    double speed = 1.0;

    explicit ActionRobot01(std::string name) : Node(name){
        RCLCPP_INFO(this->get_logger(),"the node %s is starting.", name.c_str());
       
        this->declare_parameter<double>("speed",speed);
        this->get_parameter("speed",speed);

        using namespace std::placeholders;

        this->action_server = rclcpp_action::create_server<MoveToTarget>(this,"move_to_target",
            std::bind(&ActionRobot01::handle_goal,this,_1,_2),
            std::bind(&ActionRobot01::handle_cancel,this,_1),
            std::bind(&ActionRobot01::handle_accepted,this,_1));
      
        }

private:

   
    

    Robot robot;
    rclcpp_action::Server<MoveToTarget>::SharedPtr action_server;
    

    std::mutex goal_mutex;
    std::shared_ptr<GoalHandleMoveToTarget> active_goal;
    std::atomic<uint64_t> goal_id{0};
    uint64_t active_goal_id{0};

    rclcpp_action::GoalResponse handle_goal(const rclcpp_action::GoalUUID & uuid,std::shared_ptr<const MoveToTarget::Goal> goal){
        (void)uuid;
        double speed = this->get_parameter("speed").as_double();
        robot.set_speed(speed);
        RCLCPP_INFO(this->get_logger(),"Received goal request with target_position (%f, %f)",goal->target_position.x,goal->target_position.y);
        
        std::lock_guard<std::mutex> lock(goal_mutex);
        if (active_goal) {
            RCLCPP_WARN(this->get_logger(),"New goal arrives,preempting old goal");
        
            active_goal->abort(std::make_shared<MoveToTarget::Result>());
            active_goal.reset();
            robot.stop_move();
        }
        return rclcpp_action::GoalResponse::ACCEPT_AND_EXECUTE;
        
    }

    
    rclcpp_action::CancelResponse handle_cancel(
        const std::shared_ptr<GoalHandleMoveToTarget> goal_handle){
        RCLCPP_INFO(this->get_logger(), "Received request to cancel goal");
        (void)goal_handle;
        robot.stop_move();
        return rclcpp_action::CancelResponse::ACCEPT;
    }

    
    void execute_move(const std::shared_ptr<GoalHandleMoveToTarget> goal_handle,uint64_t my_id){
        const auto goal = goal_handle->get_goal();
        RCLCPP_INFO(this->get_logger(),"start (%f, %f)",goal->target_position.x,goal->target_position.y);

        auto result = std::make_shared<MoveToTarget::Result>();
        const auto start_time = this->now();

        rclcpp::Rate rate = rclcpp::Rate(5);   
        robot.set_goal(goal->target_position.x,goal->target_position.y);

        while (rclcpp::ok() && !robot.close_goal()){
            robot.move_step(0.5);

            {
                std::lock_guard<std::mutex> lock(goal_mutex);
                if (my_id != active_goal_id) {
                    RCLCPP_WARN(this->get_logger(),"Goal preempted, exiting");
                    return;  
                }
            }

            auto feedback = std::make_shared<MoveToTarget::Feedback>();
            feedback->current_position = robot.get_current_pose();
            feedback->current_velocity = robot.get_current_velocity();
            feedback->distance_to_target = robot.get_distance_to_target();
            goal_handle->publish_feedback(feedback);

            if (goal_handle->is_canceling()) {
                result->final_position = robot.get_current_pose();
                result->total_time_sec = (this->now()-start_time).seconds();
                goal_handle->canceled(result);
                RCLCPP_INFO(this->get_logger(),"Goal Canceled");
                return;
            }

            RCLCPP_INFO(this->get_logger(),"Publisher Feedback");
            rate.sleep();
        }

        result->final_position = robot.get_current_pose();
        result->total_time_sec = (this->now()-start_time).seconds();
        goal_handle->succeed(result);
        RCLCPP_INFO(this->get_logger(),"Goal Succeeded");
    }

  
    void handle_accepted(const std::shared_ptr<GoalHandleMoveToTarget> goal_handle){
        using std::placeholders::_1;{
            std::lock_guard<std::mutex> lock(goal_mutex);
            active_goal = goal_handle;
            active_goal_id = ++goal_id;
        }
        const uint64_t my_id = active_goal_id;

        std::thread{[this, goal_handle, my_id](){
            this->execute_move(goal_handle,my_id);
        } }.detach();
        }
};

int main(int argc, char ** argv){
    rclcpp::init(argc, argv);
    auto action_server = std::make_shared<ActionRobot01>("action_robot_01");
    rclcpp::spin(action_server);
    rclcpp::shutdown();
    return 0;
}

//bu xing l ,wo shou bu liao l ,zhe ge ren wu Action ,di er ge ren wu wan cheng bu liao l ,Pamameter de ren wu wo mei sui bian xie l yi dian
//wo zen me da bu chu zhong wen 
//mei jiao wo zen me duo xian cheng qiang zhan ren wu a , zhi you vibecoding yi xia l ,da bu fen wo hai shi zi ji qiao d 
//gei dian shi jian wo xiao hua yi xia ba ,you dian lei dao l