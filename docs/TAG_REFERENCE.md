# Updated TAG hardware reference

Hardware source: [`trungbao0301/TAG`](https://github.com/trungbao0301/TAG)
commit `35b80ad28a1792af9c4f3ae312fc90b5a6f14bdd`.

## Imported working packages

- `tag_camera`
- `tag_state_estimation`
- `tag_interfaces`
- `tag_hiwonder`
- `tag_dreamer`
- Camera tuning, HSV selection, viewer, TCP bridge, and ROS setup utilities

The latest state-estimation commit is included. It masks the closest board
corner during marble tracking, increases the corner-mask radius from 10 to 16
pixels, and tightens the candidate blob gates to circularity greater than 0.25
and area greater than 50 pixels. This reduces the risk of locking onto a blue
corner marker instead of the marble.

## Hardware facts carried into simulation

- Board/insert footprint: `0.259 x 0.229 m`
- Ball-radius prior: `0.006 m`
- Camera request: `1280 x 720 @ 60 FPS`; working source reports about 45 FPS
- Rectified policy crop: `64 x 64 mm` rendered as `64 x 64 x 1`
- Detector loss threshold: 6 missed frames
- Normal loss grace: 0.35 s; configured occlusion grace: 1.50 s
- Hiwonder update rate: 30 Hz
- Servo home: `500, 500`; effective targets: `230..770`
- Maximum movement: 20 servo units per driver tick
- Command timeout: 1 s, returning home
- Reset: position 700 pre-home, then position 500 home

## Corrections and compatibility work

The reference repository is treated as hardware evidence, not as unquestioned
training truth. This project adds these safeguards:

- The preserved route pickle files still name the pre-rename Python module
  `cyberrunner_dreamer.path`; `tag_dreamer.path` now loads them through an
  explicit compatibility unpickler.
- The hardware Gym task is consistently `gym_tag_dreamer:tag-ros-v0`.
- The upstream learner scale is 240 but the working bridge executable defaults
  to a clamp of 180; simulation models the effective clamp.
- Simulator training uses the fixed `cyberrunner` config and uniform replay;
  real TAG training has a separate `tag` config and replay implementation.
- Dreamer4 entry points and Feetech/Dynamixel helpers were removed because this
  project uses DreamerV3 and Hiwonder only.

Unknown servo-angle gain, backlash, full latency, and friction remain explicit
randomized priors until physical identification is possible.
