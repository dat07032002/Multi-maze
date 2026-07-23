# Hiwonder actuator setup

TAG uses two Hiwonder servos through a Hiwonder HID controller. The active
driver is `hiwonder_compat_node.py`. The containing ROS package still has the
historical name `cyberrunner_dynamixel` for compatibility.

## Configuration

The canonical parameters are in
`cyberrunner_dynamixel/config/hiwonder.yaml`. They include:

- USB vendor and product IDs
- servo IDs
- home positions and travel limits
- command-to-position scaling
- smoothing and command timeout
- reset sequence
- optional temperature-reader settings

Treat home positions, direction, scale, and limits as robot-specific calibration.
Record a known-good value before changing it.

## Dependencies and permissions

The HID path requires a Python HID package and permission to access the matching
`/dev/hidraw*` device. `scripts/reconnect_hiwonder.sh` diagnoses USB visibility,
repairs temporary permissions, and restarts the legacy-compatible node. Its
deep-reset option can reset a USB hub and may briefly interrupt the camera or
Arduino, so use that option deliberately.

## Build and launch

```bash
colcon build --symlink-install
source install/setup.bash
ros2 launch cyberrunner_dynamixel hiwonder.launch.py
```

The node accepts both APIs during migration:

| API | Command | Reset |
| --- | --- | --- |
| Preferred | `/cyberrunner/actuator/command` (`BoardCommand`) | `/cyberrunner/actuator/reset` (`BoardReset`) |
| Legacy | `/cyberrunner_dynamixel/cmd` (`DynamixelVel`) | `/cyberrunner_dynamixel/reset` (`DynamixelReset`) |

## Safe smoke test

1. Disconnect the maze linkage or ensure the board has unobstructed low-range travel.
2. Confirm both servos are at the configured home positions.
3. Start the Hiwonder launch file and watch for the detected `0483:5750` device.
4. Send very small commands on one axis at a time.
5. Confirm positive/negative direction and physical axis assignment.
6. Stop commands and confirm the timeout returns the servos home.
7. Call the reset service and confirm the reset motion stays within safe travel.

Never test the old Dynamixel or Feetech executables against the TAG hardware.
