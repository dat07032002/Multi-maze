# CyberRunner system model

This directory contains an RL-agnostic model of the physical CyberRunner loop.
It deliberately does not define a reward, replay format, learner, or RL
algorithm.

## Signal path

```text
normalized policy action [-1, 1]^2
  -> legacy command sign and +/-180 command limit
  -> Hiwonder absolute target: home + command * 1.5
  -> 30 Hz driver update, 20 servo-units/tick limit, deadband
  -> command delay and uncertain servo/linkage response
  -> MuJoCo two-axis board
  -> rolling/sliding ball, walls, and physical holes
  -> calibrated board-coordinate camera remap
  -> detector hysteresis and short-loss prediction
  -> delayed raw sensor state
  -> deployed {image, states, goal} policy observation
```

The old ROS message calls the two commands velocities, but the active Hiwonder
driver interprets them as absolute offsets around the configured home
positions. `actuator_model.py` reproduces that behavior.

## Observation interface

The observation intentionally matches the useful portion of the existing
Dreamer environment:

| Key | Shape | Meaning |
| --- | --- | --- |
| `image` | `64 x 64 x 1`, `uint8` | Grayscale, ball-centered 64 mm physical patch |
| `states` | `4`, `float32` | TAG-normalized board X/Y angles and lower-left-frame ball X/Y position |
| `goal` | `10`, `float32` | Five normalized 2D route targets relative to the ball |

`ball_visible` remains available as diagnostic information but is not encoded
by the deployed policy. Exact normalization is defined in
`HARDWARE_CONTRACT.md` and implemented by `policy_contract.py`.
Reward and termination interpretation also remain outside this layer, although
the model reports physical terminal reasons such as `ball_fell`.

The separate `cyberrunner_env.py` task layer normalizes these signals, tracks
route progress within a bounded window so adjacent corridors cannot cause
false jumps, samples only from the requested immutable maze split, defines
configurable progress reward variants, and logs success, fall, cross-track,
and clearance measurements independently. The physical model remains reward
agnostic.

## Route safety

Generated routes are validated for the full ball rather than a point. Walls,
holes, and board boundaries are treated as forbidden whenever the ball surface
would enter the configured safety margin. Routes are smoothed only when the
entire shortcut passes a dense swept-ball check and are then resampled at fixed
physical spacing. The uninflated geometry remains the geometry used by MuJoCo
and future 3D printing; inflation exists only in the planning calculation.

## Camera model

The same See3CAM calibration file used by the ROS estimator is parsed and
validated. It was calibrated at 1920 x 1200 and the estimator scales it by
three to 640 x 400. The active publisher also produces 640 x 400 after resizing
to 640 x 360 and adding 20-pixel top and bottom borders.

The policy does not receive that raw image. The state estimator uses the OCam
model and marker poses to remap a 64 mm square centered on the ball. Therefore,
`camera_model.py` renders the post-calibration board-coordinate image directly.
This avoids adding a synthetic lens distortion and immediately undoing it.

Per-episode camera randomization covers brightness, contrast, blur, crop error,
and pixel noise. Per-frame dropout represents temporary ball-detection loss.
The complete state/image observation is delayed together.

## Known parameters

These values are sourced directly from the current project:

- board dimensions and maze geometry from each layout JSON;
- ball radius of 6 mm;
- Hiwonder home positions, limits, scale, driver rate, rate limit, deadband, and
  move time from `cyberrunner_dynamixel/config/hiwonder.yaml`;
- normalized action conversion and sign from `env_tcp_shaped.py`;
- camera calibration from `calib_results_cyberrunner.txt`;
- 64 mm by 64 mm board-coordinate remap from `measurements.py`; and
- 64 x 64 grayscale channel-average conversion from `tcp_ros_bridge.py`.

## Uncalibrated priors

The following values cannot be identified without hardware or synchronized
real trajectories. They are explicit in `system_config.py` and sampled during
randomized resets:

- servo-units-to-board-angle gain;
- actuator delay and response time;
- linkage zero offset and cross-axis coupling;
- ball mass tolerance and contact friction;
- camera photometric noise and crop error; and
- estimator measurement noise.

The nominal servo gain is inferred by mapping the configured +/-180 policy
command through the 1.5 scale to the environment's +/-10 degree board range.
It must be measured later.

## Validation

Run both the original physical smoke tests and the complete system tests:

```powershell
.venv\Scripts\python.exe verify_physics.py
.venv\Scripts\python.exe verify_system_model.py
```

The system validation checks calibration dimensions, actuator delay and signs,
observation shapes, randomized parameters, and physical fall-through holes.
