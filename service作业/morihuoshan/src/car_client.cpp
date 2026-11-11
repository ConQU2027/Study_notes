#include <memory>
#include <chrono>
#include <functional>
#include <cstdlib>
#include <iostream>
#include "rclcpp/rclcpp.hpp"
#include "jiekou/srv/lrinterfaces.hpp"

class CarClient : public rclcpp::Node {
public:
    CarClient(std::string name) : Node(name) {
        RCLCPP_INFO(this->get_logger(),"节点已启动: %s.",name.c_str());
        client_ = this->create_client<jiekou::srv::Lrinterfaces>("morihuoshan");
    }
    void send_request(int height) {
      //  RCLCPP_INFO(this->get_logger(),"计算pa %d zheemegaozzzd",height);
        while(!client_->wait_for_service(std::chrono::seconds(1))) {
            if(!rclcpp::ok()) {
                RCLCPP_ERROR(this->get_logger(),"等待服务的过程中被打断...");
                return;
            }
            RCLCPP_INFO(this->get_logger(),"等待服务端上线中");
        }
        auto request = std::make_shared<jiekou::srv::Lrinterfaces::Request>();
        request->target_height=height;
        client_->async_send_request(request,std::bind(&CarClient::result_callback_,this,std::placeholders::_1));
    }
private:
    rclcpp::Client<jiekou::srv::Lrinterfaces>::SharedPtr client_;
    void result_callback_(rclcpp::Client<jiekou::srv::Lrinterfaces>::SharedFuture result_future) {
    auto response = result_future.get();
    const int step=3 ;   // 与服务端的步长保持一致
    // 逐天输出过程
    for (int d=1; d <=response->days; d++) {
        int h=std::min(d * step, response->current_height);
        RCLCPP_INFO(this->get_logger(), "第 %d 天，当前高度 %d 米", d, h);
        std::this_thread::sleep_for(std::chrono::milliseconds(400));   // gundongzimu
    }
    RCLCPP_INFO(this->get_logger(), "共需 %d 天，最终高度 %d 米",response->days, response->current_height);
    //说是service是一问一答，无法将中间变量输给客户端，所以只能这么伪造输出
    }
};





int main(int argc,char **argv) {
    rclcpp::init(argc,argv);
    int target=0;                  
    std::cout<<"请输入目标高度: ";
    std::cin>>target;    
   // if (argc > 1) {
   //     target = std::atoi(argv[1]);    // ros2 run jiedian car_client 15
   // }
    auto node = std::make_shared<CarClient>("Car_client");
  //   node->send_request(target);         // ← 关键：一定要调用  (ai zhe me shuon de)
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}
