#!/usr/bin/env bash
set -euo pipefail

if [[ "${TAG_TRAINING_APPROVED:-NO}" != "YES" ]] ||
   [[ "${TAG_VALIDATION_APPROVED:-NO}" != "YES" ]]; then
  echo "Set TAG_TRAINING_APPROVED=YES and TAG_VALIDATION_APPROVED=YES."
  exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_checkpoint="${1:?Pass the current hole-aware checkpoint as argument 1.}"
source_run="${2:?Pass its source run directory as argument 2.}"
prior_confirmation="${3:?Pass a prior 192-episode result as argument 3.}"
confirmation_root="${4:?Pass a new dual-confirmation directory as argument 4.}"
python_bin="${TAG_PYTHON:-python}"
run_id="${TAG_RUN_ID:-holeaware_nominal_continue_250k_$(date +%Y%m%d_%H%M%S)}"
run_dir="${TAG_LOGDIR:-$HOME/cyberrunner_logs/$run_id}"
source_contract="$source_run/policy_contract.json"

test -f "$source_checkpoint"
test -f "$source_contract"
test -f "$prior_confirmation"
test ! -e "$run_dir"
test ! -e "$confirmation_root"

export TAG_TRAINING_VARIANT=v2
export TAG_TRAINING_PROFILE=tag_sim_v2_nominal_holeaware
export TAG_CHECKPOINT_MODE=agent_only
export TAG_FROM_CHECKPOINT="$source_checkpoint"
export TAG_CHECKPOINT_CONTRACT="$source_contract"
export TAG_STEPS=250000
export TAG_RUN_ID="$run_id"
export TAG_LOGDIR="$run_dir"
export TAG_PYTHON="$python_bin"
export TAG_TRAIN_GPU="${TAG_TRAIN_GPU:-2}"
bash "$repo_root/scripts/start_remote_gpu2_training.sh" "$repo_root"

training_status="$repo_root/$run_id.exit_status"
while [[ ! -f "$run_dir/config.yaml" ]]; do
  if [[ -f "$training_status" ]]; then
    code="$(tr -d '[:space:]' <"$training_status")"
    echo "Nominal continuation exited before writing config.yaml: $code"
    exit 3
  fi
  sleep 5
done

"$python_bin" - "$run_dir/config.yaml" <<'PY'
import sys
import ruamel.yaml as yaml
config = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))
env = config["env"]["tagmaze"]
checks = {
    "random starts disabled": not env["random_start"],
    "plant randomization disabled": not env["randomize_plant"],
    "randomization curriculum disabled": not env["randomization_curriculum"],
    "hole margin retained": env["hole_clearance_penalty"] == 0.02,
    "action-rate penalty disabled": env["action_rate_penalty"] == 0.0,
}
failed = [name for name, passed in checks.items() if not passed]
if failed:
    raise SystemExit("Invalid nominal continuation config: " + ", ".join(failed))
PY

# Use the training-subset dev split for curve monitoring. The held-out
# validation split is read only by the final dual-seed mastery confirmation.
export TAG_MANIFEST="$repo_root/tag_mujoco/maze_splits_v2.json"
export TAG_START_STEP=125000
export TAG_INTERVAL=125000
export TAG_ROBUST_INTERVAL=1000000
export TAG_END_STEP=250000
export TAG_BASELINE=YES
export TAG_SPLIT=dev
export TAG_POLICY_MODE=sample
export TAG_CANONICAL_EPISODES=1
export TAG_CANONICAL_GPU="${TAG_CANONICAL_GPU:-3}"
export TAG_ROBUST_GPU="${TAG_ROBUST_GPU:-4}"
unset TAG_ROBUST_STRENGTH
bash "$repo_root/scripts/start_remote_validation_monitor.sh" \
  "$repo_root" "$run_dir"

wait_for_status() {
  local status_file="$1"
  local label="$2"
  while [[ ! -f "$status_file" ]]; do
    sleep 30
  done
  local code
  code="$(tr -d '[:space:]' <"$status_file")"
  if [[ "$code" != "0" ]]; then
    echo "$label failed with exit status $code."
    exit 4
  fi
}

wait_for_status "$training_status" "Nominal 250k continuation"
wait_for_status "$run_dir/validation/monitor.exit_status" "Dev validation"
test -f "$run_dir/checkpoint.ckpt"

# The confirmation script detects that this is a new checkpoint and therefore
# requires it to pass both the original and new seed protocols. A dual pass
# unlocks only the already-bounded fixed DR-0.10 stage.
bash "$repo_root/scripts/confirm_nominal_then_start_dr010.sh" \
  "$run_dir/checkpoint.ckpt" \
  "$run_dir" \
  "$prior_confirmation" \
  "$confirmation_root"

