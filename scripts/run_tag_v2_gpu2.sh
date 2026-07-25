#!/usr/bin/env bash
set -euo pipefail

if [[ "${TAG_TRAINING_APPROVED:-NO}" != "YES" ]]; then
  echo "V2 training is locked. Obtain approval, then set TAG_TRAINING_APPROVED=YES."
  exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

manifest="$repo_root/tag_mujoco/maze_splits_v2.json"
test -f "$manifest"
grep -q 'cyberrunner_fixed_board_512train_64val_64test_v2' "$manifest"

export CUDA_VISIBLE_DEVICES="2"
export XLA_PYTHON_CLIENT_PREALLOCATE="false"
export MUJOCO_GL="egl"
export PYTHONUNBUFFERED="1"

stamp="$(date +%Y%m%d_%H%M%S)"
logdir="${TAG_LOGDIR:-$HOME/tag_logs/multimaze_v2_gpu2_$stamp}"
steps="${TAG_STEPS:-10000}"
python_bin="${TAG_PYTHON:-python}"

if [[ -e "$logdir" ]] && [[ -n "$(find "$logdir" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
  echo "V2 requires a fresh, empty log directory: $logdir"
  exit 4
fi

mkdir -p "$logdir"
printf '{"policy_contract_version":"tag_hardware_policy_v1","training_profile":"tag_sim_v2","dataset_id":"cyberrunner_fixed_board_512train_64val_64test_v2","checkpoint_compatible_with_v1":false}\n' \
  >"$logdir/policy_contract.json"

extra_args=()
if [[ -n "${TAG_DEMO_DIR:-}" ]]; then
  test -d "$TAG_DEMO_DIR"
  extra_args+=(--run.demo_dir "$TAG_DEMO_DIR")
fi

if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi -i 2 --query-gpu=index,uuid,name --format=csv,noheader
fi
echo "V2 steps=$steps envs=8 dataset=512/64/64 logdir=$logdir"

"$python_bin" dreamerv3/dreamerv3/train.py \
  --configs tag_sim_v2 medium \
  --logdir "$logdir" \
  --run.script train \
  --run.steps "$steps" \
  "${extra_args[@]}" \
  "$@"
