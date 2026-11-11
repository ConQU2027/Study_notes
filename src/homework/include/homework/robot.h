// robot_demo_rclcpp/include/robot_demo_rclcpp/robot.h
#ifndef HOMEWORK__ROBOT_H_
#define HOMEWORK__ROBOT_H_

#include <mutex>
#include "geometry_msgs/msg/point.hpp"
#include "geometry_msgs/msg/vector3.hpp"

class Robot{
public:
    Robot() = default;

    
    void set_goal(double x, double y);
    
    void set_speed(double speed);
    geometry_msgs::msg::Point move_step(double dt);
  
    geometry_msgs::msg::Point get_current_pose() const {return current_pose;}
    geometry_msgs::msg::Vector3 get_current_velocity() const {return velocity;}
    double get_distance_to_target() const;
    bool close_goal() const;

   
    void stop_move();

private:

    mutable std::mutex mutex;
    geometry_msgs::msg::Point current_pose{};   
    geometry_msgs::msg::Point target_pose{};    
    geometry_msgs::msg::Vector3 velocity{};     
    bool moving = false;                        
    double speed = 1.0;                         
};

#endif  