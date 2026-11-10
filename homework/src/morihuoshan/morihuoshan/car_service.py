import rclpy
from rclpy.node import Node
from lr_interfaces.srv import Climb

class ServiceServer01(Node):
    def __init__(self,name):
        super().__init__(name)
        self.get_logger().info("Node has been started:%s!" % name)
        self.server_ = self.create_service(Climb,"climb_service",self.server_callback)

    def server_callback(self,request,response):
        self.get_logger().info(f"Received request, target height: {request.target_height}")
        target = request.target_height
        step = 3
        if target % step == 0:
            response.days = target // step
        else:
            response.days = target // step + 1
        response.current_height = target
        return response


def main(args=None):
    rclpy.init(args=args)
    node = ServiceServer01("service_server01")
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
