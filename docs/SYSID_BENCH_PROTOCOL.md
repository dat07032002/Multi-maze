# System identification bench protocol

Field document for the hardware session. Blocks run in order; each yields a
usable result alone, so stopping early still produces something.

Simulator predictions below come from `tag_mujoco/actuator_authority.py`
(`python -m tag_mujoco.actuator_authority`). They are **predictions of the
current model, not measurements** — the point of the session is to check them.

## Why this session exists

`board_rad_per_command_*` sets every dynamic limit in the simulator: achievable
acceleration, minimum turn radius, stopping distance, and therefore which routes
are trackable at all. It is a local slope fitted near |command|=80 from
camera-derived board angles, applied at the policy limit of command 180. The
source campaign's own "Remaining uncertainty" section
(`SYSID_ACTUATOR_STEP80_2026-07-27.md`) says it "identifies local response
through command 80, not saturation at the policy limit."

Separately, every ball-dynamics parameter in `tag_mujoco/assumed_dynamics.json`
carries `"status": "assumed"`. Those have never been measured at all.

## Safety: the interlocks read the instrument under test

`tag_sysid/tag_sysid/active.py:169-227` enforces `max_board_angle_deg` and
`max_angle_excursion_deg` against `message.alpha` / `message.beta` — the camera
estimate. **If the camera under-reads tilt, every guard is loose by the same
factor.**

That the command-80 campaign never tripped its 4 degree guard is therefore not
evidence the board stayed under 4 degrees. Guard and measurement share an
instrument and cannot cross-validate each other.

Consequences:

- Block A must complete before any command exceeds 80, which is the highest
  previously-tested value.
- `tag_sysid/tag_sysid/protocols.py:8` sets `HARD_COMMAND_LIMIT = 120.0`.
  Reaching the policy's 180 requires editing that constant — a reviewed change,
  not a bench decision.
- `marble.py:211` sets `max_board_angle_deg = 15.0`. This is a safety threshold,
  **not** a measured mechanical range. It has been mistaken for one.
- Marble out for Blocks A, B and D. It adds failure modes and contributes
  nothing to an actuator measurement.

## Kit

- Steel rule or calipers (primary angle reference)
- Shims of known thickness spanning ~5–45 mm, measured with calipers
- Digital angle gauge (optional; speeds up Block B)
- 12 mm steel marble and the actual printed maze insert (Block C only)
- ESP32 + BNO086 and its USB cable

## Instruments

**Primary: edge lift.** Vertical rise of the board edge relative to the fixed
base frame — not the table, since a crooked rig makes the table a false datum.
`angle = atan(lift / span)`, span 259 mm across (alpha) and 229 mm deep (beta).

Right as primary because it touches nothing under suspicion: no camera, no
estimator, no IMU, no code.

| Angle | Lift @259 mm | Lift @229 mm |
| ---: | ---: | ---: |
| 0.5 deg | 2.3 mm | 2.0 mm |
| 1.0 deg | 4.5 mm | 4.0 mm |
| 2.0 deg | 9.0 mm | 8.0 mm |
| 5.0 deg | 22.7 mm | 20.0 mm |
| 10.0 deg | 45.7 mm | 40.4 mm |

1 mm of lift = 0.221 deg at the 259 mm span.

Shim heights, 259 mm span: 5 mm = 1.11 deg, 10 mm = 2.21 deg, 20 mm = 4.42 deg,
45 mm = 9.86 deg.

**Reference: BNO086.** The only instrument that logs synchronized with commands,
so it carries Blocks B and D. Validate against edge lift in Block A first.

## IMU bring-up

Find the device:

```bash
ls -l /dev/serial/by-id/
```

Confirm camera-only still works, as a regression check:

```bash
ros2 launch tag_camera camera_estimation_gpu.launch.py orientation_mode:=camera
```

Then bring up the IMU. **Use `orientation_mode:=imu`, not `fused`.**

```bash
ros2 launch tag_camera camera_estimation_gpu.launch.py \
  orientation_mode:=imu \
  start_imu_serial:=true \
  imu_port:=/dev/serial/by-id/YOUR_ESP32_DEVICE
```

`fused` mode "slowly corrects [the alignment] toward valid camera poses"
(`IMU_ORIENTATION.md`). That is correct for deployment and wrong here: it would
pull the independent reference toward the very bias being measured. Fusion is a
decision to make *after* this session, not during it.

Keep the board still during startup until alignment is established. Monitor:

```bash
ros2 topic hz /tag_imu/data
ros2 topic echo /tag_state_estimation/orientation_source
ros2 topic echo /tag_state_estimation/imu_age_sec
ros2 topic echo /tag_state_estimation/orientation_disagreement_deg
```

