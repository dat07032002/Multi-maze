#!/usr/bin/env bash
set -euo pipefail

if [[ "${TAG_TRAINING_APPROVED:-NO}" != "YES" ]]; then
  echo "V2 training is locked. Obtain approval, then set TAG_TRAINING_APPROVED=YES."
  exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

training_profile="${TAG_TRAINING_PROFILE:-tag_sim_v2}"
case "$training_profile" in
  tag_sim_v2_noholes_group016)
    manifest="$repo_root/artifacts/paired_hole_curriculum/no_holes/maze_splits_group_016.json"
    dataset_id="cyberrunner_paired_no_holes_group016_v1"
    ;;
  tag_sim_v2_noholes_group032)
    manifest="$repo_root/artifacts/paired_hole_curriculum/no_holes/maze_splits_group_032.json"
    dataset_id="cyberrunner_paired_no_holes_group032_v1"
    ;;
  tag_sim_v2_noholes_group064)
    manifest="$repo_root/artifacts/paired_hole_curriculum/no_holes/maze_splits_group_064.json"
    dataset_id="cyberrunner_paired_no_holes_group064_v1"
    ;;
  tag_sim_v2_noholes_group128)
    manifest="$repo_root/artifacts/paired_hole_curriculum/no_holes/maze_splits_group_128.json"
    dataset_id="cyberrunner_paired_no_holes_group128_v1"
    ;;
  tag_sim_v2_noholes_group512)
    manifest="$repo_root/artifacts/paired_hole_curriculum/no_holes/maze_splits_group_512.json"
    dataset_id="cyberrunner_paired_no_holes_group512_v1"
    ;;
  tag_sim_v2_phase1_noholes_fullstart_scratch|tag_sim_v2_phase2_noholes_fullstart)
    manifest="$repo_root/artifacts/paired_hole_curriculum/no_holes/maze_splits.json"
    dataset_id="cyberrunner_paired_no_holes_512train_64val_64test_v1"
    ;;
  tag_sim_v2_phase3_branch_holes)
    manifest="$repo_root/artifacts/paired_hole_curriculum/branch_holes/maze_splits.json"
    dataset_id="cyberrunner_paired_branch_holes_512train_64val_64test_v1"
    ;;
  tag_sim_v2_phase4_easy_dodge)
    manifest="$repo_root/artifacts/paired_hole_curriculum/easy_dodge/maze_splits.json"
    dataset_id="cyberrunner_paired_easy_dodge_512train_64val_64test_v1"
    ;;
  tag_sim_v2_phase5_mixed_holes)
    manifest="$repo_root/artifacts/paired_hole_curriculum/mixed_holes/maze_splits.json"
    dataset_id="cyberrunner_paired_mixed_holes_512train_64val_64test_v1"
    ;;
  tag_sim_v2_singlepath_progress)
    manifest="$repo_root/tag_mujoco/generated_singlepath_progress_mazes/maze_splits_progress.json"
    dataset_id="tag_singlepath_progress_v1"
    ;;
  tag_sim_v2_branch_blockers)
    manifest="$repo_root/tag_mujoco/generated_branch_blocker_mazes/maze_splits_branch_blockers.json"
    dataset_id="tag_singlepath_branch_blockers_v1"
    ;;
  tag_sim_v2_dodge_progress|tag_sim_v2_easy_dodge_holes)
    manifest="$repo_root/tag_mujoco/generated_dodge_mazes/maze_splits_dodge.json"
    dataset_id="tag_dodge_curriculum_v1"
    ;;
  tag_sim_v3_skill_stabilize_retention)
    skill=stabilize
    manifest="${TAG_MANIFEST:-$repo_root/artifacts/universal_skills/stabilize/maze_splits.json}"
    dataset_id="tag_universal_skill_stabilize_v1"
    ;;
  tag_sim_v3_skill_straight_retention)
    skill=straight
    manifest="${TAG_MANIFEST:-$repo_root/artifacts/universal_skills/straight/maze_splits.json}"
    dataset_id="tag_universal_skill_straight_v1"
    ;;
  tag_sim_v3_skill_straight_head)
    manifest="${TAG_MANIFEST:-$repo_root/artifacts/universal_skills/straight/maze_splits.json}"
    dataset_id="tag_universal_skill_straight_v1"
    ;;
  tag_sim_v3_skill_turn_head)
    manifest="${TAG_MANIFEST:-$repo_root/artifacts/universal_skills/turn/maze_splits.json}"
    dataset_id="tag_universal_skill_turn_v1"
    ;;
  tag_sim_v3_skill_stabilize|tag_sim_v3_skill_straight|tag_sim_v3_skill_turn|tag_sim_v3_skill_compound|tag_sim_v3_skill_recovery|tag_sim_v3_skill_hazard)
    skill="${training_profile#tag_sim_v3_skill_}"
    manifest="${TAG_MANIFEST:-$repo_root/artifacts/universal_skills/$skill/maze_splits.json}"
    dataset_id="tag_universal_skill_${skill}_v1"
    ;;
  tag_sim_v3_skill_actuator025)
    manifest="${TAG_MANIFEST:-$repo_root/artifacts/universal_skills/compound/maze_splits.json}"
    dataset_id="tag_universal_skill_compound_v1"
    ;;
  tag_sim_v3_sequential_map_local|tag_sim_v3_sequential_map_fullstart)
    manifest="${TAG_MANIFEST:?Sequential map training requires TAG_MANIFEST.}"
    dataset_id="${TAG_DATASET_ID:?Sequential map training requires TAG_DATASET_ID.}"
    ;;
  tag_sim_v3_continuous_unified)
    manifest="${TAG_MANIFEST:-$repo_root/tag_mujoco/maze_splits_v2.json}"
    dataset_id="cyberrunner_fixed_board_512train_64val_64test_v2"
    ;;
  tag_sim_v4_continuous_curriculum_noholes)
    manifest="${TAG_MANIFEST:-$repo_root/artifacts/paired_hole_curriculum/no_holes/maze_splits.json}"
    dataset_id="cyberrunner_paired_no_holes_512train_64val_64test_v1"
    ;;
  *)
    manifest="$repo_root/tag_mujoco/maze_splits_v2.json"
    dataset_id="cyberrunner_fixed_board_512train_64val_64test_v2"
    ;;
