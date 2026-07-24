# Training and validation

## Learning task

Training does not proceed maze by maze. Each episode selects one of 40 training
layouts using the curriculum sampler. The same policy must follow the supplied
five-point route and react to walls and holes visible in the image.

The split in `cyberrunner_mujoco/maze_splits.json` is fixed:

| Split | Count | Use |
| --- | ---: | --- |
| Train | 40 | Environment interaction and replay |
| Validation | 8 | Repeated checkpoint selection |
| Test | 8 | One final held-out report only |

## Current production run

The contract-v1 production run was launched fresh on 2026-07-23 after a
successful 10,015-step smoke test. It does not resume the pre-contract run.

```text
Server code:
/home/tn22833/TAG_hardware_contract_fed232e

Production log directory:
/home/tn22833/cyberrunner_logs/hardware_contract_v1_production_10m_gpu2_20260723

Validation directory:
/home/tn22833/cyberrunner_logs/hardware_contract_v1_production_10m_gpu2_20260723/validation

Preserved stopped pre-contract run:
/home/tn22833/cyberrunner_logs/multimaze_production_10m_gpu2_20260723
```

The production limit is 10,000,000 environment steps. At approximately 100
simulator steps per second this is roughly 28 hours before validation overhead.

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

tail -f /home/tn22833/TAG_hardware_contract_fed232e/\
hardware_contract_v1_production_10m_gpu2_20260723.log

tail -f /home/tn22833/cyberrunner_logs/\
hardware_contract_v1_production_10m_gpu2_20260723/validation/monitor.log
```

To stop safely, first inspect the exact commands above, then send `SIGTERM` only
to the confirmed training and validation processes. Never delete their log
directories; the latest completed checkpoint and replay chunks remain useful.

## Starting a future run

The launchers require approval and expose only physical GPU 2:

```bash
export CYBERRUNNER_TRAINING_APPROVED=YES
export CYBERRUNNER_STEPS=10000000
bash scripts/start_remote_gpu2_training.sh /absolute/path/to/repository
```

Start validation only after the production run directory exists:

```bash
export CYBERRUNNER_VALIDATION_APPROVED=YES
bash scripts/start_remote_validation_monitor.sh \
  /absolute/path/to/repository \
  /absolute/path/to/production/logdir
```

The launch guard rejects old checkpoints and nonempty log directories that do
not contain matching `tag_hardware_policy_v1` metadata.
