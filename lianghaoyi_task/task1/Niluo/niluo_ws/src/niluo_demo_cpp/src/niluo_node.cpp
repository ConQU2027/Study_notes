# include "rclcpp/rclcpp.hpp"
# include "std_msgs/msg/string.hpp"

class NiluoNode :public rclcpp::Node {
public:
    NiluoNode(std::string name) : Node(name) {
        RCLCPP_INFO(this->get_logger(),"大家好，我是%s",name.c_str());
        mingyue_pub_ = this->create_publisher<std_msgs::msg::String>("mingyue",10);
        timer_=this->create_wall_timer(std::chrono::milliseconds(5000),std::bind(&NiluoNode::timer_callback,this));
        makeboat_sub_ = this->create_subscription<std_msgs::msg::String>("makeboat",10,std::bind(&NiluoNode::makeboat_callback,this,std::placeholders::_1));
    }

private:
    int count_ = 0;
    void timer_callback(){
        std_msgs::msg::String message;
        message.data = "我上了第"+ std::to_string(count_)+"节工程设计";
        RCLCPP_INFO(this->get_logger(),"Publishing:'%s'",message.data.c_str());
        mingyue_pub_->publish(message);
        count_++;
    }
    void makeboat_callback(const std_msgs::msg::String::SharedPtr msg){
        RCLCPP_INFO(this->get_logger(),"收到 makeboat: '%s',我们做的船负重增加到%d!",msg->data.c_str(),count_);
    }
    rclcpp::Publisher<std_msgs::msg::String>::SharedPtr mingyue_pub_;
    rclcpp::TimerBase::SharedPtr timer_;
    rclcpp::Subscription<std_msgs::msg::String>::SharedPtr makeboat_sub_;
};
    
int main(int argc,char **argv){
    rclcpp::init(argc,argv);
    auto node = std::make_shared<NiluoNode>("niluo_node");
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}