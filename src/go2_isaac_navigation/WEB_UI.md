# Go2 Web UI

This package includes a FastAPI web dashboard for the Isaac Go2 2D navigation pipeline.

## Build

```bash
cd ~/go2_isaac_nav_ws
colcon build --packages-select go2_isaac_navigation
source install/setup.bash
```

Install the Python web dependencies if they are not already installed:

```bash
pip install fastapi uvicorn pydantic
```

## Run

For the current Isaac configuration, the robot base frame is usually `unitree_go2/base_link`.

```bash
export WEB_BASE_FRAME=unitree_go2/base_link
export GO2_MAP=/home/robotics4/maps/go2_slam_map.yaml
ros2 run go2_isaac_navigation go2_web_server.py
```

Open on the same PC:

```text
http://localhost:8000
```

Open from another PC on the same network:

```text
http://PC_IP:8000
```

The browser connects to rosbridge at:

```text
ws://<current-host>:9090
```

## Environment Variables

```text
GO2_MAP         Optional map YAML path used by Start NAV
WEB_MAP_FRAME   TF map frame, default: map
WEB_BASE_FRAME  TF robot base frame, default: base_link
ROS_DISTRO      ROS distribution name, default: humble
WEB_HOST        FastAPI host, default: 0.0.0.0
WEB_PORT        FastAPI port, default: 8000
```

## Dashboard Buttons

```text
Start Scan  -> ros2 launch go2_isaac_navigation go2_scan.launch.py
Start SLAM  -> stops NAV, ensures scan is running, starts go2_slam.launch.py
Start NAV   -> stops SLAM, ensures scan is running, starts go2_isaac_nav.launch.py
Stop All    -> stops NAV, SLAM, scan, and rosbridge
```

If `GO2_MAP` exists, Start NAV launches with:

```bash
map:=$GO2_MAP
```

## Browser Topics

```text
/map              nav_msgs/msg/OccupancyGrid
/web_robot_pose   geometry_msgs/msg/PoseStamped
```

The backend publishes `/web_robot_pose` from TF:

```text
WEB_MAP_FRAME -> WEB_BASE_FRAME
```

The browser sends:

```text
Pose Estimate -> /initialpose
Goal          -> /navigate_to_pose action
```
