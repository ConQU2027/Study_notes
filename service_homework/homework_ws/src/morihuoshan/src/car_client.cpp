#include "lr_interfaces/srv/car.hpp"
#include "rclcpp/rclcpp.hpp"
#include <iostream>
  using namespace std::placeholders;
  
class CarClient : public rclcpp::Node {
public:
    CarClient(std::string name) : Node(name) {
        RCLCPP_INFO(this->get_logger(),"节点已启动：%s",name.c_str());
        car_client_ = this->create_client<lr_interfaces::srv::Car>("car_service");
    }

    void send_request(int target_height) {
        while (!car_client_->wait_for_service(std::chrono::seconds(1))) {
            if(!rclcpp::ok()) {
                RCLCPP_ERROR(this->get_logger(),"等待服务端上线中...");
                return;
            }
            RCLCPP_INFO(this->get_logger(),"等待服务端上线中");
        }
        auto request = std::make_shared<lr_interfaces::srv::Car::Request>();
        request->target_height = target_height;
        car_client_->async_send_request(request,std::bind(&CarClient::handle_response,this,_1));
    }

private:
    rclcpp::Client<lr_interfaces::srv::Car>::SharedPtr car_client_;

    void handle_response(rclcpp::Client<lr_interfaces::srv::Car>::SharedFuture future) {
        auto response = future.get();
        RCLCPP_INFO(this->get_logger(),"当前高度: %d 米",response->current_height);
        RCLCPP_INFO(this->get_logger(),"达到目标高度共用了 %d 天",response->days);
    };
};

int main(int argc,char **argv) {
    rclcpp::init(argc,argv);
    auto node = std::make_shared<CarClient>("car_client");
    int target_height = 0;
    std::cout << "请输入目标高度：";
    std::cin >> target_height;
    node->send_request(target_height);
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}
