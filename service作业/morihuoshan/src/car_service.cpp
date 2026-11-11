#include <memory>
#include <functional>
#include "rclcpp/rclcpp.hpp"
#include"jiekou/srv/lrinterfaces.hpp"

class Carservice : public rclcpp::Node {
public:
    Carservice(std::string name) : Node(name) {
        RCLCPP_INFO(this->get_logger(),"节点已启动：%s.",name.c_str());
        move_car_server_ = this->create_service<jiekou::srv::Lrinterfaces>("morihuoshan",std::bind(&Carservice::tianshujisuan,this,std::placeholders::_1,std::placeholders::_2));        
    }
private:
 	rclcpp::Service<jiekou::srv::Lrinterfaces>::SharedPtr move_car_server_;
	void tianshujisuan(const std::shared_ptr<jiekou::srv::Lrinterfaces::Request>request, const std::shared_ptr<jiekou::srv::Lrinterfaces::Response> response)
	{
		 RCLCPP_INFO(this->get_logger(),"收到目标高度: %d",request->target_height);
		int x=0,now_height=0;
		while(now_height< request->target_height)
		{
 			now_height+=3;
  			  x++;
			//std::cout<<"di "<<x<<"tian, sheng yu gao du wei"<<height<<std::endl;
			RCLCPP_INFO(this->get_logger(), "第 %d 天，当前高度:%d 米", x, now_height);
			response->current_height=now_height;
			response->days=x;
		}
        	response->days = x;
       		RCLCPP_INFO(this->get_logger(), "小车成功达到目标高度%d米，所需天数:%d",response->days, response->current_height)	;
		//std::cout<<"!woqu"<<std::endl;
	}	
};

int main(int argc,char **argv) {
    rclcpp::init(argc,argv);
    auto node = std::make_shared<Carservice>("Car_service");
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}
