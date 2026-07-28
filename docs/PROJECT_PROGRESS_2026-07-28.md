# Multi-maze project progress through 2026-07-28

## Current state

The project trains one DreamerV3 policy to solve procedurally generated
tilting-board mazes from the deployed camera/state/goal observation contract.
Training uses 512 immutable layouts, validation uses 64 disjoint layouts, and
the 64-layout test split remains untouched for one final report.

The best preserved pre-PLA checkpoint is:

```text
/home/tn22833/cyberrunner_logs/
multimaze_v2_stagedrand_13m_gpu2_20260727_235843/checkpoint.ckpt
```

Its evaluation under the previous dynamics distribution was:

| Protocol | Completion | Falls | Mean maximum route completion |
| --- | ---: | ---: | ---: |
| Canonical, 64 episodes | 59.38% | 32.81% | 75.70% |
| Corrected robust, 192 episodes | 29.17% | 38.02% | not used as a training target |

The robust protocol now uses full-route starts and randomizes only the plant.
Older robust results that used random mid-route starts are not comparable.

## Training improvements completed

- Replaced the legacy 40/8/8 experiment with deterministic 512/64/64
  train/validation/test splits.
- Added outcome-based prioritized level replay while retaining uniform and
  staleness coverage.
- Added reverse start-state and success-gated plant-randomization curricula.
- Added full-route continuation profiles to address weak starts.
- Added privileged-planner demonstrations without privileged fields in saved
  policy replay.
- Added eight process-parallel environments and guarded GPU launchers.
- Corrected robust evaluation, added canonical/robust checkpoint monitoring,
  and made final checkpoint collection stable.
- Added a staged-randomization continuation, which produced the current 13M
  checkpoint.

## Hardware and simulator work completed

- Preserved the deployed image, state, goal and action contract.
- Modeled calibrated camera remapping, observation delay, position/angle noise,
  brightness, contrast, blur, crop shift, pixel noise, frame dropout and
  dropout bursts.
- Added observation prediction/hysteresis for short detector losses and
  bounded loss handling for longer occlusions.
- Incorporated the measured direction-dependent actuator response, cross-axis
  coupling, approximately 33 ms pure delay, approximately 86 ms response time
  constant, and conservative stiction/backlash priors.
- Added quality-gated trajectory fitting for rolling resistance, velocity
  damping and wall restitution.
- Corrected MuJoCo contact semantics by using six-dimensional contacts and
  length-valued rolling/torsional friction.

Camera exposure jitter, motion-dependent blur, reflections, spatial lighting,
physical occlusion geometry and detector false positives are still model gaps.
The present simulator approximates some consequences of these effects but does
not render a photorealistic physical camera.

## Untreated FDM PLA assumptions

No suitable contact system-identification run exists yet for the printed maze.
The active simulator therefore records broad engineering priors in
`tag_mujoco/assumed_dynamics.json`:

| Parameter | Nominal | Training range |
| --- | ---: | ---: |
| Floor sliding friction | 0.38 | 0.15-0.70 |
| Wall sliding friction | 0.40 | 0.15-0.75 |
| Ball sliding friction | 0.25 | 0.10-0.60 |
| Rolling resistance coefficient | 0.004 | 0.0005-0.030 |
| Linear velocity damping | 0.22 1/s | 0.00-0.80 1/s |
| Wall restitution | 0.35 | 0.05-0.70 |

These are distributions, not measurements. Directional top-skin friction,
local seams/rough patches, and drift from dust, wear and polishing remain
explicit gaps. Tests on the actual printed part must replace the assumptions.

## PLA adaptation workflow implemented

The adaptation path deliberately loads only the 13M agent weights. It does not
load the old step counter or replay buffer. The new run starts at step zero with
fresh PLA demonstrations and replay.

The `tag_sim_v2_pla_adaptation` profile uses full starts and increases
randomization strength through 0.25, 0.50, 0.75 and 1.00 as recent success
permits. `tag_sim_v2_pla_scratch` provides a matched scratch control.

The guarded sequence is:

1. Evaluate the frozen 13M checkpoint on all 64 validation mazes under nominal
   PLA dynamics and three randomized PLA episodes per maze.
2. Generate 128 full-start and 64 random-start successful PLA demonstrations.
3. Run a 500k agent-only adaptation with validation at 250k and 500k.
4. Continue only when `tag_mujoco/pla_training_gate.py` passes:
   robust completion improves by at least five percentage points or robust
   falls decrease by five points; canonical completion loses no more than
   three points; and hard-maze maximum progress loses no more than five points.
5. Run a matched 500k-1M scratch control before choosing the adaptation method.
6. Fit the actual printed surface and perform another bounded adaptation.

The baseline and demonstration phases started on 2026-07-28:

```text
PLA baseline:
/home/tn22833/cyberrunner_logs/pla_baseline_13m_20260728_100913

PLA demonstrations:
/home/tn22833/cyberrunner_logs/pla_expert_demos_20260728_100921
```

The 500k pilot is intentionally not launched until both phases finish
successfully. `scripts/continue_pla_pilot_after_prereqs.sh` enforces that
ordering, launches the bounded pilot and its 250k/500k validation, writes the
continuation-gate result, and never starts a longer continuation.

## Verification

The complete local and staged-server suites pass:

```text
53 unit tests passed
verify_system_model.py: all_passed=true
```

Server-side pre-change backups are retained under:

```text
/home/tn22833/TAG_vision_20260727/backups/pla_priors_pre_20260728
/home/tn22833/TAG_vision_20260727/backups/pla_workflow_pre_20260728
```
