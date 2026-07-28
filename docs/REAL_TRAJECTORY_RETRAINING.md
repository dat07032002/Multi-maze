# Real-trajectory simulator refinement

This workflow records physical deployment trajectories without online learning,
fits effective marble dynamics, and quality-gates an update to the simulator.
The recorder is subscribe-only.  It has no publishers, services, or action
clients and cannot command the motors.

## Assumed dynamics before physical identification

Until a physical fit passes the quality gates below, simulation loads
`tag_mujoco/assumed_dynamics.json`. These are explicit training priors for a
12 mm steel marble on an untreated FDM-printed PLA maze, rather than
measurements:

| Parameter | Nominal | Training range |
| --- | ---: | ---: |
| Floor sliding friction | 0.38 | 0.15-0.70 |
| MuJoCo torsional friction length | 0.25 mm | 0.03-1.50 mm |
| Rolling resistance coefficient | 0.004 | 0.0005-0.030 |
| MuJoCo rolling friction length | 0.024 mm | 0.003-0.180 mm |
| Linear velocity damping | 0.22 1/s | 0.00-0.80 1/s |
| Wall restitution | 0.35 | 0.05-0.70 |

MuJoCo rolling and torsional friction coefficients have units of length. The
simulator therefore converts the dimensionless rolling-resistance coefficient
to a rolling-friction length by multiplying it by the measured 6 mm ball
radius, and enables six-dimensional contacts so the rolling term is active.
Positive length parameters are sampled on a log scale because their uncertainty
spans orders of magnitude.

The current model draws one spatially uniform contact model per episode. It
does not yet model directional friction from print lines, local seams or rough
patches, or slow surface changes caused by dust, wear, temperature, and
polishing. Those effects remain explicit model gaps until measurements on the
actual print justify a directional or spatial contact model. Print layer height,
top-skin pattern, wall count and infill, PLA formulation, and any ironing,
sanding, paint, or coating must be recorded with the physical test data.

This changes the simulator dynamics but not the observation/action contract.
Re-evaluate the preserved 13M checkpoint under these priors before any
continuation. Use a short curriculum from nominal to fully randomized assumed
dynamics; do not immediately start another long run.

References for parameter semantics and the identification approach:

- MuJoCo contact computation:
  <https://mujoco.readthedocs.io/en/stable/computation/index.html#contact>
- MuJoCo contact-friction modeling:
  <https://mujoco.readthedocs.io/en/stable/modeling.html>
- Li, Xi and Shi, *Estimation of rolling friction coefficients in a
  tribosystem using optical measurements*:
  <https://doi.org/10.1108/ILT-05-2016-0110>

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
rolling-friction length, linear damping, restitution, uncertainty ranges, and
provenance. The original fit remains immutable beside the raw session.

## 4. Validate before fine-tuning

```bash
tag_mujoco/.venv/bin/python -m unittest discover -s tag_mujoco/tests -v
tag_mujoco/.venv/bin/python tag_mujoco/verify_system_model.py
```

Re-evaluate preserved checkpoints under both nominal and randomized identified
dynamics before starting replacement fine-tuning.  Physical logs improve the
simulator; they are not used for unconstrained online policy exploration.
