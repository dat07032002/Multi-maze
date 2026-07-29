#!/usr/bin/env bash
set -euo pipefail

if [[ "${TAG_TRAINING_APPROVED:-NO}" != "YES" ]]; then
  echo "Set TAG_TRAINING_APPROVED=YES before launching curriculum DR."
  exit 2
fi

echo "Curriculum DR launcher is locked: the v3 run imported non-finite replay"
echo "and its process-local curriculum could not advance."
echo "Run scripts/start_clean_training_smoke.sh first."
exit 3
