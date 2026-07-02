import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, SetEnvironmentVariable
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.descriptions import ParameterFile
from nav2_common.launch import RewrittenYaml


def generate_launch_description():
    pkg_dir = get_package_share_directory("go2_isaac_navigation")

    use_sim_time = LaunchConfiguration("use_sim_time")
    map_yaml_file = LaunchConfiguration("map")
    params_file = LaunchConfiguration("params_file")
    autostart = LaunchConfiguration("autostart")
    publish_laser_tf = LaunchConfiguration("publish_laser_tf")
    enable_cmd_bridge = LaunchConfiguration("enable_cmd_bridge")

    configured_params = ParameterFile(
        RewrittenYaml(
            source_file=params_file,
            root_key="",
            param_rewrites={
                "use_sim_time": use_sim_time,
                "yaml_filename": map_yaml_file,
            },
            convert_types=True,
        ),
        allow_substs=True,
    )

    lifecycle_nodes = [
        "map_server",
        "amcl",
        "controller_server",
        "smoother_server",
        "planner_server",
        "behavior_server",
        "bt_navigator",
        "waypoint_follower",
    ]

    return LaunchDescription([
        SetEnvironmentVariable("RCUTILS_LOGGING_BUFFERED_STREAM", "1"),

        DeclareLaunchArgument("use_sim_time", default_value="false"),
        DeclareLaunchArgument(
            "map",
            default_value="/home/unitree/maps/go2_d500_map.yaml",
        ),
        DeclareLaunchArgument(
            "params_file",
            default_value=os.path.join(pkg_dir, "config", "go2_real_nav2.yaml"),
        ),
        DeclareLaunchArgument("autostart", default_value="true"),
        DeclareLaunchArgument("publish_laser_tf", default_value="true"),
        DeclareLaunchArgument("enable_cmd_bridge", default_value="true"),
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
                LaunchConfiguration("laser_x"),
                LaunchConfiguration("laser_y"),
                LaunchConfiguration("laser_z"),
                LaunchConfiguration("laser_yaw"),
                LaunchConfiguration("laser_pitch"),
                LaunchConfiguration("laser_roll"),
                LaunchConfiguration("base_frame"),
                LaunchConfiguration("laser_frame"),
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
            package="go2_isaac_navigation",
            executable="cmd_vel_to_sport_bridge.py",
            name="cmd_vel_to_sport_bridge",
            output="screen",
            parameters=[{
                "cmd_vel_topic": "/cmd_vel",
                "sport_request_topic": "/api/sport/request",
                "max_vx": 0.25,
                "max_vy": 0.0,
                "max_wz": 0.6,
                "command_timeout": 0.5,
            }],
            condition=IfCondition(enable_cmd_bridge),
        ),

        Node(
            package="nav2_map_server",
            executable="map_server",
            name="map_server",
            output="screen",
            parameters=[configured_params],
        ),

        Node(
            package="nav2_amcl",
            executable="amcl",
            name="amcl",
            output="screen",
            parameters=[configured_params],
        ),

        Node(
            package="nav2_controller",
            executable="controller_server",
            name="controller_server",
            output="screen",
            parameters=[configured_params],
        ),

        Node(
            package="nav2_smoother",
            executable="smoother_server",
            name="smoother_server",
            output="screen",
            parameters=[configured_params],
        ),

        Node(
            package="nav2_planner",
            executable="planner_server",
            name="planner_server",
            output="screen",
            parameters=[configured_params],
        ),

        Node(
            package="nav2_behaviors",
            executable="behavior_server",
            name="behavior_server",
            output="screen",
            parameters=[configured_params],
        ),

        Node(
            package="nav2_bt_navigator",
            executable="bt_navigator",
            name="bt_navigator",
            output="screen",
            parameters=[configured_params],
        ),

        Node(
            package="nav2_waypoint_follower",
            executable="waypoint_follower",
            name="waypoint_follower",
            output="screen",
            parameters=[configured_params],
        ),

        Node(
            package="nav2_lifecycle_manager",
            executable="lifecycle_manager",
            name="lifecycle_manager_navigation",
            output="screen",
            parameters=[
                {"use_sim_time": use_sim_time},
                {"autostart": autostart},
                {"node_names": lifecycle_nodes},
            ],
        ),
    ])
