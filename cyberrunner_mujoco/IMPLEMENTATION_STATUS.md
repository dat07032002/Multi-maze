# Hardware-first implementation status

## Implementable without hardware

- Canonical TAG policy observation and action conversion
- Hardware-compatible DreamerV3 encoder keys
- Hiwonder absolute-position target, clamp, smoothing, timeout, and reset model
- Camera crop, grayscale conversion, noise, dropout bursts, detector hysteresis,
  short-loss prediction, and observation delay
- Fixed 40/8/8 maze split and validation isolation
- Finite-radius route validation
- Single-source maze package export to JSON, route, MJCF, preview, metadata, and
  prototype STL
- Automated offline tests and training approval gate

## Blocked until physical platform access

- Insert footprint is confirmed at 0.259 x 0.229 m; thickness and any retention
  or underside geometry remain unmeasured
- Servo position to board-angle calibration
- Board zero offsets and cross-axis coupling measurement
- Backlash, command latency, and mechanical response identification
- Marble/floor/wall friction identification
- End-to-end camera and estimator latency distribution
- Final-fit STL approval
- Safe hardware commissioning and held-out printed-maze evaluation

No blocked quantity may be silently promoted to `measured`. Its provisional
value must remain randomized or marked as an explicit design prior.
