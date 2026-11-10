import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from geometry_msgs.msg import Point
from lr_interfaces.action import MoveToPoint

class CarActionClient(Node):
    def __init__(self):
        super().__init__("car_action_client")
        self._action_client = ActionClient(self, MoveToPoint, "move_to_point")
        self.get_logger().info("waiting for action server...")

    def send_goal(self, x, y):
        goal_msg = MoveToPoint.Goal()
        goal_msg.target_position = Point(x=x, y=y)
        self._action_client.wait_for_server()
        self.get_logger().info(f"sent goal: x={x}, y={y}")
        send_future = self._action_client.send_goal_async(
            goal_msg,
            feedback_callback=self.feedback_callback
        )
        send_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().info("goal is rejected")
            return
        res_future = goal_handle.get_result_async()
        res_future.add_done_callback(self.result_callback)

    def feedback_callback(self, feedback):
        fb = feedback.feedback
        self.get_logger().info(
            f"feedbak:current:x={fb.current_position.x:.2f},y={fb.current_position.y:.2f},rest distance={fb.distance_to_target:.2f},status={fb.status}"
        )

    def result_callback(self, future):
        res = future.result().result
        self.get_logger().info(
            f"the task has been completed! final position: x={res.final_position.x:.2f}, y={res.final_position.y:.2f}, time elapsed={res.total_time_sec:.2f}s, remaining distance={res.remain_distance:.2f}"
        )

def main():
    rclpy.init()
    client = CarActionClient()
    client.send_goal(2.0, 1.0)
    rclpy.spin(client)
    client.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    main()
