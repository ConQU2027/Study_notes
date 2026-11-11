#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"

class NiluoNode : public rclcpp::Node {
public:
    NiluoNode(std::string name) : Node(name) {
        RCLCPP_INFO(this->get_logger(),"大家好，我是%s",name.c_str());
        mingyue_publisher_ = this->create_publisher<std_msgs::msg::String>("mingyue",10);
        timer_ = this->create_wall_timer(std::chrono::milliseconds(5000),std::bind(&NiluoNode::timer_callback, this));
        makeboat_subscribe_ = this->create_subscription<std_msgs::msg::String>("makeboat",10,std::bind(&NiluoNode::makeboat_callback,this,std::placeholders::_1));
    }

private:
    void timer_callback() {
        count++;
        std_msgs::msg::String message;
        message.data = "我上了第" + std::to_string(count) + "节工程设计";
        mingyue_publisher_->publish(message);
    }

    void makeboat_callback(const std_msgs::msg::String::SharedPtr msg) {
        RCLCPP_INFO(this->get_logger(),"我要造船");
    }

    int count = 0;
    rclcpp::TimerBase::SharedPtr timer_;
    rclcpp::Publisher<std_msgs::msg::String>::SharedPtr mingyue_publisher_;
    rclcpp::Subscription<std_msgs::msg::String>::SharedPtr makeboat_subscribe_;
};

int main(int argc,char **argv) {
    rclcpp::init(argc,argv);
    auto node = std::make_shared<NiluoNode>("niluo");
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}
