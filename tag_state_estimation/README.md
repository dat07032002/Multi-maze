# TAG state estimation

ROS 2 board-pose and marble-state estimation used by the physical platform.
It subscribes to `tag_camera/image` and publishes state on
`tag_state_estimation/estimate`; the policy-facing estimator additionally
publishes its image crop on `tag_state_estimation/estimate_subimg`.

```bash
ros2 run tag_state_estimation estimator_sub
```

The checked-in calibration is `calib/calib_results_tag.txt`. The synchronized
upstream detector masks the nearest corner marker and uses the updated marker
radius, area, and circularity gates. Treat calibration and camera placement as
hardware-specific: revalidate them if the camera mount changes.
