"""Bounded DreamerV3 checkpoint evaluation on exact held-out maze layouts."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import time

import numpy as np
import ruamel.yaml as yaml


FILE = pathlib.Path(__file__).resolve()
PACKAGE_DIR = FILE.parent
sys.path.extend(
    [str(PACKAGE_DIR.parent), str(PACKAGE_DIR.parent.parent)]
)
__package__ = PACKAGE_DIR.name

import embodied  # noqa: E402

from . import agent as agt  # noqa: E402
from . import train as trainlib  # noqa: E402
from .embodied.envs.tag_maze import TagMaze  # noqa: E402
from tag_mujoco.maze_dataset import file_sha256, load_split  # noqa: E402
from tag_mujoco.validation_metrics import (  # noqa: E402
    episode_record,
    evaluation_env_overrides,
    summarize_records,
)


def _make_env(
    config,
    layout_path: pathlib.Path,
    seed: int,
    robust: bool,
    randomization_strength: float | None = None,
):
    kwargs = dict(config.env.tagmaze)
    kwargs.update(
        evaluation_env_overrides(
            "robust" if robust else "canonical",
            randomization_strength=randomization_strength,
        )
    )
    env = TagMaze(
        "sim",
        layout_paths=[str(layout_path)],
        seed=seed,
        **kwargs,
    )
    env = trainlib.wrap_env(env, config)
    return embodied.BatchEnv([env], parallel=False)


def _run_episode(agent, env, policy_mode: str = "eval") -> dict[str, np.ndarray]:
    episodes: list[dict[str, np.ndarray]] = []
    driver = embodied.Driver(env)
    driver.on_episode(lambda episode, _: episodes.append(episode))
    policy = lambda *args: agent.policy(*args, mode=policy_mode)
    driver(policy, episodes=1)
    if len(episodes) != 1:
        raise RuntimeError(f"Expected one completed episode, got {len(episodes)}")
    return episodes[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=pathlib.Path, required=True)
    parser.add_argument("--config", type=pathlib.Path, required=True)
    parser.add_argument("--manifest", type=pathlib.Path, required=True)
    # "dev" is a subset of the training layouts used to rank tuning decisions
    # without reading the validation split that the mastery gate measures.
    # "train" sweeps every training layout to find which ones the policy has not
    # learned, so demonstrations can target them.
    parser.add_argument(
        "--split", choices=("validation", "test", "dev", "train"), default="validation"
    )
    parser.add_argument("--mode", choices=("canonical", "robust"), required=True)
    parser.add_argument("--episodes-per-maze", type=int, default=1)
    parser.add_argument("--max-steps", type=int, default=3000)
    parser.add_argument("--seed", type=int, default=20260723)
    parser.add_argument("--trigger-step", type=int, required=True)
    # "sample" reproduces the historical protocol, which draws each action from
    # the actor distribution. "mode" acts on the distribution mode instead.
    parser.add_argument("--policy-mode", choices=("sample", "mode"), default="sample")
    parser.add_argument(
        "--randomization-strength",
        type=float,
        help="Fixed robust-evaluation strength in (0, 1]; omitted means full strength.",
    )
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()

    if args.episodes_per_maze <= 0 or args.max_steps <= 0:
        raise ValueError("Episode count and maximum steps must be positive")
    checkpoint = args.checkpoint.resolve()
    if not checkpoint.is_file():
        raise FileNotFoundError(checkpoint)

    config_data = yaml.safe_load(args.config.resolve().read_text(encoding="utf-8"))
    config = embodied.Config(config_data)
    config = config.update(
        {
            "jax.prealloc": False,
            "wrapper.length": args.max_steps,
            "env.tagmaze.maze_sampling": "uniform",
        }
    )
    split = load_split(args.split, args.manifest)
    robust = args.mode == "robust"
    if args.randomization_strength is not None and not robust:
        parser.error("--randomization-strength requires --mode robust")
    policy_mode = "eval" if args.policy_mode == "sample" else "eval_mode"

    prototype = _make_env(
        config,
        split.paths[0],
        args.seed,
        robust,
        args.randomization_strength,
    )
    step = embodied.Counter()
    agent = agt.Agent(prototype.obs_space, prototype.act_space, step, config)
    prototype.close()

    loader = embodied.Checkpoint(parallel=False)
    loader.agent = agent
    loader.step = step
    loader.load(checkpoint, keys=["agent", "step"])
    checkpoint_step = int(step)

    records = []
    started = time.time()
    for layout_index, (layout_path, metadata) in enumerate(
        zip(split.paths, split.metadata)
    ):
        for episode_index in range(args.episodes_per_maze):
            evaluation_seed = (
                args.seed + 10000 * layout_index + episode_index
            )
            env = _make_env(
                config,
                layout_path,
                evaluation_seed,
                robust,
                args.randomization_strength,
            )
            try:
                episode = _run_episode(agent, env, policy_mode)
            finally:
                env.close()
            record = episode_record(
                episode,
                layout=layout_path.name,
                layout_seed=int(metadata["seed"]),
                difficulty_score=float(metadata["difficulty_score"]),
                difficulty_band=str(metadata["difficulty_band"]),
                evaluation_seed=evaluation_seed,
            )
            records.append(record)
            print(
                f"[{args.mode}] {layout_path.name} seed={evaluation_seed} "
                f"success={record['success']} fall={record['fall']} "
                f"progress={record['max_route_completion']:.3f}"
            )

    aggregates = summarize_records(records)
    result = {
        "schema_version": 1,
        "completed": True,
        "mode": args.mode,
        "split": args.split,
        "trigger_step": args.trigger_step,
        "checkpoint_step": checkpoint_step,
        "checkpoint": str(checkpoint),
        "checkpoint_sha256": file_sha256(checkpoint),
        "config": str(args.config.resolve()),
        "manifest": str(split.manifest_path),
        "episodes_per_maze": args.episodes_per_maze,
        "max_steps": args.max_steps,
        "seed": args.seed,
        # Results from different action-selection protocols are not comparable.
        "policy_mode": args.policy_mode,
        "randomization_strength": (
            args.randomization_strength if robust else 0.0
        ),
        "duration_seconds": time.time() - started,
        **aggregates,
        "episodes": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, args.output)
    print(json.dumps({"output": str(args.output), **result["summary"]}, indent=2))


if __name__ == "__main__":
    main()
