# Multi-maze TAG DreamerV3

One route-conditioned DreamerV3 policy for a physical ball-maze robot. Trained
in MuJoCo on a UT Austin GPU server, deployed on TAG hardware over ROS 2. The
policy sees `image`, `states`, `goal` (5 future route points) — never a maze,
skill, or stage ID. Board is 259 x 229 mm.

## Where things are

| Path | What |
| --- | --- |
| `tag_mujoco/` | Simulator, maze generators, curricula, gates, tests. The center of gravity. |
| `tag_mujoco/tag_env.py` | `TaskConfig`, reward and cost functions, `TagMazeTask`/`TagMazeEnv` |
| `tag_mujoco/gate_criteria.py` | Shared promotion tolerances (single source of truth) |
| `tag_mujoco/policy_contract.py` | `tag_hardware_policy_v1` — obs/action contract shared with hardware |
| `dreamerv3/` | Maintained fork; `embodied/envs/tag_maze.py` is the adapter, `configs.yaml` the profiles |
| `scripts/` | Server launchers (`start_*`, `build_*`, `run_*`) and `server_status.sh` |
| `tag_camera/ tag_state_estimation/ tag_hiwonder/ tag_interfaces/ tag_dreamer/` | ROS 2 hardware stack |
| `tag_adaptation/` | Shadow-mode hardware fine-tuning, gated off by default |
| `docs/` | ~35 files. Read `docs/README.md` first — it routes by topic and marks superseded designs. |

Doc routing: `README.md` = active experiment. `docs/README.md` = index.
`docs/HANDOFF.md` = where the last session stopped. `CHANGELOG.md` = research
log, reverse-chronological, records rejected hypotheses; it does **not** answer
"what is true now".

## Training server

Training never runs locally.

```bash
ssh -i ~/.ssh/aere_codex_ed25519 tn22833@aere-a83514.ae.utexas.edu
```

| What | Where |
| --- | --- |
| Active repo | `/home/tn22833/Multi-maze` |
| Training Python (pass as `TAG_PYTHON`) | `/home/tn22833/TAG_dreamerv3_smoke_20260723/.venv/bin/python` |
| Run logs | `/home/tn22833/cyberrunner_logs/<run_id>/` |
| Curriculum datasets | `/home/tn22833/Multi-maze/artifacts/master_course_curriculum/` |

There is no `.venv` in the server repo, so `TAG_PYTHON` must be passed to every
launcher. Two traps: `/home/tn22833/TAG_hardware_contract_fed232e` is a stale
pre-rename checkout (older docs point at it — never launch from it), and
`scripts/inspect_server_env.sh` names a `roboracer_project` venv that has no jax.

GPU 0 belongs to another user. GPU 2 trains, GPU 3 canonical validation, GPU 4
robust validation. Validation must never share a device with its own run.

Prefer `bash scripts/server_status.sh` over exploring by hand.

## Reading training output

**Never cat/tail/head `metrics.jsonl`.** ~300 fields per row, thousands of
tokens per row. Project server-side:

```bash
python3 -c "
import json
rows=[json.loads(l) for l in open('metrics.jsonl') if l.strip()]
print(rows[-1]['step'], rows[-1].get('stats/mean_log_path_cost'))
"
```

`validation/history.jsonl` is compact and safe to read whole; its
`checkpoint_sha256` / `checkpoint_step` distinguish a flat learning curve from a
monitor re-scoring a stale checkpoint. Also per-run: `training_health.json`
(optimizer sanity), `validation/plateau_state.json` (why it self-stopped),
`STOP_TRAINING` (stop reason, plain text),
`validation/latest_weakness_report.json`.

## Local environment

Windows, default shell **PowerShell 5.1**: `&&` is a parse error and binary data
through a pipeline is corrupted — never pipe `tar` to `ssh` there. Git Bash
handles both. Prefer per-file `scp` in commands given to the user.

Local Python has `numpy`, `mujoco`, `gymnasium`, `PIL`; it has **no** `jax`,
`yaml`, or `ruamel.yaml`, so `verify_dreamer_config.py` cannot run locally and
`configs.yaml` cannot be parsed locally. The other two verifiers work.

```bash
python -m unittest discover -s tag_mujoco/tests -t .
```

227 tests, ~20 s. Run before shipping anything to the server.

## Reward design

Episode budget is `progress_reward_scale + success_bonus`. Every dense penalty
stays a minority of it; guards live in `tests/test_hole_clearance_penalty.py`
and `tests/test_action_rate_penalty.py`.

All hazard costs in `tag_env.py` return `[0, 1]` — `hole_proximity_cost`,
`wall_riding_cost`, `path_tracking_cost`. A new cost term must be bounded the
same way. An unbounded one collapsed the foundation stage (see
`docs/MASTER_COURSE_CURRICULUM.md`): ~-165 per episode against a budget of 35,
and the policy learned to stand still.

`tag_sim_v2_safe_path_tracking` ships `path_tracking_penalty: 0.20`,
uncalibrated and out of budget even bounded. Retired curriculum — do not copy
its coefficients.

## Reading route_completion

`route_completion` is the ball's *projection* onto the route, not proof it
travelled it. `TaskConfig.progress_corridor_m` (40 mm) stops progress being
credited outside the corridor, but a ball that repeatedly dips in can still
ratchet `max_route_completion`.

Never read route progress without `mean_cross_track_error_m` beside it — on a
259 mm board, a mean cross-track error in the hundreds of mm means the ball was
not on the route whatever progress says. The gate enforces this via
`MAXIMUM_TRUSTED_CROSS_TRACK_M`.

`success` is stricter: ball center within `goal_radius_m` (8 mm) of the final
waypoint. Near-zero completion alongside high progress means the ball is not
where progress implies.

## Gates and promotion

`curriculum_phase_gate.py`, `skill_curriculum_gate.py`, and
`master_course_gate.py` share tolerances from `gate_criteria.py`. Change a
tolerance there, not in a copy.

Always pass `--validation-root` to `master_course_gate.py`; without it the gate
reads one snapshot and cannot tell a stage that never learned from one that
unlearned what it started with.

Select the best monitored checkpoint, never the latest.

## Conventions

- Long runs are approval-gated behind `TAG_TRAINING_APPROVED=YES` and
  `TAG_VALIDATION_APPROVED=YES`. These are human gates — never launch a
  multi-hour run unasked.
- Launchers refuse a non-empty log directory. Pick a fresh `TAG_RUN_ID`.
- Test splits are read once at the end. Tune against `dev` or `validation`.
</content>
</invoke>
