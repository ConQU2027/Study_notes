#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"

class StudentNode : public rclcpp::Node{
public:
    StudentNode(std::string name) : Node(name){
        RCLCPP_INFO(this->get_logger(), "Hello,I'm waya");
        subscription = this->create_subscription<std_msgs::msg::String>("mingyue",10,std::bind(&StudentNode::mingyue_callback,this,std::placeholders::_1));
        publisher = this->create_publisher<std_msgs::msg::String>("makeboat",10);
        timer = this->create_wall_timer(std::chrono::seconds(5),std::bind(&StudentNode::timer_callback, this));
    
    }

private:
    void mingyue_callback(const std_msgs::msg::String::SharedPtr msg){
        RCLCPP_INFO(this->get_logger(),"mingyue:%s",msg->data.c_str());
    }

    void timer_callback(){
        int count = 0;
        count++;
        auto boat = std_msgs::msg::String();
        boat.data = "I have a class,I make"+std::to_string(count)+"kg boat";
        publisher->publish(boat);
        RCLCPP_INFO(this->get_logger(),"makeboat:%s",boat.data.c_str());
    }

    rclcpp::Publisher<std_msgs::msg::String>::SharedPtr publisher;
    rclcpp::Subscription<std_msgs::msg::String>::SharedPtr subscription;
    rclcpp::TimerBase::SharedPtr timer;
    
};

int main(int argc, char** argv)
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<StudentNode>("student_node"));
    rclcpp::shutdown();
    return 0;
}