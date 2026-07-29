#!/usr/bin/env bash
set -euo pipefail

repo_root="${1:?Pass the staged repository as argument 1.}"
run_dir="${2:?Pass the training run directory as argument 2.}"
python_bin="${TAG_PYTHON:-python}"
steps="${TAG_ATTRIBUTION_STEPS:-50000 100000}"
poll_seconds="${TAG_ATTRIBUTION_POLL_SECONDS:-30}"
output_root="$run_dir/dr_attribution"
pid_file="$output_root/monitor.pid"
status_file="$output_root/monitor.exit_status"
log_file="$output_root/monitor.log"

test -d "$run_dir"
test -f "$run_dir/config.yaml"
test -x "$python_bin"
mkdir -p "$output_root"
test ! -e "$pid_file"

nohup bash -c '
  repo_root="$1"
  run_dir="$2"
  python_bin="$3"
  steps="$4"
  poll_seconds="$5"
  status_file="$6"
  for step in $steps; do
    padded="$(printf "%09d" "$step")"
    checkpoint="$run_dir/validation/step_$padded/checkpoint.ckpt"
    while [[ ! -f "$checkpoint" ]]; do
      sleep "$poll_seconds"
    done
    TAG_PYTHON="$python_bin" \
    TAG_ATTRIBUTION_GPU="${TAG_ATTRIBUTION_GPU:-3}" \
    TAG_ATTRIBUTION_STRENGTH="${TAG_ATTRIBUTION_STRENGTH:-0.25}" \
      bash "$repo_root/scripts/run_dr_attribution.sh" \
        "$checkpoint" \
        "$run_dir/config.yaml" \
        "$run_dir/dr_attribution/step_$padded" \
        "$step"
  done
  printf "0\n" >"$status_file"
' _ "$repo_root" "$run_dir" "$python_bin" "$steps" "$poll_seconds" \
  "$status_file" >"$log_file" 2>&1 </dev/null &
pid=$!
printf '%s\n' "$pid" >"$pid_file"

echo "PID=$pid"
echo "LOG=$log_file"
echo "STATUS=$status_file"
