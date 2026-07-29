# Safe-path dodge curriculum

Goal: teach the TAG policy to track a planned safe route, actively dodge holes
that obstruct the old centerline, and use walls only as backup rails.

## Stage workflow

Every skill stage uses the same continuation contract:

1. warm-start from the best checkpoint so far;
2. load agent weights only;
3. reset optimizer state;
4. start a fresh replay buffer;
5. seed replay with selected successful prior experience;
6. collect new experience for the current skill;
7. validate at fixed milestones;
8. select the best validated checkpoint, not the last checkpoint.

## Skill stages

1. `tag_sim_v2_singlepath_progress`
   - scratch stage;
   - single-path topology;
   - no holes yet;
   - train-from-goal/random starts enabled;
   - progress reward dominates, with no path/wall style penalty.

2. `tag_sim_v2_branch_blockers`
   - warm-start from the best Stage 1 checkpoint;
   - wrong branches are stopped by blocker holes;
   - route hazards are still absent;
   - progress remains the dominant objective.

3. `tag_sim_v2_dodge_progress`
   - warm-start from the best Stage 2 checkpoint;
   - red route-hazard holes are introduced;
   - path/wall penalties are deliberately light so the policy keeps moving.

4. `tag_sim_v2_easy_dodge_holes`
   - warm-start from the best Stage 3 checkpoint;
   - same dodge layouts;
   - stronger path-centering, hole-clearance, and wall-riding shaping;
   - use this only after progress is healthy.

5. `tag_sim_v2_safe_path_tracking`
   - normal safe-path tracking;
   - gentle path-centering penalty;
   - gentle wall-riding penalty;
   - no domain randomization.

6. Tight dodge holes
   - future stage;
   - smaller margins and harder layouts after easy dodge is reliable.

7. Mixed hard mastery
   - future stage;
   - normal hard mazes plus dodge mazes.

8. Domain randomization
   - future stage;
   - only after nominal safe-path and dodge success are high.

## Why the scratch stages are progress-first

The first scratch dodge pilot reached 0% completion. Its best route progress was
early, then collapsed from 33.2% at 25k to 0.3% at 75k while falls and
cross-track error improved. That means the policy discovered a local optimum:
stay safe and near the path, but stop moving. The staged curriculum prevents
that by teaching forward progress before adding blocker holes, dodge holes, and
clean-driving penalties.

## Layout overlay convention

- cyan: replanned safe path used for training;
- orange dashed: original centerline route that is now blocked/unsafe;
- red-ring holes: dodge-required route hazards;
- purple-ring holes: wrong-branch blockers.

## Reward direction

The desired behavior is:

```text
 progress along the safe path
- cross-track/path error
- hole proximity
- sustained wall riding
- action oscillation
+ goal bonus
- fall penalty
```

Walls are not forbidden. Brief contact is allowed, but long wall-riding should
not be the main control strategy.
