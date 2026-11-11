#include "rclcpp/rclcpp.hpp"
#include "lr_interfaces/srv/lr_interfaces.hpp"

using LrInterfaces = lr_interfaces::srv::LrInterfaces;

class CarClient : public rclcpp::Node{
public:
    CarClient(std::string name) : Node(name){
        RCLCPP_INFO(this->get_logger(),"the node %s is starting",name.c_str());
        client = this->create_client<LrInterfaces>("car_height");
        }
    
    void move_robot(float target_height) {
        RCLCPP_INFO(this->get_logger(),"send:%f",target_height);
        while(!client -> wait_for_service(std::chrono::seconds(1))) {
            if(!rclcpp::ok()) {
                RCLCPP_ERROR(this->get_logger(),"service Error");
                return;
            }
            RCLCPP_INFO(this->get_logger(),"waiting for server online");
        }
        auto request = std::make_shared<LrInterfaces::Request>(); 
        request->target_height = target_height;
        using namespace std::placeholders;
        client->async_send_request(request,std::bind(&CarClient::result_callback,this,_1));
    }
private:
    rclcpp::Client<LrInterfaces>::SharedPtr client;
    
    void result_callback(rclcpp::Client<LrInterfaces>::SharedFuture result_future){
        auto response = result_future.get();
        RCLCPP_INFO(this->get_logger(),"reach:%d,%d days",response->current_height,response->days);
    }
};

int main(int argc,char** argv) {
    rclcpp::init(argc,argv);
    auto node = std::make_shared<CarClient>("car_client");
    node->move_robot(22);
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}
  