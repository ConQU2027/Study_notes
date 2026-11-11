import rclpy
from rclpy.node import Node
from lr_interfaces.srv import CarHeight


class CarService(Node):
    def __init__(self):
        super().__init__('car_service')
        # 记录小车的当前高度和已用天数
        self.current_height = 0
        self.days = 0
        # 创建服务，服务名叫 car_height
        self.srv = self.create_service(CarHeight, 'car_height', self.climb_callback)
        self.get_logger().info('服务端已启动，小车每次往上爬 3 米')

    def climb_callback(self, request, response):
        # 每次收到请求，小车就往上爬 3 米，天数 +1
        self.current_height += 3
        self.days += 1
        # 把结果填进 response 返回给客户端
        response.current_height = self.current_height
        response.days = self.days
        self.get_logger().info(
            f'目标高度: {request.target_height} m | '
            f'当前高度: {self.current_height} m | 已用天数: {self.days}')
        return response


def main(args=None):
    rclpy.init(args=args)
    node = CarService()
    rclpy.spin(node)
    rclpy.shutdown()