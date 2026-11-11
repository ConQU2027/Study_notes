#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"

class student_node : public rclcpp::Node
{
public:
    // 构造函数,有一个参数为节点名称
    student_node(std::string name) : Node(name)
    {
        RCLCPP_INFO(this->get_logger(), "大家好，我是waya.");
        command_subscribe_ = this->create_subscription<std_msgs::msg::String>("mingyue", 10, std::bind(&student_node::command_callback, this, std::placeholders::_1));
        command_publisher_ = this->create_publisher<std_msgs::msg::String>("makeboat", 10);
        // 创建定时器，5000ms为周期，定时发布
        timer_ = this->create_wall_timer(std::chrono::milliseconds(5000), std::bind(&student_node::timer_callback, this));
        }
        
private:
    // 声明一个订阅者 
    rclcpp::Subscription<std_msgs::msg::String>::SharedPtr command_subscribe_;
    void command_callback(const std_msgs::msg::String::SharedPtr msg)
    {
        RCLCPP_INFO(this->get_logger(), "我上了课，我要多做1kg船！");
    }
    void timer_callback()
    {
        // 创建消息
        std_msgs::msg::String message;
        message.data = "boat.data";
        // 日志打印(lue)
      //  RCLCPP_INFO(this->get_logger(), "Publishing: '%s'", message.data.c_str());
        // 发布消息
        command_publisher_->publish(message);
    }
    // 声名定时器指针
    rclcpp::TimerBase::SharedPtr timer_;
    // 声明话题发布者指针
    rclcpp::Publisher<std_msgs::msg::String>::SharedPtr command_publisher_;        
};



int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    /*创建对应节点的共享指针对象*/
    auto node = std::make_shared<student_node>("student_node");
    /* 运行节点，并检测退出信号*/
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}