`orientation_disagreement_deg` publishes the camera-versus-IMU difference
directly, which is most of Block A's deliverable without post-processing.

**Prerequisite:** the default assumes BNO086 axes are parallel to board axes. If
the mount rotates the sensor, set `imu_mount_roll_deg` / `imu_mount_pitch_deg` /
`imu_mount_yaw_deg` and verify by moving one physical board axis at a time. An
unverified extrinsic makes the IMU as untrustworthy as the camera.

## Block A — Instrument calibration (no servo motion)

Shim the board to known angles and record all instruments together. Shims give
known *inputs* rather than trusted outputs, which makes this a calibration
rather than a comparison.

Sample the low end densely: that is where the disputed measurements live and
where planar PnP is worst conditioned.

| Shim (mm) | True angle | Measured lift | Angle gauge | IMU alpha/beta | Camera alpha/beta | disagreement_deg |
| ---: | ---: | --- | --- | --- | --- | --- |
| 0 | 0.00 deg | | | | | |
| 5 | 1.11 deg | | | | | |
| 10 | 2.21 deg | | | | | |
| 15 | 3.32 deg | | | | | |
| 20 | 4.42 deg | | | | | |
| 30 | 6.61 deg | | | | | |
| 45 | 9.86 deg | | | | | |

Repeat for the second axis.

**Deliverables.** The camera error curve — a required input to the observation
model regardless of anything else — and a validated IMU.

**Gate.** If the camera tracks the reference within a few percent, it is
exonerated and the remaining question is purely the extrapolation. If not,
recalibrate the interlock thresholds into true degrees before Block B.

## Block B — Actuator

One motor at a time; `protocols.py:154` rejects any phase driving both axes.
Approach every command from the same direction.

Predicted values are the **shipped calibration's** output. It reproduces the
2026-07-27 measurements at command 80 exactly, including the zero rows at motor-1
negative and motor-2 positive command 40 — the directional ambiguity that
campaign recorded.

| Motor | Cmd | Action | Pred alpha | Pred beta | Pred lift A | Pred lift B | Meas lift A | Meas lift B | IMU | Camera |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- |
| 1 | 40 | -0.167 | 0.182 | -0.356 | 0.82 | -1.42 | | | | |
| 1 | 80 | -0.333 | 0.364 | -0.711 | 1.65 | -2.84 | | | | |
| 1 | 120 | -0.500 | 0.547 | -1.067 | 2.47 | -4.26 | | | | |
| 1 | 180 | -0.750 | 0.820 | -1.600 | 3.71 | -6.40 | | | | |
| 1 | -40 | 0.167 | 0.000 | 0.000 | 0.00 | 0.00 | | | | |
| 1 | -80 | 0.333 | 0.274 | 0.271 | 1.24 | 1.08 | | | | |
| 1 | -120 | 0.500 | 0.410 | 0.406 | 1.86 | 1.62 | | | | |
| 1 | -180 | 0.750 | 0.616 | 0.609 | 2.78 | 2.44 | | | | |
| 2 | 40 | -0.167 | 0.000 | 0.000 | 0.00 | 0.00 | | | | |
| 2 | 80 | -0.333 | -0.437 | -0.208 | -1.98 | -0.83 | | | | |
| 2 | 120 | -0.500 | -0.656 | -0.312 | -2.96 | -1.25 | | | | |
| 2 | 180 | -0.750 | -0.983 | -0.468 | -4.45 | -1.87 | | | | |
| 2 | -40 | 0.167 | 0.209 | 0.156 | 0.94 | 0.62 | | | | |
| 2 | -80 | 0.333 | 0.418 | 0.313 | 1.89 | 1.25 | | | | |
| 2 | -120 | 0.500 | 0.627 | 0.469 | 2.83 | 1.87 | | | | |
| 2 | -180 | 0.750 | 0.940 | 0.703 | 4.25 | 2.81 | | | | |

**The headline criterion.** The largest lift the shipped model predicts anywhere
at command 180 is **6.4 mm**. If the board lifts substantially more than that,
the calibration is wrong and everything trained against it is mis-calibrated.
This is visible with a rule; it does not need careful measurement.

Order of work:

1. **Command 80 first** — the documented safe point, now with trusted
   instruments beside it. Confirms the shipped numbers or measures their
   correction factor against the same protocol that produced them.
2. **100 and 120** — the purpose is *linearity*, which the local-slope method
   assumed and never tested. Curvature by 120 invalidates extrapolation to 180
   whatever the slope, and settles the question on its own.
