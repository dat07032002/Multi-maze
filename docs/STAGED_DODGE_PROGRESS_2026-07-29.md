# Staged dodge curriculum progress — 2026-07-29

This note records the state after switching from direct scratch dodge training
to a staged progress-first curriculum.

## Code and dataset changes

Latest pushed implementation commit at the time of this note:

- `f9f0710 Add staged scratch dodge curriculum`

Implemented:

1. Single-path maze topology:
   - no loop shortcuts;
   - one cell-level route from start to goal.
2. Wrong-branch blocker holes:
   - purple-ring holes stop dead branches.
3. Dodge route hazards:
   - red-ring holes sit near the old centerline;
   - the safe route bends around them.
4. Staged scratch profiles:
   - `tag_sim_v2_singlepath_progress`
   - `tag_sim_v2_branch_blockers`
   - `tag_sim_v2_dodge_progress`
   - `tag_sim_v2_easy_dodge_holes`
5. Launcher routing:
   - each stage points to its own manifest/dataset id.
6. Tests:
   - local full test suite passed: `127 OK`;
   - server staged profile/manifest tests passed: `12 OK`.

New tracked manifests:

- `tag_mujoco/generated_singlepath_progress_mazes/maze_splits_progress.json`
- `tag_mujoco/generated_branch_blocker_mazes/maze_splits_branch_blockers.json`
- `tag_mujoco/generated_dodge_mazes/maze_splits_dodge.json`

Local preview montages, not tracked:

- `artifacts/singlepath_progress_previews/singlepath_progress_montage.png`
- `artifacts/branch_blocker_previews/branch_blocker_montage.png`
- `artifacts/dodge_maze_previews/dodge_maze_overlay_montage.png`

## Why we changed the curriculum

The direct scratch dodge run learned a bad local optimum: safe but stuck.

Evidence from `scratch_singlepath_dodge_250k_20260729_155153`:

| Checkpoint | Completion | Fall rate | Mean route progress | Cross-track |
|---|---:|---:|---:|---:|
| 0 | 0% | 16.7% | 30.1% | 70.6 mm |
| 25k | 0% | 0% | 33.2% | 51.6 mm |
| 50k | 0% | 8.3% | 7.6% | 29.6 mm |
| 75k | 0% | 0% | 0.3% | 16.0 mm |

Interpretation: path/wall/hole safety improved, but forward progress collapsed.
So longer training with that exact reward would likely train the policy to sit
near the start/path rather than solve the maze.

The new curriculum teaches:

1. move forward first;
2. avoid wrong branches;
3. dodge route hazards;
4. then clean up path/wall style.

## Server checkout

Server:

- `tn22833@aere-a83514.ae.utexas.edu`

Clean staged repo:

- `/home/tn22833/Multi-maze`

Training Python:

- `/home/tn22833/TAG_dreamerv3_smoke_20260723/.venv/bin/python`

Current server checkout:

- branch: `nominal-hole-margin-gate-pass`
- commit: `f9f0710`

## Runs so far

### 1. Direct scratch dodge pilot

Run:

- `scratch_singlepath_dodge_250k_20260729_155153`
- profile: `tag_sim_v2_easy_dodge_holes`
- steps: `255,336`
- status: training exited `0`
- best monitored checkpoint: `25k`

Result:

- 0% completion through evaluated milestones;
- route progress collapsed after 25k;
- useful as diagnosis, not as a keeper policy.

### 2. Stage 1 250k pilot

Run:

- `stage1_singlepath_progress_250k_20260729_170406`
- profile: `tag_sim_v2_singlepath_progress`
- steps: `254,160`
- status: training exited `0`; validation monitor exited `0`

Training signal at the end:

- final logged episode succeeded;
- episode length: `1010`
- score: `16.78`
- mean progress signal: `0.983`
- cross-track error: `15.2 mm`

Full-start dev validation:

| Checkpoint | Completion | Fall rate | Mean route progress | Cross-track |
|---|---:|---:|---:|---:|
| 0 | 0% | 0% | 24.9% | 52.7 mm |
| 125k | 0% | 0% | 16.6% | 44.1 mm |
| 250k | 0% | 0% | 19.3% | 34.2 mm |

Result:

- train-from-goal/local success works;
- full-start solving did not emerge in 250k;
- monitor marked plateau;
- best by validation remained baseline `0`.

Interpretation:

- Stage 1 is directionally better than direct dodge because it learns local
  goal-reaching behavior;
- but 250k and the tiny 4-maze train split are not enough for full-route
  validation.

### 3. Stage 1 1M run on free GPU

Run:

- `stage1_singlepath_progress_1m_gpu1_20260729_173747`
- profile: `tag_sim_v2_singlepath_progress`
- steps requested: `1,000,000`
- GPU: `1`
- training PID at launch: `3257189`
- validation monitor PID at launch: `3259493`
- validation schedule: `0`, `500k`, `1M`
- status at last check: running

Last observed training metrics:

- step: `22,456`
- fps: `205.18`
- score: `1.67`
- success: `0`
- mean progress signal: `0.987`
- cross-track error: `16.9 mm`

This run is intended to test whether longer Stage 1 training converts
train-from-goal/local success into full-start progress.

## Current recommendation

Do not move to branch blockers or dodge holes yet.

Wait for the `500k` and `1M` validation from
`stage1_singlepath_progress_1m_gpu1_20260729_173747`.

If full-start completion or route progress improves, continue Stage 1 from the
best validated checkpoint. If validation is still flat, revise Stage 1 before
spending long training time:

- increase full-start probability;
- increase the number of Stage 1 training layouts toward the old serious scale
  (`512/64/64`);
- possibly lower/disable PLR until forward motion is stable;
- optionally add a simpler short-route Stage 0 before the current Stage 1.

