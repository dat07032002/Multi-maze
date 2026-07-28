# Source-timestamped actuator response at command 80 — 2026-07-27

The marble was removed and the guarded actuator protocol completed a one-run
envelope check followed by three positive/negative repetitions on each motor.
Every run returned to neutral. No 4-degree excursion, 15-degree
baseline-relative angle, stale-state, or command-exclusivity interlock fired.
DreamerV3, the TCP bridge, and physical policy remained stopped.

Accepted repeated sessions:

- `/home/dat/tag_sysid_logs/active/step_20260727T215053Z` (motor 1)
- `/home/dat/tag_sysid_logs/active/step_20260727T215131Z` (motor 2)

The machine-readable fit and raw-file hashes are in
`docs/sysid_actuator_step80_2026-07-27.json`.

## Direction-dependent local response

Changes are phase-tail medians relative to the immediately preceding home
phase. Values below are medians across three repetitions.

| Motor/direction | Alpha change | Beta change | Dominant t90 |
| --- | ---: | ---: | ---: |
| 1 positive | +0.3644 deg | -0.7111 deg | 0.265 s |
| 1 negative | +0.2736 deg | +0.2708 deg | 0.275 s |
| 2 positive | -0.4370 deg | -0.2081 deg | 0.139 s |
| 2 negative | +0.4179 deg | +0.3125 deg | 0.198 s |

At command 40, positive motor 2 and negative motor 1 were directionally
ambiguous because of preload, backlash, and home drift. Command 80 cleared that
region and produced the expected reversal on both axes. The simulator therefore
uses the command-80 maps as its nominal local response and continues to
randomize lower-amplitude stiction and hysteresis.

Across usable 10% and 90% crossing pairs, a first-order-plus-delay
approximation gives a nominal pure delay of 33 ms and a response time constant
of 86 ms. This predicts a nominal end-to-end t90 near 0.23 s. Timing includes
the Hiwonder driver, linkage, camera exposure and transport, estimator, and ROS
delivery; it is not pure servo latency.

## Remaining uncertainty

This campaign identifies local response through command 80, not saturation at
the policy limit. It does not justify a memoryless model of backlash, thermal
drift, rare stalls, or simultaneous two-axis coupling. Those effects remain
domain-randomized. Servo temperature telemetry is unavailable on the current
HID controller.
