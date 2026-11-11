#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"

using namespace std::chrono_literals;

class NiluoNode : public rclcpp::Node
{
public:
    NiluoNode(std::string name) : Node(name){
    RCLCPP_INFO(this->get_logger(),"Hello,I'm niluo");
    publisher = this->create_publisher<std_msgs::msg::String>("mingyue",10);
    timer = this->create_wall_timer(std::chrono::seconds(5), std::bind(&NiluoNode::timer_callback,this));

    
    subscription = this->create_subscription<std_msgs::msg::String>("makeboat",10,std::bind(&NiluoNode::makeboat_callback,this,std::placeholders::_1));
    }

private:
    void timer_callback(){
        int count = 0;
        count++;
        auto msg = std_msgs::msg::String();
        msg.data = "I have"+std::to_string(count)+"engineering disign class";
        publisher->publish(msg);
        RCLCPP_INFO(this->get_logger(),"mingyue: %s",msg.data.c_str());

    }

    void makeboat_callback(const std_msgs::msg::String::SharedPtr msg){
        RCLCPP_INFO(this->get_logger(),"makeboat: %s",msg->data.c_str());
    }

    rclcpp::Publisher<std_msgs::msg::String>::SharedPtr publisher;
    rclcpp::Subscription<std_msgs::msg::String>::SharedPtr subscription;
    rclcpp::TimerBase::SharedPtr timer;


};

int main(int argc, char** argv)
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<NiluoNode>("niluo_node"));
    rclcpp::shutdown();
    return 0;


}



