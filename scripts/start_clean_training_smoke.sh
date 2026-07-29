#!/usr/bin/env bash
set -euo pipefail

if [[ "${TAG_TRAINING_APPROVED:-NO}" != "YES" ]]; then
  echo "Set TAG_TRAINING_APPROVED=YES before launching the clean smoke."
  exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_checkpoint="${1:?Pass the source champion checkpoint as argument 1.}"
source_run="${2:?Pass the source run directory as argument 2.}"
python_bin="${TAG_PYTHON:-python}"
run_id="${TAG_RUN_ID:-holeaware_clean_smoke_2k_$(date +%Y%m%d_%H%M%S)}"
run_dir="${TAG_LOGDIR:-$HOME/cyberrunner_logs/$run_id}"
source_contract="$source_run/policy_contract.json"
source_replay="$source_run/replay"

test -f "$source_checkpoint"
test -f "$source_contract"
test -d "$source_replay"
test ! -e "$run_dir"

export TAG_TRAINING_VARIANT=v2
export TAG_TRAINING_PROFILE=tag_sim_v2_clean_smoke
export TAG_CHECKPOINT_MODE=agent_only
export TAG_FROM_CHECKPOINT="$source_checkpoint"
export TAG_CHECKPOINT_CONTRACT="$source_contract"
export TAG_DEMO_DIR="$source_replay"
export TAG_DEMO_LIMIT_STEPS="${TAG_DEMO_LIMIT_STEPS:-25000}"
export TAG_DEMO_SAMPLING=uniform_chunks
export TAG_STEPS="${TAG_STEPS:-2000}"
export TAG_RUN_ID="$run_id"
export TAG_LOGDIR="$run_dir"
export TAG_PYTHON="$python_bin"
export TAG_TRAIN_GPU="${TAG_TRAIN_GPU:-2}"

bash "$repo_root/scripts/start_remote_gpu2_training.sh" "$repo_root"

echo "Clean float32 smoke launched."
echo "RUN_DIR=$run_dir"
echo "Required artifacts: replay_import_report.json and training_health.json"
