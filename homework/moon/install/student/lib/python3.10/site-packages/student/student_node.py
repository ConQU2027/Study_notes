import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class StudentNode(Node):
    def __init__(self):
        super().__init__('waya')                     # rqt_graph 里显示为 /waya
        self.get_logger().info('大家好，我是waya')

        # 发布者：往 makeboat 话题发 boat 消息
        self.pub = self.create_publisher(String, 'makeboat', 10)

        # 订阅者：监听 niluo 发的 mingyue 话题
        self.sub = self.create_subscription(String, 'mingyue', self.class_callback, 10)

    def class_callback(self, msg):
        self.get_logger().info('我上了课，我要多做1kg船！')
        boat = String()
        boat.data = '1kg船'        # 这就是题目说的 boat.data
        self.pub.publish(boat)


def main(args=None):
    rclpy.init(args=args)
    node = StudentNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()