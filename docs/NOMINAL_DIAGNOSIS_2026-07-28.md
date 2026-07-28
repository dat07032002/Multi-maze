# Nominal 500k pilot diagnosis, 2026-07-28

The bounded nominal pilot
`nominal_fullstart_13m_500k_20260728_134149` completed its full 500,000 steps
and both scheduled canonical validations. This document records what its
checkpoint actually does, because the single-seed milestone numbers overstated
it and pointed at the wrong remedies.

## The mastery gate fails on every criterion

The gate requires three fixed evaluation seeds per maze. Running all 192
episodes on the 500k checkpoint gives:

| Criterion | Required | Measured | Verdict |
| --- | ---: | ---: | :-- |
| Overall completion | at least 90% | 79.17% | fail |
| Fall rate | at most 10% | 16.15% | fail |
| Mean maximum route completion | at least 95% | 86.64% | fail |
| Hard-maze completion | at least 80% | 73.02% | fail |
| Every difficulty band | at least 75% | 73.02% medium and hard | fail |

The single-seed 500k milestone reported 82.81% completion and 10.94% falls. The
three-seed protocol is materially worse, and falls nearly doubled. Single-seed
canonical results should not be read as gate predictions.

Artifacts:

```text
/home/tn22833/cyberrunner_logs/nominal_gate192_500k_20260728/canonical192.json
```

## Mean maximum route completion is the binding criterion

On 64 layouts, if the remaining failures stop near half the route, reaching 95%
mean maximum route completion requires no more than five failures, which is
92.2% completion. The 95% progress bar is therefore stricter than the 90%
completion bar, and failures that stop early cost far more than failures that
stop late. The present failures stop early: five of them below 34% of the route.

## A structural ceiling below the gate

Per-layout success over the three seeds:

| Successes out of 3 | Layouts |
| ---: | ---: |
| 3 | 43 |
| 2 | 9 |
| 1 | 5 |
| 0 | 7 |

The seven layouts that never succeed are 10.9% of the split, so completion
cannot exceed 89.1% while they remain unsolved. **The gate cannot be reached by
broad improvement alone. Those specific layouts have to be fixed.**

## Root cause: the policy cannot turn sharp corners

Three checks locate the failure.

**The failures are pinpoint-reproducible.** Across three independent evaluation
seeds each layout stops at nearly the same route position, so a fixed geometric
feature is responsible rather than run-to-run variance.

| Layout seed | Maximum route completion per seed | Spread |
| --- | --- | ---: |
| 20025 | 0.122, 0.122, 0.122 | 0.000 |
| 20024 | 0.399, 0.400, 0.403 | 0.004 |
| 20045 | 0.639, 0.644, 0.646 | 0.007 |
| 20030 | 0.232, 0.238, 0.242 | 0.011 |
| 20041 | 0.182, 0.229, 0.229 | 0.047 |

**Clearance is ruled out.** At every failure point the route clears the nearest
hole by 9.4 to 20.1 mm, and no route in the split runs below 1 mm anywhere. Each
route's globally tightest point is somewhere other than where it fails. Wall
clearance at the failure points, 4 to 14 mm, is normal or generous against each
route's own median. The generator's 1.5 mm requirement is satisfied throughout.

**Every failure sits at a near-right-angle turn.** Measuring local heading
change against each route's own distribution:

| Layout seed | Turn at failure | Percentile within its route |
| --- | ---: | ---: |
| 20040 | 87.3 deg | 100 |
| 20058 | 85.1 deg | 100 |
| 20025 | 80.6 deg | 100 |
| 20045 | 84.8 deg | 99 |
| 20041 | 71.9 deg | 98 |
| 20024 | 58.9 deg | 96 |
| 20030 | 60.5 deg | 95 |

Seven of seven at or above the 95th percentile.

Sharp turns alone do not explain it, because every layout in the split has an
86 to 88 degree maximum turn. Two things distinguish the unsolved layouts:

