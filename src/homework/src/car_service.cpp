#include "rclcpp/rclcpp.hpp"
#include "lr_interfaces/srv/lr_interfaces.hpp"

using LrInterfaces = lr_interfaces::srv::LrInterfaces;

class CarService : public rclcpp::Node{
public:
    CarService(std::string name) : Node(name){
    service_ = this->create_service<LrInterfaces>("car_height",std::bind(&CarService::handle_car_height,this,std::placeholders::_1,std::placeholders::_2));
    RCLCPP_INFO(this->get_logger(),"car_service is starting,wait for survice");
    }

private:
    void handle_car_height(const std::shared_ptr<LrInterfaces::Request> request,std::shared_ptr<LrInterfaces::Response> response){
    int32_t target_height = request->target_height;
    int32_t current_height = 0;
    int32_t days = 0;

    RCLCPP_INFO(this->get_logger(),"receive: %d m,the car up 3 m",target_height);


    while (current_height < target_height) {
        current_height += 3;
        days += 1;
        RCLCPP_INFO(this->get_logger(),"%d day,today'height: %d m",days,current_height);
    }

    response->current_height = current_height;
    response->days = days;

    RCLCPP_INFO(this->get_logger(),"I have reach %d m,need %d days",current_height,days);
    }

    rclcpp::Service<LrInterfaces>::SharedPtr service_;
};

int main(int argc, char** argv){
    rclcpp::init(argc, argv);
    auto node = std::make_shared<CarService>("car_service");
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}