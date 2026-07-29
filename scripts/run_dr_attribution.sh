#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
checkpoint="${1:?Pass a checkpoint as argument 1.}"
config="${2:?Pass its resolved config.yaml as argument 2.}"
output_dir="${3:?Pass a new output directory as argument 3.}"
trigger_step="${4:?Pass the checkpoint trigger step as argument 4.}"
python_bin="${TAG_PYTHON:-python}"
manifest="${TAG_MANIFEST:-$repo_root/tag_mujoco/maze_splits_v2.json}"
strength="${TAG_ATTRIBUTION_STRENGTH:-0.25}"
episodes="${TAG_ATTRIBUTION_EPISODES_PER_MAZE:-1}"
seed="${TAG_ATTRIBUTION_SEED:-20260731}"
gpu="${TAG_ATTRIBUTION_GPU:-3}"

test -f "$checkpoint"
test -f "$config"
test -f "$manifest"
test ! -e "$output_dir"
mkdir -p "$output_dir"

evaluate() {
  local mode="$1"
  local group="$2"
  local output="$output_dir/$group.json"
  local args=(
    --checkpoint "$checkpoint"
    --config "$config"
    --manifest "$manifest"
    --split dev
    --mode "$mode"
    --episodes-per-maze "$episodes"
    --max-steps 3000
    --seed "$seed"
    --policy-mode sample
    --trigger-step "$trigger_step"
    --output "$output"
  )
  if [[ "$mode" == "robust" ]]; then
    args+=(--randomization-strength "$strength")
    args+=(--randomization-groups "$group")
  fi
  CUDA_VISIBLE_DEVICES="$gpu" \
  XLA_PYTHON_CLIENT_PREALLOCATE=false \
  MUJOCO_GL=egl \
  PYTHONUNBUFFERED=1 \
    "$python_bin" "$repo_root/dreamerv3/dreamerv3/eval_multimaze.py" \
      "${args[@]}" >"$output_dir/$group.log" 2>&1
}

evaluate canonical canonical
evaluate robust all
evaluate robust actuator
evaluate robust physics
evaluate robust camera

"$python_bin" "$repo_root/tag_mujoco/dr_attribution.py" \
  --input \
    "$output_dir/canonical.json" \
    "$output_dir/all.json" \
    "$output_dir/actuator.json" \
    "$output_dir/physics.json" \
    "$output_dir/camera.json" \
  --output "$output_dir/report.json" \
  >"$output_dir/report.log" 2>&1

echo "DR attribution complete: $output_dir/report.json"
