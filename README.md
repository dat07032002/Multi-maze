# Multi-maze TAG DreamerV3

This repository trains one route-conditioned DreamerV3 policy in MuJoCo and
deploys it on the physical TAG labyrinth robot. The camera, state estimator,
TCP bridge, and Hiwonder servo driver come from the working
[`trungbao0301/TAG`](https://github.com/trungbao0301/TAG) hardware stack. Only
the removable `259 x 229 mm` maze insert changes between tests.

The target is generalization: episodes sample different training mazes, while
the policy receives a camera crop, board/marble state, and five future route
points. It never receives a maze ID and is not retrained maze by maze.

## Hardware truth

- Camera and estimator: `tag_camera` and `tag_state_estimation`
- Actuators: two Hiwonder servos through `tag_hiwonder`
- Messages and services: `tag_interfaces`
- Real-robot TCP environment: `tag_dreamer`
- Simulator and printable-maze pipeline: `cyberrunner_mujoco`
- Learner: the maintained fork under `dreamerv3`

This project does not use Dynamixel motors or Dreamer4. The imported hardware
snapshot is pinned to TAG commit `35b80ad28a1792af9c4f3ae312fc90b5a6f14bdd`,
which includes the corner-marker rejection update for marble detection.

## Repository map

| Path | Purpose |
| --- | --- |
| `cyberrunner_mujoco/` | MuJoCo model, 40/8/8 dataset, route planner, camera/actuator model, tests |
| `dreamerv3/` | DreamerV3 plus the multi-maze simulator adapter and TAG hardware profile |
| `tag_camera/` | ROS 2 camera package |
| `tag_state_estimation/` | Calibrated marble and board-state estimator |
| `tag_hiwonder/` | Active Hiwonder HID servo driver |
| `tag_interfaces/` | ROS 2 TAG messages and reset service |
| `tag_dreamer/` | Real-hardware Gym/TCP environment and preserved route data |
| `hardware/mazes/` | Versioned removable-maze authoring template |
| `scripts/` | GPU 2 training and GPU 3/4 validation launchers |
| `docs/` | Architecture, training, upstream reference, cleanup, and handoff |

## Quick verification

On Windows, using the existing project environment:

```powershell
.\cyberrunner_mujoco\.venv\Scripts\python.exe -m unittest discover `
  -s cyberrunner_mujoco\tests -v

Push-Location cyberrunner_mujoco
.\.venv\Scripts\python.exe verify_dreamer_config.py
.\.venv\Scripts\python.exe verify_dreamer_adapter.py
.\.venv\Scripts\python.exe verify_training_readiness.py
Pop-Location
```

On Linux, replace the interpreter with `.venv/bin/python`.

## Training rules

- Physical GPU 0 is never used.
- Production training uses physical GPU 2.
- Canonical validation uses physical GPU 3 every 500,000 steps.
- Robust validation additionally uses physical GPU 4 every 1,000,000 steps.
- Checkpoints from before policy contract `tag_hardware_policy_v1` must not be
  mixed with current replay or training.
- Full training launchers remain protected by an explicit approval variable.

See [docs/README.md](docs/README.md) for the complete documentation index and
[docs/HANDOFF.md](docs/HANDOFF.md) when moving to another desktop.
