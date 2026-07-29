# Real-hardware policy adaptation design

Status: planned future architecture. This document does not authorize online
hardware learning or motor commands.

## Decision

Real-hardware adaptation will use three distinct roles:

1. an immutable main policy that supplies the normal action;
2. a bounded residual helper that corrects localized weaknesses;
3. an independent safety supervisor that may limit, replace, or reject an
   action.

The helper is not a second unrestricted policy competing with the main policy.
The main checkpoint remains a rollback target throughout training.

```text
camera and state
      |
      +--> frozen main policy --------------------> base action
      |
      +--> weakness and risk detector ---> residual enable/scale
      |                                             |
      +--> residual helper ----------------> small correction
                                                    |
                      clipped base + correction ----+
                                                    |
                                      safety supervisor
                                                    |
                                                hardware
```

The executed action is

```text
clip(main_action + residual_scale(state) * residual_action)
```

The residual scale is zero in familiar, safe states. The residual action has
explicit magnitude and action-rate bounds. Initially the main policy is frozen;
only the residual may learn.

## Responsibilities

### Main policy

- Provides the established full-maze behavior.
- Is immutable during the first hardware adaptation stages.
- Remains available for immediate rollback.
- Is replaced only through champion/challenger promotion.

### Residual helper

- Corrects localized real-world mismatch rather than relearning the task.
- Targets braking before sharp turns, hole-edge recovery, actuator delay,
  direction-dependent stiction, and persistent calibration bias.
- Receives no authority outside its tested state envelope.
- Starts with zero output and a small maximum correction.

### Safety supervisor

- Is logically independent of the task reward.
- Predicts near-term fall, estimator-loss, timeout, saturation, and excessive
  action-rate risk.
- May attenuate the residual, clamp the combined action, issue a reviewed
  braking/recovery action, or stop the episode.
- Logs every intervention as training data and as a deployment metric.

The supervisor must be validated before any online parameter updates. Reward
learning alone is not accepted as a hardware safety mechanism.

## Adaptation workflow

### 1. Shadow and fixed-policy data collection

Deploy a fixed champion without learning. Record synchronized observations,
raw and executed actions, servo commands, source timestamps, board response,
route geometry, hole clearance, estimator confidence, outcomes, and safety
interventions. Preserve successful trajectories and pre-failure windows.

### 2. System identification before policy optimization

Use real trajectories to update actuator delay, response, directional maps,
stiction, friction, damping, restitution, and camera error. Retrain and
re-evaluate in the calibrated simulator first. A systematic model or estimator
error should be repaired at its source instead of being hidden inside a policy.

### 3. Weakness mining

Partition experience by turn angle and direction, entry speed, hole clearance,
actuator reversal, camera confidence, maze difficulty, and identified dynamics.
Rank slices using completion, falls, interventions, clearance, and simulated
versus observed next-state error. Oversample weak slices while retaining
ordinary successful behavior.

### 4. Offline-first residual training

Train from a mixture of nominal simulation replay, real successful episodes,
real failure precursors, supervisor interventions, and calibrated simulated
weakness cases. Keep a large nominal component to prevent catastrophic
forgetting. Training produces a challenger; it never overwrites the champion.

### 5. Guarded online fine-tuning

Begin only after offline gates pass. Use short reviewed sessions, low learning
rates, bounded residual authority, replay retention, and a fixed interaction
budget. Save immutable checkpoints between sessions. Stop on increased falls,
interventions, estimator loss, action saturation, or nominal regression.

### 6. Promotion and optional distillation

Evaluate champion and challenger separately on the same starts and seeds.
Promote only when the challenger improves the targeted weak slices without
regressing overall completion, falls, clearance, or hard-maze performance.
Once the combined controller is stable, it may be distilled into one policy
for simpler deployment; this is optional and requires the same gates.

## Required evaluation views

Every candidate report must include:

- overall and per-difficulty completion and fall rates;
- the targeted weakness slices;
- minimum hole clearance and action-rate statistics;
- safety intervention and estimator-loss rates;
- main-only, main-plus-residual, and residual-disabled matched trials;
- checkpoint and dataset hashes;
- hardware, maze, camera calibration, and dynamics-fit identities.

Raw correlation is diagnostic, not causal. Matched residual-on/off trials on
the same conditions determine whether the helper caused an improvement.

## Rejected default alternatives

- Two unrestricted policies blended together: ambiguous credit assignment and
  unsafe combined actions.
- Immediate full-policy online fine-tuning: high forgetting and rollback risk.
- Training from hardware failures alone: wasteful, sparse, and unsafe.
- Permanent specialist mixture from the start: gating errors add complexity
  before the data show that specialists are necessary.

## Research basis

- Bi and D'Andrea, *Sample-Efficient Learning to Solve a Real-World Labyrinth
  Game Using Data-Augmented Model-Based Reinforcement Learning*:
  <https://arxiv.org/abs/2312.09906>
- Johannink et al., *Residual Reinforcement Learning for Robot Control*:
  <https://arxiv.org/abs/1812.03201>
- Ball et al., *Efficient Online Reinforcement Learning with Offline Data*:
  <https://proceedings.mlr.press/v202/ball23a.html>
- Nakamoto et al., *Cal-QL: Calibrated Offline RL Pre-Training for Efficient
  Online Fine-Tuning*: <https://arxiv.org/abs/2303.05479>
- Wagener, Boots, and Cheng, *Safe Reinforcement Learning Using
  Advantage-Based Intervention*:
  <https://proceedings.mlr.press/v139/wagener21a.html>
- Xu et al., *Look Before You Leap: Safe Model-Based Reinforcement Learning
  with Human Intervention*: <https://proceedings.mlr.press/v164/xu22a.html>
- Peng et al., *Sim-to-Real Transfer of Robotic Control with Dynamics
  Randomization*: <https://arxiv.org/abs/1710.06537>

