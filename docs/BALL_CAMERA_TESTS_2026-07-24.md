# Angle-independent camera and marble tests — 2026-07-24

## Scope

These tests intentionally did not use board-angle estimates and did not command
either Hiwonder motor. They characterize the camera stream and the running
hybrid classical/AI marble estimator while the TCP policy bridge is inactive.

The tests used `/cyberrunner_camera/image` and
`/cyberrunner_state_estimation/estimate`. Manual actions were limited to
covering, gently rolling, dropping, retrieving, and replacing the marble.

## Camera timing

The camera publishes 640 x 400 BGR images with nonzero ROS timestamps.

| measurement | first 30 s run | repeat 30 s run |
|:---|---:|---:|
| frames | 1,719 | 1,731 |
| effective rate | 59.14 Hz | 59.87 Hz |
| median interval | 16.67 ms | 16.69 ms |
| p95 interval | 19.55 ms | 19.52 ms |
| p99 interval | 20.49 ms | 20.10 ms |
| maximum interval | 350.97 ms | 33.48 ms |
| intervals over 40 ms | 1 | 0 |
| mean header age at subscriber | 2.20 ms | 2.23 ms |
| p95 header age | 2.76 ms | 2.88 ms |

No nonpositive, duplicate, or backward timestamp intervals occurred. The
repeat shows that approximately 60 Hz is the normal camera rate. The isolated
351 ms stall in the first run means rare long scheduling/transport stalls must
still be tolerated by the policy interface.

Before timing, stale read-only capture and topic-rate processes left by earlier
diagnostics were stopped. The active AI estimator and dataset processes were
not modified.

## Stationary marble

The marble was stationary in an open region for 30 seconds.

- 1,751 state messages at 58.34 Hz.
- 100% finite positions.
- All 1,750 classified source messages were `fused`.
- AI confidence: 0.99936 mean.
- AI/classical detector disagreement: 0.744 px mean.
- x position standard deviation: 0.0615 mm.
- y position standard deviation: 0.0549 mm.
- x peak-to-peak range: 0.684 mm.
- y peak-to-peak range: 0.428 mm.
- Half-to-half drift: +0.0065 mm x and -0.0043 mm y.

Position tracking is sufficiently stable for maze navigation. Velocity is not
yet suitable for friction fitting: with the marble stationary, reported x
velocity averaged -7.69 mm/s with 4.87 mm/s standard deviation, and y velocity
averaged -1.83 mm/s with 4.52 mm/s standard deviation. A stationary-velocity
zero/bias correction or a trajectory-level smoother is required.

## Full visual occlusion

The marble was covered by hand and then uncovered.

Observed source progression:

`fused -> AI reacquired -> Kalman occlusion -> lost uncertain -> lost -> AI reacquired -> fused`

- 1,897 state messages.
- 95.36% finite positions over the complete interval.
- `lost_uncertain` began about 0.43 seconds after the first sustained non-fused
  transition.
- `lost` began about 1.52 seconds after that transition.
- After visual reacquisition, the estimator returned from AI reacquisition to
  fused tracking in approximately 0.1 seconds.

The measured 2.0 seconds from first non-fused output to recovery includes the
physical time for which the hand covered the marble and is not pure algorithm
latency.

## Gentle rolling motion

The marble received one manual push through an open region.

- 2,129 state messages.
- 100% finite output.
- All 2,128 classified source messages remained `fused`.
- Maximum estimated speed: 0.221 m/s.
- Integrated tracked path: 0.234 m.

This validates detector coverage during motion up to the observed speed. It is
not a rolling-friction measurement because board tilt was unavailable and the
stationary velocity estimate has a measurable bias.

## Hole loss and replacement

The marble was manually dropped into a hole, left absent, retrieved, and placed
back in an open region.

Observed source progression:

`fused -> Kalman occlusion -> brief fused -> Kalman occlusion -> lost uncertain -> lost -> fused`

- 1,194 state messages.
- 79.98% finite positions over the complete interval.
- `lost_uncertain` occurred approximately 0.48 seconds after first loss.
- `lost` occurred approximately 1.62 seconds after first loss.
- The estimator returned to fused output after the marble was replaced.

The finite fraction is expected to be lower because the marble was physically
absent. Replacement time was manual, so this run does not establish a precise
camera-to-reacquisition latency.

## Hiwonder software path verified without motion testing

The running driver configuration was read directly from ROS parameters:

- command loop: 30 Hz;
- HID move time: 30 ms;
- home targets: 500, 500;
- command-to-target scale: 1.5 servo units per command;
- maximum target change per driver tick: 20 servo units;
- deadband: 1 servo unit;
- command timeout: 1 second, then return home;
- requested temperature limit: 70 C.

The current HID controller exposes no temperature telemetry because
`temp_serial_port` is empty. Therefore the configured automatic temperature
pause cannot be validated from real temperature measurements.

## Reliable conclusions

1. The normal camera and ball-state rate is approximately 58-60 Hz, not
   90-107 Hz.
2. Stationary position noise is below 0.1 mm standard deviation.
3. Hybrid tracking survives manual rolling at at least 0.22 m/s in this trial.
4. Occlusion prediction is bounded and becomes explicit `lost` state.
5. Hole loss and replacement are recognized.
6. Raw reported velocity has too much stationary bias for friction system
   identification.

## Still missing

- Camera-to-state processing latency tied to the exact source image timestamp.
- Velocity estimator bias correction and validation against known motion.
- Rolling friction, damping, restitution, and tilt-to-acceleration; these require
  reliable board angle.
- Repeated coverage trials at multiple board locations and lighting levels.
- Reliable fixed-marker board-pose initialization and recovery.
