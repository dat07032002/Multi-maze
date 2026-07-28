"""Analyze passive recorder sessions and guarded active sysid sessions."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from .analysis import fit_command_to_angle, timing_summary


def _rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _numbers(rows: list[dict[str, str]], key: str) -> np.ndarray:
    return np.asarray([float(row[key]) for row in rows], dtype=np.float64)


def _complete_numbers(
    rows: list[dict[str, str]], key: str
) -> np.ndarray | None:
    values = [row.get(key, "") for row in rows]
    if not values or any(value in ("", None) for value in values):
        return None
    return np.asarray([float(value) for value in values], dtype=np.float64)


def _range(values: np.ndarray) -> dict[str, float | None]:
    finite = values[np.isfinite(values)]
    if not finite.size:
        return {"minimum": None, "maximum": None, "mean": None, "std": None}
    return {
        "minimum": float(np.min(finite)),
        "maximum": float(np.max(finite)),
        "mean": float(np.mean(finite)),
        "std": float(np.std(finite)),
    }


def analyze_session(session_dir: Path) -> dict[str, Any]:
    session_dir = session_dir.resolve()
    camera = _rows(session_dir / "camera.csv")
    states = _rows(session_dir / "states.csv")
    active_session = False
    if not states:
        states = _rows(session_dir / "board_angles.csv")
        active_session = bool(states)
    commands = _rows(session_dir / "commands.csv")
    result: dict[str, Any] = {
        "schema_version": 1,
        "session": str(session_dir),
        "session_kind": "active" if active_session else "passive",
        "timing": {
            "camera": timing_summary(int(row["monotonic_ns"]) for row in camera),
            "state": timing_summary(int(row["monotonic_ns"]) for row in states),
            "command": timing_summary(int(row["monotonic_ns"]) for row in commands),
        },
    }
    if camera:
        ages_ms = np.asarray(
            [
                float(row["header_age_ns"]) / 1e6
                for row in camera
                if row.get("header_age_ns", "") not in ("", None)
            ],
            dtype=np.float64,
        )
        plausible = ages_ms[(ages_ms >= 0.0) & (ages_ms <= 5000.0)]
        result["camera_header_age_ms"] = (
            {
                "samples": int(plausible.size),
                "median": float(np.median(plausible)),
                "p95": float(np.percentile(plausible, 95)),
                "maximum": float(np.max(plausible)),
            }
            if plausible.size
            else None
        )
    if states:
        source_ages = _complete_numbers(states, "source_age_ns")
        if source_ages is not None:
            source_ages_ms = source_ages / 1.0e6
            result["state_source_age_ms"] = {
                "samples": int(source_ages_ms.size),
                "median": float(np.median(source_ages_ms)),
                "p95": float(np.percentile(source_ages_ms, 95)),
                "maximum": float(np.max(source_ages_ms)),
            }
        visible = _numbers(states, "ball_visible") > 0.5
        result["ball_detection"] = {
            "samples": len(states),
            "visible_fraction": float(np.mean(visible)),
            "missing_fraction": float(1.0 - np.mean(visible)),
        }
        result["observed_state_ranges"] = {
            key: _range(_numbers(states, key))
            for key in (
                "x_b_m",
                "y_b_m",
                "x_b_dot_mps",
                "y_b_dot_mps",
                "alpha_rad",
                "beta_rad",
            )
        }
    if commands:
        command_keys = (
            ("command_1", "command_2")
            if active_session
            else ("vel_1", "vel_2", "target_pos_1", "target_pos_2")
        )
        result["observed_command_ranges"] = {
            key: _range(_numbers(commands, key))
            for key in command_keys
        }
    if states and commands:
        command_1_key = "command_1" if active_session else "vel_1"
        command_2_key = "command_2" if active_session else "vel_2"
        command_times = _complete_numbers(commands, "ros_time_ns")
        state_times = _complete_numbers(states, "source_time_ns")
        source_timestamp_fit = command_times is not None and state_times is not None
        if not source_timestamp_fit:
            command_times = _numbers(commands, "monotonic_ns")
            state_times = _numbers(states, "monotonic_ns")
        fit = fit_command_to_angle(
            command_times.astype(np.int64),
            np.column_stack(
                (
                    _numbers(commands, command_1_key),
                    _numbers(commands, command_2_key),
                )
            ),
            state_times.astype(np.int64),
            np.column_stack((_numbers(states, "alpha_rad"), _numbers(states, "beta_rad"))),
        )
        fit_key = (
            "active_command_angle_fit"
            if active_session
            else "passive_command_angle_fit"
        )
        result[fit_key] = fit
        if fit is not None:
            fit["timestamp_basis"] = (
                "command_ros_time_to_state_source_time"
                if source_timestamp_fit
                else "recorder_monotonic_receipt_time"
            )
    result["interpretation"] = {
        "usable_now": [
            "camera, estimator, and command rates and jitter",
            "camera header-to-recorder age when clocks are compatible",
            "ball detection loss rate and observed operating ranges",
            "preliminary command-to-board-angle gain, coupling, and correlation lag",
        ],
        "still_requires_gated_active_test": [
            "bidirectional backlash and hysteresis",
            "accurate actuator delay and step response",
            "ball/floor friction and wall restitution",
        ],
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("session", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = analyze_session(args.session)
    output = args.output or args.session.resolve() / "summary.json"
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, allow_nan=False))
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
