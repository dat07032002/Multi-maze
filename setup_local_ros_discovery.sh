#!/usr/bin/env bash
# Local robot-PC setup for direct ROS 2 over the server discovery service.
# Source this before camera, state estimation, and Hiwonder nodes.

if [ -f /opt/ros/humble/setup.bash ]; then
  source /opt/ros/humble/setup.bash
fi

tag_workspace="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$tag_workspace/install/setup.bash" ]; then
  source "$tag_workspace/install/setup.bash"
fi

export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_DISCOVERY_SERVER=10.157.146.38:11811
unset ROS_SUPER_CLIENT
