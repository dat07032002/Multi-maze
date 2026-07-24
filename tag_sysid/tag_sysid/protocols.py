"""Pure, testable protocol definitions for guarded hardware measurements."""

from __future__ import annotations

from dataclasses import dataclass


HARD_COMMAND_LIMIT = 120.0


@dataclass(frozen=True)
class Phase:
    """One constant-command phase in an active measurement protocol."""

    name: str
    repetition: int
    axis: int
    command_1: float
    command_2: float
    duration_seconds: float


def _phase(
    name: str,
    repetition: int,
    axis: int,
    value: float,
    duration: float,
) -> Phase:
    if axis not in (0, 1, 2):
        raise ValueError("axis must be 0, 1, or 2")
    if abs(value) > HARD_COMMAND_LIMIT:
        raise ValueError(
            f"command {value} exceeds hard sysid limit {HARD_COMMAND_LIMIT}"
        )
    command_1 = value if axis == 1 else 0.0
    command_2 = value if axis == 2 else 0.0
    return Phase(
        name=name,
        repetition=repetition,
        axis=axis,
        command_1=command_1,
        command_2=command_2,
        duration_seconds=float(duration),
    )


def build_protocol(
    test: str,
    repetitions: int | None = None,
    hold_seconds: float | None = None,
    command_scale: float = 1.0,
    axes: tuple[int, ...] = (1, 2),
) -> list[Phase]:
    """Return the conservative command phases for a named measurement."""

    if not 0.1 <= command_scale <= 1.0:
        raise ValueError("command_scale must be in [0.1, 1.0]")
    if not axes or any(axis not in (1, 2) for axis in axes):
        raise ValueError("axes must contain only axis 1 and/or axis 2")

    def scaled(value: float) -> float:
        return float(value) * command_scale

    if test == "home":
        count = repetitions if repetitions is not None else 5
        hold = hold_seconds if hold_seconds is not None else 30.0
        plan = []
        for repetition in range(1, count + 1):
            # A small alternating displacement makes return-home repeatability
            # observable without requiring the more aggressive reset service.
            axis = 1 if repetition % 2 else 2
            sign = 1.0 if repetition % 4 in (1, 2) else -1.0
            plan.append(
                _phase(
                    "home_departure",
                    repetition,
                    axis,
                    scaled(sign * 40.0),
                    1.5,
                )
            )
            plan.append(_phase("home_measurement", repetition, 0, 0.0, hold))
        return plan

    if test == "axis":
        count = repetitions if repetitions is not None else 3
        hold = hold_seconds if hold_seconds is not None else 2.0
        plan = []
        for repetition in range(1, count + 1):
            for axis in axes:
                for value in (40.0, 0.0, -40.0, 0.0):
                    name = "axis_measurement" if value else "home_settle"
                    duration = hold if value else 2.0
                    plan.append(
                        _phase(
                            name,
                            repetition,
                            axis if value else 0,
                            scaled(value),
                            duration,
                        )
                    )
        return plan

    if test == "sweep":
        count = repetitions if repetitions is not None else 3
        hold = hold_seconds if hold_seconds is not None else 2.5
        values = (0, 40, 80, 120, 80, 40, 0, -40, -80, -120, -80, -40, 0)
        plan = []
        for repetition in range(1, count + 1):
            for axis in axes:
                for value in values:
                    plan.append(
                        _phase(
                            "static_sweep",
                            repetition,
                            axis,
                            scaled(float(value)),
                            hold,
                        )
                    )
                plan.append(_phase("home_settle", repetition, 0, 0.0, 3.0))
        return plan

    if test == "step":
        count = repetitions if repetitions is not None else 10
        hold = hold_seconds if hold_seconds is not None else 1.5
        plan = []
        for repetition in range(1, count + 1):
            for axis in axes:
                for value in (0.0, 80.0, 0.0, -80.0, 0.0):
                    name = "step_measurement" if value else "home_settle"
                    plan.append(
                        _phase(name, repetition, axis, scaled(value), hold)
                    )
        return plan

    raise ValueError(f"unknown test: {test}")


def validate_protocol(phases: list[Phase]) -> None:
    """Reject plans that violate the active-test safety invariants."""

    if not phases:
        raise ValueError("protocol is empty")
    for phase in phases:
        if phase.duration_seconds <= 0.0:
            raise ValueError("phase durations must be positive")
        if abs(phase.command_1) > HARD_COMMAND_LIMIT:
            raise ValueError("axis 1 command exceeds the hard limit")
        if abs(phase.command_2) > HARD_COMMAND_LIMIT:
            raise ValueError("axis 2 command exceeds the hard limit")
        if phase.command_1 and phase.command_2:
            raise ValueError("active sysid may excite only one axis at a time")
    if phases[-1].command_1 or phases[-1].command_2:
        raise ValueError("protocol must finish at the home command")
