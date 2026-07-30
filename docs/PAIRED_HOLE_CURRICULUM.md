# Paired no-hole to hole curriculum

This curriculum trains navigation before hazard avoidance. Domain
randomization is disabled in every phase. The builder generates wide candidate
topologies and accepts a seed only if all four hole variants have safe
finite-ball routes. The resulting fixed 512/64/64 split preserves walls, start,
goal, and split membership across phases while changing only holes and, when
necessary, the replanned safe route.

## Build datasets

Generated layouts are intentionally ignored by Git:

```bash
TAG_PYTHON=/path/to/python \
bash scripts/build_paired_hole_curriculum.sh
```

Outputs:

| Variant | Purpose |
| --- | --- |
| `no_holes` | route learning with no fall hazards |
| `branch_holes` | visible holes away from the valid route |
| `easy_dodge` | one route-adjacent hazard and a safe replanned route |
| `mixed_holes` | retained branch holes plus two route hazards |

The builder validates every saved route with the finite-ball clearance planner.
It fails instead of emitting an unsafe or incomplete paired dataset.

## Nested no-hole exposure stages

The first full-start 512-map run completed only about 505 episodes, while each
of its eight workers kept independent PLR state. Most layouts therefore stayed
locally unseen and were not practiced to mastery. Build deterministic nested
groups from the same no-hole training split:

```bash
TAG_PYTHON=/path/to/python \
bash scripts/build_grouped_nohole_curriculum.sh
```

The order balances the two initial route directions and takes the easiest
layouts first. Stages contain 16, 32, 64, 128, and 512 maps. Sampling is uniform
within a stage, every episode starts at the true entrance, and each later stage
warm-starts agent weights with bounded retained replay from the accepted prior
stage.

Launch the scratch pilot:

```bash
export TAG_TRAINING_APPROVED=YES
export TAG_VALIDATION_APPROVED=YES
export TAG_PYTHON=/path/to/repo/.venv/bin/python
bash scripts/start_grouped_nohole_stage.sh 16
```

Do not expand the group merely because its step budget ended. Promote only
after the stage's `dev` mastery evaluation demonstrates actual goal completion.

## Training phases

| Phase | Profile | Ceiling | Screen interval | Promotion target |
| ---: | --- | ---: | ---: | --- |
| 1 | `tag_sim_v2_phase1_noholes_fullstart_scratch` | 1.5M | 250k | 80% completion, 90% progress |
| 2 | `tag_sim_v2_phase2_noholes_fullstart` | 2M | 250k | 90% completion, 95% progress |
| 3 | `tag_sim_v2_phase3_branch_holes` | 1M | 250k | 90% completion, ≤10% falls |
| 4 | `tag_sim_v2_phase4_easy_dodge` | 2M | 250k | 80% completion, ≤15% falls |
| 5 | `tag_sim_v2_phase5_mixed_holes` | 5M | 500k | 90% completion, ≤10% falls |

All profiles use float32, train ratio 8, conservative optimizers, fixed nominal
plant parameters, and the finite replay/training health checks. Phase 1 starts
from scratch and every episode starts at the true maze entrance; it does not
sample near-goal starts. Phases 2–5 require agent-only loading, reset optimizer state, and
25k retained replay transitions from the accepted source run before collecting
new phase experience.

Launch Phase 1:

```bash
export TAG_TRAINING_APPROVED=YES
export TAG_VALIDATION_APPROVED=YES
export TAG_PYTHON=/path/to/repo/.venv/bin/python
bash scripts/start_paired_hole_phase.sh 1
```

Launch a later phase only after promotion:

```bash
bash scripts/start_paired_hole_phase.sh \
  3 \
  /path/to/accepted/checkpoint.ckpt \
  /path/to/accepted/source_run
```

The launcher monitors the 64-layout validation split at fixed milestones and
may stop a three-milestone plateau. It never launches the next phase
automatically.

## Promotion and retention

Milestone evaluations use one episode per validation layout for screening. A
candidate must then be evaluated for three episodes per layout (192 episodes)
and passed through:

```bash
python tag_mujoco/curriculum_phase_gate.py \
  --phase 2 \
  --candidate /path/to/candidate_192.json \
  --output /path/to/phase2_gate.json
```

Phases 3–5 also require paired evaluation on the previous accepted dataset:

```bash
python tag_mujoco/curriculum_phase_gate.py \
  --phase 4 \
  --candidate /path/to/easy_dodge_192.json \
  --retention-baseline /path/to/phase3_champion_on_retention_192.json \
  --retention-candidate /path/to/phase4_candidate_on_retention_192.json \
  --output /path/to/phase4_gate.json
```

Retention permits at most 0.02 absolute completion loss and 0.01 mean maximum
route-progress loss. The best validated checkpoint is promoted; the final
checkpoint is never selected merely because it is latest.

No test split is used for tuning. Domain randomization remains a separate,
future phase after Phase 5 passes nominal mastery.
