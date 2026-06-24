from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    use_sim_time = LaunchConfiguration("use_sim_time")
    cloud_in = LaunchConfiguration("cloud_in")
    scan = LaunchConfiguration("scan")
    target_frame = LaunchConfiguration("target_frame")

    return LaunchDescription([
        DeclareLaunchArgument(
            "use_sim_time",
            default_value="true",
        ),
        DeclareLaunchArgument(
            "cloud_in",
            default_value="/unitree_go2/lidar/point_cloud",
        ),
        DeclareLaunchArgument(
            "scan",
            default_value="/scan",
        ),
        DeclareLaunchArgument(
            "target_frame",
            default_value="unitree_go2/base_link",
        ),
        DeclareLaunchArgument(
            "transform_tolerance",
            default_value="0.5",
        ),
        DeclareLaunchArgument(
            "min_height",
            default_value="0.05",
        ),
        DeclareLaunchArgument(
            "max_height",
            default_value="1.2",
        ),
        DeclareLaunchArgument(
            "angle_min",
            default_value="-3.14",
        ),
        DeclareLaunchArgument(
            "angle_max",
            default_value="3.14",
        ),
        DeclareLaunchArgument(
            "angle_increment",
            default_value="0.0087",
        ),
        DeclareLaunchArgument(
            "scan_time",
            default_value="0.1",
        ),
        DeclareLaunchArgument(
            "range_min",
            default_value="0.2",
        ),
        DeclareLaunchArgument(
            "range_max",
            default_value="10.0",
        ),

        Node(
            package="pointcloud_to_laserscan",
            executable="pointcloud_to_laserscan_node",
            name="pointcloud_to_laserscan",
            output="screen",
            parameters=[{
                "use_sim_time": use_sim_time,
                "target_frame": target_frame,
                "transform_tolerance": LaunchConfiguration("transform_tolerance"),
                "min_height": LaunchConfiguration("min_height"),
                "max_height": LaunchConfiguration("max_height"),
                "angle_min": LaunchConfiguration("angle_min"),
                "angle_max": LaunchConfiguration("angle_max"),
                "angle_increment": LaunchConfiguration("angle_increment"),
                "scan_time": LaunchConfiguration("scan_time"),
                "range_min": LaunchConfiguration("range_min"),
                "range_max": LaunchConfiguration("range_max"),
            }],
            remappings=[
                ("cloud_in", cloud_in),
                ("scan", scan),
            ],
        ),
    ])
