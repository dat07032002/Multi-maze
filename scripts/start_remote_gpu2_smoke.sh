#!/usr/bin/env bash
set -euo pipefail

if [[ "${TAG_TRAINING_APPROVED:-NO}" != "YES" ]]; then
  echo "Training is locked. Set TAG_TRAINING_APPROVED=YES only after approval."
  exit 2
fi

repo_root="${1:?Pass the absolute staged repository path as argument 1.}"
python_bin="$repo_root/.venv/bin/python"
launcher="$repo_root/scripts/run_tag_dreamerv3_gpu2.sh"
launcher_log="$repo_root/smoke_gpu2_launcher.log"
pid_file="$repo_root/smoke_gpu2.pid"

test -x "$python_bin"
test -f "$launcher"

export TAG_PYTHON="$python_bin"
export TAG_STEPS="${TAG_STEPS:-10000}"

nohup bash "$launcher" >"$launcher_log" 2>&1 </dev/null &
pid=$!
printf '%s\n' "$pid" >"$pid_file"

echo "PID=$pid"
echo "LOG=$launcher_log"
