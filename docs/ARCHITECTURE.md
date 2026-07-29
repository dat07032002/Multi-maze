# Architecture

## Training in simulation

```text
40 training maze JSON files
          |
          v
MuJoCo plant -- camera/latency/dropout model --> image, states, goal
          ^                                      |
          |                                      v
Hiwonder delay/rate/clamp model <------- DreamerV3 action
```

One environment step advances exactly `1/35 s` of modeled physical time. The
server may generate roughly 100 simulation steps per wall-clock second, so it
runs faster than real time without changing the modeled 35 Hz controller or
30 Hz Hiwonder driver.

The immutable dataset contains 40 training, 8 validation, and 8 final-test
mazes. Validation and test layouts never enter replay.

## Deployment on TAG

```text
See3CAM / V4L2 camera
          |
          v
tag_state_estimation -- /tag_state_estimation/estimate_subimg
          |
          v
tcp_ros_bridge.py <==== TCP ====> tag_dreamer Gym environment on server
          |                              |
          v                              v
tag_hiwonder <------------------ DreamerV3 policy action
```

The deployed policy contract is `tag_hardware_policy_v1`:

| Input | Shape | Meaning |
| --- | ---: | --- |
| `image` | `64 x 64 x 1` | Arithmetic-channel-mean grayscale crop covering 64 mm around the estimated marble |
| `states` | `4` | Board angles divided by 10 degrees, then lower-left marble XY divided by `0.259, 0.229` |
| `goal` | `10` | Five relative XY route points, each divided by its own `k x 12 mm` horizon |

`ball_visible` remains diagnostic and is not encoded by the policy. A normalized
action is scaled by 240, signed on both axes, clamped by the bridge to 180, then
converted to servo targets around position 500 with scale 1.5.

See the canonical numerical specification in
[`HARDWARE_CONTRACT.md`](../tag_mujoco/HARDWARE_CONTRACT.md).

Future real-hardware learning will retain an immutable main policy, add only a
bounded residual correction, and place both behind an independent safety
supervisor. The staged data, system-identification, weakness-mining, training,
and promotion design is specified in
[`REAL_HARDWARE_ADAPTATION_DESIGN.md`](REAL_HARDWARE_ADAPTATION_DESIGN.md).

## Maze contract

The confirmed removable footprint is `259 x 229 mm`. A single JSON definition
generates route data, MJCF, preview, metadata, and a prototype STL. Plate
thickness and any retaining/underside geometry are deliberately left for the
physical insert measurement and do not block simulation training.
