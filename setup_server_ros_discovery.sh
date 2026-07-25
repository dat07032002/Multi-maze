#!/usr/bin/env bash
# Server-side setup for direct ROS 2 over Fast DDS Discovery Server.
# Use this only for direct ROS diagnostics; production training uses the TCP bridge.

export PATH=/home/tbt589/micromamba/envs/tag_ros/bin:$PATH

if [ -f /home/tbt589/micromamba/envs/tag_ros/setup.bash ]; then
  source /home/tbt589/micromamba/envs/tag_ros/setup.bash
fi

tag_workspace="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$tag_workspace/install/setup.bash" ]; then
  source "$tag_workspace/install/setup.bash"
fi

export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_DISCOVERY_SERVER=10.157.146.38:11811
unset ROS_SUPER_CLIENT
