#!/usr/bin/env bash
set -euo pipefail

if [[ "${TAG_TRAINING_APPROVED:-NO}" != "YES" ]] ||
   [[ "${TAG_VALIDATION_APPROVED:-NO}" != "YES" ]]; then
  echo "Set both TAG_TRAINING_APPROVED=YES and TAG_VALIDATION_APPROVED=YES."
  exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
baseline_root="${1:?Pass the PLA baseline directory as argument 1.}"
demo_root="${2:?Pass the PLA demonstration directory as argument 2.}"
source_checkpoint="${3:?Pass the frozen v2 checkpoint as argument 3.}"
python_bin="${TAG_PYTHON:-python}"
run_id="${TAG_RUN_ID:-pla_adapt_13m_500k_$(date +%Y%m%d_%H%M%S)}"
run_dir="${TAG_LOGDIR:-$HOME/cyberrunner_logs/$run_id}"
baseline_status="${baseline_root}.launcher.exit_status"
demo_status="${demo_root}.launcher.exit_status"

wait_for_status() {
  local status_file="$1"
  local label="$2"
  while [[ ! -f "$status_file" ]]; do
    echo "Waiting for $label: $status_file"
    sleep 30
  done
  local code
  code="$(tr -d '[:space:]' <"$status_file")"
  if [[ "$code" != "0" ]]; then
    echo "$label failed with exit status $code."
    exit 3
  fi
}

wait_for_status "$baseline_status" "PLA baseline"
wait_for_status "$demo_status" "PLA demonstration generation"
test -s "$baseline_root/canonical.json"
test -s "$baseline_root/robust.json"
demo_count="$(find "$demo_root" -name '*.npz' -type f | wc -l)"
if (( demo_count < 192 )); then
  echo "Expected at least 192 complete demonstrations, found $demo_count."
  exit 4
fi
test -f "$source_checkpoint"
test ! -e "$run_dir"

export TAG_TRAINING_VARIANT=v2
export TAG_TRAINING_PROFILE=tag_sim_v2_pla_adaptation
export TAG_CHECKPOINT_MODE=agent_only
export TAG_FROM_CHECKPOINT="$source_checkpoint"
export TAG_DEMO_DIR="$demo_root"
export TAG_STEPS=500000
export TAG_RUN_ID="$run_id"
export TAG_LOGDIR="$run_dir"
export TAG_PYTHON="$python_bin"

bash "$repo_root/scripts/start_remote_gpu2_training.sh" "$repo_root"
training_status="$repo_root/$run_id.exit_status"

while [[ ! -f "$run_dir/config.yaml" ]]; do
  if [[ -f "$training_status" ]]; then
    code="$(tr -d '[:space:]' <"$training_status")"
    echo "Training exited before writing config.yaml with status $code."
    exit 5
  fi
  sleep 5
done

export TAG_MANIFEST="$repo_root/tag_mujoco/maze_splits_v2.json"
export TAG_START_STEP=250000
export TAG_INTERVAL=250000
export TAG_ROBUST_INTERVAL=250000
export TAG_END_STEP=500000
export TAG_BASELINE=NO
bash "$repo_root/scripts/start_remote_validation_monitor.sh" \
  "$repo_root" "$run_dir"

validation_status="$run_dir/validation/monitor.exit_status"
wait_for_status "$training_status" "PLA 500k pilot"
wait_for_status "$validation_status" "PLA pilot validation"

"$python_bin" "$repo_root/tag_mujoco/pla_training_gate.py" \
  --baseline-canonical "$baseline_root/canonical.json" \
  --baseline-robust "$baseline_root/robust.json" \
  --candidate-canonical \
    "$run_dir/validation/step_000500000/canonical.json" \
  --candidate-robust \
    "$run_dir/validation/step_000500000/robust.json" \
  --output "$run_dir/validation/continuation_gate.json"

echo "PLA 500k pilot complete. No longer continuation was started."
