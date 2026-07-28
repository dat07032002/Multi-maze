# Real-trajectory simulator refinement

This workflow records physical deployment trajectories without online learning,
fits effective marble dynamics, and quality-gates an update to the simulator.
The recorder is subscribe-only.  It has no publishers, services, or action
clients and cannot command the motors.

## 1. Record a fixed-policy or supervised trajectory

Keep training and online learning stopped.  Start the passive recorder before a
bounded fixed-checkpoint run or a separately reviewed manual excitation:

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run tag_sysid record --ros-args \
  -p session_name:=physical_fixed_policy_01 \
  -p max_duration_sec:=120.0 \
  -p record_camera_timing:=true
```

Collect multiple trajectories across both board directions.  Useful free-roll
data need at least 200 moving state samples.  Restitution activation additionally
requires five controlled low-speed impacts.  Do not mix dropped-marble, hand
contact, or estimator-loss intervals into a dynamics fit.

## 2. Fit the physical dynamics

```bash
ros2 run tag_sysid fit-dynamics \
  ~/tag_sysid_logs/physical_fixed_policy_01
```

The result is `dynamics_fit.json` in the session directory.  It contains the
source-timestamped local quadratic velocity/acceleration estimate, a robust fit
of the 2x2 tilt-to-acceleration map, linear damping, rolling resistance, detected
impact coefficients, residual error, R-squared, and explicit quality gates.

## 3. Activate the fit in simulation

```bash
tag_mujoco/.venv/bin/python tag_mujoco/apply_dynamics_fit.py \
  ~/tag_sysid_logs/physical_fixed_policy_01/dynamics_fit.json
```

The updater refuses a weak free-roll fit unless `--force` is explicitly used.
Do not force physical calibration data for training.  An accepted fit writes
`tag_mujoco/identified_dynamics.json`; new simulator processes then load its
rolling-friction coefficient, linear damping, restitution, uncertainty ranges,
and provenance.  The original fit remains immutable beside the raw session.

## 4. Validate before fine-tuning

```bash
tag_mujoco/.venv/bin/python -m unittest discover -s tag_mujoco/tests -v
tag_mujoco/.venv/bin/python tag_mujoco/verify_system_model.py
```

Re-evaluate preserved checkpoints under both nominal and randomized identified
dynamics before starting replacement fine-tuning.  Physical logs improve the
simulator; they are not used for unconstrained online policy exploration.
