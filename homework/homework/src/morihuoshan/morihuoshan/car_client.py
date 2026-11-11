import rclpy
from rclpy.node import Node
from lr_interfaces.srv import CarHeight


class CarClient(Node):
    def __init__(self):
        super().__init__('car_client')
        # 创建客户端，服务名必须和服务端一致
        self.client = self.create_client(CarHeight, 'car_height')
        while not self.client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('等待服务端启动...')
        self.req = CarHeight.Request()

    def send_request(self, target_height):
        self.req.target_height = target_height
        future = self.client.call_async(self.req)
        rclpy.spin_until_future_complete(self, future)
        return future.result()


def main(args=None):
    rclpy.init(args=args)
    node = CarClient()

    # 启动时让用户输入目标高度
    target = int(input('请输入目标高度(m): '))

    # 不断发请求，每发一次小车爬 3 米，直到达到目标高度
    response = node.send_request(target)
    while response.current_height < target:
        node.get_logger().info(f'当前高度 {response.current_height} m，还没到，继续爬...')
        response = node.send_request(target)

    node.get_logger().info(f'达到目标高度 {target} m，一共用了 {response.days} 天！')

    node.destroy_node()
    rclpy.shutdown()