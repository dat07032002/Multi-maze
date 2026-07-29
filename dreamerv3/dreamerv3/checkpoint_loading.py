"""Utilities for selectively restoring DreamerV3 checkpoints."""

import re


_OPTIMIZER_VARIABLE = re.compile(
    r"/(?:model_opt|actor_opt|critic_opt|disag_opt)(?:/|$)"
)


def is_optimizer_variable(name):
    """Return whether a Ninjax variable belongs to an optimizer."""

    return bool(_OPTIMIZER_VARIABLE.search(str(name)))
