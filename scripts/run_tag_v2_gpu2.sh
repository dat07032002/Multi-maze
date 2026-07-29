#!/usr/bin/env bash
set -euo pipefail

if [[ "${TAG_TRAINING_APPROVED:-NO}" != "YES" ]]; then
  echo "V2 training is locked. Obtain approval, then set TAG_TRAINING_APPROVED=YES."
  exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

manifest="$repo_root/tag_mujoco/maze_splits_v2.json"
test -f "$manifest"
grep -q 'cyberrunner_fixed_board_512train_64val_64test_v2' "$manifest"

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
training_profile="${TAG_TRAINING_PROFILE:-tag_sim_v2}"
checkpoint_mode="${TAG_CHECKPOINT_MODE:-full}"

case "$training_profile" in
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
  tag_sim_v2_nominal_ratio64|tag_sim_v2_nominal_fallpenalty|tag_sim_v2_nominal_sharp_plr|tag_sim_v2_nominal_smooth|tag_sim_v2_nominal_holeaware|tag_sim_v2_nominal_smooth_holeaware)
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
  tag_sim_v2_holeaware_dr010)
    configs=(tag_sim_v2 tag_sim_v2_holeaware_dr010 medium)
    if [[ "$checkpoint_mode" != "agent_only" ]]; then
      echo "DR-0.10 training requires TAG_CHECKPOINT_MODE=agent_only."
      exit 7
    fi
    if [[ -z "${TAG_FROM_CHECKPOINT:-}" ]]; then
      echo "DR-0.10 training requires TAG_FROM_CHECKPOINT."
      exit 7
    fi
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

if [[ -e "$logdir" ]] && [[ -n "$(find "$logdir" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
  echo "V2 requires a fresh, empty log directory: $logdir"
  exit 4
fi

mkdir -p "$logdir"
assumptions_sha256="$(sha256sum "$repo_root/tag_mujoco/assumed_dynamics.json" | awk '{print $1}')"
printf '{"policy_contract_version":"tag_hardware_policy_v1","training_profile":"%s","dataset_id":"cyberrunner_fixed_board_512train_64val_64test_v2","checkpoint_compatible_with_v1":false,"checkpoint_load_mode":"%s","assumed_dynamics_sha256":"%s"}\n' \
  "$training_profile" "$checkpoint_mode" "$assumptions_sha256" >"$logdir/policy_contract.json"

extra_args=()
if [[ -n "${TAG_DEMO_DIR:-}" ]]; then
  test -d "$TAG_DEMO_DIR"
  extra_args+=(--run.demo_dir "$TAG_DEMO_DIR")
fi
if [[ -n "${TAG_FROM_CHECKPOINT:-}" ]]; then
  test -f "$TAG_FROM_CHECKPOINT"
  checkpoint_contract="${TAG_CHECKPOINT_CONTRACT:-$(dirname "$TAG_FROM_CHECKPOINT")/policy_contract.json}"
  if [[ ! -f "$checkpoint_contract" ]]; then
    echo "Refusing checkpoint without v2 policy metadata: $TAG_FROM_CHECKPOINT"
    exit 6
  fi
  if ! grep -q '"policy_contract_version":"tag_hardware_policy_v1"' "$checkpoint_contract" ||
     ! grep -q '"dataset_id":"cyberrunner_fixed_board_512train_64val_64test_v2"' "$checkpoint_contract"; then
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
echo "V2 profile=$training_profile checkpoint_mode=$checkpoint_mode steps=$steps envs=8 gpu=$train_gpu dataset=512/64/64 logdir=$logdir"

"$python_bin" dreamerv3/dreamerv3/train.py \
  --configs "${configs[@]}" \
  --logdir "$logdir" \
  --run.script train \
  --run.steps "$steps" \
  "${extra_args[@]}" \
  "$@"
