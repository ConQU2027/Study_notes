import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class NiluoNode(Node):
    def __init__(self):
        super().__init__('niluo')                      # 节点名字，rqt_graph 里显示为 /niluo
        self.get_logger().info('大家好，我是niluo')

        self.count = 0        # 上了几节课
        self.weight = 0       # 船的负重

        # 零件1：发布者——往 mingyue 话题发 String 消息，10 是队列长度（照抄即可）
        self.pub = self.create_publisher(String, 'mingyue', 10)

        # 零件2：定时器——每 5.0 秒自动调用一次 timer_callback
        self.timer = self.create_timer(5.0, self.timer_callback)

        # 零件3：订阅者——监听 makeboat 话题，收到消息就调用 boat_callback
        self.sub = self.create_subscription(String, 'makeboat', self.boat_callback, 10)

    def timer_callback(self):
        msg = String()
        msg.data = '我上了第%d节工程设计' % self.count
        self.pub.publish(msg)                                  # 真正发出去
        self.get_logger().info('罗の课：第%d次上工程设计课' % self.count)
        self.count += 1

    def boat_callback(self, boat):                            # boat 就是收到的消息
        self.weight += 1
        self.get_logger().info('收到%s，我们做的船负重增加到%d!' % (boat.data, self.weight))


def main(args=None):
    rclpy.init(args=args)
    node = NiluoNode()
    rclpy.spin(node)        # 让节点一直转着等回调，不会跑完就退出
    node.destroy_node()
    rclpy.shutdown()