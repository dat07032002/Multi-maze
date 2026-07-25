# TAG camera

ROS 2 camera publishers for the physical TAG labyrinth. The live publisher
publishes `sensor_msgs/Image` on `tag_camera/image`; the supplied launch file
can start it together with `tag_state_estimation`.

```bash
ros2 run tag_camera fast_camera_publisher.py --ros-args -p device:=/dev/video2
# Or launch camera plus estimator:
ros2 launch tag_camera camera_estimation_gpu.launch.py
```

The fast publisher locks white balance to 4000, exposure to approximately 8 ms,
and saturation to 40 so the learned detector receives the camera appearance it
was trained on. Device, resolution, frame rate, crop, and color controls remain
ROS parameters. Verify the device path and image orientation on the robot.
