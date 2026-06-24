#!/usr/bin/env python3
import atexit
import math
import os
import signal
import subprocess
import threading
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped
from nav2_msgs.action import NavigateToPose
from pydantic import BaseModel
import rclpy
from rclpy.action import ActionClient
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.time import Time
from tf2_ros import Buffer, TransformException, TransformListener
import uvicorn


PACKAGE_NAME = "go2_isaac_navigation"
HOST = os.environ.get("WEB_HOST", "0.0.0.0")
PORT = int(os.environ.get("WEB_PORT", "8000"))
MAP_FRAME = os.environ.get("WEB_MAP_FRAME", "map")
BASE_FRAME = os.environ.get("WEB_BASE_FRAME", "base_link")
ROS_DISTRO = os.environ.get("ROS_DISTRO", "humble")


class PoseRequest(BaseModel):
    x: float
    y: float
    yaw: float


class LaunchProcess:
    def __init__(self, name, command):
        self.name = name
        self.command = command
        self.process = None

    def is_running(self):
        return self.process is not None and self.process.poll() is None


class ProcessManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._processes = {
            "scan": LaunchProcess(
                "scan",
                ["ros2", "launch", PACKAGE_NAME, "go2_scan.launch.py"],
            ),
            "slam": LaunchProcess(
                "slam",
                ["ros2", "launch", PACKAGE_NAME, "go2_slam.launch.py"],
            ),
            "nav": LaunchProcess(
                "nav",
                ["ros2", "launch", PACKAGE_NAME, "go2_isaac_nav.launch.py"],
            ),
            "rosbridge": LaunchProcess(
                "rosbridge",
                [
                    "ros2",
                    "launch",
                    "rosbridge_server",
                    "rosbridge_websocket_launch.xml",
                ],
            ),
        }

    def _launch(self, key, command=None):
        launch = self._processes[key]
        if launch.is_running():
            return {"name": key, "running": True, "pid": launch.process.pid}

        env = os.environ.copy()
        env.setdefault("ROS_DISTRO", ROS_DISTRO)
        launch.command = command or launch.command
        launch.process = subprocess.Popen(
            launch.command,
            env=env,
            preexec_fn=os.setsid,
        )
        return {"name": key, "running": True, "pid": launch.process.pid}

    def start_rosbridge(self):
        with self._lock:
            return self._launch("rosbridge")

    def start_scan(self):
        with self._lock:
            rosbridge = self._launch("rosbridge")
            scan = self._launch("scan")
            return {"rosbridge": rosbridge, "scan": scan}

    def start_slam(self):
        with self._lock:
            self._stop_unlocked("nav")
            rosbridge = self._launch("rosbridge")
            scan = self._launch("scan")
            slam = self._launch("slam")
            return {"rosbridge": rosbridge, "scan": scan, "slam": slam}

    def start_nav(self):
        with self._lock:
            self._stop_unlocked("slam")
            rosbridge = self._launch("rosbridge")
            scan = self._launch("scan")
            command = [
                "ros2",
                "launch",
                PACKAGE_NAME,
                "go2_isaac_nav.launch.py",
                "use_rviz:=false",
            ]
            map_path = os.environ.get("GO2_MAP")
            if map_path:
                command.append(f"map:={map_path}")
            nav = self._launch("nav", command)
            return {"rosbridge": rosbridge, "scan": scan, "nav": nav, "map": map_path or ""}

    def stop_all(self):
        with self._lock:
            results = {}
            for key in ("nav", "slam", "scan", "rosbridge"):
                results[key] = self._stop_unlocked(key)
            return results

    def _stop_unlocked(self, key):
        launch = self._processes[key]
        proc = launch.process
        if proc is None:
            return {"name": key, "running": False, "stopped": False}
        if proc.poll() is not None:
            launch.process = None
            return {"name": key, "running": False, "stopped": False}

        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGINT)
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            try:
                proc.wait(timeout=4)
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                proc.wait(timeout=2)
        finally:
            launch.process = None

        return {"name": key, "running": False, "stopped": True}

    def status(self):
        with self._lock:
            state = {}
            for key, launch in self._processes.items():
                state[key] = {
                    "running": launch.is_running(),
                    "pid": launch.process.pid if launch.is_running() else None,
                    "command": launch.command,
                }
            state["frames"] = {"map": MAP_FRAME, "base": BASE_FRAME}
            state["go2_map"] = os.environ.get("GO2_MAP", "")
            return state


