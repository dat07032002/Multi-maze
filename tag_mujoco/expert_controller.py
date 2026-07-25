"""Privileged route controller and offline Dreamer demonstration generator.

The controller reads simulator truth only while producing offline examples. The
saved transitions contain exactly the deployed TAG policy observations, so the
privileged position, velocity, layout identity, and clearance cannot leak into
the learned policy interface.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

try:
    from .tag_env import TagMazeTask, TaskConfig
    from .maze_dataset import DEFAULT_MANIFEST
except ImportError:
    from tag_env import TagMazeTask, TaskConfig
    from maze_dataset import DEFAULT_MANIFEST


@dataclass(frozen=True)
class ExpertConfig:
    lookahead_m: float = 0.018
    tangent_probe_m: float = 0.008
    target_speed_mps: float = 0.030
    position_gain: float = 11.0
    velocity_gain: float = 1.8
    action_limit: float = 0.45
    action_smoothing: float = 0.35


class RouteExpertController:
    """PD route follower using privileged simulator position and velocity."""

    def __init__(self, config: ExpertConfig = ExpertConfig()):
        self.config = config
        self._last_action = np.zeros(2, dtype=np.float64)

    def reset(self) -> None:
        self._last_action[:] = 0.0

    def action(self, task: TagMazeTask) -> np.ndarray:
        position = task.model.sim.ball_board_position()[:2]
        velocity = np.asarray(
            task.last_info.get("ball_velocity_board_mps", np.zeros(2)),
            dtype=np.float64,
        )
        progress, _, _ = task.route.project(
            position,
            progress_hint=task.progress_m,
            backward_window=task.task_config.progress_backward_window_m,
            forward_window=task.task_config.progress_forward_window_m,
        )
        target = task.route.point_at(progress + self.config.lookahead_m)
        before = task.route.point_at(progress + 0.5 * self.config.lookahead_m)
        after = task.route.point_at(
            progress + self.config.lookahead_m + self.config.tangent_probe_m
        )
        tangent = after - before
        tangent /= max(float(np.linalg.norm(tangent)), 1e-9)

        # Slow before sharp changes of route direction.
        near = task.route.point_at(progress + self.config.tangent_probe_m)
        near_direction = near - position
        near_direction /= max(float(np.linalg.norm(near_direction)), 1e-9)
        alignment = float(np.clip(np.dot(near_direction, tangent), -1.0, 1.0))
        corner_scale = 0.35 + 0.65 * max(0.0, alignment)
        desired_velocity = tangent * self.config.target_speed_mps * corner_scale
        board_control = (
            self.config.position_gain * (target - position)
            + self.config.velocity_gain * (desired_velocity - velocity)
        )

        # TAG action 1 drives +X; the first tilt joint has the opposite board-Y
        # sign in the active MuJoCo/Hiwonder linkage convention.
        raw_action = np.asarray(
            (-board_control[1], board_control[0]), dtype=np.float64
        )
        raw_action = np.clip(
            raw_action, -self.config.action_limit, self.config.action_limit
        )
        smoothing = float(np.clip(self.config.action_smoothing, 0.0, 1.0))
        action = smoothing * self._last_action + (1.0 - smoothing) * raw_action
        self._last_action = action
        return action.astype(np.float32)


def _transition(
    observation: Dict[str, np.ndarray],
    action: np.ndarray,
    reward: float,
    *,
    is_first: bool,
    is_last: bool,
    is_terminal: bool,
) -> Dict[str, np.ndarray]:
    result = {
        key: np.asarray(value)
        for key, value in observation.items()
        if not key.startswith("log_")
    }
    result.update(
        {
            "action": np.asarray(action, dtype=np.float32),
            "reset": np.asarray(is_last, dtype=bool),
            "reward": np.asarray(reward, dtype=np.float32),
            "is_first": np.asarray(is_first, dtype=bool),
            "is_last": np.asarray(is_last, dtype=bool),
            "is_terminal": np.asarray(is_terminal, dtype=bool),
        }
    )
    return result


def collect_episode(
    task: TagMazeTask,
    controller: RouteExpertController,
    *,
    layout_index: int,
    seed: int,
    max_steps: int,
) -> tuple[Dict[str, np.ndarray], Dict[str, Any]]:
    observation, info = task.reset(seed=seed, options={"layout_index": layout_index})
    controller.reset()
    transitions: List[Dict[str, np.ndarray]] = []
    reward = 0.0
    is_first = True
    for _ in range(max_steps):
        action = controller.action(task)
        transitions.append(
            _transition(
                observation,
                action,
                reward,
                is_first=is_first,
                is_last=False,
                is_terminal=False,
            )
        )
        is_first = False
        observation, reward, terminated, truncated, info = task.step(action)
        if terminated or truncated:
            transitions.append(
                _transition(
                    observation,
                    np.zeros(2, dtype=np.float32),
                    reward,
                    is_first=False,
                    is_last=True,
                    is_terminal=bool(terminated),
                )
            )
            break
    else:
        info = dict(info)
        info["termination_reason"] = "generator_limit"
        transitions.append(
            _transition(
                observation,
                np.zeros(2, dtype=np.float32),
                reward,
                is_first=False,
                is_last=True,
                is_terminal=False,
            )
        )
    keys = transitions[0].keys()
    episode = {key: np.stack([item[key] for item in transitions]) for key in keys}
    return episode, info


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--split", default="train")
    parser.add_argument("--output", type=Path, default=Path("expert_demos_v2"))
    parser.add_argument("--episodes", type=int, default=128)
    parser.add_argument("--max-steps", type=int, default=1500)
    parser.add_argument("--seed", type=int, default=20260723)
    parser.add_argument("--random-start", action="store_true")
    parser.add_argument("--keep-failures", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    task = TagMazeTask(
        seed=args.seed,
        task_config=TaskConfig(
            maze_manifest=str(args.manifest),
            maze_split=args.split,
            maze_sampling="uniform",
            random_start=args.random_start,
            start_progress_min=0.55 if args.random_start else 0.0,
            start_progress_max=0.90 if args.random_start else 0.0,
            failure_penalty=10.0,
        ),
    )
    controller = RouteExpertController()
    saved = 0
    attempts = 0
    outcomes: Dict[str, int] = {}
    maximum_attempts = max(args.episodes, 5 * args.episodes)
    while saved < args.episodes and attempts < maximum_attempts:
        layout_index = attempts % len(task.layout_paths)
        episode, info = collect_episode(
            task,
            controller,
            layout_index=layout_index,
            seed=args.seed + attempts,
            max_steps=args.max_steps,
        )
        attempts += 1
        reason = str(info.get("termination_reason", "unknown"))
        outcomes[reason] = outcomes.get(reason, 0) + 1
        if not args.keep_failures and reason != "goal_reached":
            continue
        filename = args.output / f"expert_episode_{saved:06d}.npz"
        np.savez_compressed(filename, **episode)
        saved += 1

    summary = {
        "schema_version": 1,
        "manifest": str(args.manifest.resolve()),
        "split": args.split,
        "requested_episodes": args.episodes,
        "saved_episodes": saved,
        "attempts": attempts,
        "random_start": args.random_start,
        "expert_config": asdict(controller.config),
        "outcomes": outcomes,
    }
    (args.output / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    if saved < args.episodes:
        raise RuntimeError(
            f"Only generated {saved}/{args.episodes} requested expert episodes"
        )


if __name__ == "__main__":
    main()
