#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
output_root="${1:?Pass a new demonstration output directory as argument 1.}"
python_bin="${TAG_PYTHON:-python}"
manifest="${TAG_MANIFEST:-$repo_root/tag_mujoco/maze_splits_v2.json}"
full_start_episodes="${TAG_FULL_START_EPISODES:-128}"
random_start_episodes="${TAG_RANDOM_START_EPISODES:-64}"

test -f "$manifest"
if [[ -e "$output_root" ]] && [[ -n "$(find "$output_root" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
  echo "Demonstration output directory must be empty: $output_root"
  exit 3
fi
mkdir -p "$output_root/full_start" "$output_root/random_start"
cp "$repo_root/tag_mujoco/assumed_dynamics.json" "$output_root/assumed_dynamics.json"

"$python_bin" "$repo_root/tag_mujoco/expert_controller.py" \
  --manifest "$manifest" \
  --split train \
  --output "$output_root/full_start" \
  --episodes "$full_start_episodes" \
  --max-steps 1500 \
  --seed 20260728

"$python_bin" "$repo_root/tag_mujoco/expert_controller.py" \
  --manifest "$manifest" \
  --split train \
  --output "$output_root/random_start" \
  --episodes "$random_start_episodes" \
  --max-steps 1500 \
  --seed 20261728 \
  --random-start

echo "PLA demonstrations completed: $output_root"
