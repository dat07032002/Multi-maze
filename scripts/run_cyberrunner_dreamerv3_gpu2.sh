#!/usr/bin/env bash
set -euo pipefail

if [[ "${CYBERRUNNER_TRAINING_APPROVED:-NO}" != "YES" ]]; then
  echo "Training is locked. Obtain user approval, then set CYBERRUNNER_TRAINING_APPROVED=YES."
  exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

# Physical GPU 0 is intentionally never exposed. JAX will call physical GPU 2
# logical device 0 inside this process.
export CUDA_VISIBLE_DEVICES="2"
export XLA_PYTHON_CLIENT_PREALLOCATE="false"
export MUJOCO_GL="egl"
export PYTHONUNBUFFERED="1"

if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi -i 2 --query-gpu=index,uuid,name --format=csv,noheader
fi
echo "CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES (physical GPU 2 only)"

stamp="$(date +%Y%m%d_%H%M%S)"
logdir="${CYBERRUNNER_LOGDIR:-$HOME/cyberrunner_logs/clean_dreamerv3_medium_gpu2_$stamp}"
steps="${CYBERRUNNER_STEPS:-10000}"
echo "Approved training-step limit: $steps"

extra_args=()
if [[ -n "${CYBERRUNNER_FROM_CHECKPOINT:-}" ]]; then
  test -f "$CYBERRUNNER_FROM_CHECKPOINT"
  echo "Resume checkpoint: $CYBERRUNNER_FROM_CHECKPOINT"
  extra_args+=(--run.from_checkpoint "$CYBERRUNNER_FROM_CHECKPOINT")
fi

python_bin="${CYBERRUNNER_PYTHON:-python}"
"$python_bin" dreamerv3/dreamerv3/train.py \
  --configs cyberrunner medium \
  --logdir "$logdir" \
  --run.script train \
  --run.steps "$steps" \
  "${extra_args[@]}" \
  "$@"
