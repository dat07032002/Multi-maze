"""Continuity gate for rejecting impossible plate-pose solutions."""

from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class PoseGateResult:
    """One filtered plate-pose decision."""

    angles: tuple[float, float]
    accepted: bool
    consecutive_rejections: int


class PoseContinuityGate:
    """Reject PnP pose branches that cannot be physical frame-to-frame motion."""

    def __init__(
        self,
        max_abs_deg: float = 20.0,
        max_step_deg: float = 3.0,
        hold_frames: int = 2,
    ) -> None:
        if not 0.0 < max_abs_deg <= 45.0:
            raise ValueError("max_abs_deg must be in (0, 45]")
        if not 0.0 < max_step_deg <= 10.0:
            raise ValueError("max_step_deg must be in (0, 10]")
        if not 0 <= hold_frames <= 5:
            raise ValueError("hold_frames must be in [0, 5]")
        self.max_abs_rad = math.radians(max_abs_deg)
        self.max_step_rad = math.radians(max_step_deg)
        self.hold_frames = int(hold_frames)
        self.last_valid: tuple[float, float] | None = None
        self.consecutive_rejections = 0

    def update(self, angles) -> PoseGateResult:
        """Accept a plausible pose or briefly hold the last valid pose."""

        candidate = (float(angles[0]), float(angles[1]))
        finite = all(math.isfinite(value) for value in candidate)
        within_absolute = finite and all(
            abs(value) <= self.max_abs_rad for value in candidate
        )
        within_step = self.last_valid is None or all(
            abs(value - previous) <= self.max_step_rad
            for value, previous in zip(candidate, self.last_valid)
        )
        if within_absolute and within_step:
            self.last_valid = candidate
            self.consecutive_rejections = 0
            return PoseGateResult(candidate, True, 0)

        self.consecutive_rejections += 1
        if (
            self.last_valid is not None
            and self.consecutive_rejections <= self.hold_frames
        ):
            output = self.last_valid
        else:
            output = (math.nan, math.nan)
        return PoseGateResult(output, False, self.consecutive_rejections)