class WebRosNode(Node):
    def __init__(self):
        super().__init__("go2_web_backend")
        self.map_frame = MAP_FRAME
        self.base_frame = BASE_FRAME
        self.pose_pub = self.create_publisher(PoseStamped, "/web_robot_pose", 10)
        self.initial_pose_pub = self.create_publisher(
            PoseWithCovarianceStamped, "/initialpose", 10
        )
        self.nav_client = ActionClient(self, NavigateToPose, "/navigate_to_pose")
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.create_timer(0.1, self._publish_robot_pose)

    def _publish_robot_pose(self):
        try:
            transform = self.tf_buffer.lookup_transform(
                self.map_frame,
                self.base_frame,
                Time(),
            )
        except TransformException:
            return

        pose = PoseStamped()
        pose.header.stamp = transform.header.stamp
        pose.header.frame_id = self.map_frame
        pose.pose.position.x = transform.transform.translation.x
        pose.pose.position.y = transform.transform.translation.y
        pose.pose.position.z = transform.transform.translation.z
        pose.pose.orientation = transform.transform.rotation
        self.pose_pub.publish(pose)

    def publish_initial_pose(self, x, y, yaw):
        msg = PoseWithCovarianceStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.map_frame
        msg.pose.pose.position.x = x
        msg.pose.pose.position.y = y
        msg.pose.pose.orientation = yaw_to_quaternion(yaw)
        msg.pose.covariance[0] = 0.25
        msg.pose.covariance[7] = 0.25
        msg.pose.covariance[35] = 0.0685
        self.initial_pose_pub.publish(msg)
        return {"published": True, "topic": "/initialpose"}

    def send_nav_goal(self, x, y, yaw):
        if not self.nav_client.wait_for_server(timeout_sec=2.0):
            raise RuntimeError("Nav2 action server /navigate_to_pose is not available")

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()
        goal_msg.pose.header.frame_id = self.map_frame
        goal_msg.pose.pose.position.x = x
        goal_msg.pose.pose.position.y = y
        goal_msg.pose.pose.orientation = yaw_to_quaternion(yaw)

        event = threading.Event()
        result = {}

        def on_goal_response(future):
            goal_handle = future.result()
            result["accepted"] = bool(goal_handle.accepted)
            event.set()

        future = self.nav_client.send_goal_async(goal_msg)
        future.add_done_callback(on_goal_response)

        if not event.wait(timeout=4.0):
            return {"sent": True, "accepted": None}
        return {"sent": True, "accepted": result["accepted"]}


def yaw_to_quaternion(yaw):
    q = PoseStamped().pose.orientation
    q.z = math.sin(yaw * 0.5)
    q.w = math.cos(yaw * 0.5)
    return q


process_manager = ProcessManager()
ros_node = None
executor = None
executor_thread = None
app = FastAPI(title="Go2 Isaac Navigation Web UI")


@app.on_event("startup")
def startup():
    global ros_node, executor, executor_thread
    if not rclpy.ok():
        rclpy.init()
    ros_node = WebRosNode()
    executor = MultiThreadedExecutor()
    executor.add_node(ros_node)
    executor_thread = threading.Thread(target=executor.spin, daemon=True)
    executor_thread.start()
    process_manager.start_rosbridge()


@app.on_event("shutdown")
def shutdown():
    process_manager.stop_all()
    if executor is not None:
        executor.shutdown()
    if ros_node is not None:
        ros_node.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()


@app.get("/")
def index():
    share_dir = Path(get_package_share_directory(PACKAGE_NAME))
    return FileResponse(share_dir / "web" / "index.html")


@app.get("/api/status")
def status():
    return process_manager.status()


@app.post("/api/start_scan")
def start_scan():
    return process_manager.start_scan()


@app.post("/api/start_slam")
def start_slam():
    return process_manager.start_slam()


@app.post("/api/start_nav")
def start_nav():
    return process_manager.start_nav()


@app.post("/api/stop_all")
def stop_all():
    return process_manager.stop_all()


@app.post("/api/pose_estimate")
def pose_estimate(request: PoseRequest):
    if ros_node is None:
        raise HTTPException(status_code=503, detail="ROS node is not ready")
    return ros_node.publish_initial_pose(request.x, request.y, request.yaw)


@app.post("/api/goal")
def goal(request: PoseRequest):
    if ros_node is None:
        raise HTTPException(status_code=503, detail="ROS node is not ready")
    try:
        return ros_node.send_nav_goal(request.x, request.y, request.yaw)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def main():
    atexit.register(process_manager.stop_all)
    uvicorn.run(app, host=HOST, port=PORT)


if __name__ == "__main__":
    main()