esac
test -f "$manifest"
grep -q "$dataset_id" "$manifest"

# Physical GPU 2 remains the default for production training. Bounded A/B arms
# may be placed on another idle device so arms can run concurrently. Physical
# GPU 0 is never used, and 3 and 4 are reserved for validation.
train_gpu="${TAG_TRAIN_GPU:-2}"
case "$train_gpu" in
  1|2) ;;
  *)
    echo "TAG_TRAIN_GPU must be 2 (production) or 1 (bounded arm); got $train_gpu."
    exit 8
    ;;
esac
export CUDA_VISIBLE_DEVICES="$train_gpu"
export XLA_PYTHON_CLIENT_PREALLOCATE="false"
export MUJOCO_GL="egl"
export PYTHONUNBUFFERED="1"

stamp="$(date +%Y%m%d_%H%M%S)"
logdir="${TAG_LOGDIR:-$HOME/tag_logs/multimaze_v2_gpu2_$stamp}"
steps="${TAG_STEPS:-10000}"
python_bin="${TAG_PYTHON:-python}"
checkpoint_mode="${TAG_CHECKPOINT_MODE:-full}"
checkpoint_dataset_id="$dataset_id"

case "$training_profile" in
  tag_sim_v2_noholes_group016)
    configs=(tag_sim_v2 medium "$training_profile")
    if [[ -n "${TAG_FROM_CHECKPOINT:-}" ]]; then
      echo "The 16-map group must start from scratch."
      exit 7
    fi
    checkpoint_mode="none"
    ;;
  tag_sim_v2_noholes_group032)
    configs=(tag_sim_v2 medium "$training_profile")
    checkpoint_dataset_id="cyberrunner_paired_no_holes_group016_v1"
    ;;
  tag_sim_v2_noholes_group064)
    configs=(tag_sim_v2 medium "$training_profile")
    checkpoint_dataset_id="cyberrunner_paired_no_holes_group032_v1"
    ;;
  tag_sim_v2_noholes_group128)
    configs=(tag_sim_v2 medium "$training_profile")
    checkpoint_dataset_id="cyberrunner_paired_no_holes_group064_v1"
    ;;
  tag_sim_v2_noholes_group512)
    configs=(tag_sim_v2 medium "$training_profile")
    checkpoint_dataset_id="cyberrunner_paired_no_holes_group128_v1"
    ;;
  tag_sim_v2_phase1_noholes_fullstart_scratch)
    configs=(tag_sim_v2 medium "$training_profile")
    if [[ -n "${TAG_FROM_CHECKPOINT:-}" ]]; then
      echo "Phase 1 must start from scratch."
      exit 7
    fi
    checkpoint_mode="none"
    ;;
  tag_sim_v2_phase2_noholes_fullstart)
    configs=(tag_sim_v2 medium "$training_profile")
    checkpoint_dataset_id="cyberrunner_paired_no_holes_512train_64val_64test_v1"
    ;;
  tag_sim_v2_phase3_branch_holes)
    configs=(tag_sim_v2 medium "$training_profile")
    checkpoint_dataset_id="cyberrunner_paired_no_holes_512train_64val_64test_v1"
    ;;
  tag_sim_v2_phase4_easy_dodge)
    configs=(tag_sim_v2 medium "$training_profile")
    checkpoint_dataset_id="cyberrunner_paired_branch_holes_512train_64val_64test_v1"
    ;;
  tag_sim_v2_phase5_mixed_holes)
    configs=(tag_sim_v2 medium "$training_profile")
    checkpoint_dataset_id="cyberrunner_paired_easy_dodge_512train_64val_64test_v1"
    ;;
  tag_sim_v2)
    configs=(tag_sim_v2 medium)
    ;;
  tag_sim_v2_fullstart_finetune)
    configs=(tag_sim_v2 tag_sim_v2_fullstart_finetune medium)
    ;;
  tag_sim_v2_nominal_fullstart)
    configs=(tag_sim_v2 tag_sim_v2_nominal_fullstart medium)
    if [[ "$checkpoint_mode" != "agent_only" ]]; then
      echo "Nominal full-start training requires TAG_CHECKPOINT_MODE=agent_only."
      exit 7
    fi
    if [[ -z "${TAG_FROM_CHECKPOINT:-}" ]]; then
      echo "Nominal full-start training requires TAG_FROM_CHECKPOINT."
      exit 7
    fi
    ;;
  tag_sim_v2_nominal_ratio64|tag_sim_v2_nominal_fallpenalty|tag_sim_v2_nominal_sharp_plr|tag_sim_v2_nominal_smooth|tag_sim_v2_nominal_holeaware|tag_sim_v2_nominal_smooth_holeaware|tag_sim_v2_nominal_safe_resume)
    # Bounded nominal A/B arms. Each changes one thing against
    # tag_sim_v2_nominal_fullstart and carries the same agent-only requirement,
    # so every arm starts from the same policy with a fresh nominal replay.
    configs=(tag_sim_v2 "$training_profile" medium)
    if [[ "$checkpoint_mode" != "agent_only" ]]; then
      echo "Nominal A/B arms require TAG_CHECKPOINT_MODE=agent_only."
      exit 7
    fi
    if [[ -z "${TAG_FROM_CHECKPOINT:-}" ]]; then
      echo "Nominal A/B arms require TAG_FROM_CHECKPOINT."
      exit 7
    fi
    ;;
  tag_sim_v2_clean_smoke)
    # Apply the smoke profile after medium so float32 cannot be overwritten by
    # the medium profile's float16 default.
    configs=(tag_sim_v2 medium tag_sim_v2_clean_smoke)
    if [[ "$checkpoint_mode" != "agent_only" ]]; then
      echo "Clean smoke training requires TAG_CHECKPOINT_MODE=agent_only."
      exit 7
    fi
    if [[ -z "${TAG_FROM_CHECKPOINT:-}" ]]; then
      echo "Clean smoke training requires TAG_FROM_CHECKPOINT."
      exit 7
    fi
    ;;
  tag_sim_v2_holeaware_dr010|tag_sim_v2_holeaware_curriculum_dr)
    configs=(tag_sim_v2 "$training_profile" medium)
    if [[ "$checkpoint_mode" != "agent_only" ]]; then
      echo "DR-0.10 training requires TAG_CHECKPOINT_MODE=agent_only."
      exit 7
    fi
    if [[ -z "${TAG_FROM_CHECKPOINT:-}" ]]; then
      echo "DR-0.10 training requires TAG_FROM_CHECKPOINT."
      exit 7
    fi
    ;;
  tag_sim_v2_singlepath_progress|tag_sim_v2_branch_blockers|tag_sim_v2_dodge_progress|tag_sim_v2_easy_dodge_holes)
    configs=(tag_sim_v2 medium "$training_profile")
    if [[ -n "${TAG_FROM_CHECKPOINT:-}" && "$checkpoint_mode" != "agent_only" ]]; then
      echo "Curriculum skill continuation requires TAG_CHECKPOINT_MODE=agent_only."
      exit 7
    fi
    if [[ -z "${TAG_FROM_CHECKPOINT:-}" ]]; then
      checkpoint_mode="none"
    fi
    ;;
  tag_sim_v3_skill_stabilize)
    configs=(tag_sim_v2 medium tag_sim_v3_skill_base "$training_profile")
    if [[ -n "${TAG_FROM_CHECKPOINT:-}" && "$checkpoint_mode" != "agent_only" ]]; then
      echo "Skill warm starts require TAG_CHECKPOINT_MODE=agent_only."
      exit 7
    fi
    if [[ -z "${TAG_FROM_CHECKPOINT:-}" ]]; then
      checkpoint_mode="none"
    else
      checkpoint_dataset_id="${TAG_CHECKPOINT_DATASET_ID:?Warm start requires TAG_CHECKPOINT_DATASET_ID.}"
    fi
    ;;
  tag_sim_v3_skill_stabilize_retention|tag_sim_v3_skill_straight_retention)
    configs=(tag_sim_v2 medium tag_sim_v3_skill_base "$training_profile")
    if [[ "$checkpoint_mode" != "agent_only" ]] || [[ -z "${TAG_FROM_CHECKPOINT:-}" ]]; then
      echo "Skill retention requires an agent-only checkpoint."
      exit 7
    fi
    if [[ -z "${TAG_DEMO_DIR:-}" ]]; then
      echo "Skill retention requires an immutable TAG_DEMO_DIR."
      exit 7
    fi
    checkpoint_dataset_id="${TAG_CHECKPOINT_DATASET_ID:?Skill retention requires TAG_CHECKPOINT_DATASET_ID.}"
    ;;
  tag_sim_v3_skill_straight_head|tag_sim_v3_skill_turn_head)
    configs=(tag_sim_v2 medium tag_sim_v3_skill_base "$training_profile")
    if [[ "$checkpoint_mode" != "multihead_init" ]] || [[ -z "${TAG_FROM_CHECKPOINT:-}" ]]; then
      echo "Initial multi-head skill training requires TAG_CHECKPOINT_MODE=multihead_init."
      exit 7
    fi
    checkpoint_dataset_id="${TAG_CHECKPOINT_DATASET_ID:?Multi-head initialization requires TAG_CHECKPOINT_DATASET_ID.}"
    ;;
  tag_sim_v3_skill_straight|tag_sim_v3_skill_turn|tag_sim_v3_skill_compound|tag_sim_v3_skill_recovery|tag_sim_v3_skill_hazard|tag_sim_v3_skill_actuator025)
    configs=(tag_sim_v2 medium tag_sim_v3_skill_base "$training_profile")
    if [[ "$checkpoint_mode" != "agent_only" ]] || [[ -z "${TAG_FROM_CHECKPOINT:-}" ]]; then
      echo "Skill stages after stabilize require an agent-only checkpoint."
      exit 7
    fi
    checkpoint_dataset_id="${TAG_CHECKPOINT_DATASET_ID:?Skill continuation requires TAG_CHECKPOINT_DATASET_ID.}"
    ;;
  tag_sim_v3_continuous_unified)
    configs=(tag_sim_v2 medium tag_sim_v3_skill_base "$training_profile")
    if [[ "$checkpoint_mode" != "agent_only" ]] || [[ -z "${TAG_FROM_CHECKPOINT:-}" ]]; then
      echo "Continuous unified training requires an agent-only checkpoint."
      exit 7
    fi
    checkpoint_dataset_id="${TAG_CHECKPOINT_DATASET_ID:?Continuous unified training requires TAG_CHECKPOINT_DATASET_ID.}"
    ;;
  tag_sim_v4_continuous_curriculum_noholes)
    configs=(tag_sim_v2 medium tag_sim_v3_skill_base "$training_profile")
    if [[ -n "${TAG_FROM_CHECKPOINT:-}" ]]; then
      echo "Connected no-hole curriculum must start from scratch."
      exit 7
    fi
    checkpoint_mode="none"
    ;;
  tag_sim_v3_sequential_map_local)
    configs=(tag_sim_v2 medium tag_sim_v3_sequential_map_local)
    if [[ "$checkpoint_mode" != "agent_only" ]] || [[ -z "${TAG_FROM_CHECKPOINT:-}" ]]; then
      echo "Sequential map stages require an agent-only checkpoint."
      exit 7
    fi
    if [[ -z "${TAG_DEMO_DIR:-}" ]]; then
      echo "Sequential map stages require a balanced TAG_DEMO_DIR rehearsal pack."
      exit 7
    fi
    checkpoint_dataset_id="${TAG_CHECKPOINT_DATASET_ID:?Sequential continuation requires TAG_CHECKPOINT_DATASET_ID.}"
    ;;
  tag_sim_v3_sequential_map_fullstart)
    configs=(tag_sim_v2 medium tag_sim_v3_sequential_map_local tag_sim_v3_sequential_map_fullstart)
    if [[ "$checkpoint_mode" != "agent_only" ]] || [[ -z "${TAG_FROM_CHECKPOINT:-}" ]]; then
      echo "Sequential map stages require an agent-only checkpoint."
      exit 7
    fi
    if [[ -z "${TAG_DEMO_DIR:-}" ]]; then
      echo "Sequential map stages require a balanced TAG_DEMO_DIR rehearsal pack."
      exit 7
    fi
    checkpoint_dataset_id="${TAG_CHECKPOINT_DATASET_ID:?Sequential continuation requires TAG_CHECKPOINT_DATASET_ID.}"
    ;;
  tag_sim_v2_fullstart_staged_randomization)
    configs=(tag_sim_v2 tag_sim_v2_fullstart_staged_randomization medium)
    ;;
  tag_sim_v2_pla_adaptation)
    configs=(tag_sim_v2 tag_sim_v2_pla_adaptation medium)
    if [[ "$checkpoint_mode" != "agent_only" ]]; then
      echo "PLA adaptation requires TAG_CHECKPOINT_MODE=agent_only."
      exit 7
    fi
    if [[ -z "${TAG_FROM_CHECKPOINT:-}" ]]; then
      echo "PLA adaptation requires TAG_FROM_CHECKPOINT."
      exit 7
    fi
    ;;
  tag_sim_v2_pla_scratch)
    configs=(tag_sim_v2 tag_sim_v2_pla_scratch medium)
    if [[ -n "${TAG_FROM_CHECKPOINT:-}" ]]; then
      echo "PLA scratch control refuses TAG_FROM_CHECKPOINT."
      exit 7
    fi
    checkpoint_mode="none"
    ;;
  *)
    echo "Unsupported TAG_TRAINING_PROFILE: $training_profile"
    exit 5
    ;;
