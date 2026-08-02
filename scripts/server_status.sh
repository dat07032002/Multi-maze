#!/usr/bin/env bash
# Compact training-server status. Read-only: starts and stops nothing.
#
# Answers, in one round trip, the questions that otherwise take a dozen ad hoc
# SSH calls: is anything training, which GPUs are busy, what was the most recent
# run, how far did it get, and why did it stop.
#
#   bash scripts/server_status.sh            # latest run
#   bash scripts/server_status.sh <run_id>   # a specific run
#   TAG_STATUS_RUNS=5 bash scripts/server_status.sh   # list more recent runs
set -euo pipefail

host="${TAG_SERVER:-tn22833@aere-a83514.ae.utexas.edu}"
key="${TAG_SSH_KEY:-$HOME/.ssh/aere_codex_ed25519}"
logs="${TAG_SERVER_LOGS:-/home/tn22833/cyberrunner_logs}"
python_bin="${TAG_SERVER_PYTHON:-/home/tn22833/TAG_dreamerv3_smoke_20260723/.venv/bin/python}"
runs="${TAG_STATUS_RUNS:-5}"
want_run="${1:-}"

ssh -i "$key" -o BatchMode=yes -o ConnectTimeout=20 "$host" \
  RUN="$want_run" LOGS="$logs" PY="$python_bin" RUNS="$runs" 'bash -s' <<'REMOTE'
set -uo pipefail

echo "=== processes ==="
# Summarize rather than print argv. The validation launcher is a several
# thousand character bash -c, and dumping it buries everything else.
summarize() {
  local label="$1" pattern="$2" found=0
  while read -r pid rest; do
    [ -z "$pid" ] && continue
    # Prefer the run id over the full command line.
    run=$(sed -n 's;.*cyberrunner_logs/\([A-Za-z0-9_.-]*\).*;\1;p' <<<"$rest" | head -1)
    age=$(ps -p "$pid" -o etimes= 2>/dev/null | tr -d ' ')
    printf "  %-11s pid %-8s %5ss  %s\n" "$label" "$pid" "${age:-?}" "${run:-unknown run}"
    found=1
  done < <(pgrep -af "$pattern" 2>/dev/null | grep -v 'bash -c' || true)
  [ "$found" -eq 0 ] && printf "  %-11s none\n" "$label"
  return 0
}
summarize training '[d]reamerv3/dreamerv3/train.py'
summarize monitor '[v]alidation_monitor.py'
summarize evaluating '[e]val_multimaze.py'

echo
echo "=== gpus (0 is another user, never ours) ==="
nvidia-smi --query-gpu=index,utilization.gpu,memory.used,memory.total \
  --format=csv,noheader | sed 's/^/  gpu /'

echo
echo "=== recent runs ==="
ls -1t "$LOGS" 2>/dev/null | head -n "$RUNS" | sed 's/^/  /'

run="$RUN"
[ -z "$run" ] && run=$(ls -1t "$LOGS" 2>/dev/null | head -1)
[ -z "$run" ] && { echo; echo "no runs found"; exit 0; }
d="$LOGS/$run"

echo
echo "=== $run ==="
[ -f "$d/STOP_TRAINING" ] && echo "STOPPED: $(cat "$d/STOP_TRAINING")"
[ -f "$d/training_health.json" ] && \
  echo "health: $(grep -o '"status"[^,]*' "$d/training_health.json" | head -1)"

# metrics.jsonl rows carry ~300 fields each. Project, never dump.
"$PY" - "$d" <<'PY'
import json, os, sys
d = sys.argv[1]

m = os.path.join(d, "metrics.jsonl")
if os.path.isfile(m):
    rows = []
    for line in open(m, encoding="utf-8"):
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    if rows:
        last = rows[-1]
        step = last.get("step")
        target = last.get("run/target_step")
        print(f"step: {step}" + (f" / {int(target)}" if target else ""))
        eps = [r for r in rows if "episode/score" in r]
        def col(key):
            return [r[key] for r in rows if isinstance(r.get(key), (int, float))]
        for label, key in (
            ("path_cost", "stats/mean_log_path_cost"),
            ("score", "episode/score"),
            ("progress", "stats/mean_log_progress"),
        ):
            v = col(key)
            if v:
                print(f"{label:>9}: mean {sum(v)/len(v):>9.4f}  "
                      f"min {min(v):>9.4f}  max {max(v):>9.4f}  n={len(v)}")
        wins = sum(1 for r in eps if r.get("stats/sum_log_success"))
        if eps:
            print(f"successes: {wins}/{len(eps)} episodes")

h = os.path.join(d, "validation", "history.jsonl")
if os.path.isfile(h):
    print("validation:")
    for line in open(h, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        print(f"  step {r['trigger_step']:>8}  "
              f"complete {r['completion_rate']:.3f}  "
              f"falls {r['fall_rate']:.3f}  "
              f"progress {r['mean_max_route_completion']:.4f}  "
              f"ckpt {str(r.get('checkpoint_sha256', ''))[:10]}")

p = os.path.join(d, "validation", "plateau_state.json")
if os.path.isfile(p):
    s = json.load(open(p, encoding="utf-8"))
    print(f"plateau: {s.get('plateaued')}  stale {s.get('stale_count')}"
          f"/{s.get('patience')}  best step {s.get('best_trigger_step')}")
PY
REMOTE
