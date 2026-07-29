# Training and validation

## Clean-training gate added 2026-07-29

The failed curriculum-DR v3 run must not be resumed. Its importer read
uninitialized storage beyond each partial replay chunk's filename-declared
length, introducing non-finite states, goals, actions, and rewards, so no
optimizer made a valid update. The valid source transitions themselves are
finite. New training now fails closed at every data boundary:

- complete imported demonstration chunks are rejected if any numeric field is
  non-finite;
- existing saved replay chunks are validated and rejected as whole chunks;
- environment transitions, policy observations/actions, replay insertions,
  replay samples, and assembled training batches are checked;
- non-finite optimizer losses or gradient norms, gradient overflows, and three
  stalled optimizer updates abort the process; and
- the actor/world-model SHA-256 digest must change by optimizer step 2, after
  the warmup schedule moves above its intentionally zero first learning rate.

Each run writes `replay_import_report.json`, `replay/replay_load_report.json`
when saved replay is restored, and `training_health.json`. A missing or failed
health report blocks checkpoint promotion.

The only authorized next training profile is `tag_sim_v2_clean_smoke`. It uses
float32, nominal dynamics, full-route starts, fresh optimizer state, sanitized
source replay, and a 2k counted-step ceiling. The historical
`start_curriculum_dr.sh` launcher is locked until this smoke and the subsequent
10k nominal gate pass.

```bash
export TAG_TRAINING_APPROVED=YES
export TAG_PYTHON=/path/to/python

bash scripts/start_clean_training_smoke.sh \
  /path/to/source/champion/checkpoint.ckpt \
  /path/to/source/run
```

This command still requires explicit approval and does not run as part of
tests or documentation updates.

The first authorized clean smoke completed at step 2,752 with status 0. Model,
actor, and critic losses and gradient norms stayed finite, optimizer counters
advanced, and the acting-parameter digest changed. The corrected importer
selected 34 source chunks, loaded 25,000 valid transitions, and rejected none.
Domain randomization remains locked pending the 10k nominal continuation gate.

## Current result

The best preserved checkpoint is the staged-randomization 13M model at
`multimaze_v2_stagedrand_13m_gpu2_20260727_235843`. Under the previous dynamics
distribution it achieved 59.38% canonical completion with 32.81% falls and
75.70% mean maximum route completion. Corrected robust completion was 29.17%
with 38.02% falls.

The simulator now uses broad untreated-FDM-PLA contact priors. The frozen 13M
checkpoint is being re-evaluated under those priors before training. A guarded
agent-only 500k adaptation and a matched scratch control are documented in
`PROJECT_PROGRESS_2026-07-28.md`. No new long training run should bypass those
evaluation gates.

## Learning task

Training does not proceed maze by maze. The active v2 profile samples from 512
training layouts using outcome-based prioritized level replay with uniform and
staleness coverage. The same policy must follow the supplied five-point route
and react to walls and holes visible in the image.

The active split in `tag_mujoco/maze_splits_v2.json` is fixed:

| Split | Count | Use |
| --- | ---: | --- |
| Train | 512 | Environment interaction and replay |
| Validation | 64 | Repeated checkpoint selection |
| Test | 64 | One final held-out report only |

The original `maze_splits.json` 40/8/8 split remains available only as the
legacy v1 profile.

## Latest production attempt

The adaptive v2 production run was launched on 2026-07-23 after a successful
smoke test. It restored the compatible v2 smoke checkpoint, loaded 160 expert
episodes, and used eight process-parallel environments.

```text
Server code:
/home/tn22833/TAG_hardware_contract_fed232e

Production log directory:
/home/tn22833/cyberrunner_logs/multimaze_v2_production_10m_gpu2_20260723_221436

Validation directory:
/home/tn22833/cyberrunner_logs/multimaze_v2_production_10m_gpu2_20260723_221436/validation

Smoke checkpoint:
/home/tn22833/cyberrunner_logs/multimaze_v2_smoke10k_gpu2_20260723_220438/checkpoint.ckpt
```

That attempt reached step 510,432 before a server reboot. It was then resumed in
`multimaze_v2_production_10m_resume_gpu2_20260724_095657` and reached step
9,520,768. On 2026-07-24 the user requested a safe stop; SIGTERM was sent only
to the confirmed training and validation processes. The main 470 MB checkpoint
was saved, the copied 9.5M checkpoint passed its SHA-256 check, and replay,
metrics and logs were preserved. The 9.5M validation was interrupted, so 9M is
the latest completed milestone. No training or validation process remained after
the stop.

The 9M canonical result was 39.06% completion and 34.38% falls. Its robust result
was 67.19% completion and 23.44% falls. The selector still ranks the 6.5M
canonical checkpoint first at 40.63% completion. Audit the large difference
between canonical and robust protocols before selecting a hardware checkpoint.

## GPU allocation

| Physical GPU | Role |
| ---: | --- |
| 0 | Excluded |
| 2 | DreamerV3 production training |
| 3 | Canonical validation every 500k steps |
| 4 | Robust validation every 1M steps |

Canonical validation runs one deterministic episode on every validation maze.
Robust validation runs three randomized episodes per maze. Selection ranks
completion rate first, then fall rate, route completion, and cross-track error.

## Server status

```bash
pgrep -af '[d]reamerv3/dreamerv3/train.py'
pgrep -af '[v]alidation_monitor.py|[e]val_multimaze.py'
nvidia-smi --query-compute-apps=pid,gpu_uuid,process_name,used_memory \
  --format=csv,noheader

tail -f /home/tn22833/cyberrunner_logs/\
multimaze_v2_production_10m_gpu2_20260723_221436.console.log

tail -f /home/tn22833/cyberrunner_logs/\
multimaze_v2_production_10m_gpu2_20260723_221436/validation/monitor.log
```

To stop safely, first inspect the exact commands above, then send `SIGTERM` only
to the confirmed training and validation processes. Never delete their log
directories; the latest completed checkpoint and replay chunks remain useful.

## Starting a future run

The launchers require approval and expose only physical GPU 2:

```bash
export TAG_TRAINING_APPROVED=YES
export TAG_TRAINING_PROFILE=tag_sim_v2_fullstart_finetune
export TAG_FROM_CHECKPOINT=/absolute/path/to/v2/checkpoint.ckpt
export TAG_STEPS=12500000
export TAG_DEMO_DIR=/absolute/path/to/expert_demos_v2
bash scripts/run_tag_v2_gpu2.sh
```

Start validation only after the production run directory exists:

```bash
export TAG_VALIDATION_APPROVED=YES
export TAG_MANIFEST=/absolute/path/to/maze_splits_v2.json
export TAG_END_STEP=10000000
bash scripts/start_remote_validation_monitor.sh \
  /absolute/path/to/repository \
  /absolute/path/to/production/logdir
```

The launch guard rejects old checkpoints and nonempty log directories that do
not contain matching `tag_hardware_policy_v1` metadata.
