# Nominal A/B arms, 2026-07-28

This is the experiment log for the bounded arms run after
[NOMINAL_DIAGNOSIS_2026-07-28.md](NOMINAL_DIAGNOSIS_2026-07-28.md) established
that the 500k nominal pilot fails every mastery-gate criterion, that seven
validation layouts never succeed on any seed, and that the policy drives
bang-bang into route turns it cannot decelerate for.

## Protocol

Every arm loads **only** the agent weights from the same source checkpoint,
starts at step zero with a fresh nominal replay buffer, runs a bounded 500,000
steps, and disables plant randomization and random starts. The launcher
verifies those flags in the written `config.yaml` rather than trusting the
profile, so a silently randomized arm cannot be compared by mistake.

```text
source: multimaze_v2_stagedrand_13m_gpu2_20260727_235843/checkpoint.ckpt
```

Arms are ranked on the **dev split**: 64 layouts drawn from the 512 training
layouts, matched to the validation split's difficulty-band composition. The
validation split is reserved for gate decisions and the test split is untouched.

**Dev scores are optimistic because the policy trains on those layouts.** They
rank arms against each other. They are not gate results. The precedent is
direct: the nominal pilot scored 82.81% on single-seed validation and 79.17%
under the 192-episode gate protocol.

Each arm records its own step-zero dev score before training changes anything.
All four arms below agree at that point, which confirms they share a start:

```text
step 0: 78.13% completion, 15.63% falls, 89.08% mean maximum route completion
```

## Results

Dev split, 64 layouts, one episode per layout, sampled actions.

| Run | Profile | Step | Completion | Falls | Mean max progress |
| --- | --- | ---: | ---: | ---: | ---: |
| Shared start | — | 0 | 78.13% | 15.63% | 89.08% |
| Control | `nominal_fullstart` | 500k | 81.25% | 18.75% | 89.11% |
| Smoothness | `nominal_smooth` | 250k | 81.25% | 17.19% | 89.54% |
| Smoothness | `nominal_smooth` | 500k | 82.81% | 15.63% | 88.60% |
| **Hole aware** | `nominal_holeaware` | 250k | 85.94% | 9.38% | 93.73% |
| **Hole aware** | `nominal_holeaware` | **500k** | **90.63%** | **7.81%** | **95.01%** |
| Combined | `nominal_smooth_holeaware` | in progress | | | |

### Hole awareness is the effective lever

The dense hole-margin penalty moves every metric that the gate measures. At 500k
on the dev split it satisfies all five criteria: 90.63% completion, 7.81% falls,
95.01% mean maximum route completion, 85.71% hard-maze completion, and no band
below 85.71%. Easy layouts are solved 22 of 22 with no falls. Terminations are
58 goals, 5 falls and 1 time limit, against 31 falls and 9 time limits in the
original gate run.

Against the matched no-penalty control at the same budget, the fall rate drops
from 18.75% to 7.81%. This is the predicted mechanism: the diagnosis argued that
hazard avoidance had only a terminal signal, so the policy could discover a rim
only by falling into it, and that falls were the criterion nearest to failing.
Progress improved as a consequence of not dying early, which is what the 95%
criterion actually needed.

The trajectory is still rising steeply at 500k (78.13, 85.94, 90.63), so this
budget is probably not where the arm saturates.

### Smoothness is the weak lever

The action-rate penalty worked mechanically. Mean step-to-step action change
fell from about 0.65 to 0.41 over training, a 35% reduction. It did not convert
into reliability: at 500k the arm is flat on completion against the control and
slightly worse on progress, all inside the noise of a 64-episode measurement.

Smoother control alone is therefore not the fix. Whether it helps on top of hole
awareness is what the combined arm tests.

### Control regression worth noting

The no-penalty control improved completion from 78.13% to 81.25% while its fall
rate got **worse**, 15.63% to 18.75%. Training longer without a hazard signal
trades falls for progress. Its completion gain should not be read as uniform
improvement, and it is the specific pathology the hole term addresses.

## Mastery gate passed on the validation split

The hole-aware 500k checkpoint, step 494616, was confirmed under the gate's own
protocol: three fixed evaluation seeds per maze on the held-out validation split,
192 episodes, sampled actions. `tag_mujoco/nominal_training_gate.py` records
`nominal_mastery.passed = true` with all six checks satisfied.

| Criterion | Required | Nominal pilot | Hole aware | |
| --- | ---: | ---: | ---: | :-- |
| Overall completion | at least 90% | 79.17% | **90.10%** | pass |
| Fall rate | at most 10% | 16.15% | **6.25%** | pass |
| Mean maximum route completion | at least 95% | 86.64% | **95.57%** | pass |
| Hard-maze completion | at least 80% | 73.02% | **88.89%** | pass |
| Every difficulty band | at least 75% | 73.02% | **88.89%** | pass |

