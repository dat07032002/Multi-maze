"""Nominal CyberRunner system parameters and simulation uncertainty ranges."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np


HERE = Path(__file__).resolve().parent
DEFAULT_CAMERA_CALIBRATION = (
    HERE.parent
    / "tag_state_estimation"
    / "calib"
    / "calib_results_tag.txt"
)


@dataclass(frozen=True)
class OcamCalibration:
    """OCamCalib values used by the real state-estimation pipeline."""

    direct_polynomial: Tuple[float, ...]
    inverse_polynomial: Tuple[float, ...]
    center_row_column: Tuple[float, float]
    affine_cde: Tuple[float, float, float]
    image_height: int
    image_width: int

    @classmethod
    def load(cls, path: Path = DEFAULT_CAMERA_CALIBRATION) -> "OcamCalibration":
        numeric = [
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        if len(numeric) != 5:
            raise ValueError(f"Unexpected OCamCalib file structure: {path}")
        direct = [float(value) for value in numeric[0].split()]
        inverse = [float(value) for value in numeric[1].split()]
        center = tuple(float(value) for value in numeric[2].split())
        affine = tuple(float(value) for value in numeric[3].split())
        size = tuple(int(float(value)) for value in numeric[4].split())
        if int(direct[0]) != len(direct) - 1 or int(inverse[0]) != len(inverse) - 1:
            raise ValueError("OCamCalib coefficient count does not match its header")
        return cls(
            tuple(direct[1:]),
            tuple(inverse[1:]),
            center,  # type: ignore[arg-type]
            affine,  # type: ignore[arg-type]
            size[0],
            size[1],
        )

    def scaled_resolution(self, factor: int = 3) -> Tuple[int, int]:
        return self.image_height // factor, self.image_width // factor

    def summary(self) -> Dict[str, Any]:
        return {
            "calibrated_resolution": [self.image_width, self.image_height],
            "state_estimator_scale_factor": 3,
            "scaled_resolution": list(reversed(self.scaled_resolution(3))),
            "center_row_column": list(self.center_row_column),
            "direct_polynomial_terms": len(self.direct_polynomial),
            "inverse_polynomial_terms": len(self.inverse_polynomial),
        }


@dataclass(frozen=True)
class ActuatorConfig:
    """Active Hiwonder software behavior plus an explicit linkage prior."""

    home_positions: Tuple[float, float] = (500.0, 500.0)
    servo_limits: Tuple[Tuple[float, float], Tuple[float, float]] = (
        (100.0, 900.0),
        (100.0, 900.0),
    )
    command_scale: Tuple[float, float] = (1.5, 1.5)
    policy_command_limit: Tuple[float, float] = (180.0, 180.0)
    policy_command_sign: Tuple[float, float] = (-1.0, -1.0)
    linkage_angle_sign: Tuple[float, float] = (-1.0, -1.0)
    update_rate_hz: float = 30.0
    max_step_per_tick: Tuple[float, float] = (20.0, 20.0)
    deadband_units: float = 1.0
    move_time_seconds: float = 0.030
    command_timeout_seconds: float = 1.0
    timeout_go_home: bool = True
    reset_prehome_positions: Tuple[float, float] = (700.0, 700.0)
    reset_prehome_move_seconds: float = 0.060
    reset_prehome_wait_seconds: float = 0.5
    reset_home_move_seconds: float = 0.600
    total_delay_seconds: float = 0.045
    response_time_constant_seconds: float = 0.075
    board_angle_limit_rad: float = math.radians(10.0)
    # Inferred only: +/-270 servo units spans the +/-10 degree policy range.
    servo_units_per_rad: Tuple[float, float] = (
        270.0 / math.radians(10.0),
        270.0 / math.radians(10.0),
    )
    zero_angle_offset_rad: Tuple[float, float] = (0.0, 0.0)
    cross_axis_coupling: Tuple[Tuple[float, float], Tuple[float, float]] = (
        (1.0, 0.0),
        (0.0, 1.0),
    )

    def randomized(
        self, rng: np.random.Generator, strength: float = 1.0
    ) -> "ActuatorConfig":
        """Sample actuator uncertainty, scaled from nominal to the full prior."""

        strength = float(np.clip(strength, 0.0, 1.0))

        def blend(sample: np.ndarray | float, nominal: np.ndarray | float):
            return np.asarray(nominal) + strength * (
                np.asarray(sample) - np.asarray(nominal)
            )

        gain_factor = blend(rng.uniform(0.75, 1.25, size=2), np.ones(2))
        units_per_rad = tuple(
            value / factor for value, factor in zip(self.servo_units_per_rad, gain_factor)
        )
        cross = strength * rng.uniform(-0.08, 0.08, size=2)
        return replace(
            self,
            servo_units_per_rad=units_per_rad,  # type: ignore[arg-type]
            total_delay_seconds=float(
                blend(rng.uniform(0.020, 0.100), self.total_delay_seconds)
            ),
            response_time_constant_seconds=float(
                blend(
                    rng.uniform(0.040, 0.140),
                    self.response_time_constant_seconds,
                )
            ),
            zero_angle_offset_rad=tuple(
                strength
                * rng.uniform(-math.radians(0.8), math.radians(0.8), size=2)
            ),  # type: ignore[arg-type]
            cross_axis_coupling=((1.0, float(cross[0])), (float(cross[1]), 1.0)),
        )


@dataclass(frozen=True)
class CameraConfig:
    """The observation produced after the real calibrated camera remap."""

    calibration_path: Path = DEFAULT_CAMERA_CALIBRATION
    capture_width: int = 1280
    capture_height: int = 720
    resized_width: int = 640
    resized_height: int = 360
    vertical_border_pixels: int = 20
    nominal_capture_rate_hz: float = 60.0
    effective_capture_rate_hz: float = 45.0
    patch_extent_m: float = 0.064
    output_pixels: int = 64
    raster_pixels_per_meter: int = 4000
    observation_delay_steps: int = 1
    dropout_probability: float = 0.005
    dropout_burst_start_probability: float = 0.002
    dropout_burst_frames: Tuple[int, int] = (1, 12)
    detector_miss_threshold: int = 6
    ball_loss_grace_seconds: float = 0.35
    occlusion_grace_seconds: float = 1.50
    prediction_max_speed_mps: float = 0.15
    angle_noise_std_rad: float = math.radians(0.15)
    position_noise_std_m: float = 0.00025
    brightness_range: Tuple[float, float] = (0.80, 1.20)
    contrast_range: Tuple[float, float] = (0.80, 1.20)
    blur_radius_range: Tuple[float, float] = (0.0, 1.0)
    crop_shift_range_m: float = 0.0015
    pixel_noise_std_range: Tuple[float, float] = (0.0, 5.0)


@dataclass(frozen=True)
class PhysicsConfig:
    """Nominal MuJoCo values. These remain priors until hardware is measured."""

    ball_mass_kg: float = 0.011
    floor_friction: Tuple[float, float, float] = (0.30, 0.015, 0.002)
    wall_friction: Tuple[float, float, float] = (0.35, 0.020, 0.003)
    ball_friction: Tuple[float, float, float] = (0.22, 0.012, 0.002)
    actuator_kp: float = 90.0
    actuator_kv: float = 8.0

    def randomized(
        self, rng: np.random.Generator, strength: float = 1.0
    ) -> "PhysicsConfig":
        """Sample dynamics uncertainty, scaled from nominal to the full prior."""

        strength = float(np.clip(strength, 0.0, 1.0))

        def factor(low: float, high: float) -> float:
            return 1.0 + strength * (float(rng.uniform(low, high)) - 1.0)

        def scale(values: Tuple[float, float, float], low: float, high: float):
            multiplier = factor(low, high)
            return tuple(value * multiplier for value in values)

        return replace(
            self,
            ball_mass_kg=float(self.ball_mass_kg * factor(0.92, 1.08)),
            floor_friction=scale(self.floor_friction, 0.55, 1.55),  # type: ignore[arg-type]
            wall_friction=scale(self.wall_friction, 0.65, 1.40),  # type: ignore[arg-type]
            ball_friction=scale(self.ball_friction, 0.55, 1.55),  # type: ignore[arg-type]
            actuator_kp=float(self.actuator_kp * factor(0.75, 1.25)),
            actuator_kv=float(self.actuator_kv * factor(0.75, 1.25)),
        )


@dataclass(frozen=True)
class SystemConfig:
    actuator: ActuatorConfig = ActuatorConfig()
    camera: CameraConfig = CameraConfig()
    physics: PhysicsConfig = PhysicsConfig()
    # Policy/TCP loop is distinct from the 30 Hz Hiwonder driver. The working
    # environment warns below 35 FPS; this remains an inferred nominal rate.
    control_rate_hz: float = 35.0
    maximum_episode_steps: int = 3000
    goal_radius_m: float = 0.008
    relative_goal_points: int = 5
    relative_goal_spacing_m: float = 0.012
