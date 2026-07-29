# Curriculum DR and attribution

The first curriculum-DR run is exploratory and capped at strength 0.25. It
starts at 0.05, advances by 0.05 only after a worker achieves at least 75%
success over 100 completed episodes, uses full-route starts, and retains the
0.02 dense hole-clearance penalty.

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
