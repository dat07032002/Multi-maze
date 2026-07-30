"""Evaluate non-learning baselines or policy callbacks on held-out maze splits."""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Dict

import numpy as np

try:
    from .tag_env import TagMazeTask, TaskConfig
    from .maze_dataset import DEFAULT_MANIFEST, load_split
except ImportError:
    from tag_env import TagMazeTask, TaskConfig
    from maze_dataset import DEFAULT_MANIFEST, load_split


HERE = Path(__file__).resolve().parent
Policy = Callable[[Dict[str, np.ndarray], np.random.Generator], np.ndarray]


def random_policy(_: Dict[str, np.ndarray], rng: np.random.Generator) -> np.ndarray:
    return rng.uniform(-1.0, 1.0, size=2).astype(np.float32)


def zero_policy(_: Dict[str, np.ndarray], __: np.random.Generator) -> np.ndarray:
    return np.zeros(2, dtype=np.float32)


def evaluate_policy(
    policy: Policy,
    split_name: str,
    manifest_path: str | Path = DEFAULT_MANIFEST,
    episodes_per_maze: int = 1,
    max_steps: int = 3000,
    seed: int = 0,
) -> Dict[str, Any]:
    split = load_split(split_name, manifest_path)
    task = TagMazeTask(
        seed=seed,
        task_config=TaskConfig(
            maze_manifest=str(split.manifest_path),
            maze_split=split_name,
            maze_sampling="uniform",
            randomize_plant=False,
            random_start=False,
            reward_mode="scaled_progress",
        ),
    )
    rng = np.random.default_rng(seed)
    episodes = []
    for layout_index, metadata in enumerate(split.metadata):
        for episode_index in range(episodes_per_maze):
            observation, info = task.reset(
                seed=seed + 10000 * layout_index + episode_index,
                options={"layout_index": layout_index},
            )
            cross_track = []
            clearance_cost = []
            max_completion = float(info["route_completion"])
            terminated = truncated = False
            for _ in range(max_steps):
                action = np.asarray(policy(observation, rng), dtype=np.float32)
                if action.shape != (2,) or not np.all(np.isfinite(action)):
                    raise ValueError(f"Policy emitted invalid action {action!r}")
                observation, _, terminated, truncated, info = task.step(
                    np.clip(action, -1.0, 1.0)
                )
                value = float(info["cross_track_error_m"])
                if math.isfinite(value):
                    cross_track.append(value)
                clearance_cost.append(float(info["clearance_cost"]))
                max_completion = max(max_completion, float(info["route_completion"]))
                if terminated or truncated:
                    break
            reason = info["termination_reason"]
            if not terminated and not truncated:
                reason = "evaluation_step_cap"
            episodes.append(
                {
                    "layout": Path(info["layout_path"]).name,
                    "layout_seed": int(info["layout_seed"]),
                    "difficulty_score": float(metadata["difficulty_score"]),
                    "difficulty_band": metadata["difficulty_band"],
                    "success": reason == "goal_reached",
                    "fall": reason in {"ball_fell", "ball_left_board"},
                    "termination_reason": reason,
                    "steps": int(info["episode_steps"]),
                    "return": float(info["episode_return"]),
                    "final_route_completion": float(info["route_completion"]),
                    "max_route_completion": max_completion,
                    "mean_cross_track_error_m": float(np.mean(cross_track)) if cross_track else math.nan,
                    "mean_clearance_cost": float(np.mean(clearance_cost)) if clearance_cost else math.nan,
                    "minimum_clearance_m": float(task.minimum_clearance_m),
                }
            )

    def aggregate(items):
        return {
            "episodes": len(items),
            "completion_rate": float(np.mean([item["success"] for item in items])),
            "fall_rate": float(np.mean([item["fall"] for item in items])),
            "mean_max_route_completion": float(
                np.mean([item["max_route_completion"] for item in items])
            ),
            "mean_cross_track_error_m": float(
                np.nanmean([item["mean_cross_track_error_m"] for item in items])
            ),
            "minimum_clearance_m": float(
                np.min([item["minimum_clearance_m"] for item in items])
            ),
            "mean_return": float(np.mean([item["return"] for item in items])),
        }

    by_band = defaultdict(list)
    for episode in episodes:
        by_band[episode["difficulty_band"]].append(episode)
    return {
        "training_started": False,
        "split": split_name,
        "manifest": str(split.manifest_path),
        "seed": seed,
        "episodes_per_maze": episodes_per_maze,
        "max_steps": max_steps,
        "summary": aggregate(episodes),
        "by_difficulty": {band: aggregate(items) for band, items in sorted(by_band.items())},
        "episodes": episodes,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", choices=("random", "zero"), default="random")
    parser.add_argument(
        "--split",
        choices=("validation", "test", "dev", "train", "seen", "rehearsal"),
        default="validation",
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--episodes-per-maze", type=int, default=1)
    parser.add_argument("--max-steps", type=int, default=300)
    parser.add_argument("--seed", type=int, default=20260723)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    policy = random_policy if args.policy == "random" else zero_policy
    result = evaluate_policy(
        policy,
        args.split,
        args.manifest,
        args.episodes_per_maze,
        args.max_steps,
        args.seed,
    )
    output = args.output or HERE / "outputs" / f"{args.policy}_policy_{args.split}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, allow_nan=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), **result["summary"]}, indent=2))


if __name__ == "__main__":
    main()
