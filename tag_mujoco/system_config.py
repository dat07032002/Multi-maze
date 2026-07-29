"""Nominal TAG system parameters and simulation uncertainty ranges."""

from __future__ import annotations

import math
import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np


HERE = Path(__file__).resolve().parent
ASSUMED_DYNAMICS_PATH = HERE / "assumed_dynamics.json"
IDENTIFIED_DYNAMICS_PATH = HERE / "identified_dynamics.json"


def _load_active_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    result = json.loads(path.read_text(encoding="utf-8"))
    return result if result.get("active", False) else {}


ASSUMED_DYNAMICS = _load_active_json(ASSUMED_DYNAMICS_PATH)
IDENTIFIED_DYNAMICS = _load_active_json(IDENTIFIED_DYNAMICS_PATH)
_assumed_parameters = ASSUMED_DYNAMICS.get("parameters", {})
_ball_radius_m = float(ASSUMED_DYNAMICS.get("ball_radius_m", 0.006))


def _parameter(name: str, default: float) -> Dict[str, Any]:
    identified = IDENTIFIED_DYNAMICS.get(name, {})
    if identified.get("value") is not None and identified.get("applied", True):
        return identified
    return _assumed_parameters.get(name, {"value": default, "range": [default, default]})


def _value(name: str, default: float) -> float:
    return float(_parameter(name, default)["value"])


def _range(name: str, default: Tuple[float, float]) -> Tuple[float, float]:
    values = _parameter(name, default[0]).get("range", default)
    if values is None:
        return default
    low, high = (float(value) for value in values)
    if low < 0.0 or high < low:
        raise ValueError(f"Invalid dynamics range for {name}: {values}")
    return low, high


_floor_sliding = _value("floor_sliding_friction", 0.38)
_wall_sliding = _value("wall_sliding_friction", 0.40)
_ball_sliding = _value("ball_sliding_friction", 0.25)
_torsional_length = _value("torsional_friction_length_m", 0.00025)
_rolling_length = _value("rolling_friction_length_m", 0.000024)
if "rolling_friction_length_m" not in IDENTIFIED_DYNAMICS:
    legacy_rolling = IDENTIFIED_DYNAMICS.get("rolling_friction_coefficient", {})
    if legacy_rolling.get("value") is not None:
        # Older fits stored a dimensionless rolling-resistance coefficient.
        _rolling_length = float(legacy_rolling["value"]) * _ball_radius_m
_linear_damping = _value("linear_ball_damping_per_second", 0.22)
_wall_restitution = _value("wall_restitution", 0.35)

