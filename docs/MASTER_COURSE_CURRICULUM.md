# Multi-skill master-course curriculum

This curriculum trains one route-conditioned policy on a deterministic family
of related courses. It does not train on one fixed maze and does not add a maze,
stage, zone, or skill identifier to the policy observation.

## Design contract

Every generated layout is checked for finite geometry, board bounds, and the
configured finite-ball route clearance. The immutable manifest hashes every
layout and keeps train, validation, and final-test geometry disjoint.

The five cumulative stages are:

| Stage | New experience | Cumulative training variants |
| --- | --- | ---: |
| Foundation | Launch, straight tracking, braking, gentle turn | 32 |
| Turns | Sharp turns and alternating S-curves | 64 |
| Recovery | Lateral displacement and cross-route velocity recovery | 96 |
| Hazards | Close holes and a narrow rail corridor | 128 |
| Compound | One long course joining all prior skills | 160 |

Default validation and final-test families add eight new disjoint variants per
stage. Scaling, mirroring, and bounded waypoint jitter prevent the controller
from memorizing one global action sequence while preserving the skill order.

Course-zone labels and reset conditions are training metadata only. The policy
continues to receive the deployed `image`, `states`, and relative `goal`
observations.

## Why the stages are cumulative

The stage-3 manifest contains foundation, turn, and recovery layouts. Stage 5
contains all five families. Earlier skills therefore remain in online replay
and validation instead of relying only on an old checkpoint. Recovery is the
only family with a displaced, moving reset; the other four families start at
the true route entrance. At the final stage, 80% of layout variants are thus
full-start anchors.

## Reward contract

The `tag_sim_v5_master_base` profile uses:

- progress reward scale 15;
- full-course completion bonus 20;
- failure penalty 10;
- small path, wall, and hole-clearance costs; and
- zero action-rate penalty.

This makes successful motion preferable to stationary low-action behavior. A
3,000-step limit keeps the long compound course bounded.

## Generate and verify

```bash
bash scripts/build_master_course_curriculum.sh
python -m unittest tag_mujoco.tests.test_master_course_curriculum -v
```

Generated files are reproducible and live under
`artifacts/master_course_curriculum/`, which is intentionally excluded from
Git. Build the same artifacts in the staged server checkout before training.

## Training order

Training and validation remain approval-gated. Foundation must start from
scratch. Every later stage requires an agent-only checkpoint from the
immediately preceding dataset.

The production ceilings total 4.5 million aggregate environment transitions:

| Stage | Maximum steps | Initialization |
| --- | ---: | --- |
| Foundation | 500,000 | Scratch |
| Turns | 750,000 | Accepted foundation weights |
| Recovery | 750,000 | Accepted turns weights |
| Hazards | 1,000,000 | Accepted recovery weights |
| Compound | 1,500,000 | Accepted hazards weights |

These are ceilings, not automatic promotion targets. Validation may select an
earlier checkpoint, but no later stage starts until the cumulative competence
and retention gate accepts its predecessor.

```bash
export TAG_TRAINING_APPROVED=YES
export TAG_VALIDATION_APPROVED=YES
bash scripts/start_master_course_stage.sh foundation

# After the validation gate accepts the selected foundation checkpoint:
bash scripts/start_master_course_stage.sh turns \
  /absolute/path/to/checkpoint.ckpt \
  /absolute/path/to/foundation_run
```

Repeat in order: `recovery`, `hazards`, then `compound`. Never select a
checkpoint from training return alone.

## Promotion gate

Run the fixed validation split, then evaluate the cumulative competence gate:

```bash
python tag_mujoco/master_course_gate.py \
  --report /absolute/path/to/canonical.json \
  --manifest artifacts/master_course_curriculum/stage_02_turns.json \
  --target-stage turns \
  --validation-root /absolute/path/to/run/validation \
  --output /absolute/path/to/turns_gate.json
```

The gate checks each included family independently. It requires sufficient
episodes, completion, route progress, and bounded falls. When a prior accepted
report is supplied with `--baseline-report`, earlier-family completion may not
drop by more than five percentage points.

