# Curriculum DR and attribution

The first curriculum-DR run is exploratory and capped at strength 0.25. It
starts at 0.05, advances by 0.05 only after a worker achieves at least 75%
success over 100 completed episodes, uses full-route starts, and retains the
0.02 dense hole-clearance penalty.

## Outcome of the first run

Run `holeaware_curriculum_dr_100k_20260729_v3` completed collection at about
101k counted environment steps, but it is **not a valid training result**:

- model, actor, and critic losses were NaN at the first reported update;
- all three optimizer `grad_steps` counters remained zero for the full run;
- the mixed-precision gradient scale fell from 10,000 to its `1e-4` floor;
- the DR strength remained 0.05; and
- 127 of 146 collected episodes succeeded, but these successes do not
  demonstrate policy learning.

The failure was in replay serialization/import, not in the valid source
transitions. Partial chunks preallocated arrays for 1,024 transitions and saved
the entire backing arrays instead of only their initialized prefix. The valid
length was encoded in the filename, but demonstration import ignored it and
treated all 1,024 slots as data. Of 906 source files, 185 contained arbitrary
non-finite values only after their declared valid length; all 906 valid prefixes
are finite. Uniform selection chose seven such partial files, and the old
importer fed their uninitialized tails to training.

The same storage artifact explains the apparent non-finite values in newly
saved replay. It was not evidence that a NaN policy propagated through the
environment. Chunk save/load and demonstration import now slice to the declared
valid length, while finite checks still reject any non-finite value inside that
valid prefix.

The curriculum also could not advance independently of that failure. Each of
the eight process-local environments owns its own 100-episode success window.
The whole run produced only 146 episodes, about 18 per worker on average, so no
worker could fill its window.

Do not resume from any checkpoint produced by this run. The unchanged source
champion remains:

```text
/home/tn22833/cyberrunner_logs/ab_nominal_holeaware_20260728_155619/validation/step_000500000/checkpoint.ckpt
```

## What is measured

Every episode logs its actual sampled actuator, physics/contact, and camera
values as `log_dr_*` metrics. These support plots and rank correlations against
success, falls, and route completion. They are observational: curriculum
strength, maze difficulty, and multiple simultaneous samples can confound a
raw correlation.

At selected checkpoints, `scripts/run_dr_attribution.sh` evaluates the same
policy and seeds in five conditions:

1. canonical (no DR);
2. all DR families;
3. actuator only;
4. physics/contact only;
5. camera only.

The family deltas in `report.json` are the causal diagnostic because all other
conditions are held fixed. `scalar_associations_observational` then ranks the
individual sampled values within the all-DR sweep. Use the family result to
choose the next ablation, and the scalar ranking to decide which parameter
inside that family to narrow or split in the next experiment.

## Completed attribution results

All rows use the same 64-layout dev split, seed 20260731, sampled-action
protocol, and fixed DR strength 0.25.

| checkpoint | condition | completion | falls | mean max progress |
|---|---|---:|---:|---:|
| source | canonical | 0.890625 | 0.093750 | 0.952050 |
| source | all | 0.796875 | 0.156250 | 0.896880 |
| source | actuator | 0.796875 | 0.140625 | 0.876675 |
| source | physics | 0.921875 | 0.062500 | 0.967123 |
| source | camera | 0.890625 | 0.093750 | 0.931818 |
| 50k | canonical | 0.890625 | 0.093750 | 0.952050 |
| 50k | all | 0.796875 | 0.156250 | 0.896880 |
| 50k | actuator | 0.796875 | 0.140625 | 0.876675 |
| 50k | physics | 0.921875 | 0.062500 | 0.967123 |
| 50k | camera | 0.890625 | 0.093750 | 0.931818 |
| 100k | canonical | 0.890625 | 0.093750 | 0.952050 |
| 100k | all | 0.796875 | 0.156250 | 0.896880 |
| 100k | actuator | 0.796875 | 0.140625 | 0.876675 |
| 100k | physics | 0.859375 | 0.109375 | 0.942721 |
| 100k | camera | 0.890625 | 0.093750 | 0.931818 |

The 50k matrix is exactly equal to the source matrix. Source and 100k
physics-only evaluations were each repeated and reproduced their respective
results exactly, so the 100k physics regression is real checkpoint-state
drift, not a partial evaluation.

Checkpoint inspection shows why it must not be called policy learning. The
actor, encoder, RSSM, and other acting parameters remained byte-identical.
Only 14 return-normalization, slow-critic, and critic-update variables changed
between the source and 100k checkpoints while the optimizer update counters
remained zero. The attribution result therefore measures invalid ancillary
state drift after NaN train calls.

The reliable source-policy conclusion is:

- actuator DR is the main causal weakness: completion decreases by 0.09375,
  falls increase by 0.046875, and mean max progress decreases by 0.075375;
- camera DR leaves completion and falls unchanged but decreases progress by
  0.020231; and
- source-policy physics DR improves this particular fixed-seed sweep, but the
  invalid 100k state shows that it must be rechecked after every real training
  stage.

Scalar correlations inside the all-DR condition remain hypothesis generators,
not causal effects. The next actuator analysis must separate timing/gain,
linkage/coupling/offset, and stiction rather than training against the full
actuator family and guessing afterward.

## Corrected training plan

