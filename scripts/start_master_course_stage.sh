#!/usr/bin/env bash
set -euo pipefail

if [[ "${TAG_TRAINING_APPROVED:-NO}" != "YES" ]] ||
   [[ "${TAG_VALIDATION_APPROVED:-NO}" != "YES" ]]; then
  echo "Set TAG_TRAINING_APPROVED=YES and TAG_VALIDATION_APPROVED=YES."
  exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
stage="${1:?Pass foundation, turns, recovery, hazards, or compound.}"
source_checkpoint="${2:-}"
source_run="${3:-}"
python_bin="${TAG_PYTHON:-$repo_root/.venv/bin/python}"
dataset_root="${TAG_MASTER_COURSE_ROOT:-$repo_root/artifacts/master_course_curriculum}"

case "$stage" in
  foundation) code=01; steps=500000;  previous= ;;
  turns)      code=02; steps=750000;  previous="tag_master_course_stage1_foundation_v1" ;;
  recovery)   code=03; steps=750000;  previous="tag_master_course_stage2_turns_v1" ;;
  hazards)    code=04; steps=1000000; previous="tag_master_course_stage3_recovery_v1" ;;
  compound)   code=05; steps=1500000; previous="tag_master_course_stage4_hazards_v1" ;;
  *) echo "Unknown master-course stage: $stage"; exit 3 ;;
esac

manifest="$dataset_root/stage_${code}_${stage}.json"
dataset_id="tag_master_course_stage${code#0}_${stage}_v1"
test -f "$manifest"
grep -q "$dataset_id" "$manifest"

if [[ "$stage" == "foundation" ]]; then
  if [[ -n "$source_checkpoint" || -n "$source_run" ]]; then
    echo "Foundation starts from scratch and refuses source arguments."
    exit 4
  fi
  unset TAG_FROM_CHECKPOINT TAG_CHECKPOINT_CONTRACT
  export TAG_CHECKPOINT_MODE=none
else
  test -f "$source_checkpoint"
  test -f "$source_run/policy_contract.json"
  grep -q "\"dataset_id\":\"$previous\"" "$source_run/policy_contract.json"
  export TAG_FROM_CHECKPOINT="$source_checkpoint"
  export TAG_CHECKPOINT_CONTRACT="$source_run/policy_contract.json"
  export TAG_CHECKPOINT_MODE=agent_only
fi

stamp="$(date +%Y%m%d_%H%M%S)"
run_id="${TAG_RUN_ID:-master_${stage}_${stamp}}"
run_dir="${TAG_LOGDIR:-$HOME/cyberrunner_logs/$run_id}"
test ! -e "$run_dir"

export TAG_TRAINING_VARIANT=v2
export TAG_TRAINING_PROFILE="tag_sim_v5_master_${stage}"
export TAG_MANIFEST="$manifest"
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

export TAG_START_STEP=50000
export TAG_INTERVAL=50000
export TAG_ROBUST_INTERVAL=100000000
export TAG_END_STEP="$TAG_STEPS"
export TAG_BASELINE=YES
export TAG_SPLIT=validation
export TAG_POLICY_MODE=sample
export TAG_CANONICAL_EPISODES=1
export TAG_CANONICAL_GPU="${TAG_CANONICAL_GPU:-3}"
export TAG_ROBUST_GPU="${TAG_ROBUST_GPU:-4}"
# Physical GPU 0 is never used, and validation must not share a device with
# its own training run. The training launcher already refuses GPU 0; these are
# overridable, so they need the same guard.
for gpu_var in TAG_CANONICAL_GPU TAG_ROBUST_GPU; do
  gpu_value="${!gpu_var}"
  if [[ ! "$gpu_value" =~ ^[0-9]+$ ]]; then
    echo "$gpu_var must be a GPU index, got '$gpu_value'."
    exit 6
  fi
  if [[ "$gpu_value" == "0" ]]; then
    echo "$gpu_var must not be physical GPU 0."
    exit 6
  fi
  if [[ "$gpu_value" == "$TAG_TRAIN_GPU" ]]; then
    echo "$gpu_var must not share device $gpu_value with training."
    exit 6
  fi
done
export TAG_STOP_ON_PLATEAU=YES
export TAG_VALIDATION_BARRIER=YES
export TAG_PLATEAU_PATIENCE=3
export TAG_MIN_COMPLETION_DELTA=0.03
export TAG_MIN_ROUTE_DELTA=0.02
export TAG_MAX_FALL_DELTA=0.02
bash "$repo_root/scripts/start_remote_validation_monitor.sh" \
  "$repo_root" "$run_dir"

printf 'STAGE=%s\nPROFILE=%s\nRUN_ID=%s\nRUN_DIR=%s\nMANIFEST=%s\n' \
  "$stage" "$TAG_TRAINING_PROFILE" "$run_id" "$run_dir" "$manifest"

# Pass --validation-root when the stage finishes. Without it the gate reads a
# single evaluation snapshot and cannot see that a stage ended worse than the
# checkpoint it started from, which is how the 150k foundation run looked.
cat <<EOF

When this stage completes, gate it with the full validation history:

  "$python_bin" -m tag_mujoco.master_course_gate \\
    --report $run_dir/validation/<final>/canonical.json \\
    --manifest $manifest \\
    --target-stage $stage \\
    --validation-root $run_dir/validation \\
    --output $run_dir/gate_decision.json
EOF
