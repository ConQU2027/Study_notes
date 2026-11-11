#ifndef ROBOT_H_
# define ROBOT_H_
# include "rclcpp/rclcpp.hpp"
# include <cmath>
class Robot{
public:
    Robot();
    bool set_goal(double target_x,double target_y);
    void move_step();
    double get_x() ;//为什么我有参考ds的代码会给一个const
    double get_y() ;
    double get_distance() ;
    bool close_goal() ;
    void stop_move();
    void set_speed(double speed);
private:
    double current_x_;
    double current_y_;
    double target_x_;
    double target_y_;
    double step_size_;
};
#endif
