"""TAG-compatible marble detection hysteresis and short-loss recovery."""

from __future__ import annotations

from typing import Callable, Iterable

import numpy as np


class TagObservationFilter:
    """Reproduce the working TAG estimator/environment behavior after misses.

    The detector retains the last marble location for a configurable number of
    missed frames.  Once a loss is reported, the environment briefly predicts
    motion along the route before declaring the marble lost.  The visibility
    flag returned here is diagnostic only and is deliberately not a policy
    input.
    """

    def __init__(
        self,
        miss_threshold: int = 6,
        grace_seconds: float = 0.35,
        prediction_max_speed_mps: float = 0.15,
        velocity_ema_old: float = 0.6,
    ):
        self.miss_threshold = max(1, int(miss_threshold))
        self.grace_seconds = max(0.0, float(grace_seconds))
        self.prediction_max_speed_mps = max(0.0, float(prediction_max_speed_mps))
        self.velocity_ema_old = float(np.clip(velocity_ema_old, 0.0, 1.0))
        self.reset()

    def reset(self) -> None:
        self.time_seconds = 0.0
        self.consecutive_misses = 0
        self.last_visible_time: float | None = None
        self.last_visible_position: np.ndarray | None = None
        self.velocity = np.zeros(2, dtype=np.float32)
        self.last_observation: dict[str, np.ndarray] | None = None
        self.mode = "uninitialized"

    @property
    def confirmed_lost(self) -> bool:
        return self.mode == "lost"

    @staticmethod
    def _copy(observation: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
        return {key: value.copy() for key, value in observation.items()}

    def update(
        self,
        *,
        image: np.ndarray,
        board_angles_rad: Iterable[float],
        measured_xy_m: Iterable[float] | None,
        relative_goal_m: np.ndarray,
        detected: bool,
        dt_seconds: float,
        goal_for_position: Callable[[np.ndarray], np.ndarray],
        project_to_route: Callable[[np.ndarray], np.ndarray],
    ) -> tuple[dict[str, np.ndarray], bool, str]:
        dt = max(0.0, float(dt_seconds))
        self.time_seconds += dt
        angles = np.asarray(tuple(board_angles_rad), dtype=np.float32)
        if angles.shape != (2,):
            raise ValueError("TAG observation filter requires two board angles")

        if detected:
            if measured_xy_m is None:
                raise ValueError("A detected marble requires an XY measurement")
            position = np.asarray(tuple(measured_xy_m), dtype=np.float32)
            if position.shape != (2,):
                raise ValueError("TAG marble measurement must be XY")
            if self.last_visible_position is not None and self.last_visible_time is not None:
                elapsed = self.time_seconds - self.last_visible_time
                if elapsed > 1e-4:
                    velocity = (position - self.last_visible_position) / elapsed
                    speed = float(np.linalg.norm(velocity))
                    if speed > self.prediction_max_speed_mps > 0.0:
                        velocity *= self.prediction_max_speed_mps / speed
                    old = self.velocity_ema_old
                    self.velocity = (old * self.velocity + (1.0 - old) * velocity).astype(
                        np.float32
                    )
            observation = {
                "image": np.asarray(image, dtype=np.uint8).copy(),
                "states": np.concatenate((angles, position)).astype(np.float32),
                "goal": np.asarray(relative_goal_m, dtype=np.float32).reshape(-1).copy(),
            }
            self.last_visible_position = position.copy()
            self.last_visible_time = self.time_seconds
            self.last_observation = self._copy(observation)
            self.consecutive_misses = 0
            self.mode = "visible"
            return observation, True, self.mode

        self.consecutive_misses += 1
        if self.last_observation is None or self.last_visible_position is None:
            self.mode = "lost"
            return {
                "image": np.zeros((64, 64, 1), dtype=np.uint8),
                "states": np.zeros(4, dtype=np.float32),
                "goal": np.zeros(10, dtype=np.float32),
            }, False, self.mode

        observation = self._copy(self.last_observation)
        observation["states"][:2] = angles
        if self.consecutive_misses < self.miss_threshold:
            self.mode = "detector_hysteresis"
            return observation, True, self.mode

        loss_frames = self.consecutive_misses - self.miss_threshold + 1
        missing_seconds = loss_frames * dt
        if missing_seconds < self.grace_seconds:
            predicted = self.last_visible_position + self.velocity * missing_seconds
            predicted = np.asarray(project_to_route(predicted), dtype=np.float32)
            observation["states"][2:4] = predicted
            observation["goal"] = np.asarray(
                goal_for_position(predicted), dtype=np.float32
            ).reshape(-1)
            self.mode = "occlusion_grace"
            return observation, True, self.mode

        self.mode = "lost"
        return observation, False, self.mode
