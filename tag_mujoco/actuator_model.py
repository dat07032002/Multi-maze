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
        raw_action = np.asarray(tuple(action), dtype=np.float64)
        if raw_action.shape != (2,):
            raise ValueError(f"Expected a two-axis action, received {raw_action.shape}")
        if not np.all(np.isfinite(raw_action)):
            # A non-finite action is how NaN from the learner reaches MuJoCo:
            # np.clip propagates it, the servo target becomes NaN, and qpos is
            # poisoned before the observation contract can reject anything.
            raise ValueError(f"TAG action must be finite, received {raw_action!r}")
        action_array = np.clip(raw_action, -1.0, 1.0)
        # Reproduce the deployed path exactly: the learner scales by 240 and the
        # bridge executable then clamps to 180. See ActuatorConfig for why these
        # must stay two stages.
        command = np.clip(
            action_array
            * np.asarray(self.config.policy_command_scale)
            * np.asarray(self.config.policy_command_sign),
            -np.asarray(self.config.policy_command_limit),
            np.asarray(self.config.policy_command_limit),
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
        effective_command = servo_offset / np.asarray(self.config.command_scale)
        positive = np.maximum(effective_command, 0.0)
        negative = np.minimum(effective_command, 0.0)
        positive[
            positive <= np.asarray(self.config.stiction_command_positive)
        ] = 0.0
        negative[
            -negative <= np.asarray(self.config.stiction_command_negative)
        ] = 0.0
        coupled = (
            np.asarray(self.config.board_rad_per_command_positive) @ positive
            + np.asarray(self.config.board_rad_per_command_negative) @ negative
        )
        # Residual axis mixing beyond the identified command maps -- unmeasured
        # linkage cross-talk. Nominal is the identity, so this changes nothing
        # without randomization; it was declared and randomized but never
        # applied until 2026-07-29, which silently made dr_act_coupling_* inert.
        coupled = np.asarray(self.config.cross_axis_coupling) @ coupled
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

    def action_for_board_target(self, board_target: Iterable[float]) -> np.ndarray:
        """Return the least-error action under the directional local maps.

        This inverse is intended for privileged simulation controllers and
        diagnostics.  A deployed policy still emits actions directly and does
        not receive actuator calibration as an observation.
        """

        target = np.asarray(tuple(board_target), dtype=np.float64)
        if target.shape != (2,):
            raise ValueError(f"Expected two board angles, received {target.shape}")
        target -= np.asarray(self.config.zero_angle_offset_rad)
        # Undo the residual axis mixing before inverting the command maps, so the
        # privileged inverse stays consistent with the forward path.
        target = np.linalg.solve(
            np.asarray(self.config.cross_axis_coupling, dtype=np.float64), target
        )
        positive_map = np.asarray(self.config.board_rad_per_command_positive)
        negative_map = np.asarray(self.config.board_rad_per_command_negative)
        candidates = []
        for signs in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            mapping = np.column_stack(
                [
                    (positive_map if sign > 0 else negative_map)[:, index]
                    for index, sign in enumerate(signs)
                ]
            )
            command = np.linalg.lstsq(mapping, target, rcond=None)[0]
            if any(command[index] * sign < -1e-9 for index, sign in enumerate(signs)):
                continue
            limits = np.asarray(self.config.policy_command_limit)
            command = np.clip(command, -limits, limits)
            # Thresholds are axis-specific, so select them independently.
            thresholds = np.asarray(
                [
                    (
                        self.config.stiction_command_positive[index]
                        if sign > 0
                        else self.config.stiction_command_negative[index]
                    )
                    for index, sign in enumerate(signs)
                ]
            )
            effective = command.copy()
            effective[np.abs(effective) <= thresholds] = 0.0
            error = float(np.linalg.norm(mapping @ effective - target))
            candidates.append((error, command))
        if not candidates:
            return np.zeros(2, dtype=np.float64)
        command = min(candidates, key=lambda item: item[0])[1]
        # Invert the learner's 240 scale, not the bridge clamp. Dividing by 180
        # here used to hand the expert a 1.33x over-scaled action, so a demo that
        # wanted the clamp boundary asked for |action| = 1.0 instead of 0.75.
        return command / (
            np.asarray(self.config.policy_command_scale)
            * np.asarray(self.config.policy_command_sign)
        )

    @property
    def commanded_servo_positions(self) -> np.ndarray:
        return self._commanded_position.copy()

    @property
    def board_target_angles(self) -> np.ndarray:
        return self._board_target.copy()

    @property
    def timed_out(self) -> bool:
        return self._timed_out
