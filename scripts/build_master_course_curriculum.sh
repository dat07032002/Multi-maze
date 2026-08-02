#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python_bin="${TAG_PYTHON:-python}"
output_root="${TAG_MASTER_COURSE_ROOT:-$repo_root/artifacts/master_course_curriculum}"

"$python_bin" "$repo_root/tag_mujoco/master_course_generator.py" \
  --output-root "$output_root" \
  --train-per-stage "${TAG_TRAIN_PER_STAGE:-32}" \
  --validation-per-stage "${TAG_VALIDATION_PER_STAGE:-8}" \
  --test-per-stage "${TAG_TEST_PER_STAGE:-8}"

echo "Master-course curriculum: $output_root"