Band detail: easy 89.39%, medium 92.06%, hard 88.89%. Terminations are 173 goals,
12 falls and 7 time limits, against 152, 31 and 9 for the pilot.

```text
/home/tn22833/cyberrunner_logs/holeaware_gate192_500k_20260728/canonical192.json
/home/tn22833/cyberrunner_logs/holeaware_gate192_500k_20260728/gate_decision.json
```

### The structural ceiling is gone

The pilot had seven layouts that failed all three seeds, capping completion at
89.1% and making the gate unreachable by broad improvement. **No layout now fails
all three seeds.** Every one of the seven improved:

| Layout seed | Pilot | Hole aware |
| --- | ---: | ---: |
| 20024 | 0 of 3 | 3 of 3 |
| 20030 | 0 of 3 | 3 of 3 |
| 20045 | 0 of 3 | 3 of 3 |
| 20025 | 0 of 3 | 2 of 3 |
| 20041 | 0 of 3 | 2 of 3 |
| 20058 | 0 of 3 | 2 of 3 |
| 20040 | 0 of 3 | 1 of 3 |

Layout distribution moved from 43 solved on all seeds, 9 on two, 5 on one and 7
on none, to **50 on all seeds, 9 on two, 5 on one and none on zero**.

Layout 20025 is the notable case. In the pilot the ball froze completely, moving
less than 0.001 in normalized units for the final 2,500 steps under saturated
tilt, on all three seeds. It now completes on two of three. That wedge was
avoidable rather than terminal, and the dense margin signal is what let the
policy avoid entering it.

### The completion margin is thin

Completion passes at 90.10% against a 90% threshold. That is 173 successes out of
192; **172 would score 89.58% and fail**. The pass therefore rests on a single
episode, which is well inside the sampling noise of the protocol. Fall rate at
6.25% and mean maximum progress at 95.57% carry real margin, but overall
completion does not.

A second confirmation at different evaluation seeds is the honest prerequisite
before treating nominal mastery as durable and unlocking domain randomization.

## Measurement caveat

At 64 episodes the sampling error on a rate near 80% is roughly plus or minus 5
points. The control, smoothness and step-zero rows are not separable from one
another at that resolution. Only the hole-aware result is larger than the noise,
and even there the individual figures should not be quoted precisely: 7.81%
falls is 5 episodes out of 64.

The comparison also favours the hole-aware arm on one axis worth stating: its
250k row is compared against 500k rows for the control and smoothness arms.

## Reward terms added

Both terms default to zero, so every pre-existing run and profile is unchanged.

### `action_rate_penalty`

Charges the mean absolute per-step change in commanded tilt. The first step of an
episode has no predecessor and is never charged. The rate is always measured and
logged as `log_action_rate` whether or not it is charged, so every run reports
how smoothly it drives.

Calibration was the risk. A full route earns `progress_reward_scale` plus
`success_bonus`, about 20, and the 500k policy averaged 16.2 return over roughly
750 steps with a mean action change near 0.57. An initial value of 0.5 was
measured to cost about 214 per episode, more than ten times the entire return,
which would have taught the policy to stand still and produced a misleading
"smoothness hurts" result. The shipped value is **0.003**, about 6% of the
return, and a test fails if the penalty exceeds 25% of the reward budget at the
measured chatter.

### `hole_clearance_penalty`

Charges a cost in `[0, 1]` that ramps from zero at the edge of an 8 mm warning
band to one at the hole rim.

The signal is **hole-only**, via a new `signed_hole_clearance`. The pre-existing
`clearance_cost` mixes walls, board boundary and holes, and normal corridor
travel runs 4.5 to 8.4 mm from a wall, inside its 5 mm band. Adding that would
have penalized the policy for being in a corridor. Wall contact is not a
failure; falling into a hole is.

The band width was measured, not guessed. On-route hole clearance across the 64
validation layouts has a median of 18.4 mm and a 1st percentile of 8.0 mm:

| Band | On-route travel incurring any cost |
| ---: | ---: |
| 3 mm | 0.04% |
| **8 mm** | **0.94%** |
| 12 mm | 15.31% |

8 mm is the knee. A 12 mm band would tax 15% of ordinary driving. Measured
reward impact for a perfectly on-route ball at penalty 0.02 is 0.00 points on
the median layout and 0.32 points on the worst, against a 20-point budget, while
undisciplined driving measured a mean cost of 0.12. Tests guard both the
hole-only property and the budget.

