# Continue from another desktop

## Clone

```bash
git clone https://github.com/dat07032002/Multi-maze.git
cd Multi-maze
git log -1 --oneline
```

The repository deliberately excludes virtual environments, ROS build products,
simulator renders, checkpoints, replay, and logs. Recreate those locally.

## Windows simulation environment

Create or reuse a Python environment with MuJoCo, NumPy, Pillow, Gymnasium, and
the Dreamer dependencies. Then run:

```powershell
python -m unittest discover -s cyberrunner_mujoco\tests -v
Push-Location cyberrunner_mujoco
python verify_dreamer_config.py
python verify_dreamer_adapter.py
python verify_training_readiness.py
Pop-Location
```

## Ubuntu/ROS hardware environment

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

Robot-side startup order:

```bash
python3 fast_camera_publisher_v2.py
ros2 run tag_hiwonder hiwonder_compat_node.py
./run_tag_estimator.sh
python3 tcp_ros_bridge.py 127.0.0.1 5555
```

Use an SSH tunnel for port 5555 when the learner is remote. Confirm motor signs
and begin with a reduced command limit before deploying a learned policy.

## Existing school-server run

The current production artifacts are external to Git. Their paths, GPU mapping,
status commands, and safe-stop instructions are in [TRAINING.md](TRAINING.md).
Cloning on another desktop does not interrupt that run.

## Next work

1. Monitor fixed-step validation and select the best checkpoint rather than the latest one.
2. Keep the eight test mazes untouched until the final report.
3. When hardware is available, measure servo-angle response, backlash, latency, and friction.
4. Measure removable-plate thickness/retention geometry before final-fit STL export.
5. Commission with small actions, then test familiar and held-out printed mazes without per-maze retraining.
