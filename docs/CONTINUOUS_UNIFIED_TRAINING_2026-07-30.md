# Continuous unified path-following training

This is the active v3 training experiment as of 2026-07-30. It trains one
route-conditioned DreamerV3 controller across all local path conditions. There
is no skill selector and no separate actor head for straight motion, turns, or
recovery.

## Meaning of continuous

Training does not optimize arrival at a maze's final goal. Each episode begins
at a sampled location on a route and asks the marble to keep following the
local path. Reaching the route endpoint is converted from `goal_reached` into a
neutral `segment_complete` truncation:

- no success bonus is awarded;
- the transition is not marked terminal;
- the environment resets to another route condition; and
- failures such as falling or leaving the board remain penalized terminals.

This produces continuous path-following experience, but it is not one
physically infinite MuJoCo track. Training samples segments from the immutable
512-map training split in `tag_mujoco/maze_splits_v2.json`. The variety reduces
memorization and repeatedly recombines path geometry, approach velocity,
lateral error, and hazards.

## Policy input and reset labels

The deployed policy contract is unchanged. The controller receives:

- the `64 x 64` grayscale camera crop;
- normalized board angles and marble position; and
- five future route points relative to the marble.

It does not receive a maze ID, reset category, skill label, or actor-head ID.
Reset categories are training metadata used only to balance experience:

| Condition | Share | Reset emphasis |
| --- | ---: | --- |
| Straight | 30% | Low-curvature route sections |
| Turn | 30% | High-curvature route sections |
| Stabilize | 20% | Low initial forward speed and small lateral velocity |
| Recovery | 15% | Lateral displacement with corrective cross-route velocity |
| Hazard | 5% | Route samples close to holes when holes are present |

These probabilities control where episodes begin; they do not partition replay
or choose different policies. The shared world model, actor, and critic learn
from all collected transitions.

## Training profile

The profile is `tag_sim_v3_continuous_unified` and is layered after
`tag_sim_v3_skill_base`:

| Parameter | Value |
| --- | --- |
| Training layouts | 512 (`train` split) |
| Online sampling | Uniform across layouts |
| Actor | One unified actor |
| Parallel environments | 16 production; 8 smoke |
| Episode wrapper length | 1,000 steps |
| Production steps | 300,000 per seed |
| Training ratio | 8 |
| Fresh replay prefill | 25,000 production; 1,000 smoke |
| Precision | float32 |
| World-model learning rate | `3e-5` |
| Actor learning rate | `3e-6` |
| Critic learning rate | `3e-6` |
| Progress reward scale | 15.0 |
| Success bonus | 0.0 |
| Failure penalty | 10.0 |
| Hole-clearance penalty | 0.02 |
| Path-tracking penalty | 0.01 |
| Action-rate penalty | 0.001 |
| Validation interval | 50,000 steps |

Plant randomization remains disabled in this experiment. Add actuator, camera,
or physics randomization only after the nominal unified controller demonstrates
reliable held-out path following.

## Warm start

Both production seeds start from the same accepted stabilization checkpoint at
step 200,000:

```text
/home/tn22833/cyberrunner_logs/skill_stabilize_v3_cont500k_20260730/
  validation/step_000200000/checkpoint.ckpt
```

Agent-only loading restores the 124 learned perception, world-model, actor, and
critic variables while resetting optimizer state, the step counter, and online
replay. This preserves basic marble perception, learned board dynamics, and
stabilizing control without importing stale optimizer momentum or replay.

The warm start can bias the initial policy toward cautious motion. The combined
60% straight-and-turn reset share is intended to correct that bias. If both
seeds remain overly cautious after held-out evaluation, run a bounded scratch
control; do not change the anchor independently between production seeds.

## Validation

Held-out evaluation overrides `continuous_path` to `False`, starts at the true
maze entrance, and restores the full-map completion criterion. Thus training
does not receive an endpoint bonus, while validation still measures whether
local path-following behavior composes into complete maze solutions.

The active comparison uses:

- seed 7101 on physical GPU 2;
- seed 7102 on physical GPU 1;
- canonical validation every 50,000 steps on GPUs 3 and 4; and
- no work on GPU 0.

Validation initially uses the held-out compound-course split for fast barrier
feedback. Before promotion or hardware deployment, evaluate the selected
checkpoint on the complete 64-layout validation split and then run the existing
robustness and hardware safety gates.

## 2026-07-30 launch record

The 10,000-step seed-7101 smoke run completed with exit status 0. It restored
all 124 learned variables, reset six optimizer variables, produced finite
world-model/actor/critic metrics, and reached approximately 184 environment
steps per second after compilation.

The production run directories are:

```text
/home/tn22833/cyberrunner_logs/continuous_unified_300k_seed7101_20260730
/home/tn22833/cyberrunner_logs/continuous_unified_300k_seed7102_20260730
```

Do not select a seed from training return alone. Compare fixed-seed held-out
completion, maximum route progress, fall rate, cross-track error, and clearance
at matching checkpoints.
