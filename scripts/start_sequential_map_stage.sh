#!/usr/bin/env bash
set -euo pipefail

if [[ "${TAG_TRAINING_APPROVED:-NO}" != "YES" ]] ||
   [[ "${TAG_VALIDATION_APPROVED:-NO}" != "YES" ]]; then
  echo "Set TAG_TRAINING_APPROVED=YES and TAG_VALIDATION_APPROVED=YES."
  exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
stage="${1:?Pass the sequential map stage number.}"
phase="${2:?Pass local or fullstart.}"
source_checkpoint="${3:?Pass the accepted source checkpoint.}"
source_run="${4:?Pass the accepted source run directory.}"
rehearsal="${5:?Pass a balanced rehearsal-pack directory.}"
python_bin="${TAG_PYTHON:-$repo_root/.venv/bin/python}"
map_root="${TAG_SEQUENTIAL_ROOT:-$repo_root/artifacts/sequential_maps}"
stage_code="$(printf '%04d' "$stage")"
manifest="$map_root/stages/stage_${stage_code}.json"

test -f "$manifest"
test -f "$source_checkpoint"
test -f "$source_run/policy_contract.json"
test -d "$rehearsal"
dataset_id="$($python_bin -c 'import json,sys; print(json.load(open(sys.argv[1]))["dataset_id"])' "$manifest")"
checkpoint_dataset_id="$($python_bin -c 'import json,sys; print(json.load(open(sys.argv[1]))["dataset_id"])' "$source_run/policy_contract.json")"

case "$phase" in
  local) profile=tag_sim_v3_sequential_map_local; steps=100000; interval=25000 ;;
  fullstart) profile=tag_sim_v3_sequential_map_fullstart; steps=100000; interval=25000 ;;
  *) echo "Phase must be local or fullstart."; exit 3 ;;
esac

export TAG_FROM_CHECKPOINT="$source_checkpoint"
export TAG_CHECKPOINT_CONTRACT="$source_run/policy_contract.json"
export TAG_CHECKPOINT_DATASET_ID="$checkpoint_dataset_id"
export TAG_CHECKPOINT_MODE=agent_only
export TAG_DEMO_DIR="$rehearsal"
export TAG_DEMO_LIMIT_STEPS="${TAG_DEMO_LIMIT_STEPS:-50000}"
export TAG_DEMO_SAMPLING=uniform_chunks
export TAG_MANIFEST="$manifest"
export TAG_DATASET_ID="$dataset_id"

stamp="$(date +%Y%m%d_%H%M%S)"
run_id="${TAG_RUN_ID:-map_${stage_code}_${phase}_${stamp}}"
run_dir="${TAG_LOGDIR:-$HOME/cyberrunner_logs/$run_id}"
test ! -e "$run_dir"

export TAG_TRAINING_VARIANT=v2
export TAG_TRAINING_PROFILE="$profile"
export TAG_STEPS="${TAG_STEPS:-$steps}"
export TAG_RUN_ID="$run_id"
export TAG_LOGDIR="$run_dir"
export TAG_PYTHON="$python_bin"
bash "$repo_root/scripts/start_remote_gpu2_training.sh" "$repo_root"

training_status="$repo_root/$run_id.exit_status"
while [[ ! -f "$run_dir/config.yaml" ]]; do
  if [[ -f "$training_status" ]]; then
    echo "Training exited before writing config.yaml."
    exit 5
  fi
  sleep 5
done

export TAG_START_STEP="$interval"
export TAG_INTERVAL="$interval"
export TAG_ROBUST_INTERVAL=100000000
export TAG_END_STEP="$TAG_STEPS"
export TAG_BASELINE=YES
export TAG_SPLIT=dev
export TAG_POLICY_MODE=sample
export TAG_CANONICAL_EPISODES=5
export TAG_STOP_ON_PLATEAU=YES
export TAG_PLATEAU_PATIENCE=2
bash "$repo_root/scripts/start_remote_validation_monitor.sh" \
  "$repo_root" "$run_dir"

printf 'MAP_STAGE=%s\nPHASE=%s\nRUN_DIR=%s\nMANIFEST=%s\n' \
  "$stage_code" "$phase" "$run_dir" "$manifest"
