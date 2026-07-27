# Adaptive multi-maze v2 training

V2 is a fresh, checkpoint-breaking training profile. It keeps the deployed
`tag_hardware_policy_v1` observation/action contract but does not reuse the v1
checkpoint or replay.

## What changes

- deterministic 512/64/64 train/validation/test split;
- four safe grid densities, four loop rates, varied hole counts, and four
  opposite-corner route directions;
- outcome-based prioritized level replay with uniform and staleness mixtures;
- reverse start-state curriculum while retaining 20% full-start episodes;
- success-gated actuator, physics, and camera randomization;
- optional privileged-controller demonstrations saved with policy fields only;
- eight process-parallel simulator environments; and
- fall penalty 10 instead of 5.

## Implemented artifacts

The v2 implementation was completed and verified locally on 2026-07-23:

- `tag_mujoco/maze_splits_v2.json` defines 512 training, 64 validation,
  and 64 test layouts;
- `tag_mujoco/generated_mazes_v2/` contains all 640 immutable JSON
  layouts with unique content hashes;
- `tag_mujoco/expert_controller.py` implements the privileged route
  controller and demonstration exporter;
- `dreamerv3/dreamerv3/configs.yaml` contains the `tag_sim_v2` profile;
- Dreamer replay can preload complete `.npz` demonstration episodes without
  joining streams across episode boundaries;
- `scripts/run_tag_sim_v2_gpu2.sh` launches fresh approval-gated v2 jobs on
  physical GPU 2; and
- the validation monitor accepts the v2 manifest and evaluates canonical and
  robust held-out rollouts on physical GPUs 3 and 4.

The generated dataset spans four grid shapes, four loop rates, varied hole
counts, and four opposite-corner route directions. All 640 continuous routes
passed the swept-ball clearance check, the split hashes are disjoint, and the
minimum observed route clearance exceeded the required 1.5 mm margin.

The local regression suite passed all 36 tests. The staged server checkout
passed its 34 available tests, Dreamer configuration merging, shell syntax
checks, and the full v2 readiness audit.

## Demonstration dataset

The bootstrap set used for server runs contains 160 successful episodes:

| Group | Successful episodes |
| --- | ---: |
| Near-goal randomized starts | 128 |
| Full starts | 32 |
| Total | 160 |

Together they contain 26,572 transitions and produce 17,002 valid length-64
Dreamer replay sequences. The saved arrays contain only deployed policy fields:
image, state, route goal, action, reward, and episode-boundary flags. The
demonstrations are intentionally ignored by Git because they are generated run
artifacts.

## Server experiment record

### V2 smoke test

The approval-gated smoke run completed successfully in:

```text
/home/tn22833/cyberrunner_logs/
multimaze_v2_smoke10k_gpu2_20260723_220438
```

The 10,000-step request ended at counter 24,008 because eight parallel
environments finish their active episode batch before the stop condition is
applied. The run loaded all demonstrations, wrote a 492 MB checkpoint, reached
a median 202.1 FPS and peak 232.9 FPS, and exited with status 0. Four of the 14
logged episode summaries were successes and eight were falls. No persistent
non-finite model state was observed.

For comparison, the previous single-environment runs had median throughput of
102.7 to 107.3 FPS with the same train ratio and batch shape. V2 therefore
measured about 1.9 to 2.0 times higher environment throughput. This is a speed
measurement, not yet proof of faster convergence.

### First 10M production attempt

The production run resumed the smoke checkpoint and targeted 10,000,000 steps:

```text
/home/tn22833/cyberrunner_logs/
multimaze_v2_production_10m_gpu2_20260723_221436
```

It reached step 510,432 at 216.9 FPS before the server rebooted at
2026-07-23 23:02:22 CDT. Training output stopped around 23:00 with no traceback,
CUDA error, or wrapper exit status, which is consistent with an external reboot
rather than an application failure. The final aggregate model and reward losses
were finite. Two earlier mixed-precision gradient overflows were detected and
skipped by the optimizer; later gradients were finite.

The baseline canonical validation used the smoke checkpoint at step 2,248 and
reported zero completions, a 0.21875 fall rate, and mean maximum route
completion 0.1204 across 64 held-out mazes. This baseline was expected to be
weak. The monitor copied a stable 500k checkpoint and began canonical
validation, but the reboot interrupted evaluation before it produced a result.

At that audit point, no training or validation process was running. The
production checkpoint, replay chunks, metrics, baseline validation, and 500k
validation snapshot remained on the server.

