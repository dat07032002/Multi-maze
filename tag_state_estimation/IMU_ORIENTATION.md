# BNO086 board-orientation estimation

TAG can use the board-mounted SparkFun BNO086 through an ESP32 while retaining
the camera markers as the absolute geometric reference. Camera-only operation
remains the default until the hardware checks below pass.

## Data path

```text
BNO086 --I2C--> ESP32 --USB serial--> bno086_serial
       --> /tag_imu/data (sensor_msgs/Imu)
       --> camera/IMU alignment and guarded fusion
       --> StateEstimate alpha, beta
```

The estimator accepts any standards-compliant `sensor_msgs/Imu` publisher. The
included serial node is only an adapter for the planned ESP32 connection.

## ESP32 serial contract

Send one newline-terminated sample per report. Quaternion order is explicit
`x,y,z,w`; angular velocity must be rad/s and linear acceleration must be m/s².

```text
TAG_IMU,qx,qy,qz,qw,gx,gy,gz,ax,ay,az,accuracy
```

Example stationary identity-orientation report:

```text
TAG_IMU,0,0,0,1,0,0,0,0,0,9.81,3
```

Named JSON with the same fields is also accepted. `accuracy` is `0..3`, or `-1`
if the firmware cannot provide a classified BNO086 accuracy status. Unlabelled
CSV is deliberately rejected so quaternion ordering cannot be guessed wrong.

## Modes

- `camera`: existing marker-only behavior; no IMU subscription is created.
- `imu`: the first simultaneous valid camera/IMU sample aligns the BNO086
  reference frame to TAG world; subsequent fresh IMU orientation is used.
- `fused`: starts with the same alignment and slowly corrects it toward valid
  camera poses. This is the intended final mode after validation.

All non-camera modes fall back to the camera when IMU data is stale. If camera
and IMU differ by more than the configured limit, the camera wins and the bad
sample is not learned into the alignment. The existing angle magnitude and
frame-to-frame continuity gates remain active after fusion.

## First hardware test

Build and source the ROS workspace, then locate the ESP32 port:

```bash
ls -l /dev/serial/by-id/
```

Start in camera mode to verify no regression:

```bash
ros2 launch tag_camera camera_estimation_gpu.launch.py \
  orientation_mode:=camera
```

Then start the serial adapter but keep camera angles authoritative:

```bash
ros2 launch tag_camera camera_estimation_gpu.launch.py \
  orientation_mode:=fused \
  start_imu_serial:=true \
  imu_port:=/dev/serial/by-id/YOUR_ESP32_DEVICE
```

Keep the board still during startup until the alignment is established. Inspect:

```bash
ros2 topic hz /tag_imu/data
ros2 topic echo /tag_imu/accuracy
ros2 topic echo /tag_state_estimation/orientation_source
ros2 topic echo /tag_state_estimation/imu_age_sec
ros2 topic echo /tag_state_estimation/orientation_disagreement_deg
```

The default assumes the BNO086 X/Y/Z axes are parallel to the board X/Y/Z
axes. If the board mount rotates the sensor, provide the fixed extrinsic angles
with `imu_mount_roll_deg`, `imu_mount_pitch_deg`, and `imu_mount_yaw_deg`. These
describe the sensor frame orientation in the board frame and must be verified
by moving one physical board axis at a time.

Move each board axis slowly and separately. Confirm alpha and beta signs match
camera-only output, disagreement stays small, stale-data fallback works by
unplugging the ESP32, and no discontinuity occurs when it reconnects. Do not run
a physical policy until these checks and the motor safety checks pass.

## Current boundary

The fused rotation improves the published board angles and displayed maze TF.
Marble pixel-to-board back-projection still uses the per-frame camera pose and
therefore still needs visible board markers. Replacing camera translation during
marker loss requires a calibrated pivot/kinematic model and is intentionally not
guessed before hardware measurements.
