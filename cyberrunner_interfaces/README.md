# cyberrunner_interfaces

Shared ROS interfaces for TAG CyberRunner.

Preferred actuator API:

- `BoardCommand.msg`: hardware-neutral two-axis board command
- `BoardReset.srv`: return the board to the driver's configured home position

`DynamixelVel.msg` and `DynamixelReset.srv` remain available for existing
trained workflows. They are compatibility names and do not describe the active
Hiwonder hardware.
