# include "rclcpp/rclcpp.hpp"
# include "lr_interfaces/srv/lr.hpp"
# include <memory>
# include <chrono>

class CarClient : public rclcpp::Node
{
public: 
  rclcpp::Client<lr_interfaces::srv::Lr>::SharedPtr client_;
  CarClient() : Node("car_client"){
    client_ = this->create_client<lr_interfaces::srv::Lr>("calculate_height");
  }
  void send_request(int target_height){
    while(!client_->wait_for_service(std::chrono::seconds(1))){
      RCLCPP_INFO(this->get_logger(),"等待服务端启动...");
    }
  auto request = std::make_shared<lr_interfaces::srv::Lr::Request>();
  request->target_height = target_height;

  auto future = client_->async_send_request(request);
  if(rclcpp::spin_until_future_complete(this->get_node_base_interface(),future)==rclcpp::FutureReturnCode::SUCCESS){
    auto response = future.get();
    RCLCPP_INFO(this->get_logger(),"收到服务端响应：需要 %d 天，当前高度为 %d 米",response->days,response->current_height);
    }else{
      RCLCPP_ERROR(this->get_logger(),"请求失败");
    }
  }
  private:
 
};

int main(int argc,char **argv){
  rclcpp::init(argc,argv);
  if(argc!=2){
    RCLCPP_ERROR(rclcpp::get_logger("rclcpp"),"请提供目标高度参数");
    return 1;
  }
  int target_height = std::atoi(argv[1]);

  auto node=std::make_shared<CarClient>();

  rclcpp::shutdown();
  return 0;
}