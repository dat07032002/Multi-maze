# TAG hardware and system-identification handoff — 2026-07-26

This is the starting document for the Ubuntu laptop that will be connected to
the physical TAG mechanism. It distinguishes completed measurements from work
that still needs hardware, and it preserves the rule that no active motion is
authorized merely because the software is installed.

## Project objective

Train one route-conditioned DreamerV3 policy that can solve multiple removable
mazes on the same physical mechanism. The camera, Hiwonder motors and outer
board remain fixed. Only the `259 x 229 mm` 3D-printed maze insert changes. The
policy receives the marble/board state, image observation and future route; it
does not receive a maze ID and is not retrained once per maze.

## What is implemented

### Simulation and learning

- MuJoCo model and printable-maze pipeline use the fixed insert dimensions.
- Adaptive v2 dataset: 512 training, 64 validation and 64 untouched test mazes.
- DreamerV3 uses prioritized level replay, curricula, domain randomization,
  eight simulator processes and 160 successful expert demonstrations.
- Production training was intentionally stopped on 2026-07-24 at step
  `9,520,768 / 10,000,000` after the user requested a safe stop.
- The main 470 MB checkpoint was saved at shutdown. The copied 9.5M checkpoint
  passed its SHA-256 check. Server replay, metrics and logs remain external to
  Git and were not deleted.
- The 9.5M validation was interrupted by the stop. The latest complete 9M
  validation reported 39.06% canonical completion with 34.38% falls and 67.19%
  robust completion with 23.44% falls. The selector still ranks the 6.5M
  canonical checkpoint first at 40.63% completion. The large canonical/robust
  gap must be audited before selecting a deployment checkpoint.

### Camera and marble state

- Normal camera delivery is approximately 59–60 Hz at `640 x 400`; an isolated
  long stall was observed, so consumers must tolerate missing frames.
- Stationary marble position noise was below 0.1 mm standard deviation.
- The hybrid learned/HSV detector tracked a manual roll up to the observed
  0.221 m/s and produced explicit bounded occlusion/loss states.
- AI modes are `off`, `shadow` and `hybrid`; `off` remains the safe default.
  Hardware validation must begin in `shadow`, not by enabling hybrid control.
- Raw velocity has a stationary bias of several mm/s and is not accepted for
  rolling-friction fitting yet.

### Camera board pose and BNO086

- Camera intrinsics, four fixed reference points, IPPE pose selection and pose
  continuity gates are implemented.
- Absolute angles above 20 degrees or frame steps above 3 degrees are rejected.
- Runtime camera zero offsets are supported because apparent home changes with
  camera/marker/mechanism placement.
- A SparkFun BNO086 path is implemented but not hardware-validated. The BNO086
  connects over I2C to an ESP32; the ESP32 sends explicit newline-delimited
  quaternion reports over USB serial.
- The ROS adapter publishes `sensor_msgs/Imu`. The estimator supports `camera`,
  `imu` and guarded `fused` modes, IMU freshness fallback, sensor-to-board mount
  alignment, camera correction and disagreement diagnostics.
- `orientation_mode:=camera` is still the default. The implementation passed
  19 local fusion/protocol/pose/tracker tests, but a complete ROS hardware build
  and physical sign/alignment test remain mandatory.
- IMU fusion currently improves published board angles. Marble back-projection
  still requires the camera board pose because pivot/translation geometry has
  not been measured.

### Hiwonder actuator measurements already completed

- Confirmed mapping: motor 1 positive drives beta negative; motor 2 positive
  drives alpha negative.
- Driver: 30 Hz loop, 30 ms move time, home targets 500/500, 1.5 servo units per
  command, 20-servo-unit maximum change per tick, one-unit deadband and
  one-second timeout-to-home.
- Accepted low-amplitude axis/sign run at actual commands ±20.
- Accepted repeated step run at actual commands ±10.
- Accepted three-cycle static sweep at actual commands 0, ±5, ±10 and ±15.
- Axis 1 shows asymmetric gain, hysteresis and roughly 0.17–0.18 s end-to-end
  response. Axis 2 at ±10/15 is close to camera-estimator noise.
- A separate ±20 step exhibited delayed large motion and triggered the
  four-degree safety abort. Do not repeat it as an unguarded step.
- These results reject one symmetric linear actuator gain; simulation needs
  direction dependence, deadband/stiction, backlash state and randomized delay.

## What is still missing

Run these stages in order. Each stage must be reviewed before moving to the
next one.

1. **Ubuntu and ROS readiness, no motion**
   - Build the clean checkout and run its tests.
   - Inventory camera, ESP32 serial and Hiwonder HID device paths/permissions.
   - Confirm one ROS domain, one camera publisher and one estimator publisher.
   - Keep DreamerV3 and `tcp_ros_bridge.py` stopped.
2. **Camera-only regression, no motion**
   - Verify 60 Hz images, marker initialization, finite board pose and marble
     position using `orientation_mode:=camera` and `ai_mode:=off`.
   - Re-measure home offsets for the current physical placement.
3. **AI shadow validation, no policy control**
   - Run `ai_mode:=shadow` and measure false positives, disagreement, confidence
     and inference latency across holes, reflections, lighting and occlusion.
4. **BNO086/ESP32 validation, no motor commands**
   - Verify quaternion order, units, rate, timestamps, calibration status and
     stale-data behavior on `/tag_imu/data`.
   - Align sensor axes to board axes. Move one board axis manually at a time and
     verify the signs against camera-only alpha/beta.
   - Record stationary drift and camera/IMU disagreement before enabling
     `fused`. Unplug/reconnect the ESP32 to prove camera fallback is continuous.
