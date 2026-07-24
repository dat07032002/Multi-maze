# TAG camera

ROS 2 camera publishers for the physical TAG labyrinth. The live publisher
publishes `sensor_msgs/Image` on `tag_camera/image`; the supplied launch file
can start it together with `tag_state_estimation`.

```bash
ros2 run tag_camera cam_publisher.py /dev/video2
# Or launch camera plus estimator:
ros2 launch tag_camera camera_estimation_gpu.launch.py
```

Device, resolution, frame-rate, crop, and optional OpenCV acceleration are
runtime parameters. Verify the device path and image orientation on the robot.
