#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"
int x=0,weight=0;

class niluo : public rclcpp::Node
{

public:
    // 构造函数,有一个参数为节点名称
    niluo(std::string name) : Node(name)
    {
        RCLCPP_INFO(this->get_logger(), "大家好，我是%s.", name.c_str());
        command_publisher_= this->create_publisher<std_msgs::msg::String>("mingyue",10);
	timer_ = this->create_wall_timer(std::chrono::milliseconds(5000), std::bind(&niluo::timer_callback, this)); 
	command_subscribe_ = this->create_subscription<std_msgs::msg::String>("makeboat", 10, std::bind(&niluo::command_callback, this, std::placeholders::_1));
    }

private:
 // 声明一个订阅者
    rclcpp::Subscription<std_msgs::msg::String>::SharedPtr command_subscribe_;
     // 收到话题数据的回调函数
    void command_callback(const std_msgs::msg::String::SharedPtr msg)
    {
            weight++;
            std::cout<<weight<<std::endl;
        RCLCPP_INFO(this->get_logger(), "我们做的船重量来到了%d", weight);
    }
void timer_callback()

    {
        x++;
        // 创建消息
        std_msgs::msg::String message;
        message.data = "节工程设计";
        // 日志打印
        RCLCPP_INFO(this->get_logger(), "我上了第%d%s",x,message.data.c_str());
        // 发布消息
        command_publisher_->publish(message);
    }
    // 声名定时器指针
    rclcpp::TimerBase::SharedPtr timer_;
    // 声明话题发布者指针
    // 声明fabzuhe
    rclcpp::Publisher<std_msgs::msg::String>::SharedPtr command_publisher_;
};

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    /*创建对应节点的共享指针对象*/
    auto node = std::make_shared<niluo>("niluo");
    /* 运行节点，并检测退出信号*/
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}

