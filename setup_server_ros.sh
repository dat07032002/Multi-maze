source /opt/ros/humble/setup.bash
tag_workspace="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$tag_workspace/install/setup.bash"

export OPENCV_VIDEOIO_PRIORITY_GSTREAMER=0
export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_DISCOVERY_SERVER=10.157.146.38:11811
export ROS_SUPER_CLIENT=TRUE