### Subsequent recovery outcome

The run was subsequently resumed in
`multimaze_v2_production_10m_resume_gpu2_20260724_095657`. It reached step
9,520,768 before the user requested a safe stop. Training, the validation
monitor and the active 9.5M evaluator received SIGTERM; all confirmed processes
exited and the unrelated shared-server workload was left untouched. The main
checkpoint was saved at shutdown, and the copied 9.5M checkpoint passed its
SHA-256 check. The 9.5M evaluation did not finish, so 9M remains the latest
complete validation milestone. See `HARDWARE_HANDOFF_2026-07-26.md` for results
and the current continuation plan.

### Recovery commands used after the reboot

First finish canonical validation of the preserved 500k snapshot. Do not resume
the 10M run unless it satisfies the rollout gates at the end of this document.
The monitor can be restarted against the interrupted directory; it skips the
completed baseline and reuses the stable 500k snapshot:

```bash
cd /home/tn22833/TAG_hardware_contract_fed232e
export TAG_VALIDATION_APPROVED=YES
export TAG_MANIFEST="$PWD/tag_mujoco/maze_splits_v2.json"
export TAG_END_STEP=10000000
bash scripts/start_remote_validation_monitor.sh \
  "$PWD" \
  "$HOME/cyberrunner_logs/multimaze_v2_production_10m_gpu2_20260723_221436"
```

If the 500k validation passes, resume into a fresh log directory; never write
over the interrupted run:

```bash
cd /home/tn22833/TAG_hardware_contract_fed232e
export TAG_TRAINING_APPROVED=YES
export TAG_STEPS=10000000
export TAG_PYTHON="$PWD/.venv/bin/python"
export TAG_DEMO_DIR="$PWD/tag_mujoco/expert_demos_v2"
export TAG_LOGDIR="$HOME/cyberrunner_logs/multimaze_v2_production_10m_gpu2_RESUME_TIMESTAMP"
bash scripts/run_tag_sim_v2_gpu2.sh \
  --run.from_checkpoint \
  "$HOME/cyberrunner_logs/multimaze_v2_production_10m_gpu2_20260723_221436/checkpoint.ckpt"
```

After the fresh run directory and configuration exist, start a new validation
monitor with `TAG_MANIFEST` set to the v2 manifest. The incomplete 500k
validation from the interrupted directory should remain preserved as evidence,
not treated as a completed metric.

## Rebuild and verify the dataset

```bash
python tag_mujoco/build_maze_dataset.py --profile diverse_v2
python -m unittest discover -s tag_mujoco/tests -v
python tag_mujoco/verify_training_readiness.py \
  --manifest tag_mujoco/maze_splits_v2.json \
  --rollout-limit 16
```

The committed manifest hashes every layout. Validation and test layouts must
never be added to replay.

## Generate bootstrap demonstrations

Start with successful near-goal segments, then add full-start successes:

```bash
python tag_mujoco/expert_controller.py \
  --manifest tag_mujoco/maze_splits_v2.json \
  --output tag_mujoco/expert_demos_v2/near_goal \
  --episodes 128 --random-start

python tag_mujoco/expert_controller.py \
  --manifest tag_mujoco/maze_splits_v2.json \
  --output tag_mujoco/expert_demos_v2/full_start \
  --episodes 128
```

The generator discards failed attempts by default. Demonstrations are local
artifacts and are intentionally ignored by Git. Set `TAG_DEMO_DIR` to
their common parent; the loader discovers episode files recursively.

## Guarded smoke launch

```bash
export TAG_TRAINING_APPROVED=YES
export TAG_STEPS=10000
export TAG_DEMO_DIR=/absolute/path/to/expert_demos_v2
bash scripts/run_tag_sim_v2_gpu2.sh
```

The launcher requires a fresh log directory, physical GPU 2, the v2 manifest,
and explicit approval. It rejects v1 resume data.

## Validation monitor

```bash
export TAG_VALIDATION_APPROVED=YES
export TAG_MANIFEST=/absolute/repo/tag_mujoco/maze_splits_v2.json
export TAG_END_STEP=20000000
bash scripts/start_remote_validation_monitor.sh REPO_ROOT DREAMER_LOGDIR
```

Do not continue from the 500k pilot to a long production run unless canonical
validation shows nonzero completion, fall rate below 0.60, maximum route
completion above 0.40, and finite main losses.
