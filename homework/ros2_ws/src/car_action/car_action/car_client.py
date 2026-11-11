import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

from action_msgs.msg import GoalStatus
from car_interfaces.action import CarTask


class CarActionClient(Node):

    def __init__(self):
        super().__init__('car_action_client')

        self._action_client = ActionClient(
            self,
            CarTask,
            'car_task'
        )

    def send_goal(self):
        self._action_client.wait_for_server()

        # Goal只用于启动任务
        # 目标坐标和速度由服务端Parameter决定
        goal = CarTask.Goal()

        self.get_logger().info(
            '发送Action启动请求'
        )

        send_goal_future = self._action_client.send_goal_async(
            goal,
            feedback_callback=self.feedback_callback
        )

        rclpy.spin_until_future_complete(
            self,
            send_goal_future
        )

        goal_handle = send_goal_future.result()

        if goal_handle is None or not goal_handle.accepted:
            self.get_logger().error('目标被服务端拒绝')
            return

        result_future = goal_handle.get_result_async()

        rclpy.spin_until_future_complete(
            self,
            result_future
        )

        response = result_future.result()
        status = response.status
        result = response.result

        days = result.total_time_sec / 86400.0

        print('\n========== Action Result ==========')
        print(
            f'最终位置：'
            f'({result.final_position.x:.2f}, '
            f'{result.final_position.y:.2f})'
        )
        print(
            f'剩余距离：'
            f'{result.remaining_distance:.2f} m'
        )

        if status == GoalStatus.STATUS_SUCCEEDED:
            print('任务状态：SUCCEEDED')
            print(f'成功到达目标，所需天数：{days:.0f} 天')

        elif status == GoalStatus.STATUS_CANCELED:
            print('任务状态：CANCELED')
            print(f'取消前已经运动：{days:g} 天')

        elif status == GoalStatus.STATUS_ABORTED:
            print('任务状态：ABORTED')
            print('任务被新Goal抢占')

        else:
            print(f'其他状态，状态码：{status}')

    def feedback_callback(self, feedback_msg):
        feedback = feedback_msg.feedback

        self.get_logger().info(
            f'当前位置：'
            f'({feedback.current_position.x:.2f}, '
            f'{feedback.current_position.y:.2f})，'
            f'速度：'
            f'({feedback.current_velocity.x:.2f}, '
            f'{feedback.current_velocity.y:.2f}) m/天，'
            f'剩余距离：'
            f'{feedback.distance_to_target:.2f} m'
        )


def main(args=None):
    rclpy.init(args=args)

    node = CarActionClient()

    try:
        node.send_goal()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()