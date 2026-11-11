#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"

class StudentNode : public rclcpp::Node {
public:
    StudentNode(std::string name) : Node(name) {
        RCLCPP_INFO(this->get_logger(),"大家好，我是waya");
        makeboat_publisher_ = this->create_publisher<std_msgs::msg::String>("makeboat",10);
        mingyue_subscribe_ = this->create_subscription<std_msgs::msg::String>("mingyue",10,std::bind(&StudentNode::mingyue_callback,this,std::placeholders::_1));
    }

private:
    rclcpp::Publisher<std_msgs::msg::String>::SharedPtr makeboat_publisher_;
    rclcpp::Subscription<std_msgs::msg::String>::SharedPtr mingyue_subscribe_;
    void mingyue_callback(const std_msgs::msg::String::SharedPtr msg) {
        std_msgs::msg::String boat;
        boat.data = "Today：" + msg->data;
        RCLCPP_INFO(this->get_logger(),"%s",boat.data.c_str());
        makeboat_publisher_->publish(boat);
    }
};

int main(int argc,char **argv) {
    rclcpp::init(argc,argv);
    auto node = std::make_shared<StudentNode>("student");
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}
