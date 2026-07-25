#!/usr/bin/env bash
set -euo pipefail

if [[ "${TAG_TRAINING_APPROVED:-NO}" != "YES" ]]; then
  echo "Training is locked. Obtain user approval, then set TAG_TRAINING_APPROVED=YES."
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
logdir="${TAG_LOGDIR:-$HOME/tag_logs/clean_dreamerv3_medium_gpu2_$stamp}"
steps="${TAG_STEPS:-10000}"
contract_version="tag_hardware_policy_v1"
echo "Approved training-step limit: $steps"

contract_file="$logdir/policy_contract.json"
if [[ -d "$logdir" && -n "$(find "$logdir" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
  if [[ ! -f "$contract_file" ]] || ! grep -q "\"$contract_version\"" "$contract_file"; then
    echo "Refusing to reuse a non-empty log directory without matching $contract_version metadata."
    exit 4
  fi
fi

extra_args=()
if [[ -n "${TAG_FROM_CHECKPOINT:-}" ]]; then
  test -f "$TAG_FROM_CHECKPOINT"
  checkpoint_contract="$(dirname "$TAG_FROM_CHECKPOINT")/policy_contract.json"
  if [[ ! -f "$checkpoint_contract" ]] || ! grep -q "\"$contract_version\"" "$checkpoint_contract"; then
    echo "Refusing checkpoint without matching $contract_version metadata: $TAG_FROM_CHECKPOINT"
    exit 5
  fi
  echo "Resume checkpoint: $TAG_FROM_CHECKPOINT"
  extra_args+=(--run.from_checkpoint "$TAG_FROM_CHECKPOINT")
fi

python_bin="${TAG_PYTHON:-python}"
mkdir -p "$logdir"
printf '{"policy_contract_version":"%s","checkpoint_compatible_with_precontract_runs":false}\n' \
  "$contract_version" >"$contract_file"
"$python_bin" dreamerv3/dreamerv3/train.py \
  --configs tag_sim medium \
  --logdir "$logdir" \
  --run.script train \
  --run.steps "$steps" \
  "${extra_args[@]}" \
  "$@"
