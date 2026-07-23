#!/usr/bin/env bash
set -euo pipefail

if [[ "${CYBERRUNNER_TRAINING_APPROVED:-NO}" != "YES" ]]; then
  echo "Training is locked. Set CYBERRUNNER_TRAINING_APPROVED=YES only after approval."
  exit 2
fi

repo_root="${1:?Pass the absolute staged repository path as argument 1.}"
python_bin="$repo_root/.venv/bin/python"
launcher="$repo_root/scripts/run_cyberrunner_dreamerv3_gpu2.sh"
run_id="${CYBERRUNNER_RUN_ID:-multimaze_gpu2_$(date +%Y%m%d_%H%M%S)}"
launcher_log="$repo_root/${run_id}.log"
pid_file="$repo_root/${run_id}.pid"
status_file="$repo_root/${run_id}.exit_status"

test -x "$python_bin"
test -f "$launcher"
test ! -e "$pid_file"

export CYBERRUNNER_PYTHON="$python_bin"
export CYBERRUNNER_STEPS="${CYBERRUNNER_STEPS:-100000}"
export CYBERRUNNER_LOGDIR="${CYBERRUNNER_LOGDIR:-$HOME/cyberrunner_logs/$run_id}"

nohup bash -c '
  launcher="$1"
  status_file="$2"
  bash "$launcher"
  code=$?
  printf "%s\n" "$code" >"$status_file"
  exit "$code"
' _ "$launcher" "$status_file" >"$launcher_log" 2>&1 </dev/null &
pid=$!
printf '%s\n' "$pid" >"$pid_file"

echo "RUN_ID=$run_id"
echo "PID=$pid"
echo "LOG=$launcher_log"
echo "STATUS=$status_file"
echo "DREAMER_LOGDIR=$CYBERRUNNER_LOGDIR"
