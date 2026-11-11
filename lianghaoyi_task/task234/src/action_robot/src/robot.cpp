#include"action_robot/robot.h"
Robot::Robot():current_x_(0.0),current_y_(0.0),target_x_(0.0),target_y_(0.0),step_size_(1.0){}

bool Robot::set_goal(double target_x,double target_y){
    target_x_=target_x;
    target_y_=target_y;
    return !close_goal();
}

void Robot::move_step(){
    double dx = target_x_-current_x_;
    double dy = target_y_-current_y_;
    double dist = std::sqrt(dx*dx+dy*dy);

    if(dist>0.01){
        current_x_ +=(dx/dist)*step_size_;
        current_y_ +=(dy/dist)*step_size_;
    }
}
double Robot::get_x(){return current_x_;}
double Robot::get_y(){return current_y_;}
double Robot::get_distance(){
    return std::sqrt(std::pow(target_x_-current_x_,2)+std::pow(target_y_-current_y_,2));
}
bool Robot::close_goal(){
    return get_distance() < 0.5;
}
void Robot::stop_move(){
    target_x_=current_x_;
    target_y_=current_y_;
}
void Robot::set_speed(double speed){
    step_size_=speed;
}