_FLOOR_SLIDING_RANGE = _range("floor_sliding_friction", (0.15, 0.70))
_WALL_SLIDING_RANGE = _range("wall_sliding_friction", (0.15, 0.75))
_BALL_SLIDING_RANGE = _range("ball_sliding_friction", (0.10, 0.60))
_TORSIONAL_LENGTH_RANGE = _range(
    "torsional_friction_length_m", (0.00003, 0.0015)
)
_ROLLING_LENGTH_RANGE = _range("rolling_friction_length_m", (0.000003, 0.00018))
_LINEAR_DAMPING_RANGE = _range("linear_ball_damping_per_second", (0.0, 0.8))
_WALL_RESTITUTION_RANGE = _range("wall_restitution", (0.05, 0.70))
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
    """Active Hiwonder behavior plus the measured local linkage response."""

    home_positions: Tuple[float, float] = (500.0, 500.0)
    servo_limits: Tuple[Tuple[float, float], Tuple[float, float]] = (
        (100.0, 900.0),
        (100.0, 900.0),
    )
    command_scale: Tuple[float, float] = (1.5, 1.5)
    # The deployed path is two separate stages and the simulator must reproduce
    # both. The learner scales a normalized action by 240; the bridge executable
    # then clamps the result to 180. Collapsing them into a single 180 scale --
    # which this config did until 2026-07-29 -- makes the simulator 25% weaker
    # for every |action| < 0.75 and removes the real saturation plateau above
    # it. `tests/test_policy_contract.py` now asserts equality against
    # `TagPolicyContract.action_to_hiwonder_command`.
    policy_command_scale: Tuple[float, float] = (240.0, 240.0)
    policy_command_limit: Tuple[float, float] = (180.0, 180.0)
    policy_command_sign: Tuple[float, float] = (-1.0, -1.0)
    update_rate_hz: float = 30.0
    max_step_per_tick: Tuple[float, float] = (20.0, 20.0)
    deadband_units: float = 1.0
    command_timeout_seconds: float = 1.0
    timeout_go_home: bool = True
    reset_prehome_positions: Tuple[float, float] = (700.0, 700.0)
    reset_prehome_move_seconds: float = 0.060
    reset_prehome_wait_seconds: float = 0.5
    reset_home_move_seconds: float = 0.600
    # Source-timestamped +/-80 step runs on 2026-07-27 reached 90% of the
    # dominant camera-observed response in about 0.23 s end to end.
    #
    # That number is NOT pure servo dynamics and must not be added on top of the
    # driver model. Command 80 is 120 servo units, and `max_step_per_tick` walks
    # 20 units per 30 Hz tick, so the modeled rate limiter alone already spends
    # 6 ticks -- 0.20 s -- reaching the target. The superseded values below
    # (33 ms pure delay, 86 ms time constant) re-fitted that same rate limit as
    # if it were servo lag and applied it a second time, making the simulated
    # board roughly 1.6x more sluggish than the measured one.
    #
    # These two values are now the *residual* after the tick quantization,
    # `max_step_per_tick` slew, and `CameraConfig.observation_delay_steps` are
    # accounted for. They are fitted offline by `fit_actuator_response.py`
    # against `docs/sysid_actuator_step80_2026-07-27.json` and regression-tested
    # by `tests/test_actuator_response_timing.py`. Do not hand-edit them without
    # re-running that tool.
    # Fitted 2026-07-29: the residual is indistinguishable from zero. Against the
    # two trustworthy step conditions (median measured t90 202 ms) the driver
    # model alone predicts 211 ms, while the superseded 33/86 ms pair predicted
    # 388 ms -- a 186 ms median overshoot on a 202 ms measurement. The 30 ms move
    # command per 33.3 ms tick means the servo does substantially reach each
    # rate-limited intermediate target within its own tick, so there is no room
    # left for a first-order lag on top. The 1 ms value keeps the filter
    # numerically defined rather than asserting a measured time constant.
    total_delay_seconds: float = 0.0
    response_time_constant_seconds: float = 0.001
    board_angle_limit_rad: float = math.radians(10.0)
    zero_angle_offset_rad: Tuple[float, float] = (0.0, 0.0)
    cross_axis_coupling: Tuple[Tuple[float, float], Tuple[float, float]] = (
        (1.0, 0.0),
        (0.0, 1.0),
    )
    # Rows are measured board [alpha, beta], columns are Hiwonder commands
    # [motor 1, motor 2].  Separate matrices retain the large direction
    # asymmetry and cross-axis coupling observed in the repeated unloaded step
    # runs.  These are local slopes near |command|=80, where both directions
    # cleared the observed preload/backlash region.
    board_rad_per_command_positive: Tuple[Tuple[float, float], Tuple[float, float]] = (
        (0.00007950, -0.00009535),
        (-0.00015514, -0.00004540),
    )
    board_rad_per_command_negative: Tuple[Tuple[float, float], Tuple[float, float]] = (
        (-0.00005969, -0.00009117),
        (-0.00005908, -0.00006818),
    )
    # Positive axis 2 and negative axis 1 did not produce an unambiguous
    # directional response until |command|=80.  Thresholds remain conservative
    # priors because the mechanism has preload and path-dependent hysteresis.
    stiction_command_positive: Tuple[float, float] = (10.0, 40.0)
    stiction_command_negative: Tuple[float, float] = (40.0, 10.0)

    def randomized(
        self, rng: np.random.Generator, strength: float = 1.0
    ) -> "ActuatorConfig":
        """Sample actuator uncertainty, scaled from nominal to the full prior."""

        strength = float(np.clip(strength, 0.0, 1.0))

        def blend(sample: np.ndarray | float, nominal: np.ndarray | float):
            return np.asarray(nominal) + strength * (
                np.asarray(sample) - np.asarray(nominal)
            )

        cross = strength * rng.uniform(-0.08, 0.08, size=2)
        positive_map = np.asarray(self.board_rad_per_command_positive) * blend(
            rng.uniform(0.65, 1.35, size=(1, 2)), np.ones((1, 2))
        )
        negative_map = np.asarray(self.board_rad_per_command_negative) * blend(
            rng.uniform(0.65, 1.35, size=(1, 2)), np.ones((1, 2))
        )
        return replace(
            self,
            # Both ranges are residuals on top of the modeled tick quantization,
            # slew limit, and observation delay. The delay upper bound is one
            # driver tick of un-modeled command-path transport; the response
            # range keeps the same relative spread the superseded 0.086 nominal
            # had, re-centered on the refitted residual.
            total_delay_seconds=float(
                blend(rng.uniform(0.0, 0.033), self.total_delay_seconds)
            ),
            response_time_constant_seconds=float(
                blend(
                    rng.uniform(0.0, 0.040),
                    self.response_time_constant_seconds,
                )
            ),
            zero_angle_offset_rad=tuple(
                strength
                * rng.uniform(-math.radians(0.8), math.radians(0.8), size=2)
            ),  # type: ignore[arg-type]
            cross_axis_coupling=((1.0, float(cross[0])), (float(cross[1]), 1.0)),
            board_rad_per_command_positive=tuple(
                tuple(float(value) for value in row) for row in positive_map
            ),  # type: ignore[arg-type]
            board_rad_per_command_negative=tuple(
                tuple(float(value) for value in row) for row in negative_map
            ),  # type: ignore[arg-type]
            stiction_command_positive=tuple(
                float(value)
                for value in blend(
                    rng.uniform((5.0, 27.0), (18.0, 55.0)),
                    self.stiction_command_positive,
                )
            ),  # type: ignore[arg-type]
            stiction_command_negative=tuple(
                float(value)
                for value in blend(
                    rng.uniform((5.0, 5.0), (18.0, 22.0)),
                    self.stiction_command_negative,
                )
            ),  # type: ignore[arg-type]
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
    floor_friction: Tuple[float, float, float] = (
        _floor_sliding,
        _torsional_length,
        _rolling_length,
    )
    wall_friction: Tuple[float, float, float] = (
        _wall_sliding,
        _torsional_length,
        _rolling_length,
    )
    ball_friction: Tuple[float, float, float] = (
        _ball_sliding,
        _torsional_length,
        _rolling_length,
    )
    linear_ball_damping_per_second: float = _linear_damping
    wall_restitution: float = _wall_restitution
    actuator_kp: float = 90.0
    actuator_kv: float = 8.0

    def randomized(
        self, rng: np.random.Generator, strength: float = 1.0
    ) -> "PhysicsConfig":
        """Sample dynamics uncertainty, scaled from nominal to the full prior."""

        strength = float(np.clip(strength, 0.0, 1.0))

        def factor(low: float, high: float) -> float:
            return 1.0 + strength * (float(rng.uniform(low, high)) - 1.0)

        def sample(
            nominal: float,
            bounds: Tuple[float, float],
            *,
            logarithmic: bool = False,
        ) -> float:
            low, high = bounds
            if logarithmic:
                drawn = float(np.exp(rng.uniform(np.log(low), np.log(high))))
            else:
                drawn = float(rng.uniform(low, high))
            return nominal + strength * (drawn - nominal)

        torsional = sample(
            self.floor_friction[1],
            _TORSIONAL_LENGTH_RANGE,
            logarithmic=True,
        )
        rolling = sample(
            self.floor_friction[2],
            _ROLLING_LENGTH_RANGE,
            logarithmic=True,
        )
        return replace(
            self,
            ball_mass_kg=float(self.ball_mass_kg * factor(0.92, 1.08)),
            floor_friction=(
                sample(self.floor_friction[0], _FLOOR_SLIDING_RANGE),
                torsional,
                rolling,
            ),
            wall_friction=(
                sample(self.wall_friction[0], _WALL_SLIDING_RANGE),
                torsional,
                rolling,
            ),
            ball_friction=(
                sample(self.ball_friction[0], _BALL_SLIDING_RANGE),
                torsional,
                rolling,
            ),
            linear_ball_damping_per_second=sample(
                self.linear_ball_damping_per_second,
                _LINEAR_DAMPING_RANGE,
            ),
            wall_restitution=sample(
                self.wall_restitution,
                _WALL_RESTITUTION_RANGE,
            ),
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
