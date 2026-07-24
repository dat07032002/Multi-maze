"""Hiwonder command semantics and uncertain servo/linkage dynamics."""

from __future__ import annotations

import collections
import math
from typing import Deque, Iterable

import numpy as np

try:
    from .system_config import ActuatorConfig
except ImportError:
    from system_config import ActuatorConfig


class HiwonderActuatorModel:
    """Convert policy actions to delayed, rate-limited board-angle targets."""

    def __init__(self, config: ActuatorConfig):
        self.config = config
        self._home = np.asarray(config.home_positions, dtype=np.float64)
        self._pending_target = self._home.copy()
        self._commanded_position = self._home.copy()
        self._board_target = np.asarray(config.zero_angle_offset_rad, dtype=np.float64)
        self._tick_accumulator = 0.0
        self._time_seconds = 0.0
        self._last_action_time: float | None = None
        self._timed_out = False
        delay_ticks = max(0, math.ceil(config.total_delay_seconds * config.update_rate_hz))
        self._delay: Deque[np.ndarray] = collections.deque(
            [self._home.copy() for _ in range(delay_ticks)]
        )

    def reset(self) -> None:
        self.__init__(self.config)

    def submit_action(self, action: Iterable[float]) -> None:
        action_array = np.clip(np.asarray(tuple(action), dtype=np.float64), -1.0, 1.0)
        if action_array.shape != (2,):
            raise ValueError(f"Expected a two-axis action, received {action_array.shape}")
        command = (
            action_array
            * np.asarray(self.config.policy_command_limit)
            * np.asarray(self.config.policy_command_sign)
        )
        target = self._home + command * np.asarray(self.config.command_scale)
        limits = np.asarray(self.config.servo_limits, dtype=np.float64)
        self._pending_target = np.clip(target, limits[:, 0], limits[:, 1])
        self._last_action_time = self._time_seconds
        self._timed_out = False

    def _driver_tick(self) -> None:
        if self._delay:
            self._delay.append(self._pending_target.copy())
            delayed_target = self._delay.popleft()
        else:
            delayed_target = self._pending_target
        error = delayed_target - self._commanded_position
        maximum_step = np.asarray(self.config.max_step_per_tick, dtype=np.float64)
        step = np.clip(error, -maximum_step, maximum_step)
        step[np.abs(error) <= self.config.deadband_units] = 0.0
        self._commanded_position += step

    def step(self, dt: float) -> np.ndarray:
        dt = float(dt)
        self._time_seconds += dt
        if (
            self.config.timeout_go_home
            and self.config.command_timeout_seconds > 0.0
            and self._last_action_time is not None
            and self._time_seconds - self._last_action_time
            > self.config.command_timeout_seconds
        ):
            self._pending_target = self._home.copy()
            self._timed_out = True
        self._tick_accumulator += dt
        tick_period = 1.0 / self.config.update_rate_hz
        while self._tick_accumulator + 1e-12 >= tick_period:
            self._tick_accumulator -= tick_period
            self._driver_tick()

        servo_offset = self._commanded_position - self._home
        raw_angle = (
            servo_offset
            / np.asarray(self.config.servo_units_per_rad)
            * np.asarray(self.config.linkage_angle_sign)
        )
        coupled = np.asarray(self.config.cross_axis_coupling) @ raw_angle
        coupled += np.asarray(self.config.zero_angle_offset_rad)
        response = 1.0 - math.exp(
            -float(dt) / max(1e-6, self.config.response_time_constant_seconds)
        )
        self._board_target += response * (coupled - self._board_target)
        self._board_target = np.clip(
            self._board_target,
            -self.config.board_angle_limit_rad,
            self.config.board_angle_limit_rad,
        )
        return self._board_target.copy()

    def hardware_reset_profile(self) -> dict[str, object]:
        """Return the two-stage physical reset sequence used by TAG."""

        return {
            "prehome_positions": tuple(self.config.reset_prehome_positions),
            "prehome_move_seconds": self.config.reset_prehome_move_seconds,
            "prehome_wait_seconds": self.config.reset_prehome_wait_seconds,
            "home_positions": tuple(self.config.home_positions),
            "home_move_seconds": self.config.reset_home_move_seconds,
        }

    @property
    def commanded_servo_positions(self) -> np.ndarray:
        return self._commanded_position.copy()

    @property
    def board_target_angles(self) -> np.ndarray:
        return self._board_target.copy()

    @property
    def timed_out(self) -> bool:
        return self._timed_out
