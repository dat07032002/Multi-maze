"""Dump one deterministic validation rollout as a per-step CSV for diagnosis.

A rendered GIF shows that a rollout failed. This probe records the numbers
needed to say why: whether the ball is pinned against geometry, oscillating in
place, cycling around a loop, or driving itself into a hole.

The environment overrides match `evaluation_env_overrides("canonical")`, so a
given layout and seed reproduce the canonical validation episode exactly.
"""

from __future__ import annotations

import argparse
import csv
import pathlib
import sys

import numpy as np
import ruamel.yaml as yaml


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=pathlib.Path, required=True)
    parser.add_argument("--checkpoint", type=pathlib.Path, required=True)
    parser.add_argument("--config", type=pathlib.Path, required=True)
    parser.add_argument("--manifest", type=pathlib.Path, required=True)
    parser.add_argument("--split", default="validation")
    parser.add_argument("--layout", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--max-steps", type=int, default=3000)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()

    repo = args.repo.resolve()
    dreamer_package = repo / "dreamerv3" / "dreamerv3"
    sys.path[:0] = [str(repo), str(dreamer_package.parent), str(dreamer_package)]

    import embodied
    from dreamerv3 import agent as agt
    from dreamerv3 import train as trainlib
    from dreamerv3.embodied.envs.tag_maze import TagMaze
    from tag_mujoco.maze_dataset import load_split
    from tag_mujoco.validation_metrics import episode_record, evaluation_env_overrides

    config_data = yaml.YAML(typ="safe").load(
        args.config.resolve().read_text(encoding="utf-8")
    )
    config = embodied.Config(config_data).update(
        {
            "jax.prealloc": False,
            "wrapper.length": args.max_steps,
            "env.tagmaze.maze_sampling": "uniform",
        }
    )
    split = load_split(args.split, args.manifest.resolve())
    matches = [
        (path, metadata)
        for path, metadata in zip(split.paths, split.metadata)
        if path.name == args.layout
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected one layout named {args.layout!r} in {args.split!r}, got {len(matches)}"
        )
    layout_path, metadata = matches[0]

    def make_env():
        kwargs = dict(config.env.tagmaze)
        kwargs.update(evaluation_env_overrides("canonical"))
        base = TagMaze("sim", layout_paths=[str(layout_path)], seed=args.seed, **kwargs)
        return embodied.BatchEnv([trainlib.wrap_env(base, config)], parallel=False)

    prototype = make_env()
    counter = embodied.Counter()
    agent = agt.Agent(prototype.obs_space, prototype.act_space, counter, config)
    prototype.close()

    loader = embodied.Checkpoint(parallel=False)
    loader.agent = agent
    loader.step = counter
    loader.load(args.checkpoint.resolve(), keys=["agent", "step"])

    env = make_env()
    rows: list[dict[str, float]] = []
    episodes: list[dict] = []

    def scalar(transition, key, default=0.0):
        value = transition.get(key, default)
        array = np.asarray(value).reshape(-1)
        return float(array[0]) if array.size else float(default)

    def record(transition, _worker):
        states = np.asarray(transition.get("states", np.zeros(4))).reshape(-1)
        action = np.asarray(transition.get("action", np.zeros(2))).reshape(-1)
        rows.append(
            {
                "step": len(rows),
                # Normalized policy-contract states: board angles then ball xy.
                "angle_0": float(states[0]) if states.size > 0 else 0.0,
                "angle_1": float(states[1]) if states.size > 1 else 0.0,
                "ball_x": float(states[2]) if states.size > 2 else 0.0,
                "ball_y": float(states[3]) if states.size > 3 else 0.0,
                "action_0": float(action[0]) if action.size > 0 else 0.0,
                "action_1": float(action[1]) if action.size > 1 else 0.0,
                "route_progress": scalar(transition, "log_progress"),
                "cross_track_error_m": scalar(transition, "log_cross_track_error"),
                "clearance_cost": scalar(transition, "log_clearance_cost"),
                "min_clearance_m": scalar(transition, "log_min_clearance"),
                "reward": scalar(transition, "reward"),
                "is_last": scalar(transition, "is_last"),
            }
        )

    driver = embodied.Driver(env)
    driver.on_step(record)
    driver.on_episode(lambda episode, _worker: episodes.append(episode))
    policy = lambda *values: agent.policy(*values, mode="eval")
    try:
        driver(policy, episodes=1)
    finally:
        env.close()

    if len(episodes) != 1 or not rows:
        raise RuntimeError("Probe did not produce one episode with recorded steps")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    summary = episode_record(
        episodes[0],
        layout=layout_path.name,
        layout_seed=int(metadata["seed"]),
        difficulty_score=float(metadata["difficulty_score"]),
        difficulty_band=str(metadata["difficulty_band"]),
        evaluation_seed=args.seed,
    )
    print(
        f"{args.layout} seed={args.seed} steps={len(rows)} "
        f"success={summary['success']} fall={summary['fall']} "
        f"reason={summary['termination_reason']} "
        f"max_progress={summary['max_route_completion']:.3f} -> {args.output}"
    )


if __name__ == "__main__":
    main()