esac

case "$training_profile" in
  tag_sim_v2_noholes_group032|tag_sim_v2_noholes_group064|tag_sim_v2_noholes_group128|tag_sim_v2_noholes_group512)
    if [[ "$checkpoint_mode" != "agent_only" ]]; then
      echo "Grouped no-hole stages after 16 require TAG_CHECKPOINT_MODE=agent_only."
      exit 7
    fi
    if [[ -z "${TAG_FROM_CHECKPOINT:-}" ]]; then
      echo "Grouped no-hole stages after 16 require TAG_FROM_CHECKPOINT."
      exit 7
    fi
    if [[ -z "${TAG_DEMO_DIR:-}" ]]; then
      echo "Grouped no-hole stages after 16 require TAG_DEMO_DIR for retention replay."
      exit 7
    fi
    ;;
  tag_sim_v2_phase2_noholes_fullstart|tag_sim_v2_phase3_branch_holes|tag_sim_v2_phase4_easy_dodge|tag_sim_v2_phase5_mixed_holes)
    if [[ "$checkpoint_mode" != "agent_only" ]]; then
      echo "Curriculum phases 2-5 require TAG_CHECKPOINT_MODE=agent_only."
      exit 7
    fi
    if [[ -z "${TAG_FROM_CHECKPOINT:-}" ]]; then
      echo "Curriculum phases 2-5 require TAG_FROM_CHECKPOINT."
      exit 7
    fi
    if [[ -z "${TAG_DEMO_DIR:-}" ]]; then
      echo "Curriculum phases 2-5 require TAG_DEMO_DIR for retention replay."
      exit 7
    fi
    ;;
