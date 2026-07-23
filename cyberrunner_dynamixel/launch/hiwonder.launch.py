from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    package_share = Path(get_package_share_directory("cyberrunner_dynamixel"))
    default_config = str(package_share / "config" / "hiwonder.yaml")

    config_arg = DeclareLaunchArgument(
        "config",
        default_value=default_config,
        description="Hiwonder controller parameter file",
    )

    actuator = Node(
        package="cyberrunner_dynamixel",
        executable="hiwonder_compat_node.py",
        name="cyberrunner_hiwonder_compat",
        output="screen",
        parameters=[LaunchConfiguration("config")],
    )

    return LaunchDescription([config_arg, actuator])
