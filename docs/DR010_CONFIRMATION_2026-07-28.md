# Second nominal confirmation and DR-0.10

The hole-aware nominal checkpoint passed the first 192-episode mastery gate by
one episode. Domain randomization therefore remains locked until the same exact
checkpoint passes a second 192-episode evaluation with a different base seed.

## Guarded workflow

`scripts/confirm_nominal_then_start_dr010.sh` performs the complete bounded
transition:

1. Verify that the first result is complete, contains at least 192 episodes,
   uses a different base seed, and names the same checkpoint SHA-256.
2. Evaluate the accepted checkpoint on the 64 held-out validation mazes with
   three sampled-action episodes per maze and base seed `20260729`.
3. Apply the unchanged nominal mastery gate.
4. Stop with domain randomization locked if any criterion fails.
5. If every criterion passes, load only the accepted agent weights into a new
   replay buffer and run 250k steps with fixed randomization strength 0.10.
6. At 250k, evaluate three nominal and three fixed-DR-0.10 episodes per
   validation maze. The workflow never advances to a higher strength.

The DR profile retains the dense hole-margin penalty, disables random starts,
and sets randomization expansion to zero. The evaluator records the exact
randomization strength in every result so partial-strength scores cannot be
mistaken for full-strength robust scores.

## Launch contract

```bash
export TAG_TRAINING_APPROVED=YES
export TAG_VALIDATION_APPROVED=YES
export TAG_PYTHON=/path/to/dreamerv3/.venv/bin/python

bash scripts/confirm_nominal_then_start_dr010.sh \
  /path/to/accepted/checkpoint.ckpt \
  /path/to/accepted/source_run \
  /path/to/first_confirmation/canonical192.json \
  /new/path/second_confirmation
```

The accepted checkpoint remains immutable. An explicit source-run contract is
used because the validation snapshot and its `policy_contract.json` live in
different directories.

If the checkpoint path was overwritten after the first evaluation, its earlier
pass is not transferred to the new bytes. The workflow instead requires the
current checkpoint to pass two 192-episode evaluations: one at the original
base seed and another at the new base seed. DR-0.10 remains locked if either
evaluation fails.
