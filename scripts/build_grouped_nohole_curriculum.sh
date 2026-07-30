#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python_bin="${TAG_PYTHON:-python}"
source_manifest="${TAG_NOHOLE_MANIFEST:-$repo_root/artifacts/paired_hole_curriculum/no_holes/maze_splits.json}"

"$python_bin" "$repo_root/tag_mujoco/grouped_map_curriculum.py" \
  --source-manifest "$source_manifest"

for size in 016 032 064 128 512; do
  test -f "$(dirname "$source_manifest")/maze_splits_group_${size}.json"
done

echo "Nested no-hole group manifests are ready beside $source_manifest"
