#!/usr/bin/env python3
import json
import math
import time

from geometry_msgs.msg import Twist
import rclpy
from rclpy.node import Node

try:
    from unitree_api.msg import Request
except ImportError:
    Request = None


SPORT_API_ID_MOVE = 1008
SPORT_API_ID_STOP_MOVE = 1003


class CmdVelToSportBridge(Node):
    def __init__(self):
        super().__init__("cmd_vel_to_sport_bridge")

        if Request is None:
            raise RuntimeError(
                "unitree_api/msg/Request is not available. "
                "Run this node on the Go2 ROS environment where unitree_api is installed."
            )

        self.declare_parameter("cmd_vel_topic", "/cmd_vel")
        self.declare_parameter("sport_request_topic", "/api/sport/request")
        self.declare_parameter("max_vx", 0.25)
        self.declare_parameter("max_vy", 0.0)
        self.declare_parameter("max_wz", 0.6)
        self.declare_parameter("deadband", 0.01)
        self.declare_parameter("command_timeout", 0.5)
        self.declare_parameter("publish_stop_on_timeout", True)

        self.cmd_vel_topic = self.get_parameter("cmd_vel_topic").value
        self.sport_request_topic = self.get_parameter("sport_request_topic").value
        self.max_vx = float(self.get_parameter("max_vx").value)
        self.max_vy = float(self.get_parameter("max_vy").value)
        self.max_wz = float(self.get_parameter("max_wz").value)
        self.deadband = float(self.get_parameter("deadband").value)
        self.command_timeout = float(self.get_parameter("command_timeout").value)
        self.publish_stop_on_timeout = bool(
            self.get_parameter("publish_stop_on_timeout").value
        )

        self.last_cmd_time = self.get_clock().now()
        self.sent_timeout_stop = False

        self.pub = self.create_publisher(Request, self.sport_request_topic, 10)
        self.sub = self.create_subscription(
            Twist,
            self.cmd_vel_topic,
            self.cmd_callback,
            10,
        )
        self.timer = self.create_timer(0.1, self.timeout_check)

        self.get_logger().info(
            f"Bridging {self.cmd_vel_topic} -> {self.sport_request_topic} "
            f"with limits vx={self.max_vx}, vy={self.max_vy}, wz={self.max_wz}"
        )

    def cmd_callback(self, msg):
        vx = clamp(msg.linear.x, -self.max_vx, self.max_vx)
        vy = clamp(msg.linear.y, -self.max_vy, self.max_vy)
        wz = clamp(msg.angular.z, -self.max_wz, self.max_wz)

        vx = apply_deadband(vx, self.deadband)
        vy = apply_deadband(vy, self.deadband)
        wz = apply_deadband(wz, self.deadband)

        self.pub.publish(make_sport_request(SPORT_API_ID_MOVE, {"x": vx, "y": vy, "z": wz}))
        self.last_cmd_time = self.get_clock().now()
        self.sent_timeout_stop = False

    def timeout_check(self):
        if not self.publish_stop_on_timeout or self.sent_timeout_stop:
            return

        elapsed = (self.get_clock().now() - self.last_cmd_time).nanoseconds / 1.0e9
        if elapsed > self.command_timeout:
            self.pub.publish(make_sport_request(SPORT_API_ID_MOVE, {"x": 0.0, "y": 0.0, "z": 0.0}))
            self.sent_timeout_stop = True


def make_sport_request(api_id, parameter):
    msg = Request()
    set_request_identity(msg, api_id)
    msg.parameter = json.dumps(parameter)
    if hasattr(msg, "binary"):
        msg.binary = []
    return msg


def set_request_identity(msg, api_id):
    # unitree_api/msg/Request mirrors the SDK Request_ structure:
    # header.identity.id, header.identity.api_id, header.policy.no_reply.
    header = msg.header
    if hasattr(header, "identity"):
        if hasattr(header.identity, "id"):
            header.identity.id = time.monotonic_ns()
        if hasattr(header.identity, "api_id"):
            header.identity.api_id = int(api_id)
    if hasattr(header, "lease") and hasattr(header.lease, "id"):
        header.lease.id = 0
    if hasattr(header, "policy"):
        if hasattr(header.policy, "priority"):
            header.policy.priority = 0
        if hasattr(header.policy, "no_reply"):
            header.policy.no_reply = True


def clamp(value, low, high):
    if math.isclose(low, high):
        return 0.0
    return max(low, min(high, value))


def apply_deadband(value, deadband):
    return 0.0 if abs(value) < deadband else value


def main():
    rclpy.init()
    node = CmdVelToSportBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.pub.publish(make_sport_request(SPORT_API_ID_MOVE, {"x": 0.0, "y": 0.0, "z": 0.0}))
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
