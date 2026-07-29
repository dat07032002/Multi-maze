"""Utilities for selectively restoring DreamerV3 checkpoints."""

import hashlib
import re

import numpy as np


_OPTIMIZER_VARIABLE = re.compile(
    r"/(?:model_opt|actor_opt|critic_opt|disag_opt)(?:/|$)"
)


def is_optimizer_variable(name):
    """Return whether a Ninjax variable belongs to an optimizer."""

    return bool(_OPTIMIZER_VARIABLE.search(str(name)))


def is_acting_variable(name):
    """Return whether a variable can affect world-model or actor behavior."""

    name = str(name)
    if is_optimizer_variable(name):
        return False
    return name.startswith("agent/wm/") or "/actor/" in name


def variable_sha256(state, predicate=lambda name: True):
    """Hash a deterministic subset of a flat Ninjax variable mapping."""

    digest = hashlib.sha256()
    count = 0
    for key in sorted(state):
        if not predicate(key):
            continue
        value = np.asarray(state[key])
        digest.update(str(key).encode("utf-8"))
        digest.update(str(value.dtype).encode("ascii"))
        digest.update(str(value.shape).encode("ascii"))
        digest.update(value.tobytes())
        count += 1
    return digest.hexdigest(), count


class OptimizerHealthTracker:
    """Fail closed on non-finite metrics, overflows, or stalled optimizers."""

    def __init__(self, stall_limit=3):
        self.stall_limit = int(stall_limit)
        self.last_grad_steps = {}
        self.stalled_grad_steps = {}

    def check(self, metrics):
        for key, value in metrics.items():
            array = np.asarray(value)
            if not np.all(np.isfinite(array)):
                raise FloatingPointError(
                    f"Training metric {key!r} is non-finite: {array}"
                )
            if key.endswith("_grad_overflow") and np.any(array != 0):
                raise FloatingPointError(
                    f"Training metric {key!r} reports gradient overflow: {array}"
                )
            if not key.endswith("_grad_steps"):
                continue
            current = int(array)
            previous = self.last_grad_steps.get(key)
            stalled = self.stalled_grad_steps.get(key, 0)
            stalled = stalled + 1 if previous is not None and current <= previous else 0
            self.last_grad_steps[key] = current
            self.stalled_grad_steps[key] = stalled
            if stalled >= self.stall_limit:
                raise RuntimeError(
                    f"Optimizer counter {key!r} did not advance for "
                    f"{stalled} consecutive updates (value={current})."
                )
