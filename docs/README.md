# Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md): simulation, policy, and physical TAG data flows
- [IMU orientation](../tag_state_estimation/IMU_ORIENTATION.md): BNO086 serial protocol, fusion modes, and hardware validation
- [HARDWARE_HANDOFF_2026-07-26.md](HARDWARE_HANDOFF_2026-07-26.md): consolidated completed work, remaining sysid plan, Ubuntu setup, and agent prompt
- [TRAINING.md](TRAINING.md): dataset, GPUs, validation schedule, server runs, and operations
- [V2_TRAINING.md](V2_TRAINING.md): adaptive 512/64/64 profile, demonstrations, and rollout gates
- [TAG_REFERENCE.md](TAG_REFERENCE.md): exactly what was imported from the updated working TAG repository
- [HARDWARE_RECORDING_2026-07-24.md](HARDWARE_RECORDING_2026-07-24.md): sanitized passive measurements and remaining calibration tests
- [HARDWARE_COMPATIBILITY_AUDIT_2026-07-24.md](HARDWARE_COMPATIBILITY_AUDIT_2026-07-24.md): read-only live hardware/training inventory, compatibility matrix, and deployment blockers
- [hardware_runtime_contract_2026-07-24.json](hardware_runtime_contract_2026-07-24.json): machine-readable camera, observation, action, Hiwonder, timing, and safety snapshot
- [LOCAL_CLEANUP_CANDIDATES_2026-07-24.md](LOCAL_CLEANUP_CANDIDATES_2026-07-24.md): completed local cache and recording cleanup record
- [`tag_state_estimation/AI_MARBLE_DETECTOR.md`](../tag_state_estimation/AI_MARBLE_DETECTOR.md): learned detector modes, diagnostics, limitations, and safe validation
- [training_snapshot_2026-07-24.json](training_snapshot_2026-07-24.json): machine-readable status of the stopped hardware-connected DreamerV3 run
- [SYSID_AXIS_2026-07-24.md](SYSID_AXIS_2026-07-24.md): accepted guarded +/-20 hardware axis/sign response and remaining identification work
- [SYSID_AXIS2_2026-07-27.md](SYSID_AXIS2_2026-07-27.md): guarded axis-2 gradual sweep, hardware compatibility findings, and limitations
- [SYSID_ACTUATOR_2026-07-27.md](SYSID_ACTUATOR_2026-07-27.md): initial source-timestamped command-26.67 actuator fit, later superseded by the command-80 fit
- [SYSID_ACTUATOR_STEP80_2026-07-27.md](SYSID_ACTUATOR_STEP80_2026-07-27.md): accepted direction-dependent command-80 actuator map and timing now used by the simulator
- [sysid_actuator_2026-07-27.json](sysid_actuator_2026-07-27.json): machine-readable initial actuator fit and raw-file hashes
- [sysid_actuator_step40_2026-07-27.json](sysid_actuator_step40_2026-07-27.json): machine-readable intermediate command-40 response
- [sysid_actuator_step80_2026-07-27.json](sysid_actuator_step80_2026-07-27.json): machine-readable accepted command-80 actuator fit and raw-file hashes
- [REAL_TRAJECTORY_RETRAINING.md](REAL_TRAJECTORY_RETRAINING.md): passive real-data recording, dynamics fitting, and quality-gated simulator refinement
- [VISION_RELIABILITY_PLAN_2026-07-27.md](VISION_RELIABILITY_PLAN_2026-07-27.md): evidence, model/data plan, and camera-only acceptance gates for robust marble tracking
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

- [`tag_mujoco/HARDWARE_CONTRACT.md`](../tag_mujoco/HARDWARE_CONTRACT.md)
- [`tag_mujoco/MODEL.md`](../tag_mujoco/MODEL.md)
- [`tag_mujoco/IMPLEMENTATION_STATUS.md`](../tag_mujoco/IMPLEMENTATION_STATUS.md)
- [`tag_mujoco/README.md`](../tag_mujoco/README.md)