3. **150 and 180** — only with linear response and comfortable true-degree
   margin, and only after raising `HARD_COMMAND_LIMIT` deliberately. If margin
   is thin, stop at 120 and fit a saturating model. A fitted curve through 120
   beats an unsafe reading at 180.
4. **Backlash** — sweep up then back down through zero, record loop width.
   `stiction_command_positive/negative` are described in config as conservative
   priors, and the campaign found command 40 directionally ambiguous.
5. **Two-axis simultaneous** — never measured, because the protocol forbids it,
   while the policy drives both axes on every step. One two-axis hold at command
   80 tests whether the off-diagonal terms are right. The simulator predicts a
   strongly anisotropic envelope: at saturation the four sign combinations give
   between 0.14 and 2.07 degrees, and the `(-180, +180)` corner is nearly dead.
   That asymmetry should be visible as very different edge lifts per corner.

## Block C — Ball dynamics

Marble in, real printed insert. Every parameter here is currently assumed.

**Two separate recordings, not one.** Verified against the fitter with synthetic
trajectories (`tag_mujoco/tests/test_sysid_recording_contract.py`):

| Recording | Result |
| --- | --- |
| Clean free roll, no wall contact | r2 = 1.000, damping and rolling resistance recovered exactly |
| Same roll with wall bounces | r2 = -0.020, damping recovered as 0.00 against a true 0.6 |

`local_kinematics` fits a centred quadratic over a 0.18 s window; a bounce
inside that window is a velocity discontinuity it cannot represent and enters
the regression as a large false acceleration. So:

- **Free-roll recording** — level the board against the edge-lift reference,
  launch by hand, let it roll without touching a wall. This is
  actuator-independent, so it is valid even if Block B goes badly.
- **Impact recording** — deliberate wall contact, for restitution only. Also
  actuator-independent.
- **Tilted roll** — only if Block B produced a trusted angle. This separates
  sliding friction from rolling resistance, and is exactly what a bad actuator
  calibration would silently corrupt.

**Session length.** The gate wants 200 moving samples (roughly 5+ seconds of
continuous clean rolling at 45 Hz) and 5 impacts. A 2 second recording still
produces plausible-looking numbers — damping 0.63 against a true 0.6 — while
failing the gate. Only `quality_gate` distinguishes them, so read it before
quoting anything.

**`source_time_ns` must be consistently populated.** The recorder writes it
empty when the estimator supplies no source stamp, and the fitter silently falls
back to `ros_time_ns`. Consistent absence is harmless (r2 = 1.000). *Mixed*
availability collapses the fit to r2 = 0.015, because the two clocks differ by
`source_age_ns` and every velocity is a numerical derivative of that axis. Check
the column before trusting a session.

Record print parameters with the data as `REAL_TRAJECTORY_RETRAINING.md`
requires — layer height, top-skin pattern, wall count, infill, PLA formulation,
post-processing — plus print orientation relative to the board axes, since
directional friction from extrusion lines is a documented model gap.

## Block D — Timing decomposition

The existing t90 near 202 ms is lumped: driver tick, slew limit, linkage, camera
exposure and transport, estimator, and ROS delivery, all in one number.

The IMU makes it separable for the first time, because it observes board motion
without the camera pipeline. Step the command and log IMU and camera together:

- IMU response alone = the actuator path.
- Offset between IMU and camera response = the camera-path latency.

This matters because `CameraConfig.observation_delay_steps` (1) and
`response_time_constant_seconds` (0.001 s) are both inferences from the lumped
figure. Neither has been measured directly.

Simulator predictions for reference: step from home to saturation reaches 90% in
0.431 s; a full reversal takes 0.855 s (alpha) and 0.788 s (beta). The binding
constraint is `max_step_per_tick`, 20 servo units per 30 Hz tick across a
540-unit reversal — not servo dynamics.

## After the session

- Preserve the `"status"` convention: mark each parameter `measured` or
  `assumed`, per parameter. `assumed_dynamics.json` never overstated its
  confidence; the replacement must not either.
- Refit through the tools: `fit_actuator_response.py` for timing,
  `fit_dynamics.py` then `apply_dynamics_fit.py` for dynamics.
  `system_config.py:174-178` forbids hand-editing the actuator map.
- Write `docs/SYSID_<block>_<date>.md` plus JSON with raw-file hashes.
- Amend `SYSID_ACTUATOR_STEP80_2026-07-27.md` to point forward, and
  `NOMINAL_AB_ARMS_2026-07-28.md:225` if its feasibility rejection no longer
  holds.
- Decide the instrument policy the results support: which source is
  authoritative for calibration, which for runtime observation, and whether
  `fused` mode should be enabled. That decision follows the measurements.