| Group | Sharp-turn density | Hole distance at sharp turns |
| --- | ---: | ---: |
| 0 of 3 (7 layouts) | 0.049 | 9.6 mm |
| 1 or 2 of 3 (14 layouts) | 0.036 | 10.9 mm |
| 3 of 3 (43 layouts) | 0.036 | 12.1 mm |

The hole-distance gradient is monotone across all three groups. The mechanism is
that the policy overshoots at every sharp corner, and the overshoot is only
fatal when a hole sits within overshoot range. With seven layouts the medians
are suggestive rather than conclusive; the per-episode clustering above is the
strong evidence.

This unifies both termination modes. The ball leaves the route at a corner and
then either reaches a hole, recorded as a fall at about -12.5 mm clearance, or
wedges where maximum tilt cannot free it. On layout 20025 the ball is
stationary to within 0.001 in normalized units for the final 2,500 steps while
the commanded tilt stays saturated.

## The proximate cause is bang-bang control

Trajectory probes over the failing rollouts show the policy does not modulate:

| Quantity | Measured |
| --- | ---: |
| Mean absolute action | 0.88 to 0.93 of full range |
| Steps at saturation | 64% to 74% |
| Mean step-to-step action change | 0.49 to 1.19 |

Slamming the board is survivable on straight sections and cannot decelerate
into a right-angle corner. This is also a deployment concern for the Hiwonder
servos independent of the gate.

## Deterministic action selection does not help

`Agent.policy` samples from the actor distribution in `eval` mode, so held-out
evaluation injects action noise and the sampling stream advances across
episodes. A single episode is therefore not reproducible in isolation, and much
of the apparent per-layout churn between the 250k and 500k milestones was
evaluation noise rather than learning.

Acting on the distribution mode was tested against the same protocol and is
worse, so the saturation is the policy's own learned behavior rather than
sampling noise. The `eval_mode` policy branch and the evaluator's
`--policy-mode` flag are retained for future comparisons, and every result now
records which protocol produced it. **Sampling remains the default.**

| Protocol | Completion | Falls | Mean maximum route completion |
| --- | ---: | ---: | ---: |
| Sample, 192 episodes | 79.17% | 16.15% | 86.64% |
| Mode, 192 episodes | 77.08% | 17.19% | 85.51% |

## What follows

The corner diagnosis redirects the work away from generic tuning:

1. An `action_rate_penalty` reward term lets the policy modulate tilt instead of
   slamming it. Calibration is the risk: a full route earns 20 in progress and
   success reward, so at the measured chatter a penalty of 0.5 would cost about
   214 per episode and simply teach the policy to stop moving. The shipped arm
   uses 0.003, about 6% of the return, and a test guards that budget.
2. Privileged demonstrations should concentrate on high-curvature route
   segments of the training layouts rather than whole routes.
3. `train_ratio`, `failure_penalty`, and prioritized-replay sharpening remain
   available but do not address corner deceleration, so they are lower priority.

Tuning arms are ranked on a new 64-layout `dev` subset of the training layouts,
matched to the validation split's difficulty-band composition. The validation
split is reserved for gate decisions and the test split remains untouched.
Dev scores are optimistic because the policy trains on those layouts and are
only valid for ranking arms against each other.

Domain randomization stays locked. The mastery gate is unchanged.

## Outcome

The arms are recorded in
[NOMINAL_AB_ARMS_2026-07-28.md](NOMINAL_AB_ARMS_2026-07-28.md). In short, the
dense hole-margin term was the effective lever and reaches every gate threshold
on the dev split at 500k, cutting falls from 18.75% to 7.81% against a matched
no-penalty control, while the action-rate term reduced chatter by about 35%
without improving completion beyond noise.

Two claims in this document did not survive later measurement and are corrected
there: the near-right-angle corners are dynamically trackable, so no route
regeneration was performed, and the corner-geometry correlation is weak at
population scale.
