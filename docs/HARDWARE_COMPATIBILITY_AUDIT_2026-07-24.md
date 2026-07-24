# Hardware and training compatibility audit — 2026-07-24

This is a read-only snapshot of the physical CyberRunner computer, its active
software, the hardware-connected DreamerV3 run, and this repository. It exists
to answer one practical question: **can a policy trained from this repository be
deployed to the current camera and Hiwonder controller without silently changing
its observation or action contract?**

No motors were commanded, ROS nodes were restarted, files were deleted, or
training processes were changed during this audit. Hostnames, usernames, device
serial numbers, and network endpoints are intentionally omitted.

## Decision

The organized `tag_*` stack is structurally compatible with the physical stack,
but it is **not yet safe to call it deployment-equivalent**. Before another
hardware training or policy test, resolve the four P0 items below:

1. Make one launch file the authoritative source of topic names and executable
   paths. The live system uses legacy `cyberrunner_*` names, while this repository
   defaults to `tag_*` names.
2. Remove the action-scale mismatch. The environment can request `240`, but the
   live TCP bridge clips each axis to `180` before the Hiwonder node sees it.
3. Launch the estimator from this repository (or record an immutable hash of the
   external workspace). The estimator observed during the audit came from a
   second ROS workspace and later was no longer running.
4. Repair ROS graph inspection before commissioning. The ROS 2 CLI daemon entered
   an `rclpy.ok()` fault state, preventing a final parameter dump. Do this only in
   a maintenance window; it was deliberately not restarted during this audit.

## What is useful from the working hardware project

### Physical I/O and actuator behavior

- Controller: Hiwonder USB controller, servo IDs 1 and 2.
- Source defaults: home `500, 500`; bounds `100..900`; scale `1.5` per axis.
- Command handling: 30 Hz loop, maximum change 20 servo units per tick, one-unit
  deadband, and a one-second command timeout that returns to home.
- Reset behavior: pre-home `700, 700` for 60 ms, wait 0.5 s, then move to home in
  600 ms.
- A 70 C temperature limit exists in source, but the default temperature serial
  port is empty. Treat temperature protection as **unverified**, not active,
  until telemetry is observed.

These values should seed simulation/domain-randomization ranges. They are not a
replacement for the guarded static-sweep and step-response tests in `tag_sysid`.

### Camera contract

- See3CAM_24CUG on a stable Linux `by-id` path.
- Capture request: MJPG, 1280 x 720 at 60 FPS, one-frame capture buffer.
- Published image: resize to 640 x 360, then add 20 black pixels above and below;
  final observation source is 640 x 400 BGR8.
- Manual controls in the active source: white-balance auto off, temperature 5477,
  manual exposure 8 ms, saturation 40, gamma 193, contrast 30, brightness -6,
  and power-line compensation off.
- The passive ten-minute recording measured 43.55 camera messages/s. Requested
  60 FPS is therefore not the effective hardware observation rate.

The Dreamer environment receives a 64 x 64 grayscale crop derived by the state
estimator. Simulation should randomize exposure, contrast, blur, crop offset,
occlusion, and frame timing around this real pipeline—not render an idealized
camera at a fixed 60 Hz.

### State and observation contract

- State vector is `[alpha, beta, x, y]`.
- Published angle mapping is `alpha = -angles[1]`, `beta = angles[0]`.
- State normalization divides angles by 10 degrees and maps position from the
  lower-left of the 0.259 x 0.229 m playable area.
- Image observation is 64 x 64 x 1, `uint8`.
- Goal observation contains five relative route points (10 values).
- Detector loss is declared after six consecutive misses. The environment has a
  0.35 s ball-loss grace period and a 1.5 s occlusion grace period.
- The estimator accepts a wider window (`x` half-limit 0.14 m, `y` half-limit
  0.13 m) than the nominal board bounds. Preserve or deliberately replace this
  behavior; do not let it change accidentally.
- The subimage message was observed without a timestamp in the previous passive
  recording. End-to-end image latency cannot be measured reliably until it is
  stamped at acquisition and propagated.

### Maze and calibration assets

- The fixed playable dimensions are 259 x 229 mm.
- The working route file is byte-identical to the organized copy.
- Calibration and marker CSV contents match; byte hashes differ because newline
  normalization differs between operating systems.
- The layout geometry matches. Only generator/header naming differs.

This lets us preserve the real coordinate system, route convention, and camera
calibration while replacing only the removable 3D-printed maze.

## Active runtime observed

| Component | Audit observation | Consequence |
|---|---|---|
| Hiwonder compatibility node | Running from the existing working checkout | Do not delete or overwrite that dirty checkout |
| TCP bridge | Running locally and forwarding to the training host | It was the sole command publisher observed |
| Camera publisher | Running from the working checkout | Camera defaults above are relevant to deployment |
| Estimator | Initially running from a second ROS workspace; absent in the final process snapshot | Deployment provenance and current observation availability must be checked |
| Command topic | Legacy `/cyberrunner_dynamixel/cmd` | Organized `/tag_hiwonder/cmd` will not connect without remapping/configuration |
| State topic | Legacy `/cyberrunner_state_estimation/estimate` | Organized `/tag_state_estimation/estimate` will not connect without remapping/configuration |

