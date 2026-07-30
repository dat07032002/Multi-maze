#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python_bin="${TAG_PYTHON:-python}"
skill_root="${TAG_SKILL_ROOT:-$repo_root/artifacts/universal_skills}"
map_root="${TAG_SEQUENTIAL_ROOT:-$repo_root/artifacts/sequential_maps}"
paired_root="${TAG_CURRICULUM_ROOT:-$repo_root/artifacts/paired_hole_curriculum}"
source_manifest="${TAG_SOURCE_MANIFEST:-$paired_root/no_holes/maze_splits.json}"

if [[ -z "${TAG_SOURCE_MANIFEST:-}" && ! -f "$source_manifest" ]]; then
  TAG_PYTHON="$python_bin" TAG_CURRICULUM_ROOT="$paired_root" \
    bash "$repo_root/scripts/build_paired_hole_curriculum.sh"
fi
test -f "$source_manifest"
"$python_bin" "$repo_root/tag_mujoco/skill_course_generator.py" \
  --output-root "$skill_root"
"$python_bin" "$repo_root/tag_mujoco/sequential_map_curriculum.py" \
  --source-manifest "$source_manifest" \
  --output-root "$map_root"

echo "Skill datasets: $skill_root"
echo "Sequential maps: $map_root"
