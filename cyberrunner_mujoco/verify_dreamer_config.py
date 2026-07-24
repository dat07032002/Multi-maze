"""Merge the Dreamer configs without creating an agent or starting training."""

from __future__ import annotations

import pathlib
import sys

import ruamel.yaml as yaml


HERE = pathlib.Path(__file__).resolve().parent
DREAMER_ROOT = HERE.parent / "dreamerv3"
DREAMER_PACKAGE = DREAMER_ROOT / "dreamerv3"
sys.path[:0] = [str(DREAMER_ROOT), str(DREAMER_PACKAGE)]

import embodied  # noqa: E402


def main() -> None:
    configs = yaml.YAML(typ="safe").load(
        (DREAMER_PACKAGE / "configs.yaml").read_text(encoding="utf-8")
    )
    config = embodied.Config(configs["defaults"])
    for name in ("cyberrunner", "medium"):
        config = config.update(configs[name])
    expected = {
        "task": "cyberrunner_sim",
        "maze_split": "train",
        "maze_sampling": "curriculum",
        "reward_mode": "scaled_progress",
        "encoder_mlp_keys": "^(states|goal)$",
    }
    actual = {
        "task": config.task,
        "maze_split": config.env.cyberrunner.maze_split,
        "maze_sampling": config.env.cyberrunner.maze_sampling,
        "reward_mode": config.env.cyberrunner.reward_mode,
        "encoder_mlp_keys": config.encoder.mlp_keys,
    }
    if actual != expected:
        raise RuntimeError(f"Unexpected merged Dreamer configuration: {actual}")
    print(f"Dreamer multi-maze config merge passed: {actual}")
    print("No agent or training was started.")


if __name__ == "__main__":
    main()