Always pass `--validation-root`. Every other check reads a single evaluation
snapshot, so on its own the gate cannot distinguish a stage that never learned
from one that unlearned what it started with. With the validation history it
also refuses promotion when the stage ended more than two percentage points
below its own first evaluation, and it reports which checkpoint scored best
rather than assuming the last one did. Plateauing above the floors is not a
regression; a stage that reaches mastery and stops improving is finished.

## Foundation stage, first production attempt

The first `foundation` production run, `master_foundation_prod500k_seed7501`,
stopped itself at step 150,048 of 500,000 on the plateau gate. It is a useful
worked example of what these checks are for.

| Trigger step | Completion | Falls | Mean max route completion |
| ---: | ---: | ---: | ---: |
| 0 | 0.00 | 0.00 | 0.7289 |
| 50,000 | 0.00 | 0.00 | 0.5012 |
| 100,000 | 0.00 | 0.00 | 0.5012 |
| 150,000 | 0.00 | 0.00 | 0.5011 |

Every checkpoint scored worse than the untrained one, and no episode ever
completed or fell; they all ran out the 3000 step limit. The cause was
`path_tracking_cost`, which was unbounded above while every other hazard term
was clipped to [0, 1]. The run logged a mean path cost of 27.5 per step, so at
`path_tracking_penalty: 0.002` it charged roughly -165 per episode against a
positive budget of `progress_reward_scale` 15 plus `success_bonus` 20. Standing
still scored better than driving, and the policy learned exactly that.

The term is now bounded, with the budget pinned by tests in
`tag_mujoco/tests/test_hole_clearance_penalty.py`.

### What the 50k re-run showed

`master_foundation_smoke50k_pathclip_20260731` confirmed the reward fix and
exposed a second, deeper problem.

The reward fix worked. Mean path cost fell from 27.5 to at most 0.992, the best
validation layouts returned +3.30 and +3.20 against -160 to -181 before, and
training episodes reached 98% route progress instead of sitting at exactly 0.500.
The run also stopped exactly on its 50,000 step budget and exited cleanly.

Completion stayed at zero, and the reason was not the reward. Four of the eight
validation layouts reported `max_route_completion` of exactly 1.0 while
averaging 116 to 174 mm of cross-track error on a 259 by 229 mm board. Those two
numbers cannot both describe a ball following a 145 mm route.

`PolylineRoute.project` returns the nearest route point inside the along-route
window and reports the cross-track distance, but never used it to reject the
match, and `TagMazeTask` assigned the result unconditionally. Progress therefore
advanced no matter how far away the ball was. A ball parked 109 mm off the route
for an entire episode measured a perfect 1.0 route completion. Success stayed
false because that check is honest: it requires the ball center within
`goal_radius_m`, 8 mm, of the final waypoint, which a wandering ball never
satisfies.

So `mean_max_route_completion` was not measuring route following, and it is the
metric behind the plateau early stop, `PROGRESS_FLOOR`, and the stage trend
check. Two guards now exist:

- `TaskConfig.progress_corridor_m`, 40 mm, stops the environment crediting
  progress or paying progress reward while the ball is outside the route
  corridor. The value is the median on-route ball clearance measured over 40
  foundation layouts, where the 1st percentile is 23.5 mm.
- The gate refuses to accept route progress as evidence of tracking from any
  episode whose mean cross-track error exceeds that same corridor.

The second guard is not redundant. A ball that repeatedly dips into the corridor
can still ratchet progress forward, so the environment gate alone does not make
`max_route_completion` bulletproof.

Earlier results are not invalidated. The projection is honest for a ball that is
actually near the route, so the metric only misreports off-route episodes.

Resolved along the way: the flat validation curve in the 150k run was not a
stale-checkpoint artifact. All four milestones carry distinct `checkpoint_step`
values and distinct `checkpoint_sha256` digests, so validation was reading fresh
weights each time.

Do not inspect the test split during curriculum development. Use it only once
for the final selected foundation policy.

## Later maze refinement

Preserve the accepted compound checkpoint as an immutable foundation. For a
specific target maze, create a separate run using agent-only loading, a lower
actor/critic learning rate, and retained master-course experience. Do not
overwrite the foundation checkpoint or silently replace the disjoint final-test
evidence.
