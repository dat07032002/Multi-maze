# Guarded hardware sysid: step response — 2026-07-24

## Result

The accepted step-response run completed 100 phases at command magnitude 10:
ten positive and ten negative steps on each motor axis, with home commands
between every excitation. It recorded 9,145 state samples and 1,520 command
samples without a safety abort.

This run is reliable for the sign and low-amplitude response of motor axis 1.
Motor-axis-2 motion at magnitude 10 is close to estimator noise, so its gain and
timing values are low confidence. The results also demonstrate amplitude-dependent
gain and a delayed large movement in a separate magnitude-20 trial; a single
linear actuator model is not yet justified.

## Conditions and safety

- Working legacy camera, estimator, and Hiwonder ROS graph.
- Marble removed and operator present.
- TCP bridge stopped; zero external command publishers before arming.
- Step protocol command scale 0.125: nominal +/-80 became +/-10.
- Hiwonder command scale 1.5 servo units per command: +/-10 corresponds to
  servo targets 485 and 515 around home 500.
- One-second median angle baseline: alpha 11.3196 degrees, beta -0.7432 degrees.
- Hard absolute estimator bound 20 degrees and baseline-excursion bound 4 degrees.
- Runtime state timeout 0.25 seconds.
- Command publisher count returned to zero after completion.

The live Hiwonder parameters were also confirmed during this run: 30 Hz command
loop, 30 ms move time, maximum 20 servo units per tick, one-command-unit
deadband, and one-second timeout-to-home.

## Step magnitudes

Primary response is beta for motor axis 1 and alpha for motor axis 2. Values are
mean +/- population standard deviation across ten trials.

| Motor step | Primary response | Cross-axis response | Local primary slope |
|---|---:|---:|---:|
| axis 1, +10 | beta -0.276 +/- 0.059 deg | alpha -0.002 +/- 0.027 deg | -0.0276 deg/command |
| axis 1, -10 | beta +0.313 +/- 0.035 deg | alpha -0.053 +/- 0.041 deg | -0.0313 deg/command |
| axis 2, +10 | alpha -0.110 +/- 0.026 deg | beta -0.010 +/- 0.030 deg | -0.0110 deg/command |
| axis 2, -10 | alpha +0.090 +/- 0.019 deg | beta +0.002 +/- 0.022 deg | -0.0090 deg/command |

Motor-axis-1 signs and response magnitudes are consistent. The first positive
trial was smaller (-0.109 degrees) than the other nine (-0.266 to -0.331
degrees), which is evidence of initialization, stiction, or backlash.

For motor axis 2, the home-phase alpha noise standard deviation averaged 0.053
to 0.056 degrees, while the measured response was only 0.09 to 0.11 degrees.
That signal-to-noise ratio is too small for a high-confidence dynamic fit.

## Timing

The timing below is end-to-end: Hiwonder driver, mechanism, camera, estimator,
ROS transport, and recorder. It is not pure servo latency.

| Motor step | Median 10% crossing | Median 90% crossing | Interpretation |
|---|---:|---:|---|
| axis 1, +10 | 0.027 s | 0.172 s | usable |
| axis 1, -10 | 0.041 s | 0.179 s | usable |
| axis 2, +10 | 0.041 s | 0.131 s | low SNR |
| axis 2, -10 | 0.044 s | 0.084 s | low SNR |

For axis 1, the positive step settled within the analysis band in a median
0.139 seconds among the nine trials that settled; one did not settle within the
1.5-second phase. Negative steps settled much more slowly, with a median 1.175
seconds. This direction asymmetry needs to be represented in identification and
domain randomization.

Overshoot percentages are not accepted from this run. The responses are small
enough that estimator noise inflates peak-to-steady ratios, especially on axis 2.

## Home repeatability

Using the home phase immediately before each of the 40 steps:

- alpha median range 11.2956 to 11.4289 degrees; standard deviation 0.0236
  degrees;
- beta median range -0.7608 to -0.4644 degrees; standard deviation 0.1040
  degrees.

The nonzero alpha home remains a coordinate/calibration offset and must not be
mistaken for a physical zero in simulation.

## Evidence of nonlinearity and stick-slip

The earlier accepted magnitude-20 axis run produced substantially larger slopes:

| Mapping | Slope at magnitude 10 | Slope at magnitude 20 |
|---|---:|---:|
| motor 1 positive to beta | -0.0276 | -0.0397 deg/command |
| motor 1 negative to beta | -0.0313 | -0.0345 deg/command |
| motor 2 positive to alpha | -0.0110 | -0.0239 deg/command |
| motor 2 negative to alpha | -0.0090 | -0.0203 deg/command |

This is strong evidence that the command-to-angle map is not linear near home.
Motor axis 2 in particular has a low-gain/deadband region around magnitude 10.

A magnitude-20 step test was attempted first and safely aborted. The board stayed
near baseline for approximately 1.15 seconds, then moved rapidly until beta had
changed -4.87 degrees and the 4-degree excursion interlock fired. The tool sent
ten home commands. That transition is evidence of intermittent stick-slip,
backlash, or actuator scheduling and must not be averaged into the accepted
magnitude-10 fit.

## Raw accepted-run identity

| File | Bytes | SHA-256 |
|---|---:|---|
| `metadata.json` | 17,382 | `16d62edac9d87def4a8d3c8f51618c27093c892cc097529a99fc45a1163f157a` |
| `commands.csv` | 91,164 | `f11eb8a4b1da22e6acfc661b106ef0062f95eded1dc307b6013f18023b90fcf4` |
| `board_angles.csv` | 1,715,754 | `1520ae684336515e9d6ad184acb49d72ee696c9489ae12bf340f452e8265e065` |

The raw files remain in the timestamped active-sysid session on the hardware
computer. The hashes bind this report to the source measurements without
publishing private machine paths.

## Modeling decision

Do not use one symmetric linear gain. The next simulator model should include:

1. separate motor-axis mapping (`u1 -> -beta`, `u2 -> -alpha`);
2. direction-dependent gain;
3. a command deadband/nonlinear gain near home;
4. approximately 0.17 to 0.18 seconds end-to-end response for axis 1;
5. home/zero offsets as separately calibrated quantities;
6. stochastic delay or stick-slip events until their physical cause is isolated;
7. estimator noise and rare pose-solution failures.

Before fitting those parameters, run the guarded multilevel static sweep within
the demonstrated safe envelope. Levels near 5, 10, and 15 command units will
show where the deadband ends without repeating the unsafe magnitude-20 step.
