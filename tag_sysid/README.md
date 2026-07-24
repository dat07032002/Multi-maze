# TAG passive system-identification recorder

This ROS 2 package records useful timing and operating data while the physical
CyberRunner is already running. The recorder is passive: it has no publisher,
service client, or action client and cannot command or reset the Hiwonder
servos.

## Build

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select tag_interfaces tag_sysid
source install/setup.bash
```

## Record a normal hardware run

Start the camera, estimator, Hiwonder node, and policy normally. On the same ROS
host, start a ten-minute recording:

```bash
ros2 run tag_sysid record --ros-args \
  -p session_name:=normal_policy_01 \
  -p max_duration_sec:=600.0
```

The currently working hardware checkout still uses legacy CyberRunner topic and
message names. Record that graph without changing its running nodes by selecting
the compatibility profile:

```bash
ros2 run tag_sysid record --ros-args \
  -p interface_profile:=legacy-hardware \
  -p session_name:=legacy_policy_01 \
  -p max_duration_sec:=600.0
```

The default output is `~/tag_sysid_logs/<session_name>/`:

- `camera.csv`: receipt time, image header time, dimensions, and encoding only;
- `states.csv`: board angles, marble position/velocity, and visibility;
- `commands.csv`: Hiwonder commands and derived target positions; and
- `metadata.json`: timing, counts, host information, conversion parameters,
  safety declaration, and limitations.

Image pixels are deliberately not saved, so the logger has low storage and CPU
overhead. Stop with Ctrl-C if no duration is specified.

## Analyze

```bash
ros2 run tag_sysid analyze ~/tag_sysid_logs/normal_policy_01
```

The analyzer writes `summary.json` with topic rates and jitter, camera header
age, ball-loss rate, observed ranges, and a preliminary command-to-board-angle
map and correlation lag. The map is obtained from closed-loop policy data and
must be treated as preliminary.

## What this cannot identify passively

Normal policy data is not enough for trustworthy backlash, step response,
friction, or wall-restitution estimates. Those require a separate excitation
node with explicit human approval, the marble removed for servo sweeps, strict
angle/command limits, an emergency stop, and automatic return to home. Do not
run active excitation while a policy or TCP bridge can also publish commands.

## Ubuntu hardware readiness

The known USB devices are:

```text
2560:c128  See3CAM_24CUG camera
0483:5750  Hiwonder HID controller
```

After booting Ubuntu 22.04 and connecting both devices:

```bash
lsusb
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select \
  tag_interfaces tag_camera tag_state_estimation tag_hiwonder tag_sysid
source install/setup.bash
python3 -m pytest -q tag_sysid/test
```

Before any active measurement, verify the camera, estimator, and Hiwonder
driver individually. Keep DreamerV3 and `tcp_ros_bridge.py` stopped.

## Guarded active measurements

`active` is safe-by-default: without `--execute` it prints the plan and does
not initialize ROS or create a publisher.

```bash
ros2 run tag_sysid active --test axis
ros2 run tag_sysid active --test sweep
ros2 run tag_sysid active --test step
```

Add `--interface-profile legacy-hardware` when measuring the existing working
stack. This selects its legacy topics, message package, and expected Hiwonder
node; it does not weaken any safety interlock.

Execution requires the exact arm token, an operator at the emergency stop,
confirmation that the marble is removed, finite board-angle estimates, the
expected `tag_hiwonder_compat` driver subscriber, no other command publisher,
and an explicit maximum command large enough for the selected plan. During
execution it also returns home and aborts if either estimated board angle exceeds
15 degrees, changes by more than 4 degrees from a one-second preflight median,
or the state stream is more than 0.25 seconds old. Thresholds can only be changed
within hard CLI bounds. The baseline-relative limit allows a documented estimator
zero offset without allowing an equally large physical excursion.

Run the small axis/sign measurement first:

```bash
ros2 run tag_sysid active \
  --test axis \
  --interface-profile legacy-hardware \
  --execute \
  --arm START_ACTIVE_SYSID \
  --operator-present \
  --ball-removed \
  --max-command 40
```

Only after reviewing that result should the operator consider the home,
static-sweep, and step-response plans:

```bash
# Five return-home measurements; maximum command 40.
ros2 run tag_sysid active --test home --execute \
  --arm START_ACTIVE_SYSID --operator-present --ball-removed \
  --max-command 40

# Three bidirectional sweeps; maximum command 120.
ros2 run tag_sysid active --test sweep --execute \
  --arm START_ACTIVE_SYSID --operator-present --ball-removed \
  --max-command 120

# Ten positive/negative steps per axis; maximum command 80.
ros2 run tag_sysid active --test step --execute \
  --arm START_ACTIVE_SYSID --operator-present --ball-removed \
  --max-command 80
```

Each run writes `metadata.json`, `commands.csv`, and `board_angles.csv` under
`~/tag_sysid_logs/active/`. Ctrl-C requests command zero repeatedly. If command
topic exclusivity is lost, the tool immediately stops publishing and relies on
the Hiwonder driver's one-second timeout to return home.

The order is mandatory: dry run, axis/sign at 40, review, then any larger test.
Code readiness does not authorize motor motion; the operator must approve each
active run on the Ubuntu machine.