## Hypotheses tested and rejected

Recorded so they are not re-attempted.

**Deterministic action selection.** `Agent.policy` samples from the actor
distribution in `eval` mode, so held-out evaluation injects action noise. Acting
on the distribution mode instead was measured over the same 192-episode protocol
and is **worse**: 77.08% completion and 17.19% falls against 79.17% and 16.15%.
Sampling remains the default. The `eval_mode` branch and `--policy-mode` flag are
retained, and every result now records its protocol.

A useful by-product: because the sampling stream advances across episodes, a
single held-out episode is not reproducible in isolation, so much of the apparent
per-layout churn between the 250k and 500k pilot milestones was evaluation noise
rather than learning.

**Inadequate perception or lookahead.** The policy's crop is a 64 mm
ball-centered patch at 64 by 64 pixels, so 1 mm per pixel; walls are about 2
pixels and holes about 15, all resolvable. Route preview is 5 points at 12 mm,
so 60 mm, which at the measured ball speeds of 0.016 to 0.041 m/s is 1.5 to 3
seconds against an actuator lag near 120 ms. Neither is a bottleneck.

**Dynamically infeasible routes.** This was asserted and then disproven. At the
10 degree board limit a rolling sphere reaches 1.22 m/s^2 of lateral
acceleration, giving a minimum turn radius of 0.21 to 3.47 mm and a stopping
distance of 0.22 to 1.74 mm across the observed speed range. The near-right-angle
corners are comfortably trackable, so the route planner is not setting an
impossible target and a dataset regeneration was **not** performed. The failures
are a control deficiency, not a geometric one.

**Strength of the corner-geometry correlation.** On the validation split the
seven unsolved layouts had holes a median 9.6 mm from their sharp turns against
12.1 mm for the layouts always solved. On the training sweep, with 86 failures
against 426 solves, the same measurement gives 10.3 mm against 11.4 mm and the
sharp-turn density difference nearly disappears. The direction replicates but the
effect is **weak** at population scale; the original figures were inflated by a
seven-layout sample. The interventions rest on the direct control measurements
and the per-episode clustering, not on this correlation.

## Training-layout sweep

All 512 training layouts were evaluated with the 500k pilot checkpoint: 83.20%
completion, 13.67% falls, 91.83% mean maximum route completion, with **86 failing
layouts** (34 medium, 29 hard, 23 easy) written to `failed_layouts.json`.

Training performance, 83.20%, is close to unseen-validation performance, 79.17%.
The deficit is therefore an unlearned skill rather than overfitting, which
supports the route-conditioned design: what the policy knows, it transfers.
These 86 measured failures are the demonstration targets if reward shaping proves
insufficient, and they are preferred over the weak geometric proxy above.

## Infrastructure added

- `tag_mujoco/build_dev_split.py` and optional-split support in `maze_dataset.py`,
  backward compatible with the v1 manifest and enforcing that dev is a subset of
  train.
- `--split` accepting `dev` and `train`, `--policy-mode`, and the protocol
  recorded in every result JSON.
- `--split`, `--policy-mode` and `--canonical-episodes-per-maze` on the
  validation monitor and its launcher.
- `scripts/start_nominal_ab_arm.sh`, which refuses non-nominal profiles, requires
  agent-only loading, verifies the written config, and records a step-zero
  baseline.
- `TAG_TRAIN_GPU`, `TAG_CANONICAL_GPU` and `TAG_ROBUST_GPU`, so bounded arms can
  run concurrently. Training is restricted to physical GPU 2 or 1, physical GPU 0
  remains unreachable, and training may not share a device with its validation.
- `tools/visualization/probe_validation_trajectory.py`, recording per-step ball
  position, commanded tilt, progress and clearance for one held-out rollout.
- Test count 63 to 82, passing locally and on the server.

## Open questions

1. **Repeat the gate at different evaluation seeds.** Completion passed by one
   episode. Until a second confirmation holds, nominal mastery should be treated
   as provisional.
2. Does smoothness add anything on top of hole awareness, or dilute it? The
   combined arm is running and its answer decides whether the action-rate term is
   kept.
3. Is 500k the right budget? The hole-aware dev curve was still climbing at 500k,
   78.13 to 85.94 to 90.63, so a bounded continuation may raise the thin
   completion margin.
4. Five layouts still succeed on only one of three seeds, and 20040 is among them.
   These are the natural demonstration targets, alongside the 86 measured failing
   training layouts, if more margin is wanted before domain randomization.

Domain randomization remains locked pending a second gate confirmation. The
mastery gate thresholds are unchanged, and the best nominal checkpoint must be
preserved regardless of what any later randomization stage does.
