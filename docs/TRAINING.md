# Training and validation

## Learning task

Training does not proceed maze by maze. The active v2 profile samples from 512
training layouts using outcome-based prioritized level replay with uniform and
staleness coverage. The same policy must follow the supplied five-point route
and react to walls and holes visible in the image.

The active split in `cyberrunner_mujoco/maze_splits_v2.json` is fixed:

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

The run reached step 510,432 at about 217 FPS before a server reboot at
2026-07-23 23:02 CDT stopped training and the in-progress 500k validation. No
training exception was logged and all artifacts were preserved. As of the
2026-07-24 audit, the run is stopped and must be resumed into a fresh directory.
See `V2_TRAINING.md` for the full experiment record and recovery command.

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
export CYBERRUNNER_TRAINING_APPROVED=YES
export CYBERRUNNER_STEPS=10000000
export CYBERRUNNER_DEMO_DIR=/absolute/path/to/expert_demos_v2
bash scripts/run_cyberrunner_v2_gpu2.sh \
  --run.from_checkpoint /absolute/path/to/v2/checkpoint.ckpt
```

Start validation only after the production run directory exists:

```bash
export CYBERRUNNER_VALIDATION_APPROVED=YES
export CYBERRUNNER_MANIFEST=/absolute/path/to/maze_splits_v2.json
export CYBERRUNNER_END_STEP=10000000
bash scripts/start_remote_validation_monitor.sh \
  /absolute/path/to/repository \
  /absolute/path/to/production/logdir
```

The launch guard rejects old checkpoints and nonempty log directories that do
not contain matching `tag_hardware_policy_v1` metadata.
