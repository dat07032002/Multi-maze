"""Pure phase definitions for separately gated marble-dynamics trials."""

from __future__ import annotations

from .protocols import Phase, validate_protocol


MARBLE_COMMAND_LIMIT = 100.0


def build_marble_pulse(axis: int, direction: int) -> list[Phase]:
    """Build one gradual tilt/release pulse ending at neutral."""
    if axis not in (1, 2):
        raise ValueError("axis must be 1 or 2")
    if direction not in (-1, 1):
        raise ValueError("direction must be -1 or +1")

    phases = []
    values_and_durations = (
        (0.0, 1.0, "neutral_baseline"),
        (5.0, 0.4, "ramp_out"),
        (10.0, 0.4, "ramp_out"),
        (15.0, 0.4, "ramp_out"),
        (20.0, 0.6, "peak_tilt"),
        (15.0, 0.2, "ramp_home"),
        (10.0, 0.2, "ramp_home"),
        (5.0, 0.2, "ramp_home"),
        (0.0, 2.0, "neutral_coast"),
    )
    for value, duration, name in values_and_durations:
        signed_value = direction * value
        phases.append(
            Phase(
                name=name,
                repetition=1,
                axis=axis if value else 0,
                command_1=signed_value if axis == 1 else 0.0,
                command_2=signed_value if axis == 2 else 0.0,
                duration_seconds=duration,
            )
        )
    validate_marble_protocol(phases)
    return phases


def build_marble_breakaway(axis: int, direction: int) -> list[Phase]:
    """Build a staircase that stops at runtime when the marble releases."""
    if axis not in (1, 2):
        raise ValueError("axis must be 1 or 2")
    if direction not in (-1, 1):
        raise ValueError("direction must be -1 or +1")

    phases = [Phase("neutral_baseline", 1, 0, 0.0, 0.0, 1.0)]
    for value in (20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0):
        signed_value = direction * value
        phases.append(
            Phase(
                name="breakaway_staircase",
                repetition=1,
                axis=axis,
                command_1=signed_value if axis == 1 else 0.0,
                command_2=signed_value if axis == 2 else 0.0,
                duration_seconds=0.3,
            )
        )
    phases.append(Phase("neutral_coast", 1, 0, 0.0, 0.0, 2.0))
    validate_marble_protocol(phases)
    return phases


def build_marble_high_breakaway(axis: int, direction: int) -> list[Phase]:
    """Build a short high-range staircase after a successful 50 trial."""
    if axis not in (1, 2):
        raise ValueError("axis must be 1 or 2")
    if direction not in (-1, 1):
        raise ValueError("direction must be -1 or +1")

    phases = [Phase("neutral_baseline", 1, 0, 0.0, 0.0, 1.0)]
    for value in (50.0, 60.0, 70.0, 80.0, 90.0, 100.0):
        signed_value = direction * value
        phases.append(
            Phase(
                name="high_breakaway_staircase",
                repetition=1,
                axis=axis,
                command_1=signed_value if axis == 1 else 0.0,
                command_2=signed_value if axis == 2 else 0.0,
                duration_seconds=0.25,
            )
        )
    phases.append(Phase("neutral_coast", 1, 0, 0.0, 0.0, 2.0))
    validate_marble_protocol(phases)
    return phases


def build_marble_gentle_high(axis: int, direction: int) -> list[Phase]:
    """Build a slow 10-command staircase to reduce camera motion blur."""
    if axis not in (1, 2):
        raise ValueError("axis must be 1 or 2")
    if direction not in (-1, 1):
        raise ValueError("direction must be -1 or +1")

    phases = [Phase("neutral_baseline", 1, 0, 0.0, 0.0, 1.0)]
    for value in range(10, 101, 10):
        signed_value = direction * float(value)
        phases.append(
            Phase(
                name="gentle_high_staircase",
                repetition=1,
                axis=axis,
                command_1=signed_value if axis == 1 else 0.0,
                command_2=signed_value if axis == 2 else 0.0,
                duration_seconds=0.4,
            )
        )
    for value in (80.0, 60.0, 40.0, 20.0):
        signed_value = direction * value
        phases.append(
            Phase(
                name="gentle_ramp_home",
                repetition=1,
                axis=axis,
                command_1=signed_value if axis == 1 else 0.0,
                command_2=signed_value if axis == 2 else 0.0,
                duration_seconds=0.2,
            )
        )
    phases.append(Phase("neutral_coast", 1, 0, 0.0, 0.0, 2.0))
    validate_marble_protocol(phases)
    return phases


def validate_marble_protocol(phases: list[Phase]) -> None:
    """Apply generic invariants plus the tighter marble command bound."""
    validate_protocol(phases)
    maximum = max(
        max(abs(phase.command_1), abs(phase.command_2)) for phase in phases
    )
    if maximum > MARBLE_COMMAND_LIMIT:
        raise ValueError(
            f"marble command {maximum} exceeds limit {MARBLE_COMMAND_LIMIT}"
        )
