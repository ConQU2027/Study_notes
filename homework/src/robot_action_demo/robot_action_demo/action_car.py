import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer
from rclpy.action.server import ServerGoalHandle
from rclpy.callback_groups import ReentrantCallbackGroup
from geometry_msgs.msg import Point, Vector3
from lr_interfaces.action import MoveToPoint
import math
import time


class Car():
    def __init__(self) -> None:
        self.current_pose_X = 0.0
        self.current_pose_Y = 0.0
        self.target_pose_X = 0.0
        self.target_pose_Y = 0.0
        self.move_distance = 0.0
        self.status_ = MoveToPoint.Feedback.STATUS_STOP

    def get_status(self):
        return self.status_

    def get_current_pose(self):
        return self.current_pose_X, self.current_pose_Y

    def close_goal(self):
        dx = self.target_pose_X - self.current_pose_X
        dy = self.target_pose_Y - self.current_pose_Y
        return math.hypot(dx, dy) < 0.01
        #study "gougudingli"

    def stop_move(self):
        self.status_ = MoveToPoint.Feedback.STATUS_STOP

    def move_step(self):
        dx = self.target_pose_X - self.current_pose_X
        dy = self.target_pose_Y - self.current_pose_Y
        self.move_distance = math.hypot(dx, dy)
        if self.move_distance < 0.1:
            return
        direct_x = dx / self.move_distance
        direct_y = dy / self.move_distance
        step = 0.2 * 0.1  
        self.current_pose_X += direct_x * step
        self.current_pose_Y += direct_y * step
        self.status_ = MoveToPoint.Feedback.STATUS_MOVING


class CarActionServer(Node):
    def __init__(self):
        super().__init__("car_action_server")
        self.callback_group = ReentrantCallbackGroup()
        self.car = Car()

        self._action_server = ActionServer(
            self,
            MoveToPoint,
            "move_to_point",
            self.execute_callback,
            callback_group=self.callback_group,
            goal_callback=self.goal_callback
        )
        self.get_logger().info("Car Action Server has been started")

    def goal_callback(self, goal_request):
        self.get_logger().info("Received goal request, fight for new goal")
        return rclpy.action.GoalResponse.ACCEPT

    def execute_callback(self, goal_handle: ServerGoalHandle):
        self.get_logger().info("start moving task...")
        target = goal_handle.request.target_position
        
        self.car.target_pose_X = target.x
        self.car.target_pose_Y = target.y

        feedback_msg = MoveToPoint.Feedback()
        result_msg = MoveToPoint.Result()
        start_time = time.time()

        while True:
            self.car.move_step()
            if self.car.close_goal():
                self.car.stop_move()
                break
            
            if goal_handle.is_cancel_requested:
                self.car.stop_move()
                goal_handle.canceled()
                self.get_logger().info("the task has been canceled!")
                break

            
            x, y = self.car.get_current_pose()
            feedback_msg.current_position.x = x
            feedback_msg.current_position.y = y
            feedback_msg.current_vel.x = 0.2
            feedback_msg.current_vel.y = 0.0
            dx = self.car.target_pose_X - x
            dy = self.car.target_pose_Y - y
            feedback_msg.distance_to_target = math.hypot(dx, dy)
            feedback_msg.status = self.car.get_status()
            goal_handle.publish_feedback(feedback_msg)

            time.sleep(0.1)

        end_time = time.time()
        total_time = end_time - start_time
        x_final, y_final = self.car.get_current_pose()
        result_msg.final_position.x = x_final
        result_msg.final_position.y = y_final
        result_msg.total_time_sec = total_time
        final_dx = self.car.target_pose_X - x_final
        final_dy = self.car.target_pose_Y - y_final
        result_msg.remain_distance = math.hypot(final_dx, final_dy)

        if not goal_handle.is_cancel_requested:
            goal_handle.succeed()
            self.get_logger().info("the task has been completed successfully!")
        return result_msg


def main():
    rclpy.init()
    node = CarActionServer()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    main()
