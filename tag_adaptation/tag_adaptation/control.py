"""Pure action composition and safety logic without hardware I/O."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Iterable


def _pair(values: Iterable[float], name: str) -> tuple[float, float]:
    result = tuple(float(value) for value in values)
    if len(result) != 2 or not all(math.isfinite(value) for value in result):
        raise ValueError(f"{name} must contain two finite values")
    return result  # type: ignore[return-value]


def _clip(value: float, limit: float) -> float:
    return min(max(value, -limit), limit)


@dataclass(frozen=True)
class SafetyState:
    """Safety-relevant state supplied by the future hardware runtime."""

    ball_visible: bool
    state_age_seconds: float
    board_angles_rad: tuple[float, float]
    hole_clearance_m: float | None = None
    predicted_fall_probability: float = 0.0
    weakness_score: float = 0.0

    def __post_init__(self) -> None:
        """Validate finite, physically meaningful safety inputs."""
        _pair(self.board_angles_rad, "board_angles_rad")
        if not math.isfinite(self.state_age_seconds):
            raise ValueError("state_age_seconds must be finite")
        if self.hole_clearance_m is not None and not math.isfinite(
            self.hole_clearance_m
        ):
            raise ValueError("hole_clearance_m must be finite when provided")
        for name, value in (
            ("predicted_fall_probability", self.predicted_fall_probability),
            ("weakness_score", self.weakness_score),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in [0, 1]")


@dataclass(frozen=True)
class AdaptationConfig:
    """Conservative action-composition and safety limits."""

    # Shadow mode computes and records the helper but never executes it.
    mode: str = "shadow"
    execution_enabled: bool = False
    maximum_residual_action: float = 0.15
    maximum_residual_scale: float = 1.0
    maximum_action: float = 1.0
    maximum_action_rate: float = 0.25
    maximum_state_age_seconds: float = 0.10
    maximum_board_angle_rad: float = math.radians(10.0)
    warning_hole_clearance_m: float = 0.008
    stop_hole_clearance_m: float = 0.001
    warning_fall_probability: float = 0.50
    stop_fall_probability: float = 0.80

    def __post_init__(self) -> None:
        """Validate configuration limits and threshold ordering."""
        if self.mode not in {"disabled", "shadow", "bounded"}:
            raise ValueError("mode must be disabled, shadow, or bounded")
        for name in (
            "maximum_residual_action",
            "maximum_residual_scale",
            "maximum_action",
            "maximum_action_rate",
            "maximum_state_age_seconds",
            "maximum_board_angle_rad",
            "warning_hole_clearance_m",
            "stop_hole_clearance_m",
        ):
            if float(getattr(self, name)) < 0.0:
                raise ValueError(f"{name} must be non-negative")
        if self.stop_hole_clearance_m > self.warning_hole_clearance_m:
            raise ValueError("stop clearance cannot exceed warning clearance")
        if self.warning_fall_probability > self.stop_fall_probability:
            raise ValueError("warning fall probability cannot exceed stop")


@dataclass(frozen=True)
class ControlDecision:
    """Auditable result of one main-plus-helper composition decision."""

    base_action: tuple[float, float]
    helper_action: tuple[float, float]
    proposed_residual: tuple[float, float]
    proposed_combined_action: tuple[float, float]
    executed_action: tuple[float, float]
    residual_scale: float
    residual_executed: bool
    intervention: bool
    stopped: bool
    reasons: tuple[str, ...] = field(default_factory=tuple)


class AdaptationController:
    """Compose a frozen main action with a bounded optional correction.

    Calling this class cannot command hardware. In bounded mode, the caller
    must also pass ``execution_approved=True`` for every decision.
    """

    def __init__(self, config: AdaptationConfig = AdaptationConfig()):
        """Create an episode-stateful controller from immutable limits."""
        self.config = config
        self._previous_executed: tuple[float, float] | None = None

    def reset(self) -> None:
        """Clear the previous action at an episode boundary."""
        self._previous_executed = None

    def decide(
        self,
        base_action: Iterable[float],
        helper_action: Iterable[float],
        state: SafetyState,
        *,
        execution_approved: bool = False,
    ) -> ControlDecision:
        """Return the permitted action and every intervention reason."""
        base = _pair(base_action, "base_action")
        helper = _pair(helper_action, "helper_action")
        config = self.config
        if config.mode == "bounded" and not (
            config.execution_enabled and execution_approved
        ):
            raise PermissionError(
                "bounded residual execution requires configuration and "
                "per-call approval"
            )

        scale = min(state.weakness_score, config.maximum_residual_scale)
        reasons: list[str] = []
        if state.predicted_fall_probability >= config.warning_fall_probability:
            scale = 0.0
            reasons.append("fall_risk_disabled_residual")
        residual = tuple(
            _clip(scale * value, config.maximum_residual_action)
            for value in helper
        )
        combined = tuple(base[index] + residual[index] for index in range(2))
        candidate = combined if config.mode == "bounded" else base
        residual_executed = config.mode == "bounded" and any(
            abs(value) > 0.0 for value in residual
        )

        stopped = False
        if not state.ball_visible:
            stopped = True
            reasons.append("ball_not_visible")
        if state.state_age_seconds > config.maximum_state_age_seconds:
            stopped = True
            reasons.append("stale_state")
        if any(
            abs(value) > config.maximum_board_angle_rad
            for value in state.board_angles_rad
        ):
            stopped = True
            reasons.append("board_angle_limit")
        if (
            state.hole_clearance_m is not None
            and state.hole_clearance_m <= config.stop_hole_clearance_m
        ):
            stopped = True
            reasons.append("hole_clearance_stop")
        if state.predicted_fall_probability >= config.stop_fall_probability:
            stopped = True
            reasons.append("predicted_fall_stop")

        if stopped:
            executed = (0.0, 0.0)
            residual_executed = False
        else:
            action_limit = config.maximum_action
            if (
                state.hole_clearance_m is not None
                and state.hole_clearance_m < config.warning_hole_clearance_m
            ):
                action_limit *= 0.5
                reasons.append("hole_clearance_attenuation")
            bounded = tuple(_clip(value, action_limit) for value in candidate)
            if bounded != candidate:
                reasons.append("action_magnitude_limit")
            executed = bounded
            if self._previous_executed is not None:
                rate_limited = tuple(
                    self._previous_executed[index]
                    + _clip(
                        executed[index] - self._previous_executed[index],
                        config.maximum_action_rate,
                    )
                    for index in range(2)
                )
                if rate_limited != executed:
                    reasons.append("action_rate_limit")
                executed = rate_limited

        self._previous_executed = executed
        return ControlDecision(
            base_action=base,
            helper_action=helper,
            proposed_residual=residual,
            proposed_combined_action=combined,
            executed_action=executed,
            residual_scale=scale,
            residual_executed=residual_executed,
            intervention=bool(reasons),
            stopped=stopped,
            reasons=tuple(reasons),
        )
