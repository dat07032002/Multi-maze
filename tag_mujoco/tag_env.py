"""New route-conditioned TAG task and optional Gym wrapper.

This module is intentionally independent of the legacy ROS/TCP environments,
their reward shaping, and their replay implementation.
"""

from __future__ import annotations

import glob
import math
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

import numpy as np

try:  # The training repository currently uses legacy Gym.
    import gym  # type: ignore

    _GYMNASIUM_API = False
except ImportError:  # Local verification uses maintained Gymnasium.
    import gymnasium as gym  # type: ignore

    _GYMNASIUM_API = True

try:
    from .maze_layout import load_json_layout
    from .maze_dataset import DEFAULT_MANIFEST, load_split
    from .policy_contract import TagPolicyContract
    from .route_planner import (
        PlannerConfig,
        apply_safe_route,
        signed_ball_clearance,
        signed_hole_clearance,
        signed_wall_clearance,
        validate_route,
    )
    from .system_config import SystemConfig
    from .system_model import TagSystemModel, PolylineRoute
except ImportError:  # Preserve direct-script execution from this directory.
    from maze_layout import load_json_layout
    from maze_dataset import DEFAULT_MANIFEST, load_split
    from policy_contract import TagPolicyContract
    from route_planner import (
        PlannerConfig,
        apply_safe_route,
        signed_ball_clearance,
        signed_hole_clearance,
        signed_wall_clearance,
        validate_route,
    )
    from system_config import SystemConfig
    from system_model import TagSystemModel, PolylineRoute


HERE = Path(__file__).resolve().parent
DEFAULT_LAYOUT = HERE / "generated_mazes" / "maze_seed_970.json"
DR_METRIC_KEYS = (
    "dr_act_delay_s", "dr_act_response_s",
    "dr_act_offset_0", "dr_act_offset_1", "dr_act_coupling_01",
    "dr_act_coupling_10", "dr_act_pos_00", "dr_act_pos_01",
    "dr_act_pos_10", "dr_act_pos_11", "dr_act_neg_00", "dr_act_neg_01",
    "dr_act_neg_10", "dr_act_neg_11", "dr_act_stiction_pos_0",
    "dr_act_stiction_pos_1", "dr_act_stiction_neg_0",
    "dr_act_stiction_neg_1", "dr_phys_mass", "dr_phys_floor_slide",
    "dr_phys_wall_slide", "dr_phys_ball_slide", "dr_phys_torsional",
    "dr_phys_rolling", "dr_phys_damping", "dr_phys_restitution",
    "dr_phys_kp", "dr_phys_kv", "dr_cam_brightness", "dr_cam_contrast",
    "dr_cam_blur", "dr_cam_noise", "dr_cam_crop_x", "dr_cam_crop_y",
    "dr_cam_dropout", "dr_cam_burst",
)


@dataclass(frozen=True)
class TaskConfig:
    randomize_plant: bool = False
    random_start: bool = False
    start_progress_min: float = 0.0
    start_progress_max: float = 0.85
    start_lateral_range_m: float = 0.002
    start_velocity_range_mps: float = 0.0
    progress_forward_window_m: float = 0.035
    progress_backward_window_m: float = 0.080
    clearance_warning_m: float = 0.005
    reward_mode: str = "scaled_progress"
    progress_reward_scale: float = 10.0
    success_bonus: float = 10.0
    failure_penalty: float = 5.0
    # Penalty on how fast the commanded tilt changes between steps. The 500k
    # nominal policy is effectively bang-bang: mean |action| about 0.90 on a
    # +/-1 range, saturated on roughly 70% of steps, with step-to-step changes
    # of 0.5 to 1.2. Every 192-episode failure landed at a route turn in its
    # own 95th percentile or above, which is what slammed, unmodulated tilt
    # cannot decelerate into. Zero keeps the historical reward exactly.
    action_rate_penalty: float = 0.0
    # Dense penalty for letting the ball drift toward a hole. Until now the only
    # hazard signal was the terminal failure_penalty, charged after the ball had
    # already fallen, which is a sparse teacher for a margin measured in
    # millimetres. Holes sit a median 18.4 mm from the route and the 1st
    # percentile is 8.0 mm, so an 8 mm band covers only 0.94% of on-route travel
    # and stays silent while the policy tracks the route. A 12 mm band would
    # cover 15.3% and would penalize ordinary driving. Zero keeps the historical
    # reward exactly.
    hole_warning_m: float = 0.008
    hole_clearance_penalty: float = 0.0
    path_tracking_tolerance_m: float = 0.004
    path_tracking_penalty: float = 0.0
    wall_warning_m: float = 0.003
    wall_riding_penalty: float = 0.0
    maze_manifest: str = ""
    maze_split: str = ""
    maze_sampling: str = "uniform"
    curriculum_episodes: int = 5000
    plr_uniform_mix: float = 0.25
    plr_staleness_mix: float = 0.15
    plr_ema: float = 0.10
    start_curriculum: bool = False
    start_curriculum_initial_min: float = 0.80
    start_curriculum_expand_step: float = 0.10
    start_curriculum_window: int = 40
    start_curriculum_success_threshold: float = 0.70
    full_start_probability: float = 0.20
    randomization_curriculum: bool = False
    randomization_initial_strength: float = 0.0
    randomization_expand_step: float = 0.10
    randomization_max_strength: float = 1.0
    randomization_window: int = 50
    randomization_success_threshold: float = 0.60
    randomization_groups: str = "all"


