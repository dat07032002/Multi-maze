#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python_bin="${TAG_PYTHON:-python}"
output_root="${TAG_CURRICULUM_ROOT:-$repo_root/artifacts/paired_hole_curriculum}"

"$python_bin" "$repo_root/tag_mujoco/paired_hole_curriculum.py" \
  --output-root "$output_root"

for variant in no_holes branch_holes easy_dodge mixed_holes; do
  test -f "$output_root/$variant/maze_splits.json"
done

echo "Paired curriculum datasets are ready at $output_root"
