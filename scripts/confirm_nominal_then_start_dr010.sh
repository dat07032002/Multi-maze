#!/usr/bin/env bash
set -euo pipefail

if [[ "${TAG_TRAINING_APPROVED:-NO}" != "YES" ]] ||
   [[ "${TAG_VALIDATION_APPROVED:-NO}" != "YES" ]]; then
  echo "Set TAG_TRAINING_APPROVED=YES and TAG_VALIDATION_APPROVED=YES."
  exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
checkpoint="${1:?Pass the accepted nominal checkpoint as argument 1.}"
source_run="${2:?Pass its source training directory as argument 2.}"
first_confirmation="${3:?Pass the first 192-episode evaluation as argument 3.}"
confirmation_root="${4:?Pass a new confirmation output directory as argument 4.}"
python_bin="${TAG_PYTHON:-python}"
manifest="${TAG_MANIFEST:-$repo_root/tag_mujoco/maze_splits_v2.json}"
confirmation_seed="${TAG_CONFIRMATION_SEED:-20260729}"
run_id="${TAG_RUN_ID:-holeaware_dr010_250k_$(date +%Y%m%d_%H%M%S)}"
run_dir="${TAG_LOGDIR:-$HOME/cyberrunner_logs/$run_id}"
source_config="$source_run/config.yaml"
source_contract="$source_run/policy_contract.json"

test -f "$checkpoint"
test -f "$source_config"
test -f "$source_contract"
test -f "$first_confirmation"
test -f "$manifest"
if [[ -e "$confirmation_root" ]] &&
   [[ -n "$(find "$confirmation_root" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
  echo "Confirmation output directory must be empty: $confirmation_root"
  exit 3
fi
test ! -e "$run_dir"
mkdir -p "$confirmation_root"
sha256sum "$checkpoint" >"$confirmation_root/accepted_checkpoint.sha256"
cp "$repo_root/tag_mujoco/assumed_dynamics.json" \
  "$confirmation_root/assumed_dynamics.json"

read -r first_seed first_matches < <(
  "$python_bin" - "$first_confirmation" "$checkpoint" "$confirmation_seed" <<'PY'
import hashlib
import json
import sys
first_path, checkpoint_path, seed = sys.argv[1], sys.argv[2], int(sys.argv[3])
first = json.load(open(first_path, encoding="utf-8"))
if not first.get("completed"):
    raise SystemExit("The first nominal confirmation is incomplete.")
if int(first["summary"]["episodes"]) < 192:
    raise SystemExit("The first nominal confirmation has fewer than 192 episodes.")
if int(first["seed"]) == seed:
    raise SystemExit("The second confirmation must use a different base seed.")
digest = hashlib.sha256()
with open(checkpoint_path, "rb") as stream:
    for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
        digest.update(chunk)
print(int(first["seed"]), str(first["checkpoint_sha256"] == digest.hexdigest()).lower())
PY
)

run_confirmation() {
  local seed="$1"
  local output="$2"
  local log="$3"
  CUDA_VISIBLE_DEVICES="${TAG_CANONICAL_GPU:-3}" \
  XLA_PYTHON_CLIENT_PREALLOCATE=false \
  MUJOCO_GL=egl \
  PYTHONUNBUFFERED=1 \
    "$python_bin" "$repo_root/dreamerv3/dreamerv3/eval_multimaze.py" \
      --checkpoint "$checkpoint" \
      --config "$source_config" \
      --manifest "$manifest" \
      --split validation \
      --mode canonical \
      --episodes-per-maze 3 \
      --max-steps 3000 \
      --seed "$seed" \
      --policy-mode sample \
      --trigger-step 500000 \
      --output "$output" \
      >"$log" 2>&1
}

check_mastery() {
  local baseline="$1"
  local candidate="$2"
  local output="$3"
  local log="$4"
  "$python_bin" "$repo_root/tag_mujoco/nominal_training_gate.py" \
    --baseline "$baseline" \
    --candidate "$candidate" \
    --minimum-mastery-episodes 192 \
    --output "$output" \
    >"$log" 2>&1
  "$python_bin" - "$output" <<'PY'
import json
import sys
decision = json.load(open(sys.argv[1], encoding="utf-8"))
if not decision["passed"]:
    raise SystemExit("Nominal confirmation failed; DR-0.10 remains locked.")
PY
}

gate_baseline="$first_confirmation"
if [[ "$first_matches" != "true" ]]; then
  # Never transfer a pass to checkpoint bytes that were saved later.
  printf '%s\n' \
    "First confirmation hash does not match the current checkpoint." \
    "Re-evaluating the current checkpoint at seed $first_seed before the new seed." \
    >"$confirmation_root/checkpoint_mismatch.txt"
  original_seed_result="$confirmation_root/canonical192_seed${first_seed}.json"
  run_confirmation \
    "$first_seed" \
    "$original_seed_result" \
    "$confirmation_root/canonical192_seed${first_seed}.log"
  check_mastery \
    "$first_confirmation" \
    "$original_seed_result" \
    "$confirmation_root/gate_seed${first_seed}.json" \
    "$confirmation_root/gate_seed${first_seed}.log"
  gate_baseline="$original_seed_result"
fi

run_confirmation \
  "$confirmation_seed" \
  "$confirmation_root/canonical192.json" \
  "$confirmation_root/canonical192.log"
check_mastery \
  "$gate_baseline" \
  "$confirmation_root/canonical192.json" \
  "$confirmation_root/gate_decision.json" \
  "$confirmation_root/gate.log"

printf '%s\n' \
  "Second nominal confirmation passed at seed $confirmation_seed." \
  "Accepted checkpoint: $checkpoint" \
  "Launching bounded fixed-strength DR-0.10 run: $run_dir" \
  >"$confirmation_root/unlock.txt"

export TAG_TRAINING_VARIANT=v2
export TAG_TRAINING_PROFILE=tag_sim_v2_holeaware_dr010
export TAG_CHECKPOINT_MODE=agent_only
export TAG_FROM_CHECKPOINT="$checkpoint"
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
    echo "DR-0.10 training exited before writing config.yaml: $code"
    exit 5
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
    "plant randomization enabled": env["randomize_plant"],
    "fixed strength starts at 0.10": env["randomization_initial_strength"] == 0.10,
    "strength expansion disabled": env["randomization_expand_step"] == 0.0,
    "hole margin retained": env["hole_clearance_penalty"] == 0.02,
}
failed = [name for name, passed in checks.items() if not passed]
if failed:
    raise SystemExit("Invalid DR-0.10 config: " + ", ".join(failed))
PY

export TAG_START_STEP=250000
export TAG_INTERVAL=250000
export TAG_ROBUST_INTERVAL=250000
export TAG_END_STEP=250000
export TAG_BASELINE=NO
export TAG_SPLIT=validation
export TAG_POLICY_MODE=sample
export TAG_CANONICAL_EPISODES=3
export TAG_ROBUST_STRENGTH=0.10
export TAG_CANONICAL_GPU="${TAG_CANONICAL_GPU:-3}"
export TAG_ROBUST_GPU="${TAG_ROBUST_GPU:-4}"
bash "$repo_root/scripts/start_remote_validation_monitor.sh" \
  "$repo_root" "$run_dir"

echo "Second confirmation passed and bounded DR-0.10 started."
echo "RUN_DIR=$run_dir"
