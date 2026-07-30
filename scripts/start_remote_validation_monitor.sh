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
split="${TAG_SPLIT:-validation}"
# Concurrent arms must not queue behind each other on one validation device.
canonical_gpu="${TAG_CANONICAL_GPU:-3}"
robust_gpu="${TAG_ROBUST_GPU:-4}"
policy_mode="${TAG_POLICY_MODE:-sample}"
canonical_episodes="${TAG_CANONICAL_EPISODES:-1}"
robust_strength="${TAG_ROBUST_STRENGTH:-}"
robust_groups="${TAG_ROBUST_GROUPS:-all}"
retention_manifest="${TAG_RETENTION_MANIFEST:-}"
retention_episodes="${TAG_RETENTION_EPISODES:-3}"
retention_completion_floor="${TAG_RETENTION_COMPLETION_FLOOR:-0.75}"
retention_fall_ceiling="${TAG_RETENTION_FALL_CEILING:-0.05}"
retention_actor_head="${TAG_RETENTION_ACTOR_HEAD:-}"
validation_barrier="${TAG_VALIDATION_BARRIER:-NO}"
stop_on_regression="${TAG_STOP_ON_REGRESSION:-NO}"
stop_on_plateau="${TAG_STOP_ON_PLATEAU:-NO}"
plateau_patience="${TAG_PLATEAU_PATIENCE:-3}"
min_completion_delta="${TAG_MIN_COMPLETION_DELTA:-0.01}"
min_route_delta="${TAG_MIN_ROUTE_DELTA:-0.005}"
max_fall_delta="${TAG_MAX_FALL_DELTA:-0.005}"
validation_root="$run_dir/validation"
mkdir -p "$validation_root"

launcher_log="$validation_root/monitor.log"
pid_file="$validation_root/monitor.pid"
status_file="$validation_root/monitor.exit_status"
test -x "$python_bin"
test -f "$monitor"
test -f "$manifest"
if [[ -n "$retention_manifest" ]]; then
  test -f "$retention_manifest"
fi
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
case "$stop_on_regression" in
  YES)
    stop_arg=(--stop-on-regression)
    ;;
  NO)
    stop_arg=()
    ;;
  *)
    echo "TAG_STOP_ON_REGRESSION must be YES or NO."
    exit 4
    ;;
esac
case "$stop_on_plateau" in
  YES)
    plateau_arg=(--stop-on-plateau)
    ;;
  NO)
    plateau_arg=()
    ;;
  *)
    echo "TAG_STOP_ON_PLATEAU must be YES or NO."
    exit 4
    ;;
esac
case "$validation_barrier" in
  YES) barrier_arg=(--barrier) ;;
  NO) barrier_arg=() ;;
  *) echo "TAG_VALIDATION_BARRIER must be YES or NO."; exit 4 ;;
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
  split="${12}"
  policy_mode="${13}"
  canonical_episodes="${14}"
  canonical_gpu="${15}"
  robust_gpu="${16}"
  robust_strength="${17}"
  stop_on_regression="${18}"
  stop_on_plateau="${19}"
  plateau_patience="${20}"
  min_completion_delta="${21}"
  min_route_delta="${22}"
  max_fall_delta="${23}"
  robust_groups="${24}"
  retention_manifest="${25}"
  retention_episodes="${26}"
  retention_completion_floor="${27}"
  retention_fall_ceiling="${28}"
  validation_barrier="${29}"
  retention_actor_head="${30}"
  baseline_arg=()
  if [[ "$baseline" == "YES" ]]; then
    baseline_arg=(--baseline)
  fi
  robust_strength_arg=()
  if [[ -n "$robust_strength" ]]; then
    robust_strength_arg=(
      --robust-randomization-strength "$robust_strength"
    )
  fi
  stop_arg=()
  if [[ "$stop_on_regression" == "YES" ]]; then
    stop_arg=(--stop-on-regression)
  fi
  plateau_arg=()
  if [[ "$stop_on_plateau" == "YES" ]]; then
    plateau_arg=(--stop-on-plateau)
  fi
  retention_arg=()
  if [[ -n "$retention_manifest" ]]; then
    retention_arg=(
      --retention-manifest "$retention_manifest"
      --retention-episodes-per-maze "$retention_episodes"
      --retention-completion-floor "$retention_completion_floor"
      --retention-fall-ceiling "$retention_fall_ceiling"
    )
    if [[ -n "$retention_actor_head" ]]; then
      retention_arg+=(--retention-actor-head "$retention_actor_head")
    fi
  fi
  barrier_arg=()
  if [[ "$validation_barrier" == "YES" ]]; then
    barrier_arg=(--barrier)
  fi
  "$python_bin" "$monitor" \
    --repo-root "$repo_root" \
    --run-dir "$run_dir" \
    --python "$python_bin" \
    --manifest "$manifest" \
    "${retention_arg[@]}" \
    "${barrier_arg[@]}" \
    --start-step "$start_step" \
    --interval "$interval" \
    --robust-interval "$robust_interval" \
    --end-step "$end_step" \
    "${baseline_arg[@]}" \
    --split "$split" \
    --policy-mode "$policy_mode" \
    --canonical-episodes-per-maze "$canonical_episodes" \
    --canonical-gpu "$canonical_gpu" \
    --robust-gpu "$robust_gpu" \
    --robust-episodes-per-maze 3 \
    --randomization-groups "$robust_groups" \
    "${robust_strength_arg[@]}" \
    "${stop_arg[@]}" \
    "${plateau_arg[@]}" \
    --plateau-patience "$plateau_patience" \
    --min-completion-delta "$min_completion_delta" \
    --min-route-delta "$min_route_delta" \
    --max-fall-delta "$max_fall_delta" \
    --max-steps 3000
  code=$?
  printf "%s\n" "$code" >"$status_file"
  exit "$code"
' _ "$python_bin" "$monitor" "$repo_root" "$run_dir" "$status_file" "$manifest" \
  "$start_step" "$interval" "$robust_interval" "$end_step" "$baseline" \
  "$split" "$policy_mode" "$canonical_episodes" "$canonical_gpu" "$robust_gpu" \
  "$robust_strength" "$stop_on_regression" "$stop_on_plateau" \
  "$plateau_patience" "$min_completion_delta" "$min_route_delta" "$max_fall_delta" \
  "$robust_groups" "$retention_manifest" "$retention_episodes" \
  "$retention_completion_floor" "$retention_fall_ceiling" \
  "$validation_barrier" \
  "$retention_actor_head" \
  >"$launcher_log" 2>&1 </dev/null &
pid=$!
printf '%s\n' "$pid" >"$pid_file"

echo "PID=$pid"
echo "LOG=$launcher_log"
echo "STATUS=$status_file"
echo "VALIDATION_ROOT=$validation_root"
