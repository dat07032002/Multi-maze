# Connected continuous route curriculum

This is the research-backed adaptation of `tag_sim_v3_continuous_unified`.
It preserves the deployed `tag_hardware_policy_v1` observation and action
contract while correcting the first experiment's training-distribution
mismatch.

## Intended behavior

The controller learns on complete no-hole routes whose geometry naturally
chains local challenges:

```text
straight -> turn -> straight -> turn -> recovery
```

Crossing an internal straight/turn boundary does not reset the simulator.
Marble position and velocity, board state, and the Dreamer recurrent state all
continue through the transition. Only a fall, confirmed observation loss,
leaving the board, reaching the end of the complete route, or the 3,000-step
wrapper limit ends the episode.
Route endpoints remain neutral during this pretraining stage.

This is different from constructing one physically infinite MuJoCo board.
Finite complete routes provide long connected sequences while still allowing
bounded, reproducible episodes and disjoint validation.

## Adaptive curriculum

The profile is `tag_sim_v4_continuous_curriculum_noholes`.

- Training uses the paired 512-layout no-hole split.
- Thirty percent of episodes begin at the true route entrance.
- Other episodes begin near a local straight, turn, stabilization, or recovery
  challenge.
- Stage 0 emphasizes stabilization and straight motion.
- Stages 1-3 progressively add turns, higher entry speed, and recovery states.
- A stage advances only after a 40-episode local window reaches at least 75%
  competence with at most 10% falls.
- Competence means reaching the neutral route endpoint or safely advancing at
  least 20% of the route from the sampled start.
- Layout sampling mixes 50% current-frontier difficulty, 30% previously
  mastered difficulty, and 20% uniform coverage.

The mixture prevents the uniform-all-layout overload observed in the first
experiment without allowing easy routes or broad coverage to disappear.
Curriculum state remains training metadata and is never a policy input.

## Transition measurements

The environment records, but does not expose as policy inputs:

- `log_curriculum_stage`;
- `log_challenge_transition`; and
- `log_sections_completed`.

A challenge transition is a physical crossing between locally straight and
turning route geometry. These metrics determine whether long connected
behavior is actually entering replay instead of inferring it from return.

## Training order

1. Run a bounded smoke test from scratch with a fresh replay buffer.
2. Confirm finite optimizer metrics, nonzero challenge transitions, and a
   mixture of full-start and local resets.
3. Run two bounded no-hole seeds with canonical validation every 50k steps.
4. Rank checkpoints on the complete fixed 64-layout no-hole validation split,
   not the four-course development split.
5. Add holes only after nominal completion and fall gates pass.
6. Add actuator randomization after the hole-aware nominal policy passes.
7. Add camera and physics randomization only when causal evaluation identifies
   those remaining gaps.

Do not resume either failed 300k continuous-unified run and do not warm-start
from the stabilization checkpoint. The connected no-hole curriculum is a fresh
comparison, with new agent weights, optimizer state, and replay.
