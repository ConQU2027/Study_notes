import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped

class ControlNode(Node):
    def __init__(self):
        super().__init__('control_node')
        self.target_sub = self.create_subscription(PoseStamped, '/vision/target', self.target_callback, 10)
        self.get_logger().info("control_node has started")

    def target_callback(self, msg):
        x = msg.pose.position.x
        y = msg.pose.position.y
        z = msg.pose.position.z
        self.get_logger().info(f"receive goal")

def main(args=None):
    rclpy.init(args=args)
    node = ControlNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()