def reward_components(
    config: TaskConfig,
    progress_fraction: float,
    route_completion: float,
    termination_reason: str,
) -> Tuple[float, float, float]:
    """Return progress, success, and failure reward terms independently."""
    failed = termination_reason in {"ball_fell", "ball_left_board"}
    succeeded = termination_reason == "goal_reached"
    progress_reward = float(progress_fraction)
    success_reward = 0.0
    failure_reward = 0.0
    if config.reward_mode == "scaled_progress":
        progress_reward *= config.progress_reward_scale
        success_reward = config.success_bonus * float(succeeded)
        failure_reward = -config.failure_penalty * float(failed)
    elif config.reward_mode == "progress_failure_zero" and failed:
        failure_reward = -float(route_completion)
    return progress_reward, success_reward, failure_reward


def hole_proximity_cost(config: TaskConfig, hole_clearance_m: float) -> float:
    """Return a cost in [0, 1] that ramps up as the ball nears a hole.

    Zero outside the warning band, one once the ball surface reaches the hole
    rim. Always measured so every run reports its hole exposure, whether or not
    it is charged for it.
    """

    band = max(config.hole_warning_m, 1e-6)
    if math.isinf(hole_clearance_m) and hole_clearance_m > 0.0:
        return 0.0
    if not math.isfinite(hole_clearance_m):
        raise ValueError(f"Hole clearance must be finite or +inf, got {hole_clearance_m!r}")
    return float(np.clip((band - hole_clearance_m) / band, 0.0, 1.0))


def path_tracking_cost(config: TaskConfig, cross_track_error_m: float) -> float:
    """Return zero inside the desired path tube and ramp outside it."""

    if not math.isfinite(cross_track_error_m):
        return 0.0
    tolerance = max(config.path_tracking_tolerance_m, 1e-6)
    return float(max(0.0, cross_track_error_m - tolerance) / tolerance)


def wall_riding_cost(config: TaskConfig, wall_clearance_m: float) -> float:
    """Return a soft cost for sustained near-wall driving.

    This is intentionally separate from hole clearance. Walls are allowed as
    backup rails, but a policy should not depend on riding them for progress.
    """

    band = max(config.wall_warning_m, 1e-6)
    if not math.isfinite(wall_clearance_m):
        raise ValueError(f"Wall clearance must be finite, got {wall_clearance_m!r}")
    return float(np.clip((band - wall_clearance_m) / band, 0.0, 1.0))


def action_rate_cost(
    action: np.ndarray,
    previous_action: np.ndarray | None,
) -> float:
    """Return the mean absolute per-step change in the commanded tilt.

    Always measured so every run reports how smoothly it drives, whether or not
    it is charged for it. The first step of an episode has no predecessor and is
    never charged, so a reset cannot be penalized for the tilt it inherits.
    """

    if previous_action is None:
        return 0.0
    delta = np.abs(np.asarray(action, dtype=np.float64) - previous_action)
    return float(np.mean(delta))


