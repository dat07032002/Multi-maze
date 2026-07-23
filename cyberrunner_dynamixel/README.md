# TAG actuator package

The package name `cyberrunner_dynamixel` is retained so existing trained
CyberRunner workflows continue to resolve their executables, topics, and
services. The active TAG robot uses the Hiwonder HID driver:

```bash
ros2 launch cyberrunner_dynamixel hiwonder.launch.py
```

Canonical parameters live in `config/hiwonder.yaml`. The old Dynamixel C++
executables are built only when `dynamixel_sdk` is available. Feetech and
Dynamixel files are compatibility/reference drivers and must not be launched on
the TAG Hiwonder hardware.

See `docs/08_hiwonder_setup.md` for the safe setup and test procedure.
