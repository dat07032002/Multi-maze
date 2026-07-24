# Hardware recording: 2026-07-24

This report contains only direct measurements or clearly labeled limits from
the complete 600-second passive CyberRunner session. The private raw archive is
not committed because its metadata contains a host name, user path, and PID.

## Directly measured

| Measurement | Result |
| --- | ---: |
| Session duration | 600.000 s |
| Camera messages | 26,129 |
| Camera average rate | 43.55 Hz |
| Primary state messages | 35,611 |
| State average rate | 59.36 Hz |
| Motor-command messages | 6,152 |
| Median active command cadence | 28.22 Hz |
| Longest command silence | 98.964 s |
| Axis 1 commands at +/-180 | 62.94% |
| Axis 2 commands at +/-180 | 62.48% |
| Either command at +/-180 | 85.47% |
| Both commands at +/-180 | 39.95% |
| Ball missing over whole session | 26.60% |
| Ball missing near active commands | about 6-7% |
| Official DreamerV3 episodes | 28 |
| Official successes | 0 |
| Official episode steps | 6,116 |

The environment scaled normalized actions by 240. The local bridge clamped the
actual ROS command to 180 on each axis. Thus normalized action magnitudes from
0.75 through 1.0 were indistinguishable at the hardware command interface.

The camera measurement supports the current 45 Hz simulation prior. The active
control data supports a nominal 28-30 Hz policy/actuator interface rather than
the current 35 Hz point estimate.

## Do not treat as measured plant parameters

The passive command-to-angle regression had low explanatory power (R2 about
0.085 for alpha and 0.020 for beta). Its apparent delay, gain, axis mapping,
and coupling are not accepted physical parameters.

Two stationary intervals also had different raw angle estimates. A long silent
interval produced stable means near alpha 0.3200 rad and beta 0.2956 rad, but
the recording does not prove that the physical servos were at calibrated home.

Extreme estimated ball velocities reached physically impossible values. They
are evidence of estimator outliers, not evidence of real ball speed.

## Remaining priority measurements

Run in this order, with DreamerV3 and the TCP bridge stopped:

1. home-angle offset and repeatability;
2. motor axis and direction at command magnitude 40;
3. bidirectional command-to-angle sweep, only after reviewing step 2; and
4. repeated step response for delay and response speed.

Use the guarded `tag_sysid active` executable described in
[`tag_sysid/README.md`](../tag_sysid/README.md). Active execution requires an
operator, the marble removed, exclusive ownership of the command topic, and an
explicit arm token. Code readiness does not authorize hardware motion.