This plan is deliberately checkpoint-gated. A 100k budget is a ceiling earned
by shorter successful stages, not a command to run blindly.

### Gate 0: make invalid data impossible to train on

Before another run:

1. Validate every numeric array in every replay chunk with `isfinite`.
2. Quarantine an entire bad chunk; do not repair individual transitions or
   silently replace NaNs with zero.
3. Print and save selected, accepted, rejected, and per-key non-finite counts.
4. Validate sampled training batches again immediately before the agent sees
   them.
5. Abort with a nonzero status if any input, loss, gradient norm, or policy
   action is non-finite.

Keep the source champion, but build a new sanitized replay manifest. Never
reuse the v3 replay or its 50k/100k checkpoints.

Implemented safeguards now enforce this gate in the replay loaders, replay
buffers, JAX policy/training wrapper, and main training loop. The runnable
float32 profile is `tag_sim_v2_clean_smoke`; its guarded launcher is
`scripts/start_clean_training_smoke.sh`. The old curriculum launcher exits
without starting training.

The first clean smoke completed successfully at step 2,752 (the 2k ceiling is
checked at episode boundaries). All three optimizers had finite losses and
gradient norms, their counters advanced, and the 99-variable acting digest
changed. A post-run audit found zero non-finite values inside the valid prefix
of every replay file. With the corrected length-aware importer, the source
selection supplies 25,000 valid transitions from 34 files with zero rejected
files.

Numerical success did not earn policy promotion. On the paired 64-maze
canonical gate, completion and falls remained 0.890625 and 0.093750, but mean
maximum route completion fell from 0.952050 to 0.937121. The -0.014928 change
fails the -0.01 progress tolerance. The planned 10k continuation therefore
remains blocked and DR stays disabled.

### Gate 1: prove that optimization works

Run a maximum 2k-step nominal smoke from the source champion:

- DR off;
- fresh optimizer state;
- float32 compute for the first diagnostic;
- sanitized source replay plus clean fresh collection;
- the existing conservative learning rates and warmup.

Promotion requires all of the following:

- the first model, actor, and critic losses and gradient norms are finite;
- every optimizer `grad_steps` counter increases;
- learned actor/world-model hashes change by optimizer step 2, after the
  intentionally zero first warmup learning rate;
- sampled actions and newly written replay remain finite; and
- the run terminates automatically if any counter stalls for three reported
  updates.

If this fails, isolate with one sanitized-source-only batch and one
fresh-only batch. Do not increase the step budget. If float32 passes, a
separate short float16 smoke may be used to validate mixed precision; float16
must not be assumed safe.

### Gate 2: nominal continuation

Run 10k counted steps with DR still off. Evaluate the fixed 64-layout canonical
dev matrix at 0, 2k, and 10k. Promote only if:

- canonical completion loses no more than one of 64 successes;
- canonical falls increase by no more than one of 64 episodes;
- mean max progress does not decrease by more than 0.01; and
- all numerical and learned-hash gates continue to pass.

This stage proves continuation stability before DR is allowed to explain any
change.

### Gate 3: evaluation-gated actuator curriculum

Replace the process-local 100-episode auto-curriculum with explicit
checkpoint stages. This is simpler, observable, and shared across all workers.

1. Add causal actuator selectors for:
   - timing/gain: delay, response, and servo units;
   - geometry/linkage: directional maps, cross-axis coupling, and zero offset;
   - stiction.
2. Evaluate those subfamilies at fixed strengths before training. Use the same
   mazes and paired seeds.
3. Train only the worst verified subfamily for 10k steps at strength 0.025.
4. If it passes, continue for 15k at 0.05.
5. Consider 0.10 for another 25k only after another promotion pass.

At each boundary, run canonical, all-actuator, and the active actuator
subfamily. Promotion requires the canonical gate above and either at least two
additional actuator successes out of 64 or a mean max progress improvement of
at least 0.02 without more falls.

### Gate 4: add the lower-priority families

Only after actuator improvement:

- recheck physics-only at 0.25; add physics training only if a paired
  multi-seed result shows a remaining weakness;
- introduce camera blur/noise at 0.10 separately from appearance changes; and
- do not enable full all-family DR at 0.25 until each family passes alone.

Use one fixed seed for fast stage screening. Any candidate that will become a
new champion must then pass a three-seed, 192-episode confirmation on canonical
and target-DR conditions.

### Stop, rollback, and budget rules

Stop immediately and retain the previous promoted checkpoint when:

- any non-finite value appears;
- any optimizer counter stalls;
- acting-parameter hashes fail to change after reported valid updates;
- the canonical gate fails;
- target-family falls worsen without compensating completion; or
- a requested DR stage is not actually observed in episode telemetry.

The planned budget is therefore 2k diagnostic + 10k nominal + 10k/15k/25k
conditional DR stages. Continue toward 100k only if every earlier checkpoint
earns promotion. Attribution runs are evaluation only and do not count as
training.

## Run command

```bash
TAG_PYTHON=/path/to/python \
TAG_ATTRIBUTION_STRENGTH=0.25 \
bash scripts/run_dr_attribution.sh \
  /path/to/checkpoint.ckpt \
  /path/to/config.yaml \
  /new/output/directory \
  50000
```

Do not compare reports made with different checkpoint hashes, seeds, policy
action modes, split definitions, or attribution strengths.
