#!/usr/bin/env bash
set -euo pipefail

if [[ "${TAG_TRAINING_APPROVED:-NO}" != "YES" ]] ||
   [[ "${TAG_VALIDATION_APPROVED:-NO}" != "YES" ]]; then
  echo "Set both TAG_TRAINING_APPROVED=YES and TAG_VALIDATION_APPROVED=YES."
  exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_checkpoint="${1:?Pass the frozen v2 checkpoint as argument 1.}"
baseline_canonical="${2:?Pass the nominal canonical baseline JSON as argument 2.}"
python_bin="${TAG_PYTHON:-python}"
run_id="${TAG_RUN_ID:-nominal_fullstart_13m_500k_$(date +%Y%m%d_%H%M%S)}"
run_dir="${TAG_LOGDIR:-$HOME/cyberrunner_logs/$run_id}"

test -f "$source_checkpoint"
test -s "$baseline_canonical"
test ! -e "$run_dir"
"$python_bin" - "$baseline_canonical" <<'PY'
import json
import sys

result = json.load(open(sys.argv[1], encoding="utf-8"))
if not result.get("completed", False):
    raise SystemExit("Canonical baseline is incomplete")
if int(result["summary"]["episodes"]) < 64:
    raise SystemExit("Canonical baseline must contain all 64 validation mazes")
PY

export TAG_TRAINING_VARIANT=v2
export TAG_TRAINING_PROFILE=tag_sim_v2_nominal_fullstart
export TAG_CHECKPOINT_MODE=agent_only
export TAG_FROM_CHECKPOINT="$source_checkpoint"
unset TAG_DEMO_DIR
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

mkdir -p "$run_dir/validation"
cp "$baseline_canonical" "$run_dir/validation/baseline_canonical.json"
sha256sum "$source_checkpoint" >"$run_dir/source_checkpoint.sha256"
sha256sum "$baseline_canonical" >"$run_dir/validation/baseline_canonical.sha256"

export TAG_MANIFEST="$repo_root/tag_mujoco/maze_splits_v2.json"
export TAG_START_STEP=250000
export TAG_INTERVAL=250000
# Larger than the bounded run, so only canonical validation is scheduled.
export TAG_ROBUST_INTERVAL=1000000000
export TAG_END_STEP=500000
export TAG_BASELINE=NO
bash "$repo_root/scripts/start_remote_validation_monitor.sh" \
  "$repo_root" "$run_dir"

echo "Nominal full-start 500k pilot launched."
echo "RUN_ID=$run_id"
echo "RUN_DIR=$run_dir"
echo "TRAINING_STATUS=$training_status"
echo "VALIDATION_STATUS=$run_dir/validation/monitor.exit_status"
