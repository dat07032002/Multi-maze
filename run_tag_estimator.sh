#!/usr/bin/env bash
# Launch the TAG state estimator from this checkout.
# Usage: ./run_tag_estimator.sh [additional ros2 arguments]

set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Wipe any inherited ROS overlay so tag_ws cannot win.
unset AMENT_PREFIX_PATH COLCON_PREFIX_PATH PYTHONPATH ROS_PACKAGE_PATH CMAKE_PREFIX_PATH

source /opt/ros/humble/setup.bash
if [[ ! -f "$repo_root/install/setup.bash" ]]; then
  echo "Missing install/setup.bash. Run: colcon build --symlink-install"
  exit 2
fi
source "$repo_root/install/setup.bash"

# Keep the same DDS domain as the camera/bridge (default 0).
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-0}"

echo "estimator_sub resolves to:"
echo "  AMENT head: $(echo "$AMENT_PREFIX_PATH" | tr ':' '\n' | grep tag | head -1)"

cd "$repo_root"
exec ros2 run tag_state_estimation estimator_sub "$@"