esac

if [[ -e "$logdir" ]] && [[ -n "$(find "$logdir" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
  echo "V2 requires a fresh, empty log directory: $logdir"
  exit 4
fi

mkdir -p "$logdir"
assumptions_sha256="$(sha256sum "$repo_root/tag_mujoco/assumed_dynamics.json" | awk '{print $1}')"
optimizer_state_reset=false
if [[ "$checkpoint_mode" == "agent_only" || "$checkpoint_mode" == "multihead_init" ]]; then
  optimizer_state_reset=true
fi
printf '{"policy_contract_version":"tag_hardware_policy_v1","training_profile":"%s","dataset_id":"%s","checkpoint_compatible_with_v1":false,"checkpoint_load_mode":"%s","optimizer_state_reset":%s,"assumed_dynamics_sha256":"%s"}\n' \
  "$training_profile" "$dataset_id" "$checkpoint_mode" "$optimizer_state_reset" \
  "$assumptions_sha256" >"$logdir/policy_contract.json"

extra_args=()
if [[ -n "${TAG_SEED:-}" ]]; then
  [[ "$TAG_SEED" =~ ^[0-9]+$ ]] || {
    echo "TAG_SEED must be a non-negative integer; got $TAG_SEED."
    exit 9
  }
  extra_args+=(--seed "$TAG_SEED")
fi
case "$training_profile" in
  tag_sim_v3_skill_stabilize|tag_sim_v3_skill_stabilize_retention|tag_sim_v3_skill_straight|tag_sim_v3_skill_straight_retention|tag_sim_v3_skill_straight_head|tag_sim_v3_skill_turn|tag_sim_v3_skill_turn_head|tag_sim_v3_skill_compound|tag_sim_v3_skill_recovery|tag_sim_v3_skill_hazard|tag_sim_v3_skill_actuator025|tag_sim_v3_sequential_map_local|tag_sim_v3_sequential_map_fullstart|tag_sim_v3_continuous_unified|tag_sim_v4_continuous_curriculum_noholes)
    extra_args+=(--env.tagmaze.maze_manifest "$manifest")
    if [[ -n "${TAG_ENV_COUNT:-}" ]]; then
      case "$TAG_ENV_COUNT" in
        8|16) ;;
        *) echo "TAG_ENV_COUNT must be 8 or 16 for v3 training; got $TAG_ENV_COUNT."; exit 9 ;;
      esac
      extra_args+=(--envs.amount "$TAG_ENV_COUNT")
    fi
    if [[ -n "${TAG_LOGICAL_CPUS:-}" ]]; then
      case "$TAG_LOGICAL_CPUS" in
        16|32) ;;
        *) echo "TAG_LOGICAL_CPUS must be 16 or 32 for v3 training; got $TAG_LOGICAL_CPUS."; exit 9 ;;
      esac
      extra_args+=(--jax.logical_cpus "$TAG_LOGICAL_CPUS")
    fi
    if [[ -n "${TAG_TRAIN_FILL:-}" ]]; then
      [[ "$TAG_TRAIN_FILL" =~ ^[1-9][0-9]*$ ]] || {
        echo "TAG_TRAIN_FILL must be a positive integer; got $TAG_TRAIN_FILL."
        exit 9
      }
      extra_args+=(--run.train_fill "$TAG_TRAIN_FILL")
    fi
    if [[ -n "${TAG_VALIDATION_BARRIER_INTERVAL:-}" ]]; then
      [[ "$TAG_VALIDATION_BARRIER_INTERVAL" =~ ^[1-9][0-9]*$ ]] || {
        echo "TAG_VALIDATION_BARRIER_INTERVAL must be a positive integer."
        exit 9
      }
      extra_args+=(
        --run.validation_barrier_interval "$TAG_VALIDATION_BARRIER_INTERVAL"
      )
    fi
    ;;
