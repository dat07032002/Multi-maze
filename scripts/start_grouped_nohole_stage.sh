#!/usr/bin/env bash
set -euo pipefail

if [[ "${TAG_TRAINING_APPROVED:-NO}" != "YES" ]] ||
   [[ "${TAG_VALIDATION_APPROVED:-NO}" != "YES" ]]; then
  echo "Set TAG_TRAINING_APPROVED=YES and TAG_VALIDATION_APPROVED=YES."
  exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
size="${1:?Pass group size 16, 32, 64, 128, or 512.}"
source_checkpoint="${2:-}"
source_run="${3:-}"
python_bin="${TAG_PYTHON:-$repo_root/.venv/bin/python}"
dataset_root="${TAG_CURRICULUM_ROOT:-$repo_root/artifacts/paired_hole_curriculum}"

case "$size" in
  16)  code=016; profile=tag_sim_v2_noholes_group016; steps=500000; interval=100000; previous= ;;
  32)  code=032; profile=tag_sim_v2_noholes_group032; steps=500000; interval=100000; previous=016 ;;
  64)  code=064; profile=tag_sim_v2_noholes_group064; steps=750000; interval=150000; previous=032 ;;
  128) code=128; profile=tag_sim_v2_noholes_group128; steps=1000000; interval=200000; previous=064 ;;
  512) code=512; profile=tag_sim_v2_noholes_group512; steps=2000000; interval=250000; previous=128 ;;
  *) echo "Group size must be 16, 32, 64, 128, or 512."; exit 3 ;;
esac

manifest="$dataset_root/no_holes/maze_splits_group_${code}.json"
test -f "$manifest"
grep -q "cyberrunner_paired_no_holes_group${code}_v1" "$manifest"

if [[ "$size" == "16" ]]; then
  if [[ -n "$source_checkpoint" || -n "$source_run" ]]; then
    echo "The 16-map stage starts from scratch and refuses source arguments."
    exit 4
  fi
  unset TAG_FROM_CHECKPOINT TAG_CHECKPOINT_CONTRACT TAG_DEMO_DIR
  export TAG_CHECKPOINT_MODE=none
else
  test -f "$source_checkpoint"
  test -d "$source_run/replay"
  test -f "$source_run/policy_contract.json"
  grep -q "cyberrunner_paired_no_holes_group${previous}_v1" \
    "$source_run/policy_contract.json"
  export TAG_FROM_CHECKPOINT="$source_checkpoint"
  export TAG_CHECKPOINT_CONTRACT="$source_run/policy_contract.json"
  export TAG_CHECKPOINT_MODE=agent_only
  export TAG_DEMO_DIR="$source_run/replay"
  export TAG_DEMO_LIMIT_STEPS="${TAG_DEMO_LIMIT_STEPS:-25000}"
  export TAG_DEMO_SAMPLING=uniform_chunks
fi

stamp="$(date +%Y%m%d_%H%M%S)"
run_id="${TAG_RUN_ID:-noholes_group${code}_${stamp}}"
run_dir="${TAG_LOGDIR:-$HOME/cyberrunner_logs/$run_id}"
test ! -e "$run_dir"

export TAG_TRAINING_VARIANT=v2
export TAG_TRAINING_PROFILE="$profile"
export TAG_STEPS="${TAG_STEPS:-$steps}"
export TAG_RUN_ID="$run_id"
export TAG_LOGDIR="$run_dir"
export TAG_PYTHON="$python_bin"
export TAG_TRAIN_GPU="${TAG_TRAIN_GPU:-2}"
bash "$repo_root/scripts/start_remote_gpu2_training.sh" "$repo_root"

training_status="$repo_root/$run_id.exit_status"
while [[ ! -f "$run_dir/config.yaml" ]]; do
  if [[ -f "$training_status" ]]; then
    echo "Training exited before writing config.yaml."
    exit 5
  fi
  sleep 5
done

export TAG_MANIFEST="$manifest"
export TAG_START_STEP="$interval"
export TAG_INTERVAL="$interval"
export TAG_ROBUST_INTERVAL=100000000
export TAG_END_STEP="${TAG_STEPS}"
export TAG_BASELINE=YES
export TAG_SPLIT=dev
export TAG_POLICY_MODE=sample
export TAG_CANONICAL_EPISODES=1
export TAG_CANONICAL_GPU="${TAG_CANONICAL_GPU:-3}"
export TAG_ROBUST_GPU="${TAG_ROBUST_GPU:-4}"
export TAG_STOP_ON_PLATEAU=YES
export TAG_PLATEAU_PATIENCE=2
export TAG_MIN_COMPLETION_DELTA=0.05
export TAG_MIN_ROUTE_DELTA=0.02
export TAG_MAX_FALL_DELTA=0.01
bash "$repo_root/scripts/start_remote_validation_monitor.sh" \
  "$repo_root" "$run_dir"

printf 'GROUP=%s\nPROFILE=%s\nRUN_ID=%s\nRUN_DIR=%s\nMANIFEST=%s\n' \
  "$size" "$profile" "$run_id" "$run_dir" "$manifest"
