"""Fit effective marble dynamics from a passive TAG trajectory recording."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np


def _read_states(session: Path):
    state_path = session / "states.csv"
    if not state_path.exists():
        state_path = session / "board_angles.csv"
    with state_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    values = []
    for row in rows:
        if not int(row["ball_visible"]):
            continue
        time_ns = row.get("source_time_ns") or row["ros_time_ns"]
        sample = [
            int(time_ns) * 1.0e-9,
            float(row["x_b_m"]),
            float(row["y_b_m"]),
            float(row["alpha_rad"]),
            float(row["beta_rad"]),
        ]
        if np.all(np.isfinite(sample)):
            values.append(sample)
    result = np.asarray(values, dtype=np.float64)
    if len(result) < 20:
        raise ValueError("At least 20 finite visible state samples are required")
    order = np.argsort(result[:, 0])
    result = result[order]
    keep = np.concatenate(([True], np.diff(result[:, 0]) > 1.0e-6))
    return result[keep]


def local_kinematics(times, positions, window_seconds=0.18, minimum_samples=7):
    """Estimate velocity and acceleration with centered local quadratics."""

    times = np.asarray(times, dtype=np.float64)
    positions = np.asarray(positions, dtype=np.float64)
    velocity = np.full_like(positions, np.nan)
    acceleration = np.full_like(positions, np.nan)
    half = 0.5 * float(window_seconds)
    for index, center in enumerate(times):
        selection = np.flatnonzero(np.abs(times - center) <= half)
        if len(selection) < minimum_samples:
            continue
        relative = times[selection] - center
        design = np.column_stack((np.ones(len(selection)), relative, relative**2))
        coefficients = np.linalg.lstsq(design, positions[selection], rcond=None)[0]
        velocity[index] = coefficients[1]
        acceleration[index] = 2.0 * coefficients[2]
    return velocity, acceleration


def _huber_fit(design, target, iterations=8, tuning=1.5):
    weights = np.ones(len(target), dtype=np.float64)
    coefficients = np.zeros(design.shape[1], dtype=np.float64)
    for _ in range(iterations):
        weighted = np.sqrt(weights)[:, None]
        coefficients = np.linalg.lstsq(
            design * weighted, target * weighted[:, 0], rcond=None
        )[0]
        residual = target - design @ coefficients
        scale = 1.4826 * np.median(np.abs(residual - np.median(residual)))
        if scale <= 1.0e-12:
            break
        normalized = np.abs(residual) / (tuning * scale)
        weights = np.ones_like(normalized)
        outliers = normalized > 1.0
        weights[outliers] = 1.0 / normalized[outliers]
    return coefficients, weights


def fit_free_roll(times, positions, angles):
    velocity, acceleration = local_kinematics(times, positions)
    speed = np.linalg.norm(velocity, axis=1)
    finite = np.all(np.isfinite(velocity), axis=1) & np.all(
        np.isfinite(acceleration), axis=1
    )
    usable = finite & (speed >= 0.004) & (speed <= 0.35)
    usable &= np.linalg.norm(acceleration, axis=1) <= 8.0
    indices = np.flatnonzero(usable)
    if len(indices) < 40:
        raise ValueError("At least 40 moving, finite samples are required")

    # Shared damping and rolling resistance, independent 2x2 tilt map and bias.
    rows = []
    targets = []
    for index in indices:
        unit = velocity[index] / speed[index]
        alpha, beta = angles[index]
        rows.append([alpha, beta, 0.0, 0.0, -velocity[index, 0], -unit[0], 1, 0])
        targets.append(acceleration[index, 0])
        rows.append([0.0, 0.0, alpha, beta, -velocity[index, 1], -unit[1], 0, 1])
        targets.append(acceleration[index, 1])
    design = np.asarray(rows, dtype=np.float64)
    target = np.asarray(targets, dtype=np.float64)
    coefficients, weights = _huber_fit(design, target)
    prediction = design @ coefficients
    residual = target - prediction
    centered = target - np.mean(target)
    r2 = 1.0 - float(np.sum(residual**2)) / max(
        float(np.sum(centered**2)), 1.0e-12
    )
    return {
        "samples": int(len(indices)),
        "tilt_acceleration_mps2_per_rad": [
            coefficients[0:2].tolist(), coefficients[2:4].tolist()
        ],
        "linear_damping_per_second": float(max(0.0, coefficients[4])),
        "rolling_resistance_mps2": float(max(0.0, coefficients[5])),
        "bias_mps2": coefficients[6:8].tolist(),
        "r2": r2,
        "residual_rmse_mps2": float(np.sqrt(np.mean(residual**2))),
        "robust_inlier_fraction": float(np.mean(weights >= 0.999)),
    }, velocity


def detect_impacts(times, positions, velocity, minimum_speed=0.025):
    impacts = []
    for index in range(1, len(times) - 1):
        before = velocity[index - 1]
        after = velocity[index + 1]
        if not np.all(np.isfinite(before)) or not np.all(np.isfinite(after)):
            continue
        if np.linalg.norm(before) < minimum_speed:
            continue
        change = after - before
        magnitude = np.linalg.norm(change)
        if magnitude < 0.035:
            continue
        normal = change / magnitude
        incoming = float(np.dot(before, normal))
        outgoing = float(np.dot(after, normal))
        if incoming >= -0.01 or outgoing <= 0.0:
            continue
        restitution = outgoing / -incoming
        if 0.0 <= restitution <= 1.2:
            impacts.append(
                {
                    "time_seconds": float(times[index] - times[0]),
                    "position_m": positions[index].tolist(),
                    "incoming_normal_mps": incoming,
                    "outgoing_normal_mps": outgoing,
                    "restitution": restitution,
                }
            )
    coefficients = [impact["restitution"] for impact in impacts]
    summary = {
        "count": len(impacts),
        "median": None if not coefficients else float(np.median(coefficients)),
        "p10": None if not coefficients else float(np.percentile(coefficients, 10)),
        "p90": None if not coefficients else float(np.percentile(coefficients, 90)),
        "events": impacts,
    }
    return summary


def fit_session(session: Path):
    values = _read_states(session)
    times = values[:, 0]
    positions = values[:, 1:3]
    angles = values[:, 3:5]
    free_roll, velocity = fit_free_roll(times, positions, angles)
    impacts = detect_impacts(times, positions, velocity)
    duration = float(times[-1] - times[0])
    return {
        "schema_version": 1,
        "session": str(Path(session).resolve()),
        "timestamp_basis": "state_source_time_when_available",
        "visible_samples": int(len(values)),
        "duration_seconds": duration,
        "rate_hz": (len(values) - 1) / duration,
        "free_roll": free_roll,
        "wall_impacts": impacts,
        "quality_gate": {
            "free_roll_usable": bool(free_roll["samples"] >= 200 and free_roll["r2"] >= 0.25),
            "restitution_usable": bool(impacts["count"] >= 5),
            "warnings": [
                warning
                for condition, warning in (
                    (free_roll["samples"] < 200, "fewer than 200 moving samples"),
                    (free_roll["r2"] < 0.25, "free-roll fit R2 is below 0.25"),
                    (impacts["count"] < 5, "fewer than five detected impacts"),
                )
                if condition
            ],
        },
    }


def main(args=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session", type=Path)
    parser.add_argument("--output", type=Path)
    parsed = parser.parse_args(args)
    result = fit_session(parsed.session)
    output = parsed.output or parsed.session / "dynamics_fit.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
