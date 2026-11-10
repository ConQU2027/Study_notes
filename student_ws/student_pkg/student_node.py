import rclpy
from rclpy.node import Node
from std_msgs.msg import String

class StudentNode(Node):
    def __init__(self):
        super().__init__("student_node")
        self.get_logger().info("Hello,I'm student")
        self.sub_mingyue = self.create_subscription(String,"mingyue",self.mingyue_callback,10)
        self.pub_makeboat = self.create_publisher(String, "makeboat",10)
        self.timer = self.create_timer(5.0, self.pubboat_callback)
        self.boat_cnt = 1

    def mingyue_callback(self, msg):
        self.get_logger().info(f"student receive mingyue:{msg.data}")

    def pubboat_callback(self):
        msg = String()
        msg.data = f"quality of our boat is increased by:{self.boat_cnt}kg!"
        self.pub_makeboat.publish(msg)
        self.get_logger().info(f"student publish boat.data:{msg.data}")
        self.boat_cnt +=1

def main(args=None):
    rclpy.init(args=args)
    node = StudentNode()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
