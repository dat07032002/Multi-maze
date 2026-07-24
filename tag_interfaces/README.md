# TAG ROS interfaces

Shared ROS 2 messages and service definitions for the physical TAG stack:

- `HiwonderVel.msg`: two-servo command
- `HiwonderReset.srv`: board reset request
- `StateEstimate.msg`: board and marble state
- `StateEstimateSub.msg`: state plus policy image crop

These interfaces connect `tag_state_estimation`, `tag_hiwonder`, the TCP
bridge, and the real-hardware Dreamer environment.
