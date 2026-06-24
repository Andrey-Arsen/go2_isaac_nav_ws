# Go2 Isaac Navigation

ROS 2 Humble workspace package for Unitree Go2 navigation in Isaac Sim.

## Features

- PointCloud2 to LaserScan conversion for Nav2.
- 2D SLAM with `slam_toolbox`.
- 2D navigation with `map_server`, AMCL, and Nav2.
- RViz configuration for map, scan, costmaps, TF, initial pose, and Nav2 goals.
- FastAPI web dashboard with rosbridge map display and goal/pose tools.

## Build

```bash
cd ~/go2_isaac_nav_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select go2_isaac_navigation
source install/setup.bash
```

## Basic Launches

Start scan conversion:

```bash
ros2 launch go2_isaac_navigation go2_scan.launch.py
```

Start 2D SLAM:

```bash
ros2 launch go2_isaac_navigation go2_slam.launch.py
```

Start navigation with a saved map:

```bash
ros2 launch go2_isaac_navigation go2_isaac_nav.launch.py \
  map:=/home/robotics4/maps/go2_slam_map.yaml
```

## Web UI

Install Python web dependencies:

```bash
pip install fastapi uvicorn pydantic
```

Run:

```bash
cd ~/go2_isaac_nav_ws
source /opt/ros/humble/setup.bash
source install/setup.bash

export WEB_BASE_FRAME=unitree_go2/base_link
export GO2_MAP=/home/robotics4/maps/go2_slam_map.yaml

ros2 run go2_isaac_navigation go2_web_server.py
```

Open:

```text
http://localhost:8000
```

See [`src/go2_isaac_navigation/WEB_UI.md`](src/go2_isaac_navigation/WEB_UI.md) for details.
