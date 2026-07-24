# Cleanup audit

Cleanup was performed only after comparing the project with the updated working
TAG repository. No server checkpoint, replay chunk, metric file, or training log
was deleted.

## Removed from Git

- Tracked ROS/colcon products: `build/`, `install/`, and `log/`
- Local caches and historical runtime logs: `cache/` and `run_logs/`
- Duplicated pre-rename packages: `cyberrunner_camera`,
  `cyberrunner_state_estimation`, `cyberrunner_interfaces`,
  `cyberrunner_dynamixel`, and `cyberrunner_dreamer`
- Thomas/Dynamixel reference copies and `third_party/thomasbi1_cyberrunner`
- Dreamer4, Nicklas, replay-conversion, GPU 1, Feetech, and manual legacy-control scripts
- Downloaded `.deb` installers, temporary download file, recordings, and stale editor configuration
- Old custom-robot CAD/photos and obsolete MkDocs material
- Generic Dreamer benchmark score datasets and install helper scripts
- 34 regenerated simulator output artifacts
- 48 draft maze JSON files not referenced by the immutable 40/8/8 manifest

All of these are either regenerable, duplicated by the updated `tag_*` source,
unrelated to this Hiwonder/DreamerV3 project, or outside the approved dataset.

## Explicitly retained

- The complete 56-maze train/validation/test dataset and its hashes
- Multi-maze MuJoCo, route-planning, camera, actuator, reward, and validation code
- DreamerV3 simulator adapter, evaluation program, and server launchers
- Updated TAG camera, estimator, interface, Hiwonder, and hardware Gym packages
- Both preserved route pickle files
- Original custom-layout geometry under its updated TAG name
- Camera calibration and marker coordinates
- Versioned maze authoring template and prototype-STL exporter

Before deleting the old copies, both route files, calibration, and markers were
verified byte-identical to updated TAG. The renamed layout dictionaries were
also verified semantically identical.

## Recovery

The old repository state remains recoverable from Git history, including tag
`pre-organization-20260723`. Server training artifacts remain in their original
external directories documented in `TRAINING.md`.
