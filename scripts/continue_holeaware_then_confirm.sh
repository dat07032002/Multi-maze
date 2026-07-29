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
run_id="${TAG_RUN_ID:-holeaware_nominal_safe_resume_100k_$(date +%Y%m%d_%H%M%S)}"
run_dir="${TAG_LOGDIR:-$HOME/cyberrunner_logs/$run_id}"
source_contract="$source_run/policy_contract.json"
source_replay="$source_run/replay"

test -f "$source_checkpoint"
test -f "$source_contract"
test -d "$source_replay"
test -f "$prior_confirmation"
test ! -e "$run_dir"
test ! -e "$confirmation_root"
source_checkpoint_sha="$(sha256sum "$source_checkpoint" | awk '{print $1}')"

export TAG_TRAINING_VARIANT=v2
export TAG_TRAINING_PROFILE=tag_sim_v2_nominal_safe_resume
export TAG_CHECKPOINT_MODE=agent_only
export TAG_FROM_CHECKPOINT="$source_checkpoint"
export TAG_CHECKPOINT_CONTRACT="$source_contract"
export TAG_DEMO_DIR="$source_replay"
export TAG_DEMO_LIMIT_STEPS=25000
export TAG_DEMO_SAMPLING=uniform_chunks
export TAG_STEPS=100000
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
printf '%s  %s\n' "$source_checkpoint_sha" "$source_checkpoint" \
  >"$run_dir/source_checkpoint.sha256"

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
    "conservative train ratio": config["run"]["train_ratio"] == 8,
    "50k replay warmup": config["run"]["train_fill"] == 50000,
    "prefill excluded from training budget": not config["run"]["count_prefill_steps"],
    "source replay spread across run": config["run"]["demo_sampling"] == "uniform_chunks",
    "actor learning rate reduced": config["actor_opt"]["lr"] == 3e-6,
    "critic learning rate reduced": config["critic_opt"]["lr"] == 3e-6,
}
failed = [name for name, passed in checks.items() if not passed]
if failed:
    raise SystemExit("Invalid nominal continuation config: " + ", ".join(failed))
PY

# Use the training-subset dev split for curve monitoring. The held-out
# validation split is read only by the final dual-seed mastery confirmation.
export TAG_MANIFEST="$repo_root/tag_mujoco/maze_splits_v2.json"
export TAG_START_STEP=25000
export TAG_INTERVAL=25000
export TAG_ROBUST_INTERVAL=1000000
export TAG_END_STEP=100000
export TAG_BASELINE=YES
export TAG_SPLIT=dev
export TAG_POLICY_MODE=sample
export TAG_CANONICAL_EPISODES=3
export TAG_STOP_ON_REGRESSION=YES
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

wait_for_status "$training_status" "Nominal safe continuation"
wait_for_status "$run_dir/validation/monitor.exit_status" "Dev validation"
test -f "$run_dir/checkpoint.ckpt"
current_source_sha="$(sha256sum "$source_checkpoint" | awk '{print $1}')"
if [[ "$current_source_sha" != "$source_checkpoint_sha" ]]; then
  echo "Source checkpoint changed during continuation; refusing selection."
  exit 11
fi

if [[ -f "$run_dir/STOP_TRAINING" ]]; then
  echo "Continuation regressed and was stopped. The source checkpoint remains champion."
  exit 10
fi

# Confirm the best monitored checkpoint, never merely the latest one. If the
# untouched baseline remains best, keep using the immutable source checkpoint.
readarray -t selection < <(
  "$python_bin" - "$run_dir/validation/best_checkpoint.json" \
    "$source_checkpoint" "$source_run" "$run_dir" <<'PY'
import json
import sys
from pathlib import Path

best = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if int(best["trigger_step"]) == 0:
    print(sys.argv[2])
    print(sys.argv[3])
else:
    print(best["checkpoint"])
    print(sys.argv[4])
PY
)
candidate_checkpoint="${selection[0]}"
candidate_run="${selection[1]}"
test -f "$candidate_checkpoint"

# The confirmation script detects that this is a new checkpoint and therefore
# requires it to pass both the original and new seed protocols. A dual pass
# unlocks only the already-bounded fixed DR-0.10 stage.
export TAG_RUN_ID="${TAG_DR_RUN_ID:-holeaware_dr010_250k_$(date +%Y%m%d_%H%M%S)}"
unset TAG_LOGDIR
bash "$repo_root/scripts/confirm_nominal_then_start_dr010.sh" \
  "$candidate_checkpoint" \
  "$candidate_run" \
  "$prior_confirmation" \
  "$confirmation_root"
