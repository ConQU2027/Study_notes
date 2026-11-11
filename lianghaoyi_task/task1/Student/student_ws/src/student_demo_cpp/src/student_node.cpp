# include "rclcpp/rclcpp.hpp"
# include "std_msgs/msg/string.hpp"


class StudentNode : public rclcpp::Node {
    public:
    StudentNode(std::string name) : Node(name) {
        RCLCPP_INFO(this->get_logger(),"大家好,我是明月班的学生waya",name.c_str());
        mingyue_sub_ =this->create_subscription<std_msgs::msg::String>("mingyue",10,std::bind(&StudentNode::mingyue_callback,this,std::placeholders::_1));
        makeboat_pub_= this->create_publisher<std_msgs::msg::String>("makeboat",10);
    }
    private:
        rclcpp::Subscription<std_msgs::msg::String>::SharedPtr mingyue_sub_;
        rclcpp::Publisher<std_msgs::msg::String>::SharedPtr makeboat_pub_;
        void mingyue_callback(const std_msgs::msg::String::SharedPtr msg){
            RCLCPP_INFO(this->get_logger(),"大家好,我是明月班的学生waya",msg->data.c_str());
            std_msgs::msg::String reply_msg;
            reply_msg.data = "我上了课,我要多做1kg船!";
            makeboat_pub_->publish(reply_msg);
            RCLCPP_INFO(this->get_logger(),"发布 makeboat:'%s'",reply_msg.data.c_str());
        }
};

int main(int argc,char **argv){
    rclcpp::init(argc,argv);
    auto node = std::make_shared<StudentNode>("student_node");
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;

}