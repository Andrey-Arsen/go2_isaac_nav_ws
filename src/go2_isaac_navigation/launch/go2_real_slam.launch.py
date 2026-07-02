import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, SetEnvironmentVariable
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_dir = get_package_share_directory("go2_isaac_navigation")

    slam_params_file = LaunchConfiguration("slam_params_file")
    publish_laser_tf = LaunchConfiguration("publish_laser_tf")
    laser_x = LaunchConfiguration("laser_x")
    laser_y = LaunchConfiguration("laser_y")
    laser_z = LaunchConfiguration("laser_z")
    laser_yaw = LaunchConfiguration("laser_yaw")
    laser_pitch = LaunchConfiguration("laser_pitch")
    laser_roll = LaunchConfiguration("laser_roll")
    base_frame = LaunchConfiguration("base_frame")
    laser_frame = LaunchConfiguration("laser_frame")

    return LaunchDescription([
        SetEnvironmentVariable("RCUTILS_LOGGING_BUFFERED_STREAM", "1"),

        DeclareLaunchArgument(
            "slam_params_file",
            default_value=os.path.join(pkg_dir, "config", "go2_real_slam.yaml"),
        ),
        DeclareLaunchArgument("publish_laser_tf", default_value="true"),
        DeclareLaunchArgument("base_frame", default_value="base_link"),
        DeclareLaunchArgument("laser_frame", default_value="base_laser"),
        DeclareLaunchArgument("laser_x", default_value="0.0"),
        DeclareLaunchArgument("laser_y", default_value="0.0"),
        DeclareLaunchArgument("laser_z", default_value="0.25"),
        DeclareLaunchArgument("laser_yaw", default_value="-1.5708"),
        DeclareLaunchArgument("laser_pitch", default_value="0.0"),
        DeclareLaunchArgument("laser_roll", default_value="0.0"),

        Node(
            package="tf2_ros",
            executable="static_transform_publisher",
            name="base_to_laser_tf",
            arguments=[
                laser_x,
                laser_y,
                laser_z,
                laser_yaw,
                laser_pitch,
                laser_roll,
                base_frame,
                laser_frame,
            ],
            condition=IfCondition(publish_laser_tf),
            output="screen",
        ),

        Node(
            package="go2_isaac_navigation",
            executable="odom_tf_bridge.py",
            name="odom_tf_bridge",
            output="screen",
            parameters=[{
                "input_odom_topic": "/utlidar/robot_odom",
                "output_odom_topic": "/odom",
                "odom_frame": "odom",
                "base_frame": "base_link",
                "publish_odom": True,
                "publish_tf": True,
            }],
        ),

        Node(
            package="slam_toolbox",
            executable="async_slam_toolbox_node",
            name="slam_toolbox",
            output="screen",
            parameters=[slam_params_file],
        ),
    ])
