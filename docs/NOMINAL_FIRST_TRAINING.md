# Nominal-first DreamerV3 training

This experiment proves full-route task mastery under fixed nominal PLA
dynamics before domain randomization is introduced.

## Fixed training contract

- 512 immutable training mazes and PLR maze sampling remain enabled.
- Every episode starts at the beginning of the route.
- Plant randomization and its curriculum are disabled.
- The preserved 13M agent weights are loaded without its step counter or replay.
- The new run starts at step zero with fresh nominal-only replay.
- Demonstrations are not required for the first bounded pilot.
- The 64-layout test split remains untouched.

The source checkpoint's 2026-07-28 PLA canonical baseline is 67.19% completion,
17.19% falls, and 82.15% mean maximum route completion over all 64 validation
mazes.

## Bounded pilot

The first run is limited to 500,000 steps on physical GPU 2. Canonical
validation runs on all 64 validation mazes at 250k and 500k. Robust evaluation
is intentionally not scheduled during this nominal optimization phase.

The pilot may continue in another bounded block when completion improves by at
least three percentage points or falls decrease by three points, provided hard
maze mean maximum progress does not regress by more than five points.

## Mastery gate

Domain randomization remains locked until a candidate is confirmed over three
fixed evaluation seeds per maze (192 episodes) and satisfies all of:

- overall completion at least 90%;
- hard-maze completion at least 80%;
- fall rate at most 10%;
- mean maximum route completion at least 95%; and
- every difficulty band at least 75% completion.

Use `tag_mujoco/nominal_training_gate.py` to record the bounded-continuation and
mastery decisions. Passing a single 64-episode validation can justify another
bounded nominal block, but cannot claim mastery.

After mastery, introduce plant randomization in separately reviewed stages
from strength 0.10 through 1.00. Preserve the best nominal checkpoint even if a
later DR stage is accepted.

## Active pilot

The approved 500k pilot started on 2026-07-28:

```text
/home/tn22833/cyberrunner_logs/
nominal_fullstart_13m_500k_20260728_134149
```

It uses the DreamerV3 environment at
`/home/tn22833/TAG_dreamerv3_smoke_20260723/.venv`, physical GPU 2 for
training, and physical GPU 3 for canonical validation. The monitor schedule is
exactly 250k and 500k; no robust evaluation is scheduled.

An earlier directory ending in `134018` is a preserved failed launch caused by
selecting the vision-only Python environment, which does not contain JAX. It
exited before writing `config.yaml` or starting validation and is not a
training result.

## Pilot outcome and mastery-gate result

The pilot completed all 500,000 steps and both scheduled validations. Its
single-seed milestones improved substantially over the frozen 13M baseline,
reaching 82.81% completion and 90.72% mean maximum route completion at 500k.

The 192-episode mastery gate was then run on the 500k checkpoint and **fails
every criterion**: 79.17% completion, 16.15% falls, 86.64% mean maximum route
completion, 73.02% hard-maze completion, and 73.02% in both the medium and hard
bands. Single-seed canonical milestones are not gate predictions.

Seven of the 64 validation layouts never succeed on any of the three seeds, so
completion cannot exceed 89.1% until those specific layouts are solved. All
seven fail at a route turn in its own 95th percentile or above, while hole and
wall clearance at those points is normal or generous. The policy is bang-bang
there and cannot decelerate into a near-right-angle corner.

See [NOMINAL_DIAGNOSIS_2026-07-28.md](NOMINAL_DIAGNOSIS_2026-07-28.md) for the
full evidence and the refuted deterministic-action hypothesis.

## Mastery gate passed by the hole-margin arm

Adding a dense hole-margin reward term produced a checkpoint that satisfies every
mastery criterion over the 192-episode protocol: 90.10% completion, 6.25% falls,
95.57% mean maximum route completion, 88.89% hard-maze completion, and no band
below 88.89%. No validation layout fails all three seeds any more, so the 89.1%
structural ceiling is gone.

```text
/home/tn22833/cyberrunner_logs/ab_nominal_holeaware_20260728_155619/
validation/step_000500000/checkpoint.ckpt
```

Completion passed by one episode, 173 of 192, so **domain randomization stays
locked until a second confirmation at different evaluation seeds holds.** The
thresholds themselves are unchanged. See
[NOMINAL_AB_ARMS_2026-07-28.md](NOMINAL_AB_ARMS_2026-07-28.md) for the arm
comparison, the reward calibration, and the hypotheses that were rejected.
