# Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md): simulation, policy, and physical TAG data flows
- [TRAINING.md](TRAINING.md): dataset, GPUs, validation schedule, server runs, and operations
- [V2_TRAINING.md](V2_TRAINING.md): adaptive 512/64/64 profile, demonstrations, and rollout gates
- [TAG_REFERENCE.md](TAG_REFERENCE.md): exactly what was imported from the updated working TAG repository
- [HARDWARE_RECORDING_2026-07-24.md](HARDWARE_RECORDING_2026-07-24.md): sanitized passive measurements and remaining calibration tests
- [HARDWARE_COMPATIBILITY_AUDIT_2026-07-24.md](HARDWARE_COMPATIBILITY_AUDIT_2026-07-24.md): read-only live hardware/training inventory, compatibility matrix, and deployment blockers
- [hardware_runtime_contract_2026-07-24.json](hardware_runtime_contract_2026-07-24.json): machine-readable camera, observation, action, Hiwonder, timing, and safety snapshot
- [training_snapshot_2026-07-24.json](training_snapshot_2026-07-24.json): machine-readable status of the stopped hardware-connected DreamerV3 run
- [SYSID_AXIS_2026-07-24.md](SYSID_AXIS_2026-07-24.md): accepted guarded +/-20 hardware axis/sign response and remaining identification work
- [sysid_axis_2026-07-24.json](sysid_axis_2026-07-24.json): machine-readable low-amplitude actuator response, timing, repeatability, and raw-file hashes
- [SYSID_STEP_2026-07-24.md](SYSID_STEP_2026-07-24.md): accepted +/-10 step-response results, nonlinear comparison, and rejected stick-slip event
- [sysid_step_2026-07-24.json](sysid_step_2026-07-24.json): machine-readable step magnitudes, timing, confidence, safety, and raw-file hashes
- [SYSID_SWEEP_2026-07-24.md](SYSID_SWEEP_2026-07-24.md): completed three-cycle +/-5/10/15 static sweep with calibrated home zero and hysteresis findings
- [sysid_sweep_2026-07-24.json](sysid_sweep_2026-07-24.json): machine-readable sweep protocol, response summary, safety result, and raw-file hashes
- [BALL_CAMERA_TESTS_2026-07-24.md](BALL_CAMERA_TESTS_2026-07-24.md): angle-independent camera, stationary-ball, occlusion, motion-tracking, and hole-loss measurements
- [ball_camera_tests_2026-07-24.json](ball_camera_tests_2026-07-24.json): machine-readable aggregate results and modeling limitations
- [CLEANUP_AUDIT.md](CLEANUP_AUDIT.md): what was removed, what was retained, and why
- [HANDOFF.md](HANDOFF.md): clone and continue from another desktop

Detailed simulator documentation remains next to the implementation:

- [`cyberrunner_mujoco/HARDWARE_CONTRACT.md`](../cyberrunner_mujoco/HARDWARE_CONTRACT.md)
- [`cyberrunner_mujoco/MODEL.md`](../cyberrunner_mujoco/MODEL.md)
- [`cyberrunner_mujoco/IMPLEMENTATION_STATUS.md`](../cyberrunner_mujoco/IMPLEMENTATION_STATUS.md)
- [`cyberrunner_mujoco/README.md`](../cyberrunner_mujoco/README.md)
