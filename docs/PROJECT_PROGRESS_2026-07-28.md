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

## Nominal-first decision

The PLA adaptation sequence above is deferred. The current training decision
is to first establish full-route mastery without plant domain randomization.
`tag_sim_v2_nominal_fullstart` disables plant randomization and random starts,
loads only the preserved 13M agent weights, and begins at step zero with fresh
nominal replay. The failed PLA demonstration job is not a prerequisite.

The first nominal run is bounded at 500k steps with canonical validation at
250k and 500k. Domain randomization remains locked until a 192-episode
confirmation reaches at least 90% overall completion, 80% hard-maze completion,
95% mean maximum progress, at most 10% falls, and at least 75% completion in
every difficulty band. See `NOMINAL_FIRST_TRAINING.md`.

The active nominal pilot is:

```text
/home/tn22833/cyberrunner_logs/
nominal_fullstart_13m_500k_20260728_134149
```

It loaded the preserved 13M agent weights without the old step counter or
replay, confirmed all plant-randomization and random-start flags were disabled,
and started canonical-only validation monitoring at 250k and 500k. The
preserved `134018` attempt selected the vision-only Python environment and
failed before configuration or validation; it contains no training result.

## Nominal mastery achieved

The nominal pilot completed 500k steps but failed all five mastery criteria under
the 192-episode protocol: 79.17% completion, 16.15% falls, 86.64% mean maximum
route completion. Seven validation layouts failed every seed, capping completion
at 89.1% and making the gate unreachable by broad improvement.

Diagnosis found the policy driving bang-bang, mean absolute action 0.88 to 0.93
of full range with 64% to 74% of steps saturated, and every failure landing at a
route turn in its own 95th percentile or above while hole and wall clearance
there was normal. It also found that `clearance_cost` was computed, logged and
then discarded, so hazard avoidance had only the terminal fall penalty to learn
from.

Adding a dense hole-only margin penalty passed the gate: 90.10% completion, 6.25%
falls, 95.57% mean maximum route completion, 88.89% hard-maze completion, no band
below 88.89%. No validation layout fails all three seeds any more. Completion
passed by a single episode, so domain randomization stays locked pending a second
confirmation at different seeds.

See [NOMINAL_DIAGNOSIS_2026-07-28.md](NOMINAL_DIAGNOSIS_2026-07-28.md) and
[NOMINAL_AB_ARMS_2026-07-28.md](NOMINAL_AB_ARMS_2026-07-28.md).

## Second confirmation and DR-0.10

The next transition is implemented in
`scripts/confirm_nominal_then_start_dr010.sh`. It repeats the unchanged
192-episode mastery gate with base seed `20260729`, verifies the exact accepted
checkpoint hash, and keeps domain randomization locked on any failure. A pass
starts only a bounded 250k hole-aware run at fixed strength 0.10, followed by
three nominal and three DR-0.10 validation episodes per maze. No higher
randomization strength is authorized. See
[DR010_CONFIRMATION_2026-07-28.md](DR010_CONFIRMATION_2026-07-28.md).

The original result recorded checkpoint hash `448ae790...`, but the named
snapshot path was later overwritten by the final save with hash `db4c3968...`.
The original bytes were not found among preserved checkpoints. The guarded
workflow therefore requires the current final checkpoint to pass at both the
original and new confirmation seeds before DR-0.10 can unlock.

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
