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

1. `tag_sim_v2_safe_path_tracking`
   - normal safe-path tracking;
   - gentle path-centering penalty;
   - gentle wall-riding penalty;
   - no domain randomization.

2. `tag_sim_v2_easy_dodge_holes`
   - generated dodge layouts;
   - maze topology has no loop shortcuts, so there is only one cell-level route
     from start to goal;
   - wrong branches are stopped by blocker holes;
   - dodge holes are placed near the old centerline;
   - the continuous planner replans a safe path around them;
   - reward tracks the replanned safe path.

3. Tight dodge holes
   - future stage;
   - smaller margins and harder layouts after easy dodge is reliable.

4. Mixed hard mastery
   - future stage;
   - normal hard mazes plus dodge mazes.

5. Domain randomization
   - future stage;
   - only after nominal safe-path and dodge success are high.

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
