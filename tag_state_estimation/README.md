# TAG state estimation

ROS 2 board-pose and marble-state estimation used by the physical platform.
It subscribes to `tag_camera/image` and publishes state on
`tag_state_estimation/estimate`; the policy-facing estimator additionally
publishes its image crop on `tag_state_estimation/estimate_subimg`.

```bash
ros2 run tag_state_estimation estimator_sub
```

The learned marble detector is integrated but remains disabled by default.
Use `ai_mode:=shadow` for subscribe-only validation before considering hybrid
measurements. See [AI_MARBLE_DETECTOR.md](AI_MARBLE_DETECTOR.md).

The checked-in calibration is `calib/calib_results_tag.txt`. The synchronized
upstream detector masks the nearest corner marker and uses the updated marker
radius, area, and circularity gates. Treat calibration and camera placement as
hardware-specific: revalidate them if the camera mount changes.

The checked-in `markers.csv` is synchronized to the marker coordinates in the
working hardware estimator on 2026-07-24. Earlier organized coordinates were
20-30 pixels out of date and could not initialize fixed-corner localization on
the current camera mount.

The policy-facing estimator rejects plate-pose solutions outside 20 degrees or
more than 3 degrees from the previous accepted frame. It resets predictive
corner tracking, holds at most two frames, then publishes non-finite state so a
controller or sysid tool must stop if recovery fails. Thresholds are ROS
parameters and retain hard validation bounds in the continuity gate.

Board-mounted BNO086 support is implemented behind the default-off
`orientation_mode` parameter. It accepts standard ROS IMU data, includes an
ESP32 serial adapter, aligns the IMU frame from a simultaneous camera pose, and
provides guarded `camera`, `imu`, and `fused` modes. See
[IMU_ORIENTATION.md](IMU_ORIENTATION.md) for the wire protocol and hardware test.