5. **Velocity and synchronized-latency measurement**
   - Correct/replace the current velocity estimator and prove near-zero velocity
     on a stationary marble before using velocity in physical fits.
   - Measure image-header-to-state latency and command-to-state latency with
     source timestamps, not receipt-time correlation alone.
6. **Axis-2 actuator identification, marble removed**
   - Use a gradual, axis-2-only ramp/sweep that clears the observed deadband;
     do not use the rejected abrupt ±20 step.
   - Dry-run the generated phase plan first. Retain the 20-degree absolute,
     four-degree excursion, 0.25 s stale-state and exclusive-publisher aborts.
   - The operator must approve the exact command envelope after reviewing the
     dry run and live home stability.
7. **Marble dynamics, new protocol required**
   - With reliable fused angles and corrected velocity, collect repeated small
     tilt/release trajectories for tilt-to-acceleration, rolling resistance and
     velocity-dependent damping.
   - Collect controlled low-speed wall impacts for restitution.
   - Repeat across both tilt axes and representative printed surfaces. These
     tests need a separately reviewed recorder/protocol and are not authorized
     by the existing marble-removed `tag_sysid active` token.
8. **Update and validate simulation**
   - Fit distributions, not one nominal value, and retain camera/angle noise,
     backlash and rare stalls.
   - Re-evaluate candidate checkpoints under the updated distributions before
     any reduced-command physical policy commissioning.

## Ubuntu checkout and dependencies

The known platform is Ubuntu 22.04 with ROS 2 Humble. First confirm this rather
than installing a different ROS distribution:

```bash
lsb_release -a
test -f /opt/ros/humble/setup.bash && echo "ROS Humble found"
```

For a new checkout of the organized repository:

```bash
git clone git@github.com:dat07032002/Multi-maze.git
cd Multi-maze
git branch --show-current
git log -1 --oneline
```

For an existing checkout, preserve local work and update only by fast-forward:

```bash
git status --short
git fetch origin
git switch main
git pull --ff-only origin main
```

Install the base tools only after confirming Ubuntu/ROS versions:

```bash
sudo apt update
sudo apt install -y \
  build-essential git v4l-utils \
  python3-pip python3-venv python3-pytest python3-numpy python3-scipy \
  python3-opencv python3-matplotlib python3-serial python3-hid \
  python3-colcon-common-extensions python3-rosdep \
  libhidapi-dev libhidapi-hidraw0
```

Resolve ROS package dependencies and build:

```bash
source /opt/ros/humble/setup.bash
sudo rosdep init 2>/dev/null || true
rosdep update
rosdep install --from-paths . --ignore-src -r -y
colcon build --symlink-install --packages-select \
  tag_interfaces tag_camera tag_state_estimation tag_hiwonder tag_sysid tag_dreamer
source install/setup.bash
colcon test --packages-select tag_state_estimation tag_sysid
colcon test-result --verbose
```

Do not use `sudo ros2`. If serial access is denied, add the user to `dialout`; if
camera access is denied, add the user to `video`, then log out and back in:

```bash
sudo usermod -aG dialout,video "$USER"
```

Do not apply a broad `chmod 666 /dev/hidraw*`. Identify the Hiwonder device by
VID/PID and install a narrow udev rule only after the device inventory is saved.

## First read-only inventory on Ubuntu

```bash
git status --short
git log -1 --oneline
lsusb
v4l2-ctl --list-devices
ls -l /dev/v4l/by-id/ 2>/dev/null || true
ls -l /dev/serial/by-id/ 2>/dev/null || true
ls -l /dev/hidraw* 2>/dev/null || true
python3 -c "import cv2, numpy, scipy, serial, hid; print('Python hardware dependencies OK')"
```

Expected USB identities from the earlier hardware inventory:

```text
2560:c128  See3CAM_24CUG camera
0483:5750  Hiwonder HID controller
```

## Initial no-motion ROS checks

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
python3 -m pytest -q tag_state_estimation/test tag_sysid/test
ros2 run tag_sysid active --test axis
ros2 run tag_sysid active --test sweep --axis-only 2 --command-scale 0.125
```

The last two commands are dry runs: without `--execute`, they do not initialize
ROS or create a command publisher. Save their output for review. Do not add the
arm token until the device inventory, estimator stability and exact plan have
been reviewed with the user.

## Prompt for the Ubuntu Codex agent

```text
Read docs/HARDWARE_HANDOFF_2026-07-26.md completely, then inspect the current
checkout and Ubuntu hardware without commanding motors. Confirm Ubuntu/ROS
versions, install only missing dependencies, build the six TAG ROS packages,
run state-estimation and sysid tests, inventory the camera/ESP32/Hiwonder device
paths and permissions, and report all failures. Keep DreamerV3 and the TCP bridge
stopped. Do not use --execute, publish motor commands, change udev permissions,
or start a physical policy without my explicit approval. After the no-motion
checks pass, propose the exact camera-only and BNO086 validation commands.
```

## Source records

- `docs/HARDWARE_RECORDING_2026-07-24.md`
- `docs/BALL_CAMERA_TESTS_2026-07-24.md`
- `docs/SYSID_AXIS_2026-07-24.md`
- `docs/SYSID_STEP_2026-07-24.md`
- `docs/SYSID_SWEEP_2026-07-24.md`
- `tag_state_estimation/AI_MARBLE_DETECTOR.md`
- `tag_state_estimation/IMU_ORIENTATION.md`
- `docs/TRAINING.md` and `docs/V2_TRAINING.md`
