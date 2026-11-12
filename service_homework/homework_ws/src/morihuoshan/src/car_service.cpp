#include "lr_interfaces/srv/car.hpp"
#include "rclcpp/rclcpp.hpp"

class CarService : public rclcpp::Node {
public:
    CarService(std::string name) : Node(name) {
        RCLCPP_INFO(this->get_logger(),"节点已启动：%s",name.c_str());
        car_service_ = this->create_service<lr_interfaces::srv::Car>("car_service",std::bind(&CarService::handle_car_height,this,std::placeholders::_1,std::placeholders::_2));
    }
private:
    rclcpp::Service<lr_interfaces::srv::Car>::SharedPtr car_service_;

    void handle_car_height(const std::shared_ptr<lr_interfaces::srv::Car::Request> request,std::shared_ptr<lr_interfaces::srv::Car::Response> response) {
        RCLCPP_INFO(this->get_logger(),"收到target_height: %d",request->target_height);
        int current_height = 0;
        int days = 0;
        while (current_height < request->target_height) {
            current_height += 3;
            days++;
            RCLCPP_INFO(this->get_logger(),"第 %d 天，小车爬到了 %d 米",days,current_height);
        }
        response->current_height = current_height;
        response->days = days;
        RCLCPP_INFO(this->get_logger(),"已到达目标高度，共用了 %d 天",days);
    };
};

int main(int argc,char **argv) {
    rclcpp::init(argc,argv);
    auto node = std::make_shared<CarService>("car_service");
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}
