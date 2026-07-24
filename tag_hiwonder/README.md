# TAG Hiwonder servo driver

The active ROS 2 actuator node for the physical platform. It receives
`tag_interfaces/HiwonderVel` commands on `tag_hiwonder/cmd` and exposes
`tag_hiwonder/reset`. It drives two Hiwonder HID servos and includes command
rate limiting, timeout-to-home, USB reconnect, and temperature safeguards.

```bash
ros2 run tag_hiwonder hiwonder_compat_node.py
```

Home positions, servo limits, signs/scales, timing, and thermal limits are ROS
parameters. Confirm them with small commands before policy deployment. No
Dynamixel or Feetech driver is part of the active stack.
