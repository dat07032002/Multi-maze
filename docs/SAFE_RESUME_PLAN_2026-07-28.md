# Safe nominal continuation

The previous 250k continuation reduced held-out dev completion from 90.63% to
82.81% and increased falls from 7.81% to 15.63%. Training metrics showed the
same direction, so the continuation path—not only evaluation noise—needed to be
changed before another long run.

## Implemented controls

`agent_only` now means learned variables only. The source world model, actor,
critic, and normalization state are restored, while model, actor, critic, and
exploration optimizer variables keep their freshly initialized values. Step and
replay also remain fresh.

Checkpoint restoration happens before replay prefill. A continued run therefore
uses the source policy for new warm-buffer collection instead of `RandomAgent`.
The safe-resume launcher additionally loads up to 25,000 transitions spread
uniformly over the source replay chunks. Source-policy collection fills the
buffer to 50,000 transitions, producing an approximately balanced old/new warm
buffer. Prefill is not charged against the 100,000-step fine-tuning budget.

The conservative profile uses:

- train ratio 8 instead of 32;
- model learning rate `3e-5` instead of `1e-4`;
- actor and critic learning rates `3e-6` instead of `3e-5`;
- 100 optimizer-step warmup;
- nominal dynamics, full-route starts, and the existing `0.02` hole-clearance
  penalty.

The dev monitor evaluates three sampled-policy episodes for each of the 64 dev
layouts—192 episodes—at baseline and every 25,000 training steps. If completion
is lower and falls are higher than baseline, it writes `STOP_TRAINING`; the
trainer stops after the current episode and the source checkpoint remains the
champion. If the run completes, the best monitored checkpoint is selected for
dual-seed confirmation rather than selecting the latest checkpoint.

## Launch

The source run must still contain its `replay/` directory:

```bash
export TAG_TRAINING_APPROVED=YES
export TAG_VALIDATION_APPROVED=YES
export TAG_PYTHON=/path/to/repo/.venv/bin/python

bash scripts/continue_holeaware_then_confirm.sh \
  /path/to/source/checkpoint.ckpt \
  /path/to/source/run \
  /path/to/prior/canonical192.json \
  /path/to/new/dual_confirmation
```

Domain randomization remains downstream of the unchanged dual-seed mastery
gate. A regression stop never unlocks DR.
