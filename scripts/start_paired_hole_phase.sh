#!/usr/bin/env bash
set -euo pipefail

if [[ "${TAG_TRAINING_APPROVED:-NO}" != "YES" ]] ||
   [[ "${TAG_VALIDATION_APPROVED:-NO}" != "YES" ]]; then
  echo "Set TAG_TRAINING_APPROVED=YES and TAG_VALIDATION_APPROVED=YES."
  exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
phase="${1:?Pass curriculum phase 1-5.}"
source_checkpoint="${2:-}"
source_run="${3:-}"
python_bin="${TAG_PYTHON:-$repo_root/.venv/bin/python}"
dataset_root="${TAG_CURRICULUM_ROOT:-$repo_root/artifacts/paired_hole_curriculum}"

case "$phase" in
  1)
    profile=tag_sim_v2_phase1_noholes_fullstart_scratch
    variant=no_holes
    steps=1500000
    interval=250000
    ;;
  2)
    profile=tag_sim_v2_phase2_noholes_fullstart
    variant=no_holes
    steps=2000000
    interval=250000
    ;;
  3)
    profile=tag_sim_v2_phase3_branch_holes
    variant=branch_holes
    steps=1000000
    interval=250000
    ;;
  4)
    profile=tag_sim_v2_phase4_easy_dodge
    variant=easy_dodge
    steps=2000000
    interval=250000
    ;;
  5)
    profile=tag_sim_v2_phase5_mixed_holes
    variant=mixed_holes
    steps=5000000
    interval=500000
    ;;
  *)
    echo "Phase must be 1, 2, 3, 4, or 5."
    exit 3
    ;;
esac

manifest="$dataset_root/$variant/maze_splits.json"
test -f "$manifest"
grep -q "cyberrunner_paired_${variant}_512train_64val_64test_v1" "$manifest"

if [[ "$phase" == "1" ]]; then
  if [[ -n "$source_checkpoint" || -n "$source_run" ]]; then
    echo "Phase 1 starts from scratch and refuses source arguments."
    exit 4
  fi
  unset TAG_FROM_CHECKPOINT TAG_CHECKPOINT_CONTRACT TAG_DEMO_DIR
  export TAG_CHECKPOINT_MODE=none
else
  test -f "$source_checkpoint"
  test -d "$source_run/replay"
  test -f "$source_run/policy_contract.json"
  export TAG_FROM_CHECKPOINT="$source_checkpoint"
  export TAG_CHECKPOINT_CONTRACT="$source_run/policy_contract.json"
  export TAG_CHECKPOINT_MODE=agent_only
  export TAG_DEMO_DIR="$source_run/replay"
  export TAG_DEMO_LIMIT_STEPS="${TAG_DEMO_LIMIT_STEPS:-25000}"
  export TAG_DEMO_SAMPLING=uniform_chunks
fi

stamp="$(date +%Y%m%d_%H%M%S)"
run_id="${TAG_RUN_ID:-paired_holes_phase${phase}_${variant}_${stamp}}"
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
export TAG_SPLIT=validation
export TAG_POLICY_MODE=sample
export TAG_CANONICAL_EPISODES=1
export TAG_CANONICAL_GPU="${TAG_CANONICAL_GPU:-3}"
export TAG_ROBUST_GPU="${TAG_ROBUST_GPU:-4}"
export TAG_STOP_ON_PLATEAU=YES
export TAG_PLATEAU_PATIENCE=3
export TAG_MIN_COMPLETION_DELTA=0.01
export TAG_MIN_ROUTE_DELTA=0.005
export TAG_MAX_FALL_DELTA=0.005
bash "$repo_root/scripts/start_remote_validation_monitor.sh" \
  "$repo_root" "$run_dir"

printf 'PHASE=%s\nPROFILE=%s\nRUN_ID=%s\nRUN_DIR=%s\nMANIFEST=%s\n' \
  "$phase" "$profile" "$run_id" "$run_dir" "$manifest"