esac
if [[ -n "${TAG_DEMO_DIR:-}" ]]; then
  test -d "$TAG_DEMO_DIR"
  extra_args+=(--run.demo_dir "$TAG_DEMO_DIR")
  extra_args+=(--run.demo_limit_steps "${TAG_DEMO_LIMIT_STEPS:-0}")
  extra_args+=(--run.demo_sampling "${TAG_DEMO_SAMPLING:-chronological}")
fi
if [[ -n "${TAG_FROM_CHECKPOINT:-}" ]]; then
  test -f "$TAG_FROM_CHECKPOINT"
  checkpoint_contract="${TAG_CHECKPOINT_CONTRACT:-$(dirname "$TAG_FROM_CHECKPOINT")/policy_contract.json}"
  if [[ ! -f "$checkpoint_contract" ]]; then
    echo "Refusing checkpoint without v2 policy metadata: $TAG_FROM_CHECKPOINT"
    exit 6
  fi
  if ! grep -q '"policy_contract_version":"tag_hardware_policy_v1"' "$checkpoint_contract" ||
     ! grep -q "\"dataset_id\":\"$checkpoint_dataset_id\"" "$checkpoint_contract"; then
    echo "Refusing checkpoint without matching v2 policy and dataset metadata: $TAG_FROM_CHECKPOINT"
    exit 6
  fi
  extra_args+=(
    --run.from_checkpoint "$TAG_FROM_CHECKPOINT"
    --run.from_checkpoint_mode "$checkpoint_mode"
  )
fi

if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi -i "$train_gpu" --query-gpu=index,uuid,name --format=csv,noheader
fi
echo "V2 profile=$training_profile checkpoint_mode=$checkpoint_mode steps=$steps envs=${TAG_ENV_COUNT:-8} gpu=$train_gpu dataset=$dataset_id manifest=$manifest logdir=$logdir"

"$python_bin" dreamerv3/dreamerv3/train.py \
  --configs "${configs[@]}" \
  --logdir "$logdir" \
  --run.script train \
  --run.steps "$steps" \
  "${extra_args[@]}" \
  "$@"
