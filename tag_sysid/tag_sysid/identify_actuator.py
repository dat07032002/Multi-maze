"""Identify direction-dependent actuator response from guarded step sessions."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np


ANGLE_FIELDS = ("alpha_rad", "beta_rad")


def _read_csv(path: Path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _tail_median(rows, duration_seconds=0.35):
    times = np.asarray([int(row["source_time_ns"]) * 1.0e-9 for row in rows])
    keep = times >= times.max() - float(duration_seconds)
    angles = np.asarray(
        [[float(row[field]) for field in ANGLE_FIELDS] for row in rows]
    )
    return np.median(angles[keep], axis=0)


def _first_crossing(times, values, baseline, change, fraction):
    target = baseline + fraction * change
    indices = np.flatnonzero(values >= target if change >= 0.0 else values <= target)
    return None if not len(indices) else float(times[indices[0]])


def identify_step_session(session: Path, minimum_response_deg=0.05):
    """Summarize repeated single-axis steps using source image timestamps."""

    session = Path(session)
    states = _read_csv(session / "board_angles.csv")
    commands = _read_csv(session / "commands.csv")
    active_states = [row for row in states if int(row["phase_index"]) >= 0]
    axes = {
        int(row["axis"])
        for row in active_states
        if int(row["axis"]) in (1, 2)
        and (
            float(row["command_1"]) != 0.0
            or float(row["command_2"]) != 0.0
        )
    }
    if len(axes) != 1:
        raise ValueError(f"Expected one active axis in {session}, got {sorted(axes)}")
    axis = axes.pop()
    command_field = f"command_{axis}"
    phase_indices = sorted({int(row["phase_index"]) for row in active_states})
    by_phase = {
        phase: [row for row in active_states if int(row["phase_index"]) == phase]
        for phase in phase_indices
    }
    command_by_phase = {
        phase: [row for row in commands if int(row["phase_index"]) == phase]
        for phase in phase_indices
    }
    medians = {phase: _tail_median(rows) for phase, rows in by_phase.items()}
    measurements = []
    minimum_response = math.radians(float(minimum_response_deg))
    for phase in phase_indices:
        phase_commands = command_by_phase[phase]
        if not phase_commands:
            continue
        command = float(phase_commands[0][command_field])
        if command == 0.0:
            continue
        prior_home = max(
            candidate
            for candidate in phase_indices
            if candidate < phase
            and command_by_phase[candidate]
            and float(command_by_phase[candidate][0][command_field]) == 0.0
        )
        baseline = medians[prior_home]
        change = medians[phase] - baseline
        command_time = min(
            int(row["ros_time_ns"]) * 1.0e-9 for row in phase_commands
        )
        phase_rows = by_phase[phase]
        source_times = np.asarray(
            [int(row["source_time_ns"]) * 1.0e-9 for row in phase_rows]
        )
        angles = np.asarray(
            [[float(row[field]) for field in ANGLE_FIELDS] for row in phase_rows]
        )
        crossings = {}
        for index, field in enumerate(ANGLE_FIELDS):
            if abs(change[index]) < minimum_response:
                crossings[field] = {"t10_seconds": None, "t90_seconds": None}
                continue
            crossings[field] = {
                "t10_seconds": _first_crossing(
                    source_times, angles[:, index], baseline[index], change[index], 0.1
                ),
                "t90_seconds": _first_crossing(
                    source_times, angles[:, index], baseline[index], change[index], 0.9
                ),
            }
            for key, value in crossings[field].items():
                if value is not None:
                    crossings[field][key] = value - command_time
        measurements.append(
            {
                "phase": phase,
                "command": command,
                "change_rad": change.tolist(),
                "crossings": crossings,
            }
        )

    directions = {}
    for label, sign in (("positive", 1.0), ("negative", -1.0)):
        selected = [row for row in measurements if np.sign(row["command"]) == sign]
        changes = np.asarray([row["change_rad"] for row in selected])
        median_change = np.median(changes, axis=0)
        median_command = float(np.median([row["command"] for row in selected]))
        timing = {}
        for field in ANGLE_FIELDS:
            timing[field] = {}
            for key in ("t10_seconds", "t90_seconds"):
                values = [
                    row["crossings"][field][key]
                    for row in selected
                    if row["crossings"][field][key] is not None
                    and row["crossings"][field][key] >= 0.0
                ]
                timing[field][key] = None if not values else float(np.median(values))
        directions[label] = {
            "command": median_command,
            "repetitions": len(selected),
            "median_change_rad": median_change.tolist(),
            "local_rad_per_command": (median_change / median_command).tolist(),
            "timing": timing,
        }

    return {
        "session": str(session),
        "axis": axis,
        "minimum_timed_response_deg": minimum_response_deg,
        "directions": directions,
        "raw_sha256": {
            name: hashlib.sha256((session / name).read_bytes()).hexdigest()
            for name in ("commands.csv", "board_angles.csv")
        },
    }


def main(args=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sessions", nargs="+", type=Path)
    parser.add_argument("--output", type=Path)
    parsed = parser.parse_args(args)
    result = {
        "schema_version": 1,
        "method": "phase-tail median relative to preceding home; source timestamps",
        "sessions": [identify_step_session(path) for path in parsed.sessions],
    }
    encoded = json.dumps(result, indent=2) + "\n"
    if parsed.output:
        parsed.output.write_text(encoded, encoding="utf-8")
        print(f"Wrote {parsed.output}")
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()
