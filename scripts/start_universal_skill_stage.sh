#!/usr/bin/env bash
set -euo pipefail

if [[ "${TAG_TRAINING_APPROVED:-NO}" != "YES" ]] ||
   [[ "${TAG_VALIDATION_APPROVED:-NO}" != "YES" ]]; then
  echo "Set TAG_TRAINING_APPROVED=YES and TAG_VALIDATION_APPROVED=YES."
  exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
family="${1:?Pass stabilize, stabilize_retention, straight, straight_retention, straight_head, turn, turn_head, compound, recovery, hazard, or actuator025.}"
source_checkpoint="${2:-}"
source_run="${3:-}"
rehearsal="${4:-}"
python_bin="${TAG_PYTHON:-$repo_root/.venv/bin/python}"
skill_root="${TAG_SKILL_ROOT:-$repo_root/artifacts/universal_skills}"

case "$family" in
  stabilize) profile=tag_sim_v3_skill_stabilize; manifest_family=stabilize; steps=100000; interval=25000; previous= ;;
  stabilize_retention) profile=tag_sim_v3_skill_stabilize_retention; manifest_family=stabilize; steps=100000; interval=25000; previous=stabilize ;;
  straight) profile=tag_sim_v3_skill_straight; manifest_family=straight; steps=200000; interval=50000; previous=stabilize ;;
  straight_retention) profile=tag_sim_v3_skill_straight_retention; manifest_family=straight; steps=200000; interval=25000; previous=stabilize ;;
  straight_head) profile=tag_sim_v3_skill_straight_head; manifest_family=straight; steps=200000; interval=25000; previous=stabilize ;;
  turn) profile=tag_sim_v3_skill_turn; manifest_family=turn; steps=250000; interval=50000; previous=straight ;;
  turn_head) profile=tag_sim_v3_skill_turn_head; manifest_family=turn; steps=250000; interval=25000; previous=stabilize ;;
  compound) profile=tag_sim_v3_skill_compound; manifest_family=compound; steps=300000; interval=50000; previous=turn ;;
  recovery) profile=tag_sim_v3_skill_recovery; manifest_family=recovery; steps=250000; interval=50000; previous=compound ;;
  hazard) profile=tag_sim_v3_skill_hazard; manifest_family=hazard; steps=400000; interval=100000; previous=recovery ;;
  actuator025) profile=tag_sim_v3_skill_actuator025; manifest_family=compound; steps=10000; interval=5000; previous=hazard ;;
  *) echo "Unknown skill family: $family"; exit 3 ;;
esac

validation_interval="${TAG_VALIDATION_INTERVAL:-$interval}"
if [[ "$family" == "straight_retention" || "$family" == "straight_head" || "$family" == "turn_head" ]]; then
  export TAG_VALIDATION_BARRIER_INTERVAL="$validation_interval"
else
  unset TAG_VALIDATION_BARRIER_INTERVAL
fi

manifest="$skill_root/$manifest_family/maze_splits.json"
test -f "$manifest"
grep -q "tag_universal_skill_${manifest_family}_v1" "$manifest"
export TAG_MANIFEST="$manifest"

if [[ "$family" == "stabilize" ]]; then
  if [[ -n "$rehearsal" ]]; then
    echo "Stabilize continuation does not use cross-stage rehearsal."
    exit 4
  fi
  if [[ -n "$source_checkpoint" || -n "$source_run" ]]; then
    test -f "$source_checkpoint"
    test -f "$source_run/policy_contract.json"
    export TAG_FROM_CHECKPOINT="$source_checkpoint"
    export TAG_CHECKPOINT_CONTRACT="$source_run/policy_contract.json"
    export TAG_CHECKPOINT_DATASET_ID="tag_universal_skill_stabilize_v1"
    export TAG_CHECKPOINT_MODE=agent_only
    unset TAG_DEMO_DIR
  else
    unset TAG_FROM_CHECKPOINT TAG_CHECKPOINT_CONTRACT TAG_CHECKPOINT_DATASET_ID TAG_DEMO_DIR
    export TAG_CHECKPOINT_MODE=none
  fi
elif [[ "$family" == "straight_head" || "$family" == "turn_head" ]]; then
  test -f "$source_checkpoint"
  test -f "$source_run/policy_contract.json"
  export TAG_FROM_CHECKPOINT="$source_checkpoint"
  export TAG_CHECKPOINT_CONTRACT="$source_run/policy_contract.json"
  export TAG_CHECKPOINT_DATASET_ID="tag_universal_skill_stabilize_v1"
  export TAG_CHECKPOINT_MODE=multihead_init
  unset TAG_DEMO_DIR TAG_DEMO_LIMIT_STEPS TAG_DEMO_SAMPLING
