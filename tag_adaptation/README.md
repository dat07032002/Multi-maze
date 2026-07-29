# TAG hardware adaptation

This package implements the dormant, ROS-independent parts of the future
hardware adaptation design:

- bounded main-plus-residual action composition;
- a hard safety supervisor;
- immutable adaptation-session records;
- weakness slicing;
- champion/challenger promotion gates.

It contains no ROS publishers, services, action clients, motor drivers, online
optimizers, or automatic promotion command. `AdaptationConfig` defaults to
`shadow` mode. Residual execution requires both `execution_enabled=True` in the
configuration and `execution_approved=True` on each decision.

See
[`docs/REAL_HARDWARE_ADAPTATION_DESIGN.md`](../docs/REAL_HARDWARE_ADAPTATION_DESIGN.md)
for the complete lifecycle and acceptance criteria.

## Offline usage

Analyze finalized episode summaries:

```bash
ros2 run tag_adaptation analyze-weaknesses \
  --episodes /path/to/session/episodes.jsonl \
  --output /path/to/session/weaknesses.json
```

Evaluate already-aggregated champion and candidate results:

```bash
ros2 run tag_adaptation evaluate-promotion \
  --champion champion_summary.json \
  --candidate candidate_summary.json \
  --champion-target champion_target_slice.json \
  --candidate-target candidate_target_slice.json \
  --output promotion_decision.json
```

The promotion evaluator only writes a decision. It does not change a registry,
load a policy, or command hardware. Registry mutation is a separate,
hash-guarded library call so an operator must review the decision first.

## Integration contract

The future policy runtime supplies:

- the main policy's two-dimensional normalized action;
- the helper's proposed two-dimensional correction;
- state age, visibility, board angles, hole clearance, predicted fall risk,
  and weakness score.

`AdaptationController.decide()` returns the proposed residual, proposed combined
action, actually permitted action, intervention state, stop state, and reasons.
The runtime should record the complete decision through `AdaptationSession`
before passing the permitted action to its existing hardware bridge.
