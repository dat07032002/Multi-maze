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
    for name in ("tag_sim", "medium"):
        config = config.update(configs[name])
    expected = {
        "task": "tagmaze_sim",
        "maze_split": "train",
        "maze_sampling": "curriculum",
        "reward_mode": "scaled_progress",
        "encoder_mlp_keys": "^(states|goal)$",
    }
    actual = {
        "task": config.task,
        "maze_split": config.env.tagmaze.maze_split,
        "maze_sampling": config.env.tagmaze.maze_sampling,
        "reward_mode": config.env.tagmaze.reward_mode,
        "encoder_mlp_keys": config.encoder.mlp_keys,
    }
    if actual != expected:
        raise RuntimeError(f"Unexpected merged Dreamer configuration: {actual}")
    v2 = embodied.Config(configs["defaults"])
    for name in ("tag_sim_v2", "medium"):
        v2 = v2.update(configs[name])
    v2_expected = {
        "task": "tagmaze_sim",
        "env_count": 8,
        "env_parallel": "process",
        "maze_sampling": "plr",
        "failure_penalty": 10.0,
        "start_curriculum": True,
        "randomization_curriculum": True,
    }
    v2_actual = {
        "task": v2.task,
        "env_count": v2.envs.amount,
        "env_parallel": v2.envs.parallel,
        "maze_sampling": v2.env.tagmaze.maze_sampling,
        "failure_penalty": v2.env.tagmaze.failure_penalty,
        "start_curriculum": v2.env.tagmaze.start_curriculum,
        "randomization_curriculum": v2.env.tagmaze.randomization_curriculum,
    }
    if v2_actual != v2_expected:
        raise RuntimeError(f"Unexpected v2 Dreamer configuration: {v2_actual}")
    hardware = embodied.Config(configs["defaults"]).update(configs["tag"])
    hardware_expected = {
        "task": "gym_tag_dreamer:tag-ros-v0",
        "replay": "tag",
        "train_ratio": 128,
        "encoder_mlp_keys": "^(states|goal)$",
    }
    hardware_actual = {
        "task": hardware.task,
        "replay": hardware.replay,
        "train_ratio": hardware.run.train_ratio,
        "encoder_mlp_keys": hardware.encoder.mlp_keys,
    }
    if hardware_actual != hardware_expected:
        raise RuntimeError(f"Unexpected TAG hardware configuration: {hardware_actual}")
    print(f"Dreamer multi-maze config merge passed: {actual}")
    print(f"Dreamer adaptive v2 config merge passed: {v2_actual}")
    print(f"Dreamer TAG hardware config merge passed: {hardware_actual}")
    print("No agent or training was started.")


if __name__ == "__main__":
    main()
