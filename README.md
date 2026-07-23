# TAG CyberRunner

TAG is a physical CyberRunner reinforcement-learning system. A camera estimates
the marble state, a learned policy selects two board-axis commands, and two
Hiwonder servos tilt a custom maze board.

> **Hardware truth:** this checkout's active robot uses Hiwonder servos and the
> Hiwonder HID controller (`0483:5750`), not Dynamixel motors. Some package,
> topic, message, log, and historical source names still contain `dynamixel` so
> existing trained workflows remain compatible.

## Start here

- [Project structure](docs/00_project_structure.md)
- [Hiwonder setup and safe test](docs/08_hiwonder_setup.md)
- [3D-printed maze workflow](docs/09_custom_maze_workflow.md)
- [Protected trained artifacts](docs/10_protected_artifacts.md)
- [Installation](docs/03_installation.md)
- [Training](docs/05_train.md)

## ROS packages

| Package | Purpose |
| --- | --- |
| `cyberrunner_camera` | Publishes camera frames |
| `cyberrunner_state_estimation` | Estimates marble and board state |
| `cyberrunner_interfaces` | ROS messages and services |
| `cyberrunner_dynamixel` | Historical package name; contains the active Hiwonder driver and legacy drivers |
| `cyberrunner_dreamer` | Current learning environment and training entry points |
| `cyberrunner_dreamer_thomas` | Preserved experimental/trained variant pending behavior comparison |

## Active Hiwonder launch

After building and sourcing the ROS workspace:

```bash
ros2 launch cyberrunner_dynamixel hiwonder.launch.py
```

The legacy command remains supported:

```bash
ros2 run cyberrunner_dynamixel hiwonder_compat_node.py
```

Do not start the old Dynamixel or Feetech executables on the physical TAG robot.

## Preservation policy

This repository contains a historical working snapshot, including tracked
`build/`, `install/`, `log/`, runtime logs, calibration data, and generated path
files. They are intentionally retained during organization. New generated files
are ignored, and existing artifacts will only be removed after a clean rebuild
and robot validation prove that they are reproducible and unused.

The pre-organization state is recoverable from local Git tag
`pre-organization-20260723`.
