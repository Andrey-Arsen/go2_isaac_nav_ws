# Real Go2 Navigation With External LiDAR

These files are for the real Unitree Go2 when the onboard LiDAR is not used.
The Isaac Sim files remain separate.

## Required Runtime Topics

External LiDAR driver:

```text
/scan  sensor_msgs/msg/LaserScan
```

Unitree odometry:

```text
/utlidar/robot_odom  nav_msgs/msg/Odometry
```

Unitree sport API:

```text
/api/sport/request  unitree_api/msg/Request
```

The bridge nodes create:

```text
/odom
TF odom -> base_link
/cmd_vel -> /api/sport/request
```

Expected TF tree:

```text
map
  odom
    base_link
      base_laser
```

## External LiDAR

Start your external LiDAR driver first, for example:

```bash
source /opt/ros/foxy/setup.bash
source ~/d500_ws/install/setup.bash
ros2 launch ldlidar_stl_ros2 ld19.launch.py
```

Check:

```bash
ros2 topic hz /scan
ros2 topic echo /scan --once
```

The scan frame should match the launch argument `laser_frame`, default:

```text
base_laser
```

### LD19 USB Timeout

If the LD19 worked and then stopped, the important errors usually look like:

```text
get ldlidar data is time out, please check your lidar device
serial is not open:/dev/ttyUSB0
Open open error, No such file or directory
```

This means the LiDAR driver is not receiving data from the serial device.
If `/dev/ttyUSB0` is missing, ROS is not the main problem: Linux no longer
sees the USB serial adapter.

Check on the Go2:

```bash
lsusb
ls /dev/ttyUSB*
dmesg | tail -80
```

Quick recovery:

```bash
# Stop the LiDAR launch with Ctrl+C first.
# Replug the LiDAR or USB hub, then check the port again.
ls /dev/ttyUSB*

source /opt/ros/foxy/setup.bash
source ~/d500_ws/install/setup.bash
ros2 launch ldlidar_stl_ros2 ld19.launch.py
```

Most likely causes:

```text
USB hub power drop
loose USB cable
LD19 moved from /dev/ttyUSB0 to /dev/ttyUSB1
driver stuck after USB disconnect
Wi-Fi adapter and LiDAR sharing a weak USB hub
```

## 2D SLAM

```bash
cd ~/go2_isaac_nav_ws
source /opt/ros/foxy/setup.bash
source install/setup.bash

ros2 launch go2_isaac_navigation go2_real_slam.launch.py
```

Useful checks:

```bash
ros2 run tf2_ros tf2_echo odom base_link
ros2 run tf2_ros tf2_echo base_link base_laser
ros2 topic echo /map --once
```

Save a map:

```bash
mkdir -p ~/maps
ros2 run nav2_map_server map_saver_cli -f ~/maps/go2_d500_map
```

## Navigation

```bash
cd ~/go2_isaac_nav_ws
source /opt/ros/foxy/setup.bash
source install/setup.bash

ros2 launch go2_isaac_navigation go2_real_nav.launch.py \
  map:=/home/unitree/maps/go2_d500_map.yaml
```

The navigation launch starts:

```text
odom_tf_bridge.py
cmd_vel_to_sport_bridge.py
map_server
amcl
Nav2 servers
```

## Files

```text
config/go2_real_slam.yaml
config/go2_real_nav2.yaml
launch/go2_real_slam.launch.py
launch/go2_real_nav.launch.py
scripts/odom_tf_bridge.py
scripts/cmd_vel_to_sport_bridge.py
```

## Safety

The command bridge clamps velocity by default:

```text
max_vx = 0.25 m/s
max_vy = 0.0 m/s
max_wz = 0.6 rad/s
```

It sends zero velocity if `/cmd_vel` times out.
