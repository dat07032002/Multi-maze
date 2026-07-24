# Guarded hardware sysid: multilevel static sweep — 2026-07-24

## Result

The Hiwonder mechanism completed all 84 phases of a three-cycle, two-axis
static sweep at commands 0, +/-5, +/-10, and +/-15. The run completed normally,
issued its final home sequence, and left zero publishers on the motor command
topic.

This is an accepted measurement run, but it is not evidence for a single linear
servo model. Axis 1 shows direction-dependent gain and hysteresis. Axis 2 motion
at these command levels is close to the estimator noise floor.

## Estimator correction before the run

The planar pose solver sometimes selected the wrong solvePnP branch. The
organized estimator now:

1. uses IPPE planar-pose candidates;
2. rejects candidates behind the camera;
3. selects by reprojection error and temporal continuity; and
4. retains the independent 20-degree absolute and 3-degree frame-step gate.

The current hardware/camera placement also changed the apparent home from the
earlier approximately 11.5-degree alpha offset to 20.47 degrees. Both the
organized estimator and the untouched hardware estimator reported the same new
value, so this was not a disagreement between implementations. Explicit runtime
home offsets were therefore applied in the published state convention:

- alpha zero: +20.4660 degrees;
- beta zero: -1.7529 degrees.

After removing a duplicate estimator publisher, a ten-second passive check had
545 finite samples, mean alpha 0.186 degrees, mean beta 0.074 degrees, and
maximum single-frame changes of 0.498 and 0.510 degrees. Exactly one estimator
publisher was present before the active run.

These offsets are calibration values for this camera/board placement. Measure
them again if the camera, frame, marker locations, or neutral servo geometry
changes.

## Guarded protocol

- Marble removed and operator present.
- TCP policy bridge inactive.
- Exactly one expected Hiwonder command subscriber and no command publisher
  before arming.
- Interface profile: `legacy-hardware-filtered-estimator`.
- Three cycles per axis.
- Sequence per axis and cycle: 0, +5, +10, +15, +10, +5, 0, -5, -10,
  -15, -10, -5, 0, then home settle.
- 2.5 seconds per static level and 3.0 seconds per home settle.
- Hard command limit 15, absolute board-angle limit 20 degrees, excursion limit
  4 degrees, and state timeout 0.25 seconds.
- Baseline after zeroing: alpha 0.191 degrees, beta 0.049 degrees.

The run recorded 12,912 state samples and 2,083 command samples. Across the
entire run, alpha remained from -0.385 to +0.720 degrees and beta from -0.543 to
+0.759 degrees.

## Steady response

For each static phase, the median of the final second was used. To remove slow
home drift, each response was measured relative to a linear interpolation
between the zero-command phases bracketing that half-cycle. `Away` means moving
out from zero toward +/-15; `return` means moving back toward zero.

### Axis 1 to beta

| command | path | beta delta mean +/- phase std (deg) |
|---:|:---|---:|
| +5 | away | -0.049 +/- 0.027 |
| +10 | away | -0.129 +/- 0.026 |
| +15 | away | -0.254 +/- 0.062 |
| +10 | return | -0.219 +/- 0.052 |
| +5 | return | -0.161 +/- 0.019 |
| -5 | away | +0.108 +/- 0.046 |
| -10 | away | +0.132 +/- 0.020 |
| -15 | away | +0.053 +/- 0.026 |
| -10 | return | -0.010 +/- 0.011 |
| -5 | return | +0.022 +/- 0.026 |

The positive branch is monotonic while moving away from home, but its return
path is different. The negative branch peaks before -15 and nearly disappears
on return. This is strong evidence of backlash, static friction, and/or linkage
preload; a symmetric linear gain is not appropriate.

### Axis 2 to alpha

| command | path | alpha delta mean +/- phase std (deg) |
|---:|:---|---:|
| +5 | away | +0.042 +/- 0.009 |
| +10 | away | +0.013 +/- 0.038 |
| +15 | away | -0.030 +/- 0.038 |
| +10 | return | -0.020 +/- 0.047 |
| +5 | return | -0.030 +/- 0.007 |
| -5 | away | -0.036 +/- 0.034 |
| -10 | away | -0.091 +/- 0.015 |
| -15 | away | -0.112 +/- 0.022 |
| -10 | return | -0.110 +/- 0.020 |
| -5 | return | -0.071 +/- 0.023 |

Most axis-2 responses are about 0.01 to 0.11 degrees. That is too close to the
observed camera-pose variation to fit a reliable low-command curve. The earlier
+/-20 axis test remains the stronger sign/magnitude evidence for axis 2.

## Modeling consequence

Use this sweep to define a bounded, direction-dependent actuator model:

- keep the confirmed mapping `motor 1 -> -beta` and `motor 2 -> -alpha`;
- include deadband/stiction and a previous-command or backlash state;
- do not extrapolate a single gain through zero;
- initialize simulation randomization broadly enough to include the observed
  asymmetric branches; and
- preserve camera angle noise and calibration offset as separate quantities
  from mechanical dynamics.

The next high-value hardware measurement is an axis-2-focused test with enough
excitation to clear its deadband while retaining the existing excursion and
absolute-angle aborts. End-to-end command/camera latency also remains to be
identified with synchronized timestamps.

## Raw evidence

Raw files remain on the hardware computer at:

`/home/trungbao/tag_sysid_logs/active/sweep_20260724T210924Z/`

| file | bytes | SHA-256 |
|:---|---:|:---|
| `commands.csv` | 123,180 | `d3dd8562e1e0dd5b3a80348ebe8a0d567af1758bf8e39f560b936a5d6ae24983` |
| `board_angles.csv` | 2,428,879 | `096b9714a9a36f43c61fb52620965f5a57a5df04cdb3a62734b1cf0b4861f537` |
| `metadata.json` | 14,710 | `122ee3b3d318e12a3a6067575c51648e52b21cb7b859b778160b282171823fa0` |
