#include "homework/robot.h"
#include <cmath>


void Robot::set_speed(double speed){
    std::lock_guard<std::mutex> lock(mutex);
    this->speed = speed;
}
void Robot::set_goal(double x,double y){
    target_pose.x = x;
    target_pose.y = y;
    target_pose.z = 0.0;
    moving = !close_goal();
}

geometry_msgs::msg::Point Robot::move_step(double dt){
    if (!moving){
        velocity.x = velocity.y = velocity.z = 0.0;
        return current_pose;
    }

    const double dx = target_pose.x-current_pose.x;
    const double dy = target_pose.y-current_pose.y;
    const double remain = std::hypot(dx,dy);

    

    const double vx = speed*(dx/remain);
    const double vy = speed*(dy/remain);

  


    current_pose.x += vx * dt;
    current_pose.y += vy * dt;
    velocity.x = vx;
    velocity.y = vy;

    if (close_goal()) {
        moving = false;
        velocity.x = velocity.y = velocity.z = 0.0;
    }

    return current_pose;
}

double Robot::get_distance_to_target() const
{
    return std::hypot(target_pose.x - current_pose.x,
                      target_pose.y - current_pose.y);
}

bool Robot::close_goal() const
{
    return get_distance_to_target() < 0.01;
}

void Robot::stop_move()
{
    moving = false;
    velocity.x = velocity.y = velocity.z = 0.0;
}