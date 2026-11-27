from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def _create_camera_node(context):
    parameters = [LaunchConfiguration("params_file").perform(context)]
    serial_port = LaunchConfiguration("serial_port").perform(context).strip()
    if serial_port:
        parameters.append({"serial_port": serial_port})
    return [
        Node(
            package="openmv_camera",
            executable="openmv_camera_node",
            name="openmv_camera",
            namespace="camera",
            parameters=parameters,
            output="screen",
            emulate_tty=True,
        )
    ]


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "params_file",
                default_value=PathJoinSubstitution(
                    [FindPackageShare("openmv_camera"), "config", "live.yaml"]
                ),
                description="OpenMV live camera parameters",
            ),
            DeclareLaunchArgument(
                "serial_port",
                default_value="",
                description="Optional VCP override; empty preserves the YAML value",
            ),
            OpaqueFunction(function=_create_camera_node),
        ]
    )
