# Project structure

The repository is being organized without changing the working trained system.
The current ROS packages remain at the root because moving them would invalidate
existing workspace paths and installed artifacts.

## Maintained runtime paths

- `cyberrunner_camera/`: camera acquisition
- `cyberrunner_state_estimation/`: camera calibration, markers, and state estimation
- `cyberrunner_interfaces/`: ROS messages and services
- `cyberrunner_dynamixel/`: active Hiwonder compatibility driver under its historical package name
- `cyberrunner_dreamer/`: active learning environment
- `tcp_ros_bridge.py`: robot/server transport used by TCP training
- `scripts/`: operational and training utilities

## Hardware and maze sources

- `hardware/mazes/`: canonical physical-maze revisions
- `tools/maze/`: validation and generation tools for maze geometry
- `docs/assets/`: existing camera, motor-mount, and reload-mechanism CAD assets

## Preserved compatibility paths

- `cyberrunner_dreamer_thomas/` and `cyberrunner_dynamixel_thomas/` are retained
  until their behavior and trained-run dependencies are compared.
- `third_party/` contains upstream reference material and is excluded from colcon.
- Dynamixel-named messages, services, topics, and executables remain available
  while callers migrate to the hardware-neutral actuator API.

## Generated historical snapshot

`build/`, `install/`, `log/`, `run_logs/`, `cache/`, and the root `latest` file
are preserved evidence of the previous working setup. They are not source of
truth and new content in those directories is ignored. Do not manually edit or
delete them during the compatibility phase.

## Cleanup rule

A file can be removed only when all four conditions are met:

1. No maintained code, launch file, or trained workflow references it.
2. Its required information exists in maintained source or protected storage.
3. A clean checkout builds and passes the relevant test without it.
4. The physical Hiwonder robot still completes the corresponding smoke test.
