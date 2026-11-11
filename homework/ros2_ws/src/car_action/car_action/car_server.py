import math
import threading
from dataclasses import dataclass, field

import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node

from geometry_msgs.msg import Point, Vector3
from car_interfaces.action import CarTask


@dataclass
class GoalContext:
    goal_handle: object

    preempt_event: threading.Event = field(
        default_factory=threading.Event
    )
    finished_event: threading.Event = field(
        default_factory=threading.Event
    )

    days: int = 0


class CarActionServer(Node):

    REAL_SECONDS_PER_DAY = 1.0
    SIM_SECONDS_PER_DAY = 86400.0
    EPSILON = 1e-6

    def __init__(self):
        super().__init__('car_action_server')

        # 任务一：声明目标坐标和每天运动速度两个参数
        self.declare_parameter(
            'target_position',
            [0.0, 10.0]
        )
        self.declare_parameter(
            'speed_m_per_day',
            3.0
        )

        # 小车当前位置
        self._x = 0.0
        self._y = 0.0

        self._state_lock = threading.Lock()
        self._active_context = None

        self._action_server = ActionServer(
            self,
            CarTask,
            'car_task',
            execute_callback=self.execute_callback,
            goal_callback=self.goal_callback,
            cancel_callback=self.cancel_callback,
            callback_group=ReentrantCallbackGroup()
        )

        target = self.get_target_position()
        speed = self.get_speed()

        self.get_logger().info('小车 Action 服务端已启动')
        self.get_logger().info(
            f'初始目标：({target[0]:.2f}, {target[1]:.2f})'
        )
        self.get_logger().info(
            f'初始速度：{speed:.2f} m/天'
        )

    def get_target_position(self):
        """读取当前目标坐标参数。"""

        target = self.get_parameter(
            'target_position'
        ).value

        if len(target) != 2:
            self.get_logger().error(
                'target_position 必须包含两个数值：[x, y]'
            )
            return 0.0, 0.0

        return float(target[0]), float(target[1])

    def get_speed(self):
        """读取当前速度参数。"""

        speed = float(
            self.get_parameter(
                'speed_m_per_day'
            ).value
        )

        if speed < 0.0:
            self.get_logger().warn(
                '速度不能小于0，本次按照0处理'
            )
            return 0.0

        return speed

    def goal_callback(self, goal_request):
        # 现在目标坐标由Parameter决定，不再由Goal输入
        self.get_logger().info(
            '收到Action启动请求，目标坐标由参数决定'
        )
        return GoalResponse.ACCEPT

    def cancel_callback(self, goal_handle):
        self.get_logger().info('收到取消请求')
        return CancelResponse.ACCEPT

    def execute_callback(self, goal_handle):
        context = GoalContext(
            goal_handle=goal_handle
        )

        # 新Goal抢占旧Goal
        with self._state_lock:
            previous_context = self._active_context
            self._active_context = context

            if previous_context is not None:
                previous_context.preempt_event.set()

        if previous_context is not None:
            self.get_logger().warn(
                '新目标到达，正在终止旧目标'
            )
            previous_context.finished_event.wait(
                timeout=2.0
            )

        self.get_logger().info('开始执行Action任务')

        while True:
            if context.preempt_event.is_set():
                return self.finish_aborted(context)

            if goal_handle.is_cancel_requested:
                return self.finish_canceled(context)

            # 每次运动前重新读取参数
            # ros2 param set修改后，下一个周期即可生效
            target_x, target_y = self.get_target_position()
            speed = self.get_speed()

            preempted = False

            with self._state_lock:
                if self._active_context is not context:
                    preempted = True
                    x = self._x
                    y = self._y
                    vx = 0.0
                    vy = 0.0
                    remaining = 0.0
                    finished = False

                else:
                    dx = target_x - self._x
                    dy = target_y - self._y
                    distance = math.hypot(dx, dy)
                    

                    if distance <= self.EPSILON:
                        finished = True
                        remaining = 0.0
                        vx = 0.0
                        vy = 0.0

                    else:
                        # 使用Parameter中的速度
                        step = min(speed, distance)

                        ux = dx / distance
                        uy = dy / distance

                        # step = distance /3

                        self._x += step * ux
                        self._y += step * uy

                        context.days += 1

                        vx = step * ux
                        vy = step * uy

                        remaining = math.hypot(
                            target_x - self._x,
                            target_y - self._y
                        )

                        if remaining <= self.EPSILON:
                            remaining = 0.0

                        finished = remaining <= self.EPSILON

                    x = self._x
                    y = self._y

            if preempted:
                return self.finish_aborted(context)

            feedback = CarTask.Feedback()
            feedback.current_position = Point(
                x=x,
                y=y,
                z=0.0
            )
            feedback.current_velocity = Vector3(
                x=vx,
                y=vy,
                z=0.0
            )
            feedback.distance_to_target = remaining

            goal_handle.publish_feedback(feedback)

            self.get_logger().info(
                f'第 {context.days} 天：'
                f'位置=({x:.2f}, {y:.2f})，'
                f'目标=({target_x:.2f}, {target_y:.2f})，'
                f'速度={speed:.2f} m/天，'
                f'剩余距离={remaining:.2f} m'
            )

            if finished:
                return self.finish_succeeded(
                    context,
                    x,
                    y
                )

            context.preempt_event.wait(
                self.REAL_SECONDS_PER_DAY
            )

    def make_result(self, context, x, y):
        target_x, target_y = self.get_target_position()

        result = CarTask.Result()
        result.final_position = Point(
            x=x,
            y=y,
            z=0.0
        )
        result.total_time_sec = (
            context.days * self.SIM_SECONDS_PER_DAY
        )
        result.remaining_distance = math.hypot(
            target_x - x,
            target_y - y
        )

        if result.remaining_distance <= self.EPSILON:
            result.remaining_distance = 0.0

        return result

    def make_current_result(self, context):
        with self._state_lock:
            x = self._x
            y = self._y

        return self.make_result(context, x, y)

    def clear_active_context(self, context):
        with self._state_lock:
            if self._active_context is context:
                self._active_context = None

    def finish_succeeded(self, context, x, y):
        result = self.make_result(context, x, y)

        context.goal_handle.succeed()
        self.clear_active_context(context)

        self.get_logger().info(
            f'目标完成，总耗时：{context.days} 天'
        )

        context.finished_event.set()
        return result

    def finish_canceled(self, context):
        result = self.make_current_result(context)

        context.goal_handle.canceled()
        self.clear_active_context(context)

        self.get_logger().warn(
            '目标已取消：'
            f'停止位置=('
            f'{result.final_position.x:.2f}, '
            f'{result.final_position.y:.2f})，'
            f'剩余距离={result.remaining_distance:.2f} m'
        )

        context.finished_event.set()
        return result

    def finish_aborted(self, context):
        result = self.make_current_result(context)

        context.goal_handle.abort()
        self.clear_active_context(context)

        self.get_logger().warn(
            '旧目标被新目标抢占'
        )

        context.finished_event.set()
        return result


def main(args=None):
    rclpy.init(args=args)

    node = CarActionServer()

    executor = MultiThreadedExecutor()
    executor.add_node(node)

    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()