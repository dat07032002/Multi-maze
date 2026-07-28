# TAG hardware deployment contract

Contract version: `tag_hardware_policy_v1`

Hardware reference: `trungbao0301/TAG` commit
`a9054a2939e907678e2115758a7ecda034389ae1`.

This document defines the interface that a MuJoCo-trained policy must use when
it is tested on the fixed TAG camera, Hiwonder motors, and tilt mechanism. The
maze insert may change, but the policy interface and physical platform do not.

## Coordinate frame

Maze geometry uses meters in a lower-left XY frame over a 0.259 x 0.229 m
playable area. The real state estimator publishes marble coordinates centered
on the board, so the deployment adapter first adds `(0.259 / 2, 0.229 / 2)`.

The exact axis and motor signs are retained from the working TAG software and
must be confirmed with low-amplitude hardware commissioning before policy use.

## Policy observation

Only these three fields enter DreamerV3:

| Field | Shape | Type | Definition |
|---|---:|---|---|
| `image` | 64 x 64 x 1 | `uint8` | Calibrated, board-rectified 64 x 64 mm crop centered on the estimated marble; arithmetic mean of available color channels |
| `states` | 4 | `float32` | `[alpha / 10 deg, beta / 10 deg, x / 0.259, y / 0.229]` |
| `goal` | 10 | `float32` | Five relative XY route points; point `k` is divided by `k * 0.012 m` |

Values are not clipped, matching the working TAG TCP environment. Diagnostic
fields whose names start with `log_` do not enter the encoder. `ball_visible` is
diagnostic information and is not a policy input in this contract.

This contract is checkpoint-breaking relative to the earlier simulator, which
used centered `[-1, 1]` position normalization, divided every goal point by
0.060 m, and encoded `ball_visible`. Older checkpoints and replay must remain
preserved but must not be mixed into replacement training under this contract.

## Policy action and Hiwonder command

The working learner scales normalized actions by 240 and applies a `-1` sign on
both axes. The working bridge executable then defaults to a lower clamp of 180:

```text
command = clip(-clip(action, -1, 1) * 240, -180, 180)
servo_target = clip(500 + command * 1.5, 100, 900)
```

Thus a full normalized action produces servo targets 230 or 770 with the
repository defaults. The driver updates at 30 Hz and advances each target by at
most 20 servo units per tick. It sends a 30 ms move command, returns home after
a one-second command timeout, and uses a two-stage reset through position 700.

The local mapping from command to board angle was measured with the marble
removed on 2026-07-27.  It is direction-dependent and cross-coupled; motor 2 in
the positive direction remained inside stiction/pose noise through command +40.
The simulator uses separate positive and negative 2x2 local maps and randomizes
their gains, delay, response time, and stiction.  Full-range saturation,
backlash width, and rare stalls remain unmeasured and must not be treated as
calibrated facts.

## Camera and loss recovery

The fixed camera requests 1280 x 720 at 60 FPS, publishes 640 x 360 plus 20
black rows above and below, and was reported in the working source to achieve
about 45 FPS with locked 8 ms exposure. The estimator uses OCamCalib and board
markers to form the metric policy crop.

The marble detector retains the last location for the first five missed frames
and reports loss on the sixth. The TCP environment then predicts/holds the
observation for 0.35 seconds. It supports 1.50 seconds for explicitly configured
occlusion regions. Prediction speed is capped at 0.15 m/s and projected onto
the route. A confirmed loss ends the episode.

## Swappable maze insert

Every insert is generated from one versioned layout definition. That definition
must produce the MuJoCo model, camera rendering, safe route, preview, metadata,
and STL. The route matching the installed maze is loaded before an episode; the
policy does not receive a maze identifier.

The 0.259 x 0.229 m footprint has been confirmed to fit the Sterling
swappable-board platform. It does not yet define plate thickness, retaining
features, or underside clearance. STL exports remain `prototype_only` until
those remaining dimensions are measured from one supplied insert.

## Approval boundary

Contract checks, mesh generation, simulation verification, and short non-agent
smoke tests do not authorize replacement full training. Full DreamerV3 training
requires explicit user approval after readiness results are reviewed.