else
  test -f "$source_checkpoint"
  test -f "$source_run/policy_contract.json"
  test -d "$rehearsal"
  export TAG_FROM_CHECKPOINT="$source_checkpoint"
  export TAG_CHECKPOINT_CONTRACT="$source_run/policy_contract.json"
  export TAG_CHECKPOINT_DATASET_ID="tag_universal_skill_${previous}_v1"
  if [[ "$family" == "actuator025" ]]; then
    export TAG_CHECKPOINT_DATASET_ID="tag_universal_skill_hazard_v1"
  fi
  export TAG_CHECKPOINT_MODE=agent_only
  export TAG_DEMO_DIR="$rehearsal"
  export TAG_DEMO_LIMIT_STEPS="${TAG_DEMO_LIMIT_STEPS:-50000}"
  export TAG_DEMO_SAMPLING=uniform_chunks
fi

stamp="$(date +%Y%m%d_%H%M%S)"
run_id="${TAG_RUN_ID:-skill_${family}_${stamp}}"
run_dir="${TAG_LOGDIR:-$HOME/cyberrunner_logs/$run_id}"
test ! -e "$run_dir"

export TAG_TRAINING_VARIANT=v2
export TAG_TRAINING_PROFILE="$profile"
export TAG_STEPS="${TAG_STEPS:-$steps}"
export TAG_RUN_ID="$run_id"
export TAG_LOGDIR="$run_dir"
export TAG_PYTHON="$python_bin"
bash "$repo_root/scripts/start_remote_gpu2_training.sh" "$repo_root"

training_status="$repo_root/$run_id.exit_status"
while [[ ! -f "$run_dir/config.yaml" ]]; do
  if [[ -f "$training_status" ]]; then
    echo "Training exited before writing config.yaml."
    exit 5
  fi
  sleep 5
done

export TAG_START_STEP="$validation_interval"
export TAG_INTERVAL="$validation_interval"
if [[ "$family" == "actuator025" ]]; then
  export TAG_ROBUST_INTERVAL="$TAG_STEPS"
  export TAG_ROBUST_STRENGTH=0.025
  export TAG_ROBUST_GROUPS=actuator
else
  export TAG_ROBUST_INTERVAL=100000000
  unset TAG_ROBUST_STRENGTH TAG_ROBUST_GROUPS
fi
export TAG_END_STEP="$TAG_STEPS"
export TAG_BASELINE=YES
export TAG_SPLIT=validation
export TAG_POLICY_MODE=sample
export TAG_CANONICAL_EPISODES="${TAG_CANONICAL_EPISODES:-3}"
if [[ "$family" == "straight_retention" || "$family" == "straight_head" || "$family" == "turn_head" ]]; then
  export TAG_VALIDATION_BARRIER=YES
  export TAG_RETENTION_MANIFEST="$skill_root/stabilize/maze_splits.json"
  export TAG_RETENTION_EPISODES="${TAG_RETENTION_EPISODES:-3}"
  export TAG_RETENTION_COMPLETION_FLOOR="${TAG_RETENTION_COMPLETION_FLOOR:-0.75}"
  export TAG_RETENTION_FALL_CEILING="${TAG_RETENTION_FALL_CEILING:-0.05}"
  if [[ "$family" == "straight_head" || "$family" == "turn_head" ]]; then
    export TAG_RETENTION_ACTOR_HEAD=stabilize
  else
    unset TAG_RETENTION_ACTOR_HEAD
  fi
else
  export TAG_VALIDATION_BARRIER=NO
  unset TAG_RETENTION_MANIFEST TAG_RETENTION_EPISODES
  unset TAG_RETENTION_COMPLETION_FLOOR TAG_RETENTION_FALL_CEILING
  unset TAG_RETENTION_ACTOR_HEAD
fi
export TAG_STOP_ON_PLATEAU=YES
export TAG_PLATEAU_PATIENCE=2
bash "$repo_root/scripts/start_remote_validation_monitor.sh" \
  "$repo_root" "$run_dir"

printf 'SKILL=%s\nPROFILE=%s\nRUN_DIR=%s\nMANIFEST=%s\n' \
  "$family" "$profile" "$run_dir" "$manifest"
