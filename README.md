# Multi-maze TAG DreamerV3

This repository trains one route-conditioned DreamerV3 policy in MuJoCo and
deploys it on the physical TAG labyrinth robot. The camera, state estimator,
TCP bridge, and Hiwonder servo driver come from the working
[`trungbao0301/TAG`](https://github.com/trungbao0301/TAG) hardware stack. Only
the removable `259 x 229 mm` maze insert changes between tests.

The target is generalization: one policy continuously learns local path
following across straight sections, turns, stabilization, recovery, and
hazards sampled from 512 training mazes. The policy receives a camera crop,
board/marble state, and five future route points; it never receives a skill or
maze ID.

## Hardware truth

- Camera and estimator: `tag_camera` and `tag_state_estimation`
- Actuators: two Hiwonder servos through `tag_hiwonder`
- Messages and services: `tag_interfaces`
- Real-robot TCP environment: `tag_dreamer`
- Simulator and printable-maze pipeline: `tag_mujoco`
- Learner: the maintained fork under `dreamerv3`

This project uses Hiwonder motors and DreamerV3 exclusively. The hardware stack
retains the proven pose-continuity and safety fixes from this project while the
learned marble detector was selectively imported from TAG commits `4014cec` and
`e746f67`; the unrelated upstream files were not merged.

## Repository map

| Path | Purpose |
| --- | --- |
| `tag_mujoco/` | MuJoCo model, legacy 40/8/8 and adaptive v2 512/64/64 datasets, route planner, camera/actuator model, tests |
| `dreamerv3/` | DreamerV3 plus the multi-maze simulator adapter and TAG hardware profile |
| `tag_camera/` | ROS 2 camera package |
| `tag_state_estimation/` | Calibrated marble and board-state estimator |
| `tag_hiwonder/` | Active Hiwonder HID servo driver |
| `tag_sysid/` | Passive recorder and approval-gated actuator measurements |
| `tag_interfaces/` | ROS 2 TAG messages and reset service |
| `tag_dreamer/` | Real-hardware Gym/TCP environment and preserved route data |
| `hardware/mazes/` | Versioned removable-maze authoring template |
| `scripts/` | GPU 2 training and GPU 3/4 validation launchers |
| `tools/camera/` | Camera tuning, HSV comparison, safe viewing, and overlays |
| `tools/visualization/` | Reusable validation-rollout rendering tools |
| `docs/` | Architecture, training, upstream reference, cleanup, and handoff |

The learned detector is integrated behind `off`, `shadow`, and `hybrid` modes.
It remains `off` by default. See
[tag_state_estimation/AI_MARBLE_DETECTOR.md](tag_state_estimation/AI_MARBLE_DETECTOR.md)
before running shadow validation or requesting hybrid activation.

## Quick verification

On Windows, using the existing project environment:

```powershell
.\tag_mujoco\.venv\Scripts\python.exe -m unittest discover `
  -s tag_mujoco\tests -v

Push-Location tag_mujoco
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

## Adaptive v2 status

The adaptive v2 pipeline is implemented and server-tested. It combines
prioritized level replay, start-state and domain-randomization curricula,
privileged expert demonstrations, and eight parallel simulator processes. A
10k smoke test completed successfully at about twice the environment throughput
of the single-environment v1 runs.

After recovery from the first server reboot, production reached step 9,520,768.
It was intentionally stopped on 2026-07-24 at the user's request; its final
checkpoint, replay and logs were preserved. The latest complete validation is
9M, while the copied 9.5M checkpoint is valid but its evaluation was interrupted
by the stop. See [docs/HARDWARE_HANDOFF_2026-07-26.md](docs/HARDWARE_HANDOFF_2026-07-26.md)
for the current hardware/sysid plan and Ubuntu continuation instructions.

## Continuous unified v3 training

The active experiment trains one shared world model and one actor across every
local route condition. Route endpoints are neutral training boundaries rather
than rewarded goals; held-out validation still tests complete maps from their
true entrances. See
[docs/CONTINUOUS_UNIFIED_TRAINING_2026-07-30.md](docs/CONTINUOUS_UNIFIED_TRAINING_2026-07-30.md).

## Multi-skill master-course curriculum

The guarded v5 curriculum generates related but geometrically distinct course
families for launch, straight tracking, braking, turns, recovery, hazards, and
long compound execution. Later stages retain all earlier variants, while
validation and final-test geometry remain disjoint. See
[docs/MASTER_COURSE_CURRICULUM.md](docs/MASTER_COURSE_CURRICULUM.md).

The earlier skill-first and sequential-map design remains available as a
documented alternative in
[docs/SKILL_FIRST_SEQUENTIAL_MAP_CURRICULUM.md](docs/SKILL_FIRST_SEQUENTIAL_MAP_CURRICULUM.md).
