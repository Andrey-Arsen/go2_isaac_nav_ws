#!/usr/bin/env python3
import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node
from tf2_ros import TransformBroadcaster
from geometry_msgs.msg import TransformStamped


class OdomTfBridge(Node):
    def __init__(self):
        super().__init__("odom_tf_bridge")

        self.declare_parameter("input_odom_topic", "/utlidar/robot_odom")
        self.declare_parameter("output_odom_topic", "/odom")
        self.declare_parameter("odom_frame", "odom")
        self.declare_parameter("base_frame", "base_link")
        self.declare_parameter("publish_odom", True)
        self.declare_parameter("publish_tf", True)

        self.input_topic = self.get_parameter("input_odom_topic").value
        self.output_topic = self.get_parameter("output_odom_topic").value
        self.odom_frame = self.get_parameter("odom_frame").value
        self.base_frame = self.get_parameter("base_frame").value
        self.publish_odom = self.get_parameter("publish_odom").value
        self.publish_tf = self.get_parameter("publish_tf").value

        self.odom_pub = self.create_publisher(Odometry, self.output_topic, 20)
        self.tf_broadcaster = TransformBroadcaster(self)
        self.sub = self.create_subscription(
            Odometry,
            self.input_topic,
            self.odom_callback,
            20,
        )

        self.get_logger().info(
            f"Bridging {self.input_topic} -> {self.output_topic}, "
            f"TF {self.odom_frame} -> {self.base_frame}"
        )

    def odom_callback(self, msg):
        bridged = Odometry()
        bridged.header = msg.header
        bridged.child_frame_id = msg.child_frame_id
        bridged.pose = msg.pose
        bridged.twist = msg.twist

        bridged.header.frame_id = self.odom_frame
        bridged.child_frame_id = self.base_frame

        if self.publish_odom:
            self.odom_pub.publish(bridged)

        if self.publish_tf:
            transform = TransformStamped()
            transform.header.stamp = bridged.header.stamp
            transform.header.frame_id = self.odom_frame
            transform.child_frame_id = self.base_frame
            transform.transform.translation.x = bridged.pose.pose.position.x
            transform.transform.translation.y = bridged.pose.pose.position.y
            transform.transform.translation.z = bridged.pose.pose.position.z
            transform.transform.rotation = bridged.pose.pose.orientation
            self.tf_broadcaster.sendTransform(transform)


def main():
    rclpy.init()
    node = OdomTfBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
