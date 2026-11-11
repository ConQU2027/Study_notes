# include "rclcpp/rclcpp.hpp"
# include "lr_interfaces/srv/lr.hpp"

class CarService : public rclcpp::Node
{
public:
  CarService() : Node("car_service")
  {
    service_ = this->create_service<lr_interfaces::srv::Lr>(
      "calculate_height",
      std::bind(&CarService::handle_service, this, std::placeholders::_1, std::placeholders::_2));
    RCLCPP_INFO(this->get_logger(), "服务端已启动,等待客户端发送目标高度...");
    }
private:
  void handle_service(
    const std::shared_ptr<lr_interfaces::srv::Lr::Request> request,
    std::shared_ptr<lr_interfaces::srv::Lr::Response> response)
  {
    RCLCPP_INFO(this->get_logger(), "收到目标高度: %f", request->target_height);
    // 计算结果
    int days = (request->target_height + 2)/3;
    int current_height=days*3;
    response->days = days;
    response->current_height = current_height;
    RCLCPP_INFO(this->get_logger(), "计算完成：需要 %d 天,最终高度%d米",days,current_height);
  }

  rclcpp::Service<lr_interfaces::srv::Lr>::SharedPtr service_;
};
int main(int argc, char **argv)
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<CarService>();
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}
