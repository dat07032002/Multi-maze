# CyberRunner MuJoCo Prototype

This isolated prototype reconstructs the current printed maze directly from
`cyberrunner_layout_custom.py`. It does not change the ROS, Hiwonder, or trained
DreamerV3 paths.

The first milestone contains:

- a two-axis actuated board;
- a steel ball with rolling, sliding, and torsional friction;
- procedural wall collision geometry;
- physical floor openings for all holes;
- a fixed top-down camera; and
- automated level, tilt, wall, and hole checks.

The completed system layer additionally contains:

- the active Hiwonder absolute-position command conversion;
- driver delay, update-rate, deadband, and rate limiting;
- uncertain servo/linkage response and parameter randomization;
- the calibrated camera's ball-centered 64 x 64 grayscale policy observation;
- synchronized observation delay and detection dropout;
- per-maze relative route targets; and
- an RL-independent step/reset/termination API.

The clean training layer now also contains:

- `hardware_parameters.json`, where every hardware value is tagged as design,
  extracted-but-unverified, inferred, datasheet, or measured;
- `route_planner.py`, which plans for the finite-radius ball and validates the
  complete swept route against walls, holes, and board boundaries;
- `cyberrunner_env.py`, a new normalized Gym task that does not inherit the
  legacy ROS/TCP reward or replay implementation;
- a direct DreamerV3 Embodied adapter using standard uniform replay; and
- an approval-gated GPU-1 launcher that cannot start training accidentally.

See [`MODEL.md`](MODEL.md) for parameter sources and explicit assumptions.

## Setup on Windows

```powershell
cd cyberrunner_mujoco
uv venv --python 3.11 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
```

## Verify and render

```powershell
.venv\Scripts\python.exe verify_physics.py
.venv\Scripts\python.exe render_demo.py
.venv\Scripts\python.exe verify_system_model.py
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe verify_training_readiness.py
.venv\Scripts\python.exe verify_dreamer_adapter.py
```

Open the live desktop viewer:

```powershell
.venv\Scripts\python.exe view_interactive.py
```

Open one of the generated full-board mazes instead:

```powershell
.venv\Scripts\python.exe view_interactive.py --layout generated_mazes\maze_seed_970.json
```

Open the complete delayed Hiwonder model rather than the direct-tilt physics
viewer:

```powershell
.venv\Scripts\python.exe view_system_model.py --layout generated_mazes\maze_seed_970.json
```

Add `--randomize --seed 42` to inspect one reproducible randomized plant.

Viewer controls:

- `W` / `S`: tilt the X axis by one degree;
- `A` / `D`: tilt the Y axis by one degree;
- `C`: center the board;
- `R`: reset the board and ball; and
- mouse controls: orbit, pan, and zoom using the standard MuJoCo viewer.

Generated images and JSON verification results are written to `outputs/`.

## Training approval gate

No Dreamer training is started by any verification command. The Linux server
launcher exits unless approval has been recorded explicitly:

```bash
export CYBERRUNNER_TRAINING_APPROVED=YES
scripts/run_cyberrunner_dreamerv3_gpu2.sh
```

The approved launcher exposes only physical GPU 2. Physical GPU 0 is never visible to
the process. Start with the `cyberrunner medium` DreamerV3 configuration and a
training ratio of 32. Do not set the approval variable before the user approves
each requested training run. Dataset generation, evaluation, and readiness
checks never set this variable.

## Multi-maze dataset and evaluation

`maze_splits.json` is an immutable manifest containing 40 training mazes, 8
validation mazes, and 8 test mazes. Seed 970 remains in training; seed 1024 is
validation-only and seed 765 is test-only. Every layout has a SHA-256 digest,
finite-ball route-clearance result, and geometric difficulty metadata. The
three main splits are checked for leakage whenever the manifest is loaded.

Rebuild the deterministic dataset without deleting older generated layouts:

```powershell
.venv\Scripts\python.exe build_maze_dataset.py
```

During training, one maze is sampled at each episode reset. The curriculum
starts with an easy-layout bias, retains nonzero probability for every training
maze, and becomes uniform after the configured number of episodes. Validation
and test layouts never enter the replay buffer.

Run a non-learning held-out baseline before requesting training:

```powershell
.venv\Scripts\python.exe evaluate_multimaze.py --policy random --split validation --max-steps 300
```

The report includes completion rate, maximum route completion, cross-track
error, fall rate, minimum clearance, return, and results by difficulty band.

### Fixed-step Dreamer validation

`validation_monitor.py` watches a running Dreamer log directory without
changing the learner or replay. It takes a size- and timestamp-stable copy of
the first checkpoint written after each 500,000-step threshold, records a
SHA-256 digest, and evaluates the copied agent on all eight validation mazes.
Canonical evaluation runs on physical GPU 3. At each 1,000,000-step threshold,
a three-seed randomized robustness evaluation runs concurrently on physical
GPU 4. Both workers use fixed seeds and Dreamer's evaluation policy mode.

Results are written below the training log directory in `validation/` as
per-milestone JSON, `history.csv`, `history.jsonl`, and
`best_checkpoint.json`. Validation layouts never enter replay, and the test
split is reserved for the final selected checkpoint.

The status-tracked remote entry point is:

```bash
CYBERRUNNER_VALIDATION_APPROVED=YES \
  scripts/start_remote_validation_monitor.sh REPO_ROOT DREAMER_LOGDIR
```

## Generate different full-board mazes

The procedural generator keeps every maze at the fixed printable footprint of
259 x 229 mm. It creates a dense connected 12 x 10 cell maze using randomized
depth-first search, adds limited alternate routes, computes the shortest
start-to-goal route, and places up to 30 holes in branch cells close to—but not
on—the verified route. Seeded variations in corridor width make the geometry
less uniform while retaining safe ball clearance.

```powershell
.venv\Scripts\python.exe generate_examples.py
```

The example seeds are deterministic: the same seed always produces the same
walls, holes, and route. Generated JSON and MJCF files are saved under
`generated_mazes/`. The JSON is intended to become the shared source for
simulation, Dreamer training, and future printable mesh generation.

The comparison image places the original maze beside three dense generated
mazes. The original has 56 recorded route waypoints; the selected generated
examples have 49--53 computed waypoints and the same 30-hole count.

The blue route in each plan is the graph's verified shortest route. Green is
the start, red is the goal, and black circles are physical holes. Validation
checks fixed dimensions, route connectivity, route/hole separation, stable
level-board placement, and that a ball placed over a hole actually falls.

## Modeling choices

The source layout stores the line edges extracted from the printed-maze DXF,
not ready-made solids. Each sufficiently long edge is represented by a narrow
box geom. The floor is built from horizontal collision strips that stop at the
circular hole boundaries, allowing the ball to physically fall through.

The constants in `simulator.py` are initial estimates. Friction, contact
compliance, servo response, and wall dimensions must later be calibrated using
real trajectories before simulation-trained policies are transferred safely.

The active multi-maze reward is dense scaled route progress plus an explicit
goal bonus and fall penalty. A complete route contributes 10 progress-reward
units before the 10-unit goal bonus. Falls subtract 5 units. Cross-track error
and obstacle clearance remain separately logged safety measurements rather
than hidden shaping terms. The original unit-scale progress reward remains
available as `reward_mode: progress` for controlled comparisons.
