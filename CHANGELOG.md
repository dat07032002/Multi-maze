# Change log

## Unreleased

- Added an explicitly selected `legacy-hardware` sysid profile so guarded passive
  and active measurements can use the working CyberRunner ROS message types and
  topics without replacing its camera, estimator, or Hiwonder driver.
- Added active-sysid runtime aborts for excessive estimated board angle and a
  stale estimator stream.
- Added a sanitized read-only audit of the live hardware and training systems,
  including machine-readable runtime and DreamerV3 snapshots.
- Documented the 240-to-180 action clamp, legacy-to-`tag_*` topic remapping,
  estimator provenance, missing image timestamp, stopped hardware run, and P0
  deployment gates.
- Added the passive `tag_sysid` recorder and offline analyzer.
- Added guarded home, axis/sign, static-sweep, and step-response protocols.
- Added hard bounds, publisher exclusivity, explicit arming, raw CSV output,
  home fallback, and protocol/safety/analysis tests.
- Imported the working TAG hardware stack through upstream commit `35b80ad`.
- Added a hardware-compatible DreamerV3 observation/action contract.
- Added one-policy multi-maze MuJoCo training with immutable 40/8/8 splits.
- Added route-conditioned validation on physical GPUs 3 and 4 while training uses GPU 2.
- Added detector-loss recovery, Hiwonder timing/safety behavior, and domain randomization.
- Added a single-source maze route/MJCF/preview/prototype-STL exporter.
- Confirmed that the `259 x 229 mm` printed footprint fits the removable board.
- Made maze hashes portable between Windows and Linux checkouts.
- Replaced duplicated legacy packages and tracked build products with the updated `tag_*` source tree.
- Removed Dreamer4, Dynamixel/Feetech, generic benchmark, and obsolete generated artifacts.

## v0.1.0 (2024-10-21)

Initial upstream CyberRunner release.
