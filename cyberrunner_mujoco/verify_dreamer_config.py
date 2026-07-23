"""Merge the Dreamer configs without creating an agent or starting training."""

from __future__ import annotations

import pathlib
import sys


HERE = pathlib.Path(__file__).resolve().parent
DREAMER_ROOT = HERE.parent / "dreamerv3"
DREAMER_PACKAGE = DREAMER_ROOT / "dreamerv3"
sys.path[:0] = [str(DREAMER_ROOT), str(DREAMER_PACKAGE)]

import embodied  # noqa: E402
from dreamerv3 import agent  # noqa: E402


def main() -> None:
    config = embodied.Config(agent.Agent.configs["defaults"])
    for name in ("cyberrunner", "medium"):
        config = config.update(agent.Agent.configs[name])
    expected = {
        "task": "cyberrunner_sim",
        "maze_split": "train",
        "maze_sampling": "curriculum",
        "reward_mode": "scaled_progress",
    }
    actual = {
        "task": config.task,
        "maze_split": config.env.cyberrunner.maze_split,
        "maze_sampling": config.env.cyberrunner.maze_sampling,
        "reward_mode": config.env.cyberrunner.reward_mode,
    }
    if actual != expected:
        raise RuntimeError(f"Unexpected merged Dreamer configuration: {actual}")
    print(f"Dreamer multi-maze config merge passed: {actual}")
    print("No agent or training was started.")


if __name__ == "__main__":
    main()