def _resolve_layout_paths(layout_paths: str | Sequence[str] | None) -> List[Path]:
    if layout_paths is None:
        return [DEFAULT_LAYOUT]
    if isinstance(layout_paths, str):
        items = [item.strip() for item in layout_paths.split(",") if item.strip()]
    else:
        items = list(layout_paths)
    resolved: List[Path] = []
    for item in items:
        expanded = [Path(path) for path in glob.glob(str(item))]
        if expanded:
            resolved.extend(expanded)
        else:
            resolved.append(Path(item))
    resolved = [path.resolve() for path in resolved]
    missing = [path for path in resolved if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing TAG layouts: {missing}")
    if not resolved:
        raise ValueError("At least one layout is required")
    return sorted(set(resolved))


class TagMazeTask:
    """RL task with normalized observations and independently defined rewards."""

    def __init__(
        self,
        layout_paths: str | Sequence[str] | None = None,
        seed: int = 0,
        task_config: TaskConfig = TaskConfig(),
        system_config: SystemConfig = SystemConfig(),
        planner_config: PlannerConfig = PlannerConfig(),
    ):
        if task_config.reward_mode not in {
            "progress",
            "progress_failure_zero",
            "scaled_progress",
        }:
            raise ValueError(f"Unsupported reward mode: {task_config.reward_mode}")
        if task_config.maze_sampling not in {"uniform", "curriculum", "plr"}:
            raise ValueError(f"Unsupported maze sampling: {task_config.maze_sampling}")
        if task_config.curriculum_episodes <= 0:
            raise ValueError("curriculum_episodes must be positive")
        if not 0.0 <= task_config.plr_uniform_mix <= 1.0:
            raise ValueError("plr_uniform_mix must be in [0, 1]")
        if not 0.0 <= task_config.plr_staleness_mix <= 1.0:
            raise ValueError("plr_staleness_mix must be in [0, 1]")
        if task_config.plr_uniform_mix + task_config.plr_staleness_mix > 1.0:
            raise ValueError("PLR mixture weights must sum to at most one")
        if task_config.start_curriculum_window <= 0:
            raise ValueError("start_curriculum_window must be positive")
        if task_config.randomization_window <= 0:
            raise ValueError("randomization_window must be positive")
        if not 0.0 <= task_config.randomization_max_strength <= 1.0:
            raise ValueError("randomization_max_strength must be in [0, 1]")
        if task_config.maze_split and layout_paths is not None:
            raise ValueError("Choose either maze_split or explicit layout_paths, not both")
        if task_config.maze_split:
            split = load_split(
                task_config.maze_split,
                task_config.maze_manifest or DEFAULT_MANIFEST,
            )
            self.layout_paths = list(split.paths)
            self.layout_metadata = [dict(item) for item in split.metadata]
            self.maze_split = split.name
        else:
            self.layout_paths = _resolve_layout_paths(layout_paths)
            self.layout_metadata = [{} for _ in self.layout_paths]
            self.maze_split = "explicit" if layout_paths is not None else "smoke_default"
        self.task_config = task_config
        self.system_config = system_config
        self.planner_config = planner_config
        self.rng = np.random.default_rng(seed)
        self._layout_cache: Dict[Path, Dict[str, Any]] = {}
        self.layout: Dict[str, Any]
        self.model: TagSystemModel
        self.route: PolylineRoute
        self.layout_path: Path
        self.progress_m = 0.0
        self.minimum_clearance_m = math.inf
        self.episode_return = 0.0
        self.episode_steps = 0
        self._previous_action: np.ndarray | None = None
        self.last_info: Dict[str, Any] = {}
        self.episodes_started = 0
        self.layout_index = 0
        self.layout_sampling_probability = 1.0
        self.policy_contract: TagPolicyContract
        count = len(self.layout_paths)
        self._maze_visits = np.zeros(count, dtype=np.int64)
        self._maze_success = np.zeros(count, dtype=np.float64)
        self._maze_progress = np.zeros(count, dtype=np.float64)
        self._maze_return_mean = np.zeros(count, dtype=np.float64)
        self._maze_return_square = np.zeros(count, dtype=np.float64)
        self._maze_last_visit = np.zeros(count, dtype=np.int64)
        self._recent_successes: deque[float] = deque(
            maxlen=max(
                task_config.start_curriculum_window,
                task_config.randomization_window,
            )
        )
        self._start_frontier = float(task_config.start_curriculum_initial_min)
        self._randomization_strength = float(
            np.clip(task_config.randomization_initial_strength, 0.0, 1.0)
        )
        self._last_start_expansion = 0
        self._last_randomization_expansion = 0
        self.start_progress_fraction = 0.0
        self.active_randomization_strength = 0.0

    def _record_completed_episode(self) -> None:
        """Update local adaptive curricula once for the episode just completed."""

        if self.episode_steps <= 0 or not self.last_info:
            return
        index = self.layout_index
        alpha = float(np.clip(self.task_config.plr_ema, 1e-6, 1.0))
        success = float(bool(self.last_info.get("success", False)))
        progress = float(self.last_info.get("route_completion", 0.0))
        episode_return = float(self.last_info.get("episode_return", 0.0))
        first = self._maze_visits[index] == 0
        self._maze_visits[index] += 1
        if first:
            self._maze_success[index] = success
            self._maze_progress[index] = progress
            self._maze_return_mean[index] = episode_return
            self._maze_return_square[index] = episode_return**2
        else:
            self._maze_success[index] += alpha * (success - self._maze_success[index])
            self._maze_progress[index] += alpha * (progress - self._maze_progress[index])
            self._maze_return_mean[index] += alpha * (
                episode_return - self._maze_return_mean[index]
            )
            self._maze_return_square[index] += alpha * (
                episode_return**2 - self._maze_return_square[index]
            )
        self._maze_last_visit[index] = self.episodes_started
        self._recent_successes.append(success)
        self._advance_curricula()

    def _advance_curricula(self) -> None:
        config = self.task_config
        if config.start_curriculum and len(self._recent_successes) >= config.start_curriculum_window:
            recent = tuple(self._recent_successes)[-config.start_curriculum_window :]
            enough_time = (
                self.episodes_started - self._last_start_expansion
                >= config.start_curriculum_window
            )
            if enough_time and float(np.mean(recent)) >= config.start_curriculum_success_threshold:
                self._start_frontier = max(
                    config.start_progress_min,
                    self._start_frontier - config.start_curriculum_expand_step,
                )
                self._last_start_expansion = self.episodes_started
        if (
            config.randomize_plant
            and config.randomization_curriculum
            and len(self._recent_successes) >= config.randomization_window
        ):
            recent = tuple(self._recent_successes)[-config.randomization_window :]
            enough_time = (
                self.episodes_started - self._last_randomization_expansion
                >= config.randomization_window
            )
            if enough_time and float(np.mean(recent)) >= config.randomization_success_threshold:
                self._randomization_strength = min(
                    config.randomization_max_strength,
                    self._randomization_strength + config.randomization_expand_step,
                )
                self._last_randomization_expansion = self.episodes_started

    def _plr_probabilities(self) -> np.ndarray:
        """Outcome-based PLR proxy using frontier, return dispersion, and staleness."""

        count = len(self.layout_paths)
        uniform = np.full(count, 1.0 / count, dtype=np.float64)
        unseen = self._maze_visits == 0
        progress_frontier = 1.0 - np.abs(2.0 * self._maze_progress - 1.0)
        success_frontier = 1.0 - np.abs(2.0 * self._maze_success - 1.0)
        variance = np.maximum(
            0.0,
            self._maze_return_square - self._maze_return_mean**2,
        )
        dispersion = np.sqrt(variance)
        if float(np.max(dispersion)) > 0.0:
            dispersion /= float(np.max(dispersion))
        learning = (
            0.50 * progress_frontier
            + 0.30 * dispersion
            + 0.20 * success_frontier
        )
        learning = np.maximum(learning, 0.05)
        # Novel layouts remain highest priority, while useful outcome scores
        # from already-seen layouts take effect immediately. Previously, every
        # process had to visit all 512 layouts before PLR learned anything.
        learning[unseen] = max(1.0, float(np.max(learning)))
        prioritized = learning / learning.sum()
        ages = np.maximum(1, self.episodes_started - self._maze_last_visit)
        staleness = ages.astype(np.float64) / float(np.sum(ages))
        uniform_mix = self.task_config.plr_uniform_mix
        staleness_mix = self.task_config.plr_staleness_mix
        probabilities = (
            (1.0 - uniform_mix - staleness_mix) * prioritized
            + uniform_mix * uniform
            + staleness_mix * staleness
        )
        return probabilities / probabilities.sum()

    def sampling_probabilities(self) -> np.ndarray:
        """Return adaptive probabilities for the next maze reset."""
        count = len(self.layout_paths)
        if count == 1 or self.task_config.maze_sampling == "uniform":
            return np.full(count, 1.0 / count, dtype=np.float64)
        if self.task_config.maze_sampling == "plr":
            return self._plr_probabilities()
        difficulty = np.asarray(
            [float(item.get("difficulty_score", 0.5)) for item in self.layout_metadata],
            dtype=np.float64,
        )
        difficulty = np.clip(difficulty, 0.0, 1.0)
        curriculum_progress = min(
            1.0,
            self.episodes_started / float(self.task_config.curriculum_episodes),
        )
        # At the start, easy layouts are common but every training maze keeps a
        # nonzero probability. The distribution becomes uniform by the end.
        weights = 0.10 + np.exp(-4.0 * (1.0 - curriculum_progress) * difficulty)
        return weights / np.sum(weights)

    def _load_layout(self, path: Path) -> Dict[str, Any]:
        if path not in self._layout_cache:
            layout = load_json_layout(path)
            validation = validate_route(layout, layout["waypoints"], self.planner_config)
            planner_metadata = layout.get("route_planner", {})
            metadata_matches = math.isclose(
                float(planner_metadata.get("safety_margin_m", -1.0)),
                self.planner_config.safety_margin_m,
            )
            if not validation.passed or not metadata_matches:
                layout, validation = apply_safe_route(layout, self.planner_config)
            if not validation.passed:
                raise RuntimeError(f"Unsafe route in {path}: {validation}")
            self._layout_cache[path] = layout
        return self._layout_cache[path]

    def _select_start(self) -> Tuple[np.ndarray, np.ndarray]:
        if not self.task_config.random_start:
            self.start_progress_fraction = 0.0
            return self.route.point_at(0.0), np.zeros(2, dtype=np.float64)
        minimum = self.task_config.start_progress_min
        maximum = self.task_config.start_progress_max
        if self.task_config.start_curriculum:
            minimum = max(minimum, self._start_frontier)
            if self.rng.random() < self.task_config.full_start_probability:
                minimum = 0.0
                maximum = 0.0
        fraction = float(
            self.rng.uniform(
                minimum,
                maximum,
            )
        )
        self.start_progress_fraction = fraction
        progress = fraction * self.route.total_length
        center = self.route.point_at(progress)
        epsilon = min(0.003, 0.25 * self.system_config.relative_goal_spacing_m)
        before = self.route.point_at(max(0.0, progress - epsilon))
        after = self.route.point_at(min(self.route.total_length, progress + epsilon))
        tangent = after - before
        tangent /= max(np.linalg.norm(tangent), 1e-9)
        normal = np.array((-tangent[1], tangent[0]), dtype=np.float64)
        position = center.copy()
        for _ in range(20):
            offset = float(
                self.rng.uniform(
                    -self.task_config.start_lateral_range_m,
                    self.task_config.start_lateral_range_m,
                )
            )
            candidate = center + offset * normal
            if float(signed_ball_clearance(self.layout, candidate[None])[0]) >= 0.0:
                position = candidate
                break
        velocity = self.rng.uniform(
            -self.task_config.start_velocity_range_mps,
            self.task_config.start_velocity_range_mps,
            size=2,
        )
        return position, velocity

    def reset(
        self,
        seed: int | None = None,
        options: Mapping[str, Any] | None = None,
    ) -> Tuple[Dict[str, np.ndarray], Dict[str, Any]]:
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        self._record_completed_episode()
        options = dict(options or {})
        if "layout_index" in options:
            layout_index = int(options["layout_index"])
            if not 0 <= layout_index < len(self.layout_paths):
                raise IndexError(f"layout_index {layout_index} is out of range")
            sampling_probability = 1.0
        else:
            probabilities = self.sampling_probabilities()
            layout_index = int(self.rng.choice(len(self.layout_paths), p=probabilities))
            sampling_probability = float(probabilities[layout_index])
        self.layout_index = layout_index
        self.layout_sampling_probability = sampling_probability
        self.episodes_started += 1
        self.layout_path = self.layout_paths[layout_index]
        self.layout = self._load_layout(self.layout_path)
        self.policy_contract = TagPolicyContract(
            board_width_m=float(self.layout["board_width"]),
            board_height_m=float(self.layout["board_height"]),
            angle_scale_rad=self.system_config.actuator.board_angle_limit_rad,
            relative_goal_points=self.system_config.relative_goal_points,
            relative_goal_spacing_m=self.system_config.relative_goal_spacing_m,
            bridge_command_limit=self.system_config.actuator.policy_command_limit,
            policy_command_sign=self.system_config.actuator.policy_command_sign,
            servo_home=self.system_config.actuator.home_positions,
            servo_command_scale=self.system_config.actuator.command_scale,
            servo_limits=self.system_config.actuator.servo_limits,
        )
        self.model = TagSystemModel(self.layout, self.system_config)
        self.route = self.model.route
        ball_xy, velocity = self._select_start()
        model_seed = int(self.rng.integers(0, 2**31 - 1))
        raw = self.model.reset(
            seed=model_seed,
            randomize=self.task_config.randomize_plant,
            randomization_strength=(
                self._randomization_strength
                if self.task_config.randomization_curriculum
                else float(self.task_config.randomize_plant)
            ),
            randomization_groups=self.task_config.randomization_groups,
            ball_xy=ball_xy,
            ball_velocity_xy=velocity,
        )
        self.active_randomization_strength = (
            self._randomization_strength
            if self.task_config.randomization_curriculum
            else float(self.task_config.randomize_plant)
        )
        self._dr_metrics = self._domain_randomization_metrics()
        self.progress_m = self.route.closest_progress(ball_xy)
        clearance = float(signed_ball_clearance(self.layout, ball_xy[None])[0])
        self.minimum_clearance_m = clearance
        self.episode_return = 0.0
        self.episode_steps = 0
        # No predecessor exists for the first commanded tilt of an episode.
        self._previous_action = None
        observation, diagnostic = self._observation(raw, clearance)
        observation["log_fall_cost"] = np.zeros(1, dtype=np.float32)
        observation["log_success"] = np.zeros(1, dtype=np.float32)
        observation["log_reward"] = np.zeros(1, dtype=np.float32)
        observation["log_action_rate"] = np.zeros(1, dtype=np.float32)
        observation["log_hole_cost"] = np.zeros(1, dtype=np.float32)
        observation["log_start_progress"] = np.asarray(
            [self.start_progress_fraction], dtype=np.float32
        )
        observation["log_randomization_strength"] = np.asarray(
            [self.active_randomization_strength], dtype=np.float32
        )
        observation.update(self._dr_log_observation())
        info = {
            **diagnostic,
            "layout_path": str(self.layout_path),
            "layout_seed": self.layout.get("seed"),
            "route_length_m": self.route.total_length,
            "route_completion": self.progress_m / max(self.route.total_length, 1e-6),
            "maze_split": self.maze_split,
            "maze_difficulty": float(
                self.layout_metadata[layout_index].get("difficulty_score", math.nan)
            ),
            "layout_sampling_probability": sampling_probability,
            "start_progress_fraction": self.start_progress_fraction,
            "randomization_strength": self.active_randomization_strength,
            "randomization_groups": list(self.model.active_randomization_groups),
            "domain_randomization": dict(self._dr_metrics),
            "is_terminal": False,
            "termination_reason": "reset",
        }
        self.last_info = info
        return observation, info

    def _domain_randomization_metrics(self) -> Dict[str, float]:
        """Flatten every sampled DR scalar for episode-level attribution."""

        snapshot = self.model.parameter_snapshot()
        actuator = snapshot["actuator"]
        physics = snapshot["physics"]
        camera = snapshot["camera"]
        metrics: Dict[str, float] = {
            "dr_act_delay_s": actuator["total_delay_seconds"],
            "dr_act_response_s": actuator["response_time_constant_seconds"],
            # dr_act_units_* was removed on 2026-07-29. servo_units_per_rad was
            # never read by the forward dynamics, so those two scalars ranked
            # pure noise in every attribution report produced before that date.
            # The effective command gains are already logged as dr_act_pos_* and
            # dr_act_neg_*.
            "dr_act_offset_0": actuator["zero_angle_offset_rad"][0],
            "dr_act_offset_1": actuator["zero_angle_offset_rad"][1],
            "dr_act_coupling_01": actuator["cross_axis_coupling"][0][1],
            "dr_act_coupling_10": actuator["cross_axis_coupling"][1][0],
            "dr_act_pos_00": actuator["board_rad_per_command_positive"][0][0],
            "dr_act_pos_01": actuator["board_rad_per_command_positive"][0][1],
            "dr_act_pos_10": actuator["board_rad_per_command_positive"][1][0],
            "dr_act_pos_11": actuator["board_rad_per_command_positive"][1][1],
            "dr_act_neg_00": actuator["board_rad_per_command_negative"][0][0],
            "dr_act_neg_01": actuator["board_rad_per_command_negative"][0][1],
            "dr_act_neg_10": actuator["board_rad_per_command_negative"][1][0],
            "dr_act_neg_11": actuator["board_rad_per_command_negative"][1][1],
            "dr_act_stiction_pos_0": actuator["stiction_command_positive"][0],
            "dr_act_stiction_pos_1": actuator["stiction_command_positive"][1],
            "dr_act_stiction_neg_0": actuator["stiction_command_negative"][0],
            "dr_act_stiction_neg_1": actuator["stiction_command_negative"][1],
            "dr_phys_mass": physics["ball_mass_kg"],
            "dr_phys_floor_slide": physics["floor_friction"][0],
            "dr_phys_wall_slide": physics["wall_friction"][0],
            "dr_phys_ball_slide": physics["ball_friction"][0],
            "dr_phys_torsional": physics["floor_friction"][1],
            "dr_phys_rolling": physics["floor_friction"][2],
            "dr_phys_damping": physics["linear_ball_damping_per_second"],
            "dr_phys_restitution": physics["wall_restitution"],
            "dr_phys_kp": physics["actuator_kp"],
            "dr_phys_kv": physics["actuator_kv"],
            "dr_cam_brightness": camera["sampled_brightness"],
            "dr_cam_contrast": camera["sampled_contrast"],
            "dr_cam_blur": camera["sampled_blur_radius"],
            "dr_cam_noise": camera["sampled_pixel_noise_std"],
            "dr_cam_crop_x": camera["sampled_crop_shift_m"][0],
            "dr_cam_crop_y": camera["sampled_crop_shift_m"][1],
            "dr_cam_dropout": camera["effective_dropout_probability"],
            "dr_cam_burst": camera[
                "effective_dropout_burst_start_probability"
            ],
        }
        return {key: float(value) for key, value in metrics.items()}

    def _dr_log_observation(self) -> Dict[str, np.ndarray]:
        return {
            f"log_{key}": np.asarray([value], dtype=np.float32)
            for key, value in self._dr_metrics.items()
        }

    def _project_measured_position(
        self, measured_xy: np.ndarray
    ) -> Tuple[float, np.ndarray, float]:
        return self.route.project(
            measured_xy,
            progress_hint=self.progress_m,
            backward_window=self.task_config.progress_backward_window_m,
            forward_window=self.task_config.progress_forward_window_m,
        )

    def _observation(
        self, raw: Dict[str, np.ndarray], true_clearance: float
    ) -> Tuple[Dict[str, np.ndarray], Dict[str, Any]]:
        visible = bool(raw["ball_visible"][0])
        state = np.zeros(4, dtype=np.float32)
        goals = np.zeros(self.system_config.relative_goal_points * 2, dtype=np.float32)
        cross_track = math.nan
        if visible:
            measured = raw["states"].astype(np.float64)
            measured_xy = measured[2:4]
            projected_progress, _, cross_track = self._project_measured_position(measured_xy)
            self.progress_m = projected_progress
            state = self.policy_contract.normalize_states(measured[:2], measured_xy)
            targets = [
                self.route.point_at(
                    self.progress_m
                    + self.system_config.relative_goal_spacing_m * (index + 1)
                )
                - measured_xy
                for index in range(self.system_config.relative_goal_points)
            ]
            goals = self.policy_contract.normalize_relative_goal(
                np.asarray(targets, dtype=np.float32)
            )
        warning = max(self.task_config.clearance_warning_m, 1e-6)
        clearance_cost = float(np.clip((warning - true_clearance) / warning, 0.0, 1.0))
        observation = {
            "image": raw["image"].astype(np.uint8, copy=False),
            "states": state,
            "goal": goals,
            "log_progress": np.asarray(
                [self.progress_m / max(self.route.total_length, 1e-6)],
                dtype=np.float32,
            ),
            "log_cross_track_error": np.asarray(
                [0.0 if not math.isfinite(cross_track) else cross_track],
                dtype=np.float32,
            ),
            "log_clearance_cost": np.asarray([clearance_cost], dtype=np.float32),
            "log_min_clearance": np.asarray(
                [self.minimum_clearance_m], dtype=np.float32
            ),
            "log_maze_difficulty": np.asarray(
                [float(self.layout_metadata[self.layout_index].get("difficulty_score", 0.0))],
                dtype=np.float32,
            ),
            "log_start_progress": np.asarray(
                [self.start_progress_fraction], dtype=np.float32
            ),
            "log_randomization_strength": np.asarray(
                [self.active_randomization_strength], dtype=np.float32
            ),
        }
        observation.update(self._dr_log_observation())
        self.policy_contract.validate_observation(observation)
        return observation, {
            "route_progress_m": self.progress_m,
            "cross_track_error_m": cross_track,
            "clearance_m": true_clearance,
            "clearance_cost": clearance_cost,
            "ball_visible": visible,
        }

    def step(
        self, action: Iterable[float]
    ) -> Tuple[Dict[str, np.ndarray], float, bool, bool, Dict[str, Any]]:
        previous_progress = self.progress_m
        # Materialize before stepping the model, which may consume an iterator.
        action_array = np.asarray(list(action), dtype=np.float64)
        result = self.model.step(action_array)
        true_xy = np.asarray(result.info["true_ball_position"][:2], dtype=np.float64)
        true_clearance = float(signed_ball_clearance(self.layout, true_xy[None])[0])
        self.minimum_clearance_m = min(self.minimum_clearance_m, true_clearance)
        observation, diagnostic = self._observation(result.observation, true_clearance)
        progress_fraction = (self.progress_m - previous_progress) / max(
            self.route.total_length, 1e-6
        )
        failed = result.reason in {"ball_fell", "ball_left_board"}
        succeeded = result.reason == "goal_reached"
        route_completion = self.progress_m / max(self.route.total_length, 1e-6)
        progress_reward, success_reward, failure_reward = reward_components(
            self.task_config,
            progress_fraction,
            route_completion,
            result.reason,
        )
        rate_cost = action_rate_cost(action_array, self._previous_action)
        rate_reward = -self.task_config.action_rate_penalty * rate_cost
        self._previous_action = action_array
        # Charged on the true position, like every other hazard measurement, so
        # detector noise cannot invent or hide a near miss.
        hole_clearance = float(signed_hole_clearance(self.layout, true_xy[None])[0])
        hole_cost = hole_proximity_cost(self.task_config, hole_clearance)
        hole_reward = -self.task_config.hole_clearance_penalty * hole_cost
        wall_clearance = float(signed_wall_clearance(self.layout, true_xy[None])[0])
        wall_cost = wall_riding_cost(self.task_config, wall_clearance)
        wall_reward = -self.task_config.wall_riding_penalty * wall_cost
        path_cost = path_tracking_cost(
            self.task_config,
            float(diagnostic["cross_track_error_m"]),
        )
        path_reward = -self.task_config.path_tracking_penalty * path_cost
        reward = (
            progress_reward
            + success_reward
            + failure_reward
            + rate_reward
            + hole_reward
            + wall_reward
            + path_reward
        )
        fall_cost = float(failed)
        self.episode_return += float(reward)
        self.episode_steps += 1
        observation["log_fall_cost"] = np.asarray([fall_cost], dtype=np.float32)
        observation["log_success"] = np.asarray([float(succeeded)], dtype=np.float32)
        observation["log_reward"] = np.asarray([reward], dtype=np.float32)
        observation["log_action_rate"] = np.asarray([rate_cost], dtype=np.float32)
        observation["log_hole_cost"] = np.asarray([hole_cost], dtype=np.float32)
        observation["log_path_cost"] = np.asarray([path_cost], dtype=np.float32)
        observation["log_wall_cost"] = np.asarray([wall_cost], dtype=np.float32)
        info = {
            **result.info,
            **diagnostic,
            "hole_clearance_m": hole_clearance,
            "wall_clearance_m": wall_clearance,
            "layout_path": str(self.layout_path),
            "layout_seed": self.layout.get("seed"),
            "route_length_m": self.route.total_length,
            "route_completion": route_completion,
            "maze_split": self.maze_split,
            "maze_difficulty": float(
                self.layout_metadata[self.layout_index].get("difficulty_score", math.nan)
            ),
            "layout_sampling_probability": self.layout_sampling_probability,
            "start_progress_fraction": self.start_progress_fraction,
            "randomization_strength": self.active_randomization_strength,
            "fall_cost": fall_cost,
            "success": bool(succeeded),
            "progress_reward": float(progress_reward),
            "success_reward": float(success_reward),
            "failure_reward": float(failure_reward),
            "hole_reward": float(hole_reward),
            "wall_reward": float(wall_reward),
            "path_reward": float(path_reward),
            "episode_return": self.episode_return,
            "episode_steps": self.episode_steps,
            "is_terminal": bool(result.terminated),
            "termination_reason": result.reason,
        }
        self.last_info = info
        return observation, float(reward), result.terminated, result.truncated, info

    def render(self) -> np.ndarray:
        return self.model.sim.render()

    def close(self) -> None:
        pass


class TagMazeEnv(gym.Env):  # type: ignore[misc]
    """Gym/Gymnasium compatibility wrapper around :class:`TagMazeTask`."""

    metadata = {"render_modes": ["rgb_array"]}

    def __init__(self, **kwargs: Any):
        super().__init__()
        task_fields = set(TaskConfig.__dataclass_fields__)
        task_kwargs = {key: kwargs.pop(key) for key in list(kwargs) if key in task_fields}
        self.task = TagMazeTask(task_config=TaskConfig(**task_kwargs), **kwargs)
        points = self.task.system_config.relative_goal_points
        self.observation_space = gym.spaces.Dict(
            {
                "image": gym.spaces.Box(0, 255, (64, 64, 1), dtype=np.uint8),
                "states": gym.spaces.Box(-np.inf, np.inf, (4,), dtype=np.float32),
                "goal": gym.spaces.Box(-np.inf, np.inf, (points * 2,), dtype=np.float32),
                "log_progress": gym.spaces.Box(-np.inf, np.inf, (1,), dtype=np.float32),
                "log_cross_track_error": gym.spaces.Box(
                    -np.inf, np.inf, (1,), dtype=np.float32
                ),
                "log_clearance_cost": gym.spaces.Box(
                    -np.inf, np.inf, (1,), dtype=np.float32
                ),
                "log_min_clearance": gym.spaces.Box(
                    -np.inf, np.inf, (1,), dtype=np.float32
                ),
                "log_maze_difficulty": gym.spaces.Box(
                    -np.inf, np.inf, (1,), dtype=np.float32
                ),
                "log_start_progress": gym.spaces.Box(
                    -np.inf, np.inf, (1,), dtype=np.float32
                ),
                "log_randomization_strength": gym.spaces.Box(
                    -np.inf, np.inf, (1,), dtype=np.float32
                ),
                "log_fall_cost": gym.spaces.Box(
                    -np.inf, np.inf, (1,), dtype=np.float32
                ),
                "log_success": gym.spaces.Box(-np.inf, np.inf, (1,), dtype=np.float32),
                "log_reward": gym.spaces.Box(-np.inf, np.inf, (1,), dtype=np.float32),
                "log_action_rate": gym.spaces.Box(
                    -np.inf, np.inf, (1,), dtype=np.float32
                ),
                "log_hole_cost": gym.spaces.Box(
                    -np.inf, np.inf, (1,), dtype=np.float32
                ),
                "log_path_cost": gym.spaces.Box(
                    -np.inf, np.inf, (1,), dtype=np.float32
                ),
                "log_wall_cost": gym.spaces.Box(
                    -np.inf, np.inf, (1,), dtype=np.float32
                ),
                **{
                    f"log_{key}": gym.spaces.Box(
                        -np.inf, np.inf, (1,), dtype=np.float32
                    )
                    for key in DR_METRIC_KEYS
                },
            }
        )
        self.action_space = gym.spaces.Box(-1.0, 1.0, (2,), dtype=np.float32)

    def reset(self, *, seed: int | None = None, options: Mapping[str, Any] | None = None):
        observation, info = self.task.reset(seed=seed, options=options)
        # Metrics only exist after the first action but spaces must be stable.
        observation.setdefault("log_fall_cost", np.zeros(1, dtype=np.float32))
        observation.setdefault("log_success", np.zeros(1, dtype=np.float32))
        observation.setdefault("log_reward", np.zeros(1, dtype=np.float32))
        observation.setdefault("log_action_rate", np.zeros(1, dtype=np.float32))
        observation.setdefault("log_hole_cost", np.zeros(1, dtype=np.float32))
        observation.setdefault("log_path_cost", np.zeros(1, dtype=np.float32))
        observation.setdefault("log_wall_cost", np.zeros(1, dtype=np.float32))
        if _GYMNASIUM_API:
            return observation, info
        return observation

    def step(self, action: np.ndarray):
        observation, reward, terminated, truncated, info = self.task.step(action)
        if _GYMNASIUM_API:
            return observation, reward, terminated, truncated, info
        return observation, reward, bool(terminated or truncated), info

    def render(self, mode: str = "rgb_array") -> np.ndarray:
        if mode != "rgb_array":
            raise ValueError(f"Unsupported render mode {mode!r}")
        return self.task.render()

    def close(self) -> None:
        self.task.close()
