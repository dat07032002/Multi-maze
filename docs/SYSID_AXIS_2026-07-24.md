# Guarded hardware sysid: axis/sign run — 2026-07-24

## Result

The first accepted active system-identification run completed on the physical
Hiwonder mechanism using the working legacy ROS graph. It used three repetitions
of each direction on each motor axis at command magnitude 20, with two-second
home phases between excitations.

This is an accepted **low-amplitude axis/sign and preliminary local-gain run**.
It is not yet a full servo map, backlash model, friction estimate, or validated
simulation parameter set.

## Safety and provenance

- Marble removed and operator present at the hardware.
- TCP policy bridge stopped before excitation.
- Command topic had zero publishers and exactly the expected Hiwonder subscriber
  before the sysid publisher was armed.
- Legacy-hardware interface profile selected explicitly.
- Command scale: 0.5, reducing the normal axis protocol from +/-40 to +/-20.
- Hard estimator angle bound: 20 degrees.
- Maximum excursion from the one-second median baseline: 4 degrees.
- Runtime state timeout: 0.25 seconds.
- All 24 phases completed; status `complete`.
- 2,999 state samples and 495 command samples were recorded.
- Baseline: alpha 11.4582 degrees, beta -0.5467 degrees.
- Command publisher count returned to zero after the run.

Raw files remain on the hardware computer in the timestamped active-sysid
session. Their identities are:

| File | Bytes | SHA-256 |
|---|---:|---|
| `metadata.json` | 5,027 | `1575436f9c83b66d58fd430bb0629bda777cea4d214ae2371d480ad635b0217b` |
| `commands.csv` | 29,631 | `06ebe6b1d05154052880d51889e27627f23853cfdc422af39b39f413162415a3` |
| `board_angles.csv` | 561,709 | `ca6e9b698167ab2bae596644615feed220e08564f80fdb91fe4d0805e34f8c74` |

## Measured local response

Steady changes are medians over the final 0.4 seconds of each excitation,
relative to the preceding home phase. Values below are mean +/- population
standard deviation across three repetitions.

| Motor command | Delta alpha | Delta beta | Primary interpretation |
|---|---:|---:|---|
| axis 1, +20 | -0.148 +/- 0.035 deg | -0.793 +/- 0.046 deg | positive axis 1 drives beta negative |
| axis 1, -20 | -0.221 +/- 0.019 deg | +0.690 +/- 0.006 deg | negative axis 1 drives beta positive |
| axis 2, +20 | -0.478 +/- 0.132 deg | -0.069 +/- 0.008 deg | positive axis 2 drives alpha negative |
| axis 2, -20 | +0.405 +/- 0.074 deg | +0.040 +/- 0.009 deg | negative axis 2 drives alpha positive |

Local primary-axis slopes at this amplitude are approximately:

- motor axis 1 to beta: -0.0397 deg/command on the positive side and
  -0.0345 deg/command on the negative side;
- motor axis 2 to alpha: -0.0239 deg/command on the positive side and
  -0.0203 deg/command on the negative side.

The sign convention therefore is:

```text
motor 1 positive -> beta decreases
motor 2 positive -> alpha decreases
```

The unequal positive/negative slopes are evidence to investigate asymmetry or
backlash, but a single amplitude is insufficient to separate those effects from
estimator and home drift.

## Timing

The simple timing estimate uses the first crossing of 10% and 90% of each
phase's measured steady response. It includes Hiwonder command handling,
mechanism motion, camera exposure/transport, and estimator latency.

| Command | Median 10% crossing | Median 90% crossing |
|---|---:|---:|
| axis 1, +20 | 0.133 s | 0.202 s |
| axis 1, -20 | 0.103 s | 0.186 s |
| axis 2, +20 | 0.063 s | 0.184 s |
| axis 2, -20 | 0.065 s | 0.182 s |

Use these as preliminary end-to-end response estimates, not pure servo delay.
A dedicated step analysis with source timestamps is still required.

## Home repeatability

Across the interleaved two-second home phases:

- alpha median range: 11.1891 to 11.5873 degrees; standard deviation 0.1322
  degrees;
- beta median range: -0.5733 to -0.4421 degrees; standard deviation 0.0410
  degrees.

The approximately 11.5-degree alpha value at the apparent command-zero home is
a coordinate-zero issue that must be resolved or represented explicitly in the
simulator and policy observation normalization.

## Safety aborts before the accepted run

The interlocks prevented three unsafe or invalid starts:

1. An extra TCP command publisher was present: no command sent.
2. A +/-40 trial moved beta 5.52 degrees from baseline: the tool aborted and
   issued ten home commands. This amplitude is not approved for later protocols.
3. A later preflight contained 17 invalid plate-pose samples out of 61, with
   alpha estimates from 26.5 to 34.4 degrees: no command sent.

The estimator subsequently produced 600 stable samples over ten seconds around
alpha 11.51 degrees and beta -0.51 degrees before the accepted run. The pose
ambiguity still needs a continuity/outlier gate before longer identification.

## What remains

1. Fix or explicitly calibrate the board-angle zero and reject discontinuous
   plate-pose solutions.
2. Run the guarded step protocol at the already accepted +/-20 amplitude to
   improve delay, rise-time, settling, and repeatability estimates.
3. Run a multilevel static sweep no larger than the demonstrated safe envelope
   to estimate nonlinearity, asymmetry, deadband, and backlash.
4. With the marble installed and motors under a separately approved protocol,
   collect roll-down data for rolling resistance and axis coupling.
5. Update simulator distributions only after repeated accepted trials.

Do not restart the TCP policy bridge while active sysid is armed. At the end of
this run the bridge remained stopped, the estimator service remained active, and
the Hiwonder node was the only command-topic subscriber.
