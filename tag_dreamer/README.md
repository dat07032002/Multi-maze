# TAG real-hardware environment

Gym-compatible environments and preserved route data for the physical robot.
The current remote-learner path is `tag_dreamer.env_tcp:TagGym`, registered as
`tag-ros-v0`; it communicates with `tcp_ros_bridge.py` and exposes the same
`image`, `states`, and future-route `goal` policy contract used by simulation.

`data/path_0002_hard.pkl` and `data/path_custom.pkl` are working upstream route
artifacts. The loader retains compatibility with their old pre-rename Python
module name. They are reference data, not the multi-maze training split.

Use the `tag` profile in `dreamerv3/dreamerv3/configs.yaml` for hardware. Use
the `tag_sim` profile for MuJoCo multi-maze training.
