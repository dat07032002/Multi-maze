# Skill-first, sequential-map curriculum

This is the active v3 curriculum design. It keeps one route-conditioned
DreamerV3 policy and the deployed `tag_hardware_policy_v1` observation/action
contract. Skill names, condition identifiers, reset parameters, and map
identities are training metadata only. They are never policy inputs.

## Training structure

### Universal skill stages

The policy advances through these stages:

1. `stabilize`: arrest initial motion and board tilt;
2. `straight`: accelerate, track, brake, and stop;
3. `turn`: left/right turns under varied approach speed;
4. `compound`: consecutive turns and S-shaped transitions;
5. `recovery`: lateral displacement and cross-route velocity;
6. `hazard`: route replanning around a route-adjacent hole; and
7. `actuator025`: a bounded actuator-only robustness stage at strength 0.025.

Each geometric family has deterministic rotations, reflections, lengths,
initial velocities, lateral offsets, and board tilts. The training, validation,
and test courses are disjoint. Only the current skill generates new online
experience. Later stages warm-start agent weights and use a balanced replay
pack containing accepted earlier experience.

The actuator stage is intentionally last. Do not add camera or physics
randomization until causal evaluation shows a remaining weakness and the
actuator stage passes its canonical and retention gates.

### Sequential full maps

Each generated map-stage manifest has exactly one entry in `train` and `dev`.
The source validation and test layouts remain disjoint. A map has two bounded
phases:

1. `local`: random route-segment starts plus a 30% full-start anchor;
2. `fullstart`: true-entrance starts only.

All newly collected transitions therefore come from one map. Previous maps
remain available only through the immutable rehearsal pack. This distinction
prevents catastrophic forgetting without returning to simultaneous online
multi-map collection.

## Build datasets

The default sequential source is the paired no-hole dataset:

```bash
TAG_PYTHON=/path/to/python \
bash scripts/build_skill_first_curriculum.sh
```

Override `TAG_SOURCE_MANIFEST` to build the sequence from another immutable
training split. Outputs are written below:

```text
artifacts/universal_skills/<family>/maze_splits.json
artifacts/sequential_maps/map_order.json
artifacts/sequential_maps/stages/stage_0001.json
```

`map_order.json` records the deterministic order and maneuver features. The
ordering considers an easy candidate window and prefers candidates that add a
new turn, length, hole, clearance, or initial-direction token.

## Build balanced rehearsal

Build a new pack from accepted replay directories. Quotas are per label, so a
large recent run cannot silently erase older skills:

```bash
python tag_mujoco/rehearsal_pack.py \
  --source universal=/path/to/accepted_skill_replay \
  --source prior_maps=/path/to/accepted_map_replay \
  --source weaknesses=/path/to/curated_weakness_replay \
  --quota universal=20000 \
  --quota prior_maps=20000 \
  --quota weaknesses=10000 \
  --output /new/rehearsal_pack
```

The builder checks required arrays and finite valid prefixes, selects complete
files deterministically, and writes `rehearsal_manifest.json`. It refuses a
nonempty destination. The training loader performs its independent finite-data
checks again.

## Launch skill stages

The first stage starts from scratch:

```bash
export TAG_TRAINING_APPROVED=YES
export TAG_VALIDATION_APPROVED=YES
export TAG_PYTHON=/path/to/python
bash scripts/start_universal_skill_stage.sh stabilize
```

Later stages require the accepted checkpoint, its run directory, and a new
balanced rehearsal pack:

```bash
bash scripts/start_universal_skill_stage.sh \
  straight \
  /accepted/checkpoint.ckpt \
  /accepted/run \
  /new/rehearsal_pack
```

The launcher never advances to the next skill automatically. It uses float32,
fresh optimizer state, agent-only loading, finite-data checks, and fixed-step
validation.

## Universal skill gate

Supply one held-out evaluation per skill. Straight, turn, and stabilization
require 95% completion; compound, recovery, and hazard require 90%. Every skill
requires at most 5% falls and at least 95% mean maximum progress. When a prior
baseline is supplied, completion may lose at most 0.02 and progress at most
0.01.

```bash
python tag_mujoco/skill_curriculum_gate.py \
  --report stabilize=/eval/stabilize.json \
  --report straight=/eval/straight.json \
  --report turn=/eval/turn.json \
  --report compound=/eval/compound.json \
  --report recovery=/eval/recovery.json \
  --report hazard=/eval/hazard.json \
  --output /eval/universal_skill_gate.json
```

Do not begin full maps unless this gate passes.

## Launch one map

Run the local phase, validate it, then run full-start from the accepted local
checkpoint:

```bash
bash scripts/start_sequential_map_stage.sh \
  1 local \
  /accepted/universal/checkpoint.ckpt \
  /accepted/universal/run \
  /new/rehearsal_pack

bash scripts/start_sequential_map_stage.sh \
  1 fullstart \
  /accepted/local/checkpoint.ckpt \
  /accepted/local/run \
  /new/rehearsal_pack
```

Before the next map, rebuild rehearsal so it includes successful trajectories
from the newly accepted map. Preserve a fixed universal-skill quota.

## Map gate

The final confirmation uses at least 20 fixed-seed episodes on the current map:

- completion at least 0.90;
- falls at most 0.10;
- mean maximum progress at least 0.95;
- the universal-skill gate still passes; and
- sentinel prior-map completion loses at most 0.05 and progress at most 0.02.

```bash
python tag_mujoco/sequential_map_gate.py \
  --candidate /eval/current_map_20.json \
  --skill-gate /eval/universal_skill_gate.json \
  --retention-baseline /eval/prior_baseline.json \
  --retention-candidate /eval/prior_candidate.json \
  --output /eval/map_gate.json
```

Every eight promoted maps, evaluate all previously trained maps and the held-out
validation split. Never tune on the final test split. Preserve the accepted
checkpoint and stop the stage on any non-finite value, stalled optimizer,
failed skill gate, failed map gate, or retention regression.
