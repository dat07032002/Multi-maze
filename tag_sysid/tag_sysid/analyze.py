"""Analyze a session produced by :mod:`tag_sysid.recorder`."""

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
    commands = _rows(session_dir / "commands.csv")
    result: dict[str, Any] = {
        "schema_version": 1,
        "session": str(session_dir),
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
        result["observed_command_ranges"] = {
            key: _range(_numbers(commands, key))
            for key in ("vel_1", "vel_2", "target_pos_1", "target_pos_2")
        }
    if states and commands:
        fit = fit_command_to_angle(
            _numbers(commands, "monotonic_ns").astype(np.int64),
            np.column_stack((_numbers(commands, "vel_1"), _numbers(commands, "vel_2"))),
            _numbers(states, "monotonic_ns").astype(np.int64),
            np.column_stack((_numbers(states, "alpha_rad"), _numbers(states, "beta_rad"))),
        )
        result["passive_command_angle_fit"] = fit
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
