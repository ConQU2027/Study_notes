import rclpy
from rclpy.node import Node
from lr_interfaces.srv import Climb

class ServiceClient01(Node):
    def __init__(self,name):
        super().__init__(name)
        self.get_logger().info("Node has been started")
        self.client_ = self.create_client(Climb, "climb_service")

    def result_callback(self,result_future):
        response=result_future.result()
        self.get_logger().info(f"Received response, current height: {response.current_height}, days needed: {response.days}")

    def send_request(self,target_height):
        while rclpy.ok() and not self.client_.wait_for_service(timeout_sec=1.0):
            self.get_logger().info("Waiting for service...")
        request = Climb.Request()
        request.target_height = target_height
        self.client_.call_async(request).add_done_callback(self.result_callback)

def main(args=None):
    rclpy.init(args=args)
    node = ServiceClient01("service_client01")
    target_height = 20
    node.send_request(target_height)
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()