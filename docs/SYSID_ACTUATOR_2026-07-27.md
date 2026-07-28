# Source-timestamped actuator identification — 2026-07-27

The marble-removed actuator campaign completed one gradual static sweep and one
three-repetition step protocol on each motor axis.  All runs returned to neutral
without crossing the two-degree baseline-relative safety guard.  DreamerV3, the
TCP bridge, and every physical policy remained stopped.

The accepted repeated-step datasets are:

- `/home/dat/tag_sysid_logs/active/step_20260727T185322Z` (motor 1)
- `/home/dat/tag_sysid_logs/active/step_20260727T185440Z` (motor 2)

Each direction used actual command magnitude 26.66664.  Phase-tail medians are
relative to the immediately preceding home phase.  Timing compares command ROS
time to the state source-image timestamp.  The machine-readable fit, including
raw-file SHA-256 hashes, is in `sysid_actuator_2026-07-27.json`.

| Motor/direction | Median alpha change | Median beta change | Dominant t90 |
| --- | ---: | ---: | ---: |
| 1 positive | +0.3172 deg | -0.0002 deg | 0.187 s |
| 1 negative | -0.1729 deg | +0.3647 deg | 0.198 s |
| 2 positive | -0.0157 deg | -0.0231 deg | below reliable response threshold |
| 2 negative | +0.6840 deg | +0.3454 deg | 0.188 s |

These measurements reject a symmetric diagonal actuator model.  They initially
motivated separate positive and negative 2x2 local command-to-angle maps, a
nominal one-driver-tick transport delay, a 75 ms response time constant, and a
high positive-direction stiction prior for motor 2.  The later command-80
campaign cleared the ambiguous directions and superseded these nominal map and
timing values; see `SYSID_ACTUATOR_STEP80_2026-07-27.md`.  This command-26.67
record remains useful evidence of low-amplitude preload and stiction.

The data do **not** identify full-range saturation, a precise backlash width,
thermal drift, or the probability of rare stalls.  The simulator must retain
uncertainty for those effects.  Marble rolling resistance, damping, and wall
restitution also remain priors because the corresponding physical tests were
skipped.
