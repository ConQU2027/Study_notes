import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer
from rclpy.action.server import ServerGoalHandle
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.parameter import Parameter
from lr_interfaces.action import MoveToPoint
import math
import time


class Robot():
    def __init__(self):
        self.current_x = 0.0
        self.current_y = 0.0
        self.target_x = 0.0
        self.target_y = 0.0
        self.speed = 0.2
        self.status = MoveToPoint.Feedback.STATUS_STOP

    def is_arrive(self):
        dist = math.hypot(self.target_x - self.current_x, self.target_y - self.current_y)
        return dist < 0.01

    def move_one_step(self):
        dx = self.target_x - self.current_x
        dy = self.target_y - self.current_y
        dist = math.hypot(dx, dy)
        if dist < 0.001:
            self.status = MoveToPoint.Feedback.STATUS_STOP
            return
        dir_x = dx / dist
        dir_y = dy / dist
        step_len = self.speed * 0.1
        self.current_x += dir_x * step_len
        self.current_y += dir_y * step_len
        self.status = MoveToPoint.Feedback.STATUS_MOVING


class RobotActionParamServer(Node):
    def __init__(self):
        super().__init__("robot_action_param_server")
        self.cb_group = ReentrantCallbackGroup()
        self.robot = Robot()

        # Declare parameters
        self.declare_parameter("target_x", 1.0)
        self.declare_parameter("target_y", 1.0)
        self.declare_parameter("speed", 0.2)

        # Load initial parameter value
        self.robot.target_x = self.get_parameter("target_x").value
        self.robot.target_y = self.get_parameter("target_y").value
        self.robot.speed = self.get_parameter("speed").value

        # Register parameter change callback
        self.add_on_set_parameters_callback(self.param_change_callback)

        # Create action server
        self.action_server = ActionServer(
            self,
            MoveToPoint,
            "move_robot",
            self.execute_callback,
            callback_group=self.cb_group
        )
        self.get_logger().info("Action server with parameter enabled started!")
        self.get_logger().info(f"Initial params target_x={self.robot.target_x}, target_y={self.robot.target_y}, speed={self.robot.speed}")

    def param_change_callback(self, params: list[Parameter]):
        for p in params:
            if p.name == "target_x":
                self.robot.target_x = p.value
                self.get_logger().info(f"[Param Update] target_x = {p.value}")
            elif p.name == "target_y":
                self.robot.target_y = p.value
                self.get_logger().info(f"[Param Update] target_y = {p.value}")
            elif p.name == "speed":
                self.robot.speed = p.value
                self.get_logger().info(f"[Param Update] speed = {p.value}")
        return rclpy.parameter.SetParametersResult(successful=True)

    def execute_callback(self, goal_handle: ServerGoalHandle):
        self.get_logger().info("Start moving, target read from parameter")
        feedback = MoveToPoint.Feedback()
        result = MoveToPoint.Result()

        while True:
            self.robot.move_one_step()
            if self.robot.is_arrive():
                self.robot.status = MoveToPoint.Feedback.STATUS_FINISH
                break
            if goal_handle.is_cancel_requested:
                self.robot.status = MoveToPoint.Feedback.STATUS_CANCEL
                goal_handle.canceled()
                self.get_logger().info("Task canceled")
                break

            feedback.pose_x = self.robot.current_x
            feedback.pose_y = self.robot.current_y
            feedback.status = self.robot.status
            feedback.remain_dist = math.hypot(self.robot.target_x - self.robot.current_x, self.robot.current_y)
            goal_handle.publish_feedback(feedback)
            time.sleep(0.1)

        result.final_x = self.robot.current_x
        result.final_y = self.robot.current_y
        if not goal_handle.is_cancel_requested:
            goal_handle.succeed()
            self.get_logger().info("Task finished successfully")
        return result


def main(args=None):
    rclpy.init(args=args)
    node = RobotActionParamServer()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