The working checkout is heavily modified and contains untracked detector and
recording work. It is evidence, not a cleanup target. The clean clone of this
repository on the hardware computer was left untouched.

## Hardware recording evidence

The existing 600-second passive recording remains the most trustworthy dynamic
snapshot:

- camera: 26,129 messages, 43.55 Hz;
- primary state: 35,611 messages, 59.36 Hz;
- commands: 6,152; active median rate 28.22 Hz;
- longest command silence: 98.964 s;
- 28 official episodes, 6,116 steps, zero successes;
- command saturation: axis 1 62.94%, axis 2 62.48%, either axis 85.47%.

High saturation may partly reflect an early policy, so it is not accepted as a
servo limitation. It does prove that the 240-to-180 clipping materially changes
many requested actions. Passive plant fits had low R-squared values and are not
accepted for simulator identification.

## Training snapshot

At 2026-07-24 14:15 server-local time, the hardware-connected `newmap` log had:

- current checkpoint size approximately 1.016 GB;
- 810 metric records and 809 score records;
- latest recorded step 213,180;
- latest episode length 494, score 0.308, duration 17.42 s;
- success rate 0 over the last 20, 50, and 100 episodes;
- reported environment/training throughput 11.53 FPS in the latest record;
- a full replay buffer of 1,000,000 entries.

No process for this `newmap` run was found at audit time. An unrelated DreamerV3
simulation job was running elsewhere on the shared server and must not be counted
as continuation of this run.

The current `newmap/config.yaml` says `train_ratio: 256`, batch 16 x length 64,
one GPU, RSSM deter 2048 with 32 stochastic variables and 32 classes, actor/critic
width 768, environment length 3000, and no exploration behavior. This config was
modified after the passive hardware recording, whose context reported ratio 128.
Therefore the config is a later run snapshot; do not retroactively attribute it
to the recorded session.

## Compatibility matrix

| Contract | Working hardware | Organized repository | Status |
|---|---|---|---|
| Board dimensions | 0.259 x 0.229 m | 0.259 x 0.229 m | Match |
| Route file | Working custom route | Same byte hash | Match |
| Calibration/markers | Working files | Same content | Match |
| Camera geometry | 640 x 400 source to 64 x 64 crop | Preserved implementation | Match, timing still needs modeling |
| Observation keys | image, states, goal | Preserved | Match |
| Action shape | 2 continuous axes | Preserved | Match |
| Environment command scale | 240 per axis | Preserved | Match internally |
| Bridge clamp | 180 per axis | Preserved | Mismatch with environment intent |
| Hiwonder control behavior | home/rate/step/deadband/timeout above | Same logic after namespace changes | Match by source review; hardware test pending |
| ROS names | `cyberrunner_*` | `tag_*` | Requires one explicit remap/configuration |
| Active estimator provenance | External ROS workspace | Repository source tree | Not deployment-equivalent yet |
| Temperature telemetry | Port unset by default | Guard exists | Unverified |
| Image timestamp | Missing on subimage | Not yet a measured end-to-end clock | Must fix for latency sysid |

## Required next actions

### P0 — before hardware training or policy evaluation

1. Add a single hardware launch/config profile that sets all legacy-versus-`tag`
   topic mappings, executable paths, camera device, and controller IDs.
2. Choose one action limit (`180` or `240`) and use it consistently in the
   environment, TCP protocol, safety layer, logs, and simulator.
3. Stamp the camera-derived observation at acquisition and log command-send,
   controller-write, image-acquisition, estimator-publish, and TCP-return times.
4. Use publisher-exclusivity checks before arming; the TCP bridge was already the
   active command publisher during this audit.
5. Free disk space on the hardware computer through a separately approved cleanup
   audit. Its root filesystem was 99% used with only about 1.4 GB free.

### P1 — guarded system identification

Run the existing `tag_sysid` procedures in this order after stopping training and
obtaining an exclusive maintenance window:

1. home verification and axis/sign test;
2. low-amplitude static sweep to identify servo command to board angle, center,
   gain, asymmetry, and backlash;
3. safe step responses for delay, rise time, rate limit, and settling;
4. passive ball roll-down trials for rolling resistance and board-axis coupling;
5. repeated camera/estimator timing trials, including occlusion and recovery.

Only then update MuJoCo parameter distributions. Keep raw trials and acceptance
reports; do not tune from one convenient run.

### P2 — training validation

Resume or replace the stopped hardware run only after P0. Validation should be
policy-frozen and deterministic, use held-out mazes and fixed seeds, record
completion/fall/time plus saturation and ball-loss rates, and save a GIF/video for
each validation checkpoint. A high training score alone is not proof of maze
completion.

## Machine-readable companions

- `hardware_runtime_contract_2026-07-24.json`
- `training_snapshot_2026-07-24.json`

The JSON files contain no credentials or network endpoints and can be consumed by
future deployment/preflight tooling.
