"""RL-agnostic CyberRunner plant, sensor, timing, and termination model."""

from __future__ import annotations

import collections
import math
from dataclasses import asdict, dataclass
from typing import Any, Deque, Dict, Iterable, List, Tuple

import numpy as np

try:
    from .actuator_model import HiwonderActuatorModel
    from .camera_model import PolicyCameraModel
    from .observation_filter import TagObservationFilter
    from .simulator import CyberRunnerSim
    from .system_config import ActuatorConfig, PhysicsConfig, SystemConfig
except ImportError:
    from actuator_model import HiwonderActuatorModel
    from camera_model import PolicyCameraModel
    from observation_filter import TagObservationFilter
    from simulator import CyberRunnerSim
    from system_config import ActuatorConfig, PhysicsConfig, SystemConfig


@dataclass
class ModelStep:
    observation: Dict[str, np.ndarray]
    terminated: bool
    truncated: bool
    reason: str
    info: Dict[str, Any]


def _copy_observation(observation: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
    return {key: value.copy() for key, value in observation.items()}


class PolylineRoute:
    def __init__(self, waypoints: Iterable[Iterable[float]]):
        self.points = np.asarray(tuple(tuple(point) for point in waypoints), dtype=np.float64)
        if self.points.ndim != 2 or self.points.shape[1] != 2 or len(self.points) < 2:
            raise ValueError("A route needs at least two 2D waypoints")
        self.vectors = np.diff(self.points, axis=0)
        self.lengths = np.linalg.norm(self.vectors, axis=1)
        if np.any(self.lengths <= 1e-9):
            raise ValueError("Route contains duplicate consecutive waypoints")
        self.cumulative = np.concatenate(([0.0], np.cumsum(self.lengths)))
        self.total_length = float(self.cumulative[-1])

    def project(
        self,
        xy: Iterable[float],
        progress_hint: float | None = None,
        backward_window: float = math.inf,
        forward_window: float = math.inf,
    ) -> Tuple[float, np.ndarray, float]:
        """Project XY onto the route, optionally near the previous progress.

        Restricting the search window prevents reward jumps when separate maze
        corridors are spatially close but far apart along the route.
        """
        point = np.asarray(tuple(xy), dtype=np.float64)
        relative = point - self.points[:-1]
        fractions = np.sum(relative * self.vectors, axis=1) / (self.lengths**2)
        fractions = np.clip(fractions, 0.0, 1.0)
        projections = self.points[:-1] + fractions[:, None] * self.vectors
        progresses = self.cumulative[:-1] + fractions * self.lengths
        allowed = np.ones(len(self.lengths), dtype=bool)
        if progress_hint is not None:
            lower = float(progress_hint) - float(backward_window)
            upper = float(progress_hint) + float(forward_window)
            allowed = np.logical_and(progresses >= lower, progresses <= upper)
            if not np.any(allowed):
                allowed[:] = True
        distances = np.linalg.norm(projections - point, axis=1)
        distances[~allowed] = np.inf
        index = int(np.argmin(distances))
        return float(progresses[index]), projections[index], float(distances[index])

    def closest_progress(self, xy: Iterable[float]) -> float:
        return self.project(xy)[0]

    def point_at(self, progress: float) -> np.ndarray:
        progress = float(np.clip(progress, 0.0, self.total_length))
        index = min(
            len(self.lengths) - 1,
            int(np.searchsorted(self.cumulative, progress, side="right") - 1),
        )
        fraction = (progress - self.cumulative[index]) / self.lengths[index]
        return self.points[index] + fraction * self.vectors[index]

    def relative_targets(
        self,
        xy: Iterable[float],
        count: int,
        spacing: float,
    ) -> Tuple[np.ndarray, float]:
        xy_array = np.asarray(tuple(xy), dtype=np.float64)
        progress = self.closest_progress(xy_array)
        targets = [
            self.point_at(progress + spacing * (index + 1)) - xy_array
            for index in range(count)
        ]
        return np.asarray(targets, dtype=np.float32).reshape(-1), progress


class CyberRunnerSystemModel:
    """Complete simulator model, deliberately independent of reward design."""

    def __init__(self, layout: Dict[str, Any], config: SystemConfig | None = None):
        self.layout = layout
        self.config = config or SystemConfig()
        self.route = PolylineRoute(layout["waypoints"])
        self.rng = np.random.default_rng(0)
        self.sim: CyberRunnerSim
        self.actuator: HiwonderActuatorModel
        self.camera: PolicyCameraModel
        self.observation_filter: TagObservationFilter
        self.active_actuator_config: ActuatorConfig
        self.active_physics_config: PhysicsConfig
        self.steps = 0
        self._physics_time_remainder = 0.0
        self._last_ball_xy = np.zeros(2, dtype=np.float64)
        self._observation_queue: Deque[Dict[str, np.ndarray]] = collections.deque()
        self.reset(seed=0, randomize=False)

    def reset(
        self,
        seed: int | None = None,
        randomize: bool = False,
        ball_xy: Iterable[float] | None = None,
        ball_velocity_xy: Iterable[float] = (0.0, 0.0),
        board_tilt: Tuple[float, float] = (0.0, 0.0),
    ) -> Dict[str, np.ndarray]:
        self.rng = np.random.default_rng(seed)
        self.active_actuator_config = (
            self.config.actuator.randomized(self.rng)
            if randomize
            else self.config.actuator
        )
        self.active_physics_config = (
            self.config.physics.randomized(self.rng)
            if randomize
            else self.config.physics
        )
        self.sim = CyberRunnerSim(
            self.layout,
            model_params=asdict(self.active_physics_config),
        )
        self.actuator = HiwonderActuatorModel(self.active_actuator_config)
        self.camera = PolicyCameraModel(self.layout, self.config.camera)
        camera_seed = int(self.rng.integers(0, 2**31 - 1))
        self.camera.reset(camera_seed, randomize=randomize)
        self.observation_filter = TagObservationFilter(
            miss_threshold=self.config.camera.detector_miss_threshold,
            grace_seconds=self.config.camera.ball_loss_grace_seconds,
            prediction_max_speed_mps=self.config.camera.prediction_max_speed_mps,
        )
        velocity = np.asarray(tuple(ball_velocity_xy), dtype=np.float64)
        moving_reset = bool(np.linalg.norm(velocity) > 1e-12 or np.linalg.norm(board_tilt) > 1e-12)
        self.sim.reset(
            ball_xy=ball_xy,
            tilt=board_tilt,
            ball_velocity_xy=velocity,
            settle_steps=0 if moving_reset else 30,
        )
        self.steps = 0
        self._physics_time_remainder = 0.0
        self._last_ball_xy = self.sim.ball_board_position()[:2]
        observation, _ = self._make_current_observation(dt_seconds=0.0)
        delay = max(0, int(self.config.camera.observation_delay_steps))
        self._observation_queue = collections.deque(
            [_copy_observation(observation) for _ in range(delay)]
        )
        return _copy_observation(observation)

    def _advance_physics(self) -> None:
        control_dt = 1.0 / self.config.control_rate_hz
        physics_dt = float(self.sim.model.opt.timestep)
        duration = control_dt + self._physics_time_remainder
        physics_steps = max(1, int(duration / physics_dt))
        self._physics_time_remainder = duration - physics_steps * physics_dt
        for _ in range(physics_steps):
            target_angles = self.actuator.step(physics_dt)
            self.sim.set_tilt(float(target_angles[0]), float(target_angles[1]))
            self.sim.step()

    def _route_goal_for_position(self, position: np.ndarray) -> np.ndarray:
        return self.route.relative_targets(
            position,
            self.config.relative_goal_points,
            self.config.relative_goal_spacing_m,
        )[0]

    def _project_to_route(self, position: np.ndarray) -> np.ndarray:
        progress = self.route.closest_progress(position)
        return self.route.point_at(progress)

    def _make_current_observation(
        self, dt_seconds: float
    ) -> Tuple[Dict[str, np.ndarray], Dict[str, Any]]:
        board_angles = self.sim.board_angles()
        ball = self.sim.ball_board_position()
        width, height = self.sim.board_size
        physically_visible = bool(
            ball[2] > -self.sim.ball_radius
            and 0.0 <= ball[0] <= width
            and 0.0 <= ball[1] <= height
        )
        image, detected = self.camera.capture(
            ball[:2], self.sim.ball_radius, ball_visible=physically_visible
        )
        relative_goal, progress = self.route.relative_targets(
            ball[:2],
            self.config.relative_goal_points,
            self.config.relative_goal_spacing_m,
        )
        measured_angles = board_angles + self.rng.normal(
            0.0, self.config.camera.angle_noise_std_rad, size=2
        )
        measured_ball = None
        if detected:
            measured_ball = ball[:2] + self.rng.normal(
                0.0, self.config.camera.position_noise_std_m, size=2
            )
            relative_goal = self._route_goal_for_position(measured_ball)
        observation, reported_visible, observation_mode = self.observation_filter.update(
            image=image,
            board_angles_rad=measured_angles,
            measured_xy_m=measured_ball,
            relative_goal_m=relative_goal,
            detected=detected,
            dt_seconds=dt_seconds,
            goal_for_position=self._route_goal_for_position,
            project_to_route=self._project_to_route,
        )
        observation["ball_visible"] = np.asarray([reported_visible], dtype=np.bool_)
        info = {
            "true_board_angles": board_angles.copy(),
            "true_ball_position": ball.copy(),
            "route_progress_m": progress,
            "camera_detected_ball": detected,
            "camera_reported_ball": reported_visible,
            "camera_observation_mode": observation_mode,
        }
        return observation, info

    def _termination(self) -> Tuple[bool, bool, str]:
        ball = self.sim.ball_board_position()
        width, height = self.sim.board_size
        ball_fell = ball[2] < -self.sim.ball_radius
        ball_left = ball[0] < 0.0 or ball[0] > width or ball[1] < 0.0 or ball[1] > height
        if ball_fell:
            return (
                (True, False, "ball_fell")
                if self.observation_filter.confirmed_lost
                else (False, False, "running")
            )
        if ball_left:
            return (
                (True, False, "ball_left_board")
                if self.observation_filter.confirmed_lost
                else (False, False, "running")
            )
        if self.observation_filter.confirmed_lost:
            return True, False, "ball_lost"
        goal = np.asarray(self.layout["waypoints"][-1], dtype=np.float64)
        if np.linalg.norm(ball[:2] - goal) <= self.config.goal_radius_m:
            return True, False, "goal_reached"
        if self.steps >= self.config.maximum_episode_steps:
            return False, True, "time_limit"
        return False, False, "running"

    def step(self, action: Iterable[float]) -> ModelStep:
        self.actuator.submit_action(action)
        self._advance_physics()
        self.steps += 1
        current_observation, info = self._make_current_observation(
            dt_seconds=1.0 / self.config.control_rate_hz
        )
        self._observation_queue.append(_copy_observation(current_observation))
        delayed_observation = self._observation_queue.popleft()
        terminated, truncated, reason = self._termination()
        ball_xy = info["true_ball_position"][:2]
        ball_velocity = (
            (ball_xy - self._last_ball_xy) * self.config.control_rate_hz
        )
        self._last_ball_xy = ball_xy.copy()
        info.update(
            {
                "ball_velocity_board_mps": ball_velocity,
                "actuator_board_target": self.actuator.board_target_angles,
                "actuator_servo_positions": self.actuator.commanded_servo_positions,
                "step": self.steps,
            }
        )
        return ModelStep(
            delayed_observation,
            terminated,
            truncated,
            reason,
            info,
        )

    def parameter_snapshot(self) -> Dict[str, Any]:
        return {
            "actuator": asdict(self.active_actuator_config),
            "physics": asdict(self.active_physics_config),
            "camera": self.camera.metadata(),
            "control_rate_hz": self.config.control_rate_hz,
            "maximum_episode_steps": self.config.maximum_episode_steps,
        }
