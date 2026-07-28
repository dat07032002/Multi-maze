# Continue from another desktop

## Clone

```bash
git clone https://github.com/dat07032002/Multi-maze.git
cd Multi-maze
git log -1 --oneline
```

The repository deliberately excludes virtual environments, ROS build products,
simulator renders, checkpoints, replay, and logs. Recreate those locally.

## Windows simulation environment

Create or reuse a Python environment with MuJoCo, NumPy, Pillow, Gymnasium, and
the Dreamer dependencies. Then run:

```powershell
python -m unittest discover -s tag_mujoco\tests -v
Push-Location tag_mujoco
python verify_dreamer_config.py
python verify_dreamer_adapter.py
python verify_training_readiness.py
Pop-Location
```

## Ubuntu/ROS hardware environment

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

Robot-side startup order:

```bash
ros2 run tag_camera fast_camera_publisher.py
ros2 run tag_hiwonder hiwonder_compat_node.py
./run_tag_estimator.sh
python3 tcp_ros_bridge.py 127.0.0.1 5555
```

Use an SSH tunnel for port 5555 when the learner is remote. Confirm motor signs
and begin with a reduced command limit before deploying a learned policy.

## Existing school-server run

The current production artifacts are external to Git. Their paths, GPU mapping,
status commands, and safe-stop instructions are in [TRAINING.md](TRAINING.md).
The recovered run was intentionally stopped at step 9,520,768 on 2026-07-24;
cloning or building this repository does not alter the preserved server files.

For the next physical-hardware session, use the complete setup and test order in
[HARDWARE_HANDOFF_2026-07-26.md](HARDWARE_HANDOFF_2026-07-26.md).

## State as of 2026-07-28: nominal mastery gate passed

The nominal-first phase reached its goal. A dense hole-margin reward term
produced a checkpoint that satisfies every mastery criterion over the
192-episode protocol on the held-out validation split.

| Criterion | Required | Measured |
| --- | ---: | ---: |
| Overall completion | at least 90% | 90.10% |
| Fall rate | at most 10% | 6.25% |
| Mean maximum route completion | at least 95% | 95.57% |
| Hard-maze completion | at least 80% | 88.89% |
| Lowest difficulty band | at least 75% | 88.89% |

Accepted checkpoint and its evidence, all external to Git:

```text
/home/tn22833/cyberrunner_logs/ab_nominal_holeaware_20260728_155619/
  validation/step_000500000/checkpoint.ckpt
/home/tn22833/cyberrunner_logs/holeaware_gate192_500k_20260728/canonical192.json
/home/tn22833/cyberrunner_logs/holeaware_gate192_500k_20260728/gate_decision.json
```

**Completion passed by one episode, 173 of 192.** Domain randomization is
therefore still locked. The first task on the next desktop is a second gate
confirmation at different evaluation seeds; see the open questions in
[NOMINAL_AB_ARMS_2026-07-28.md](NOMINAL_AB_ARMS_2026-07-28.md).

Read [NOMINAL_DIAGNOSIS_2026-07-28.md](NOMINAL_DIAGNOSIS_2026-07-28.md) for why
the earlier pilot failed and [NOMINAL_AB_ARMS_2026-07-28.md](NOMINAL_AB_ARMS_2026-07-28.md)
for the arm comparison, the reward calibration, and four hypotheses that were
tested and rejected. Do not re-attempt those four.

### Unfinished job left running on the server

One bounded arm was still training when this was written and needs no
intervention. It writes its own dev validation at 250k and 500k and stops.

```text
/home/tn22833/cyberrunner_logs/ab_nominal_smooth_holeaware_20260728_163114
```

It combines the action-rate and hole-margin terms. At 250k it scored 78.13%
completion, 18.75% falls and 87.79% progress against 85.94%, 9.38% and 93.73%
for the hole-margin term alone, so the action-rate term looks actively harmful
in combination rather than merely redundant. Confirm at its 500k row, then
retire `action_rate_penalty` back to zero unless it recovers.

## Next work

1. Repeat the 192-episode gate at different evaluation seeds before unlocking any
   plant randomization. The current pass rests on a single episode.
2. Consider a bounded nominal continuation. The hole-margin dev curve was still
   climbing at 500k, 78.13 to 85.94 to 90.63, so more margin is probably
   available cheaply.
3. Five validation layouts still succeed on only one of three seeds. Those, plus
   the 86 measured failing training layouts in
   `nominal_trainsweep_500k_20260728/failed_layouts.json`, are the demonstration
   targets if more margin is wanted.
4. Preserve the accepted nominal checkpoint regardless of what any later
   randomization stage does.
5. Monitor fixed-step validation and select the best checkpoint rather than the latest one.
2. Keep the eight test mazes untouched until the final report.
3. When hardware is available, measure servo-angle response, backlash, latency, and friction.
4. Measure removable-plate thickness/retention geometry before final-fit STL export.
5. Commission with small actions, then test familiar and held-out printed mazes without per-maze retraining.
