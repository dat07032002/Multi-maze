#!/usr/bin/env bash
set -euo pipefail

if [[ "${TAG_VALIDATION_APPROVED:-NO}" != "YES" ]]; then
  echo "PLA baseline evaluation is locked. Set TAG_VALIDATION_APPROVED=YES."
  exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
checkpoint="${1:?Pass the existing v2 checkpoint as argument 1.}"
output_root="${2:?Pass a new output directory as argument 2.}"
python_bin="${TAG_PYTHON:-python}"
manifest="${TAG_MANIFEST:-$repo_root/tag_mujoco/maze_splits_v2.json}"
config="${TAG_CONFIG:-$(dirname "$checkpoint")/config.yaml}"
trigger_step="${TAG_TRIGGER_STEP:-13000000}"

test -f "$checkpoint"
test -f "$config"
test -f "$manifest"
if [[ -e "$output_root" ]] && [[ -n "$(find "$output_root" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
  echo "Baseline output directory must be empty: $output_root"
  exit 3
fi
mkdir -p "$output_root"

cp "$repo_root/tag_mujoco/assumed_dynamics.json" "$output_root/assumed_dynamics.json"
sha256sum "$checkpoint" >"$output_root/checkpoint.sha256"
sha256sum "$repo_root/tag_mujoco/assumed_dynamics.json" \
  >"$output_root/assumed_dynamics.sha256"

run_eval() {
  local mode="$1"
  local episodes="$2"
  local gpu="$3"
  CUDA_VISIBLE_DEVICES="$gpu" \
  XLA_PYTHON_CLIENT_PREALLOCATE=false \
  MUJOCO_GL=egl \
  PYTHONUNBUFFERED=1 \
    "$python_bin" "$repo_root/dreamerv3/dreamerv3/eval_multimaze.py" \
      --checkpoint "$checkpoint" \
      --config "$config" \
      --manifest "$manifest" \
      --split validation \
      --mode "$mode" \
      --episodes-per-maze "$episodes" \
      --max-steps 3000 \
      --seed 20260723 \
      --trigger-step "$trigger_step" \
      --output "$output_root/$mode.json" \
      >"$output_root/$mode.log" 2>&1
}

run_eval canonical 1 3 &
canonical_pid=$!
run_eval robust 3 4 &
robust_pid=$!

set +e
wait "$canonical_pid"
canonical_status=$?
wait "$robust_pid"
robust_status=$?
set -e
printf '%s\n' "$canonical_status" >"$output_root/canonical.exit_status"
printf '%s\n' "$robust_status" >"$output_root/robust.exit_status"

if (( canonical_status != 0 || robust_status != 0 )); then
  echo "PLA baseline failed: canonical=$canonical_status robust=$robust_status"
  exit 4
fi
echo "PLA baseline completed: $output_root"
