#!/usr/bin/env bash
# Launch one bounded nominal A/B arm and validate it on the dev split.
#
# The mastery gate is measured on the validation split. Choosing between tuning
# arms from validation feedback would overfit the split that decides the gate,
# so each arm is ranked on the dev subset of the training layouts instead. Dev
# scores are optimistic because the policy trains on those layouts; they are
# only meaningful relative to the other arms and to this arm's own step-0
# baseline, which the monitor records before training changes anything.
set -euo pipefail

if [[ "${TAG_TRAINING_APPROVED:-NO}" != "YES" ]] ||
   [[ "${TAG_VALIDATION_APPROVED:-NO}" != "YES" ]]; then
  echo "Set both TAG_TRAINING_APPROVED=YES and TAG_VALIDATION_APPROVED=YES."
  exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
profile="${1:?Pass the training profile as argument 1.}"
source_checkpoint="${2:?Pass the frozen source checkpoint as argument 2.}"
python_bin="${TAG_PYTHON:-python}"
steps="${TAG_STEPS:-500000}"
policy_mode="${TAG_POLICY_MODE:-mode}"
# Concurrent arms need distinct training and validation devices.
train_gpu="${TAG_TRAIN_GPU:-2}"
canonical_gpu="${TAG_CANONICAL_GPU:-3}"
run_id="${TAG_RUN_ID:-ab_${profile#tag_sim_v2_}_$(date +%Y%m%d_%H%M%S)}"
run_dir="${TAG_LOGDIR:-$HOME/cyberrunner_logs/$run_id}"

case "$profile" in
  tag_sim_v2_nominal_*) ;;
  *)
    echo "Refusing to launch $profile: A/B arms must be nominal profiles."
    echo "Domain randomization stays locked until the mastery gate passes."
    exit 3
    ;;
esac

test -f "$source_checkpoint"
test ! -e "$run_dir"

# Every arm must load agent weights only, so all arms start from the same policy
# at step zero with a fresh replay buffer holding only its own transitions.
export TAG_TRAINING_VARIANT=v2
export TAG_TRAINING_PROFILE="$profile"
export TAG_CHECKPOINT_MODE=agent_only
export TAG_FROM_CHECKPOINT="$source_checkpoint"
unset TAG_DEMO_DIR
export TAG_STEPS="$steps"
export TAG_RUN_ID="$run_id"
export TAG_LOGDIR="$run_dir"
export TAG_PYTHON="$python_bin"
export TAG_TRAIN_GPU="$train_gpu"

if [[ "$train_gpu" == "$canonical_gpu" ]]; then
  echo "Training and canonical validation cannot share GPU $train_gpu."
  exit 4
fi

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
sha256sum "$source_checkpoint" >"$run_dir/source_checkpoint.sha256"
printf '%s\n' "$profile" >"$run_dir/ab_profile.txt"

# Confirm the arm actually disabled domain randomization and random starts. A
# silently randomized arm would not be comparable to the other arms.
"$python_bin" - "$run_dir/config.yaml" <<'PY'
import sys

import ruamel.yaml as yaml

config = yaml.YAML(typ="safe").load(open(sys.argv[1], encoding="utf-8"))
tagmaze = config["env"]["tagmaze"]
for key in ("randomize_plant", "randomization_curriculum", "random_start", "start_curriculum"):
    if tagmaze[key]:
        raise SystemExit(f"Nominal arm must disable {key}")
print(
    "Nominal arm confirmed: "
    f"train_ratio={config['run']['train_ratio']} "
    f"failure_penalty={tagmaze['failure_penalty']} "
    f"action_rate_penalty={tagmaze['action_rate_penalty']} "
    f"plr_uniform_mix={tagmaze['plr_uniform_mix']} plr_ema={tagmaze['plr_ema']}"
)
PY

export TAG_MANIFEST="$repo_root/tag_mujoco/maze_splits_v2.json"
export TAG_SPLIT=dev
export TAG_POLICY_MODE="$policy_mode"
export TAG_CANONICAL_EPISODES=1
export TAG_START_STEP=250000
export TAG_INTERVAL=250000
# Larger than the bounded run, so no robust evaluation is scheduled while the
# nominal phase is still being optimized.
export TAG_ROBUST_INTERVAL=1000000000
export TAG_END_STEP="$steps"
# Record this arm's own step-zero dev score before training changes anything.
export TAG_BASELINE=YES
export TAG_CANONICAL_GPU="$canonical_gpu"
bash "$repo_root/scripts/start_remote_validation_monitor.sh" \
  "$repo_root" "$run_dir"

echo "Nominal A/B arm launched."
echo "PROFILE=$profile"
echo "TRAIN_GPU=$train_gpu CANONICAL_GPU=$canonical_gpu"
echo "RUN_ID=$run_id"
echo "RUN_DIR=$run_dir"
echo "POLICY_MODE=$policy_mode"
echo "TRAINING_STATUS=$training_status"
echo "VALIDATION_STATUS=$run_dir/validation/monitor.exit_status"
