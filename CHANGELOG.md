# Change log

## Unreleased

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
