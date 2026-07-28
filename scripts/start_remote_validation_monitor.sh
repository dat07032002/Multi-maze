#!/usr/bin/env bash
set -euo pipefail

if [[ "${TAG_VALIDATION_APPROVED:-NO}" != "YES" ]]; then
  echo "Validation is locked. Set TAG_VALIDATION_APPROVED=YES after approval."
  exit 2
fi

repo_root="${1:?Pass the absolute staged repository path as argument 1.}"
run_dir="${2:?Pass the absolute Dreamer production log directory as argument 2.}"
python_bin="${TAG_PYTHON:-$repo_root/.venv/bin/python}"
monitor="$repo_root/tag_mujoco/validation_monitor.py"
manifest="${TAG_MANIFEST:-$repo_root/tag_mujoco/maze_splits.json}"
start_step="${TAG_START_STEP:-500000}"
interval="${TAG_INTERVAL:-500000}"
robust_interval="${TAG_ROBUST_INTERVAL:-1000000}"
end_step="${TAG_END_STEP:-10000000}"
baseline="${TAG_BASELINE:-YES}"
validation_root="$run_dir/validation"
mkdir -p "$validation_root"

launcher_log="$validation_root/monitor.log"
pid_file="$validation_root/monitor.pid"
status_file="$validation_root/monitor.exit_status"
test -x "$python_bin"
test -f "$monitor"
test -f "$manifest"
case "$baseline" in
  YES)
    baseline_arg=(--baseline)
    ;;
  NO)
    baseline_arg=()
    ;;
  *)
    echo "TAG_BASELINE must be YES or NO."
    exit 4
    ;;
esac
if [[ -e "$pid_file" ]]; then
  previous_pid="$(cat "$pid_file")"
  if kill -0 "$previous_pid" 2>/dev/null; then
    echo "Validation monitor is already running as PID $previous_pid."
    exit 3
  fi
  archive_stamp="$(date +%Y%m%d_%H%M%S)"
  mv "$pid_file" "$pid_file.failed_$archive_stamp"
  if [[ -e "$status_file" ]]; then
    mv "$status_file" "$status_file.failed_$archive_stamp"
  fi
fi

nohup bash -c '
  python_bin="$1"
  monitor="$2"
  repo_root="$3"
  run_dir="$4"
  status_file="$5"
  manifest="$6"
  start_step="$7"
  interval="$8"
  robust_interval="$9"
  end_step="${10}"
  baseline="${11}"
  baseline_arg=()
  if [[ "$baseline" == "YES" ]]; then
    baseline_arg=(--baseline)
  fi
  "$python_bin" "$monitor" \
    --repo-root "$repo_root" \
    --run-dir "$run_dir" \
    --python "$python_bin" \
    --manifest "$manifest" \
    --start-step "$start_step" \
    --interval "$interval" \
    --robust-interval "$robust_interval" \
    --end-step "$end_step" \
    "${baseline_arg[@]}" \
    --canonical-gpu 3 \
    --robust-gpu 4 \
    --robust-episodes-per-maze 3 \
    --max-steps 3000
  code=$?
  printf "%s\n" "$code" >"$status_file"
  exit "$code"
' _ "$python_bin" "$monitor" "$repo_root" "$run_dir" "$status_file" "$manifest" \
  "$start_step" "$interval" "$robust_interval" "$end_step" "$baseline" \
  >"$launcher_log" 2>&1 </dev/null &
pid=$!
printf '%s\n' "$pid" >"$pid_file"

echo "PID=$pid"
echo "LOG=$launcher_log"
echo "STATUS=$status_file"
echo "VALIDATION_ROOT=$validation_root"
