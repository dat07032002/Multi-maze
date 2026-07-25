"""Direct Embodied adapter for the clean MuJoCo TagMaze task."""

from __future__ import annotations

import functools
import pathlib
import sys
from typing import Any

import embodied
import numpy as np


REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parents[4]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from tag_mujoco.tag_env import TagMazeTask, TaskConfig  # noqa: E402


class TagMaze(embodied.Env):
    def __init__(self, task: str = "sim", layout_paths=None, seed: int = 0, **kwargs: Any):
        if task != "sim":
            raise ValueError(f"Unsupported clean TagMaze task {task!r}")
        task_fields = set(TaskConfig.__dataclass_fields__)
        task_kwargs = {key: kwargs.pop(key) for key in list(kwargs) if key in task_fields}
        if kwargs:
            raise TypeError(f"Unknown TagMaze environment options: {sorted(kwargs)}")
        self._env = TagMazeTask(
            layout_paths=layout_paths,
            seed=seed,
            task_config=TaskConfig(**task_kwargs),
        )
        self._done = True
        self._info = None

    @property
    def info(self):
        return self._info

    @functools.cached_property
    def obs_space(self):
        points = self._env.system_config.relative_goal_points
        return {
            "image": embodied.Space(np.uint8, (64, 64, 1), 0, 255),
            "states": embodied.Space(np.float32, (4,)),
            "goal": embodied.Space(np.float32, (points * 2,)),
            "log_progress": embodied.Space(np.float32, (1,)),
            "log_cross_track_error": embodied.Space(np.float32, (1,)),
            "log_clearance_cost": embodied.Space(np.float32, (1,)),
            "log_min_clearance": embodied.Space(np.float32, (1,)),
            "log_maze_difficulty": embodied.Space(np.float32, (1,)),
            "log_start_progress": embodied.Space(np.float32, (1,)),
            "log_randomization_strength": embodied.Space(np.float32, (1,)),
            "log_fall_cost": embodied.Space(np.float32, (1,)),
            "log_success": embodied.Space(np.float32, (1,)),
            "log_reward": embodied.Space(np.float32, (1,)),
            "reward": embodied.Space(np.float32),
            "is_first": embodied.Space(bool),
            "is_last": embodied.Space(bool),
            "is_terminal": embodied.Space(bool),
        }

    @functools.cached_property
    def act_space(self):
        return {
            "action": embodied.Space(np.float32, (2,), -1.0, 1.0),
            "reset": embodied.Space(bool),
        }

    def step(self, action):
        if action["reset"] or self._done:
            observation, self._info = self._env.reset()
            observation.setdefault("log_fall_cost", np.zeros(1, dtype=np.float32))
            observation.setdefault("log_success", np.zeros(1, dtype=np.float32))
            observation.setdefault("log_reward", np.zeros(1, dtype=np.float32))
            self._done = False
            return self._format(observation, 0.0, is_first=True)
        observation, reward, terminated, truncated, self._info = self._env.step(
            action["action"]
        )
        self._done = bool(terminated or truncated)
        return self._format(
            observation,
            reward,
            is_last=self._done,
            is_terminal=bool(terminated),
        )

    def _format(
        self,
        observation,
        reward,
        is_first=False,
        is_last=False,
        is_terminal=False,
    ):
        return {
            **{key: np.asarray(value) for key, value in observation.items()},
            "reward": np.float32(reward),
            "is_first": bool(is_first),
            "is_last": bool(is_last),
            "is_terminal": bool(is_terminal),
        }

    def render(self):
        return self._env.render()

    def close(self):
        self._env.close()
