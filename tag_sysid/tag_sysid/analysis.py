"""ROS-independent analysis helpers for passive TAG sysid sessions."""

from __future__ import annotations

from typing import Iterable

import numpy as np


def timing_summary(timestamps_ns: Iterable[int]) -> dict[str, float | int | None]:
    values = np.asarray(tuple(timestamps_ns), dtype=np.float64)
    if values.size < 2:
        return {
            "samples": int(values.size),
            "rate_hz": None,
            "period_ms_median": None,
            "period_ms_p95": None,
            "period_ms_max": None,
        }
    periods = np.diff(values) / 1e6
    positive = periods[periods > 0.0]
    if not positive.size:
        return {
            "samples": int(values.size),
            "rate_hz": None,
            "period_ms_median": None,
            "period_ms_p95": None,
            "period_ms_max": None,
        }
    median = float(np.median(positive))
    return {
        "samples": int(values.size),
        "rate_hz": 1000.0 / median,
        "period_ms_median": median,
        "period_ms_p95": float(np.percentile(positive, 95)),
        "period_ms_max": float(np.max(positive)),
    }


def fit_command_to_angle(
    command_times_ns: np.ndarray,
    commands: np.ndarray,
    state_times_ns: np.ndarray,
    angles: np.ndarray,
    maximum_lag_seconds: float = 0.25,
    lag_step_seconds: float = 0.005,
) -> dict[str, object] | None:
    """Fit passive command-to-angle maps over candidate receipt-time lags.

    This is a correlation estimate from closed-loop operation, not a substitute
    for an isolated step-response and bidirectional sweep.
    """

    command_times_ns = np.asarray(command_times_ns, dtype=np.int64)
    state_times_ns = np.asarray(state_times_ns, dtype=np.int64)
    commands = np.asarray(commands, dtype=np.float64)
    angles = np.asarray(angles, dtype=np.float64)
    if (
        command_times_ns.size < 10
        or state_times_ns.size < 20
        or commands.shape != (command_times_ns.size, 2)
        or angles.shape != (state_times_ns.size, 2)
    ):
        return None
    finite_commands = np.isfinite(commands).all(axis=1)
    command_times_ns = command_times_ns[finite_commands]
    commands = commands[finite_commands]
    if command_times_ns.size < 10:
        return None
    command_order = np.argsort(command_times_ns)
    command_times_ns = command_times_ns[command_order]
    commands = commands[command_order]
    finite_states = np.isfinite(angles).all(axis=1)
    state_times_ns = state_times_ns[finite_states]
    angles = angles[finite_states]
    state_order = np.argsort(state_times_ns)
    state_times_ns = state_times_ns[state_order]
    angles = angles[state_order]
    if state_times_ns.size < 20:
        return None

    best = None
    lag_values = np.arange(
        0.0,
        maximum_lag_seconds + 0.5 * lag_step_seconds,
        lag_step_seconds,
    )
    for lag in lag_values:
        query = state_times_ns - int(round(lag * 1e9))
        indices = np.searchsorted(command_times_ns, query, side="right") - 1
        valid = indices >= 0
        if int(np.sum(valid)) < 20:
            continue
        x = np.column_stack(
            (np.ones(int(np.sum(valid))), commands[indices[valid]])
        )
        y = angles[valid]
        coefficients, *_ = np.linalg.lstsq(x, y, rcond=None)
        prediction = x @ coefficients
        residual = np.sum((y - prediction) ** 2, axis=0)
        centered = np.sum((y - np.mean(y, axis=0)) ** 2, axis=0)
        r2 = 1.0 - residual / np.maximum(centered, 1e-12)
        score = float(np.mean(r2))
        candidate = (score, float(lag), coefficients, r2, int(np.sum(valid)))
        if best is None or candidate[0] > best[0]:
            best = candidate
    if best is None:
        return None
    _, lag, coefficients, r2, samples = best
    return {
        "method": "passive_closed_loop_correlation",
        "lag_seconds": lag,
        "lag_resolution_seconds": max(
            lag_step_seconds,
            float(np.median(np.diff(command_times_ns))) / 1e9,
        ),
        "samples": samples,
        "offset_rad": coefficients[0].tolist(),
        "angle_rad_per_command": coefficients[1:].T.tolist(),
        "r2": r2.tolist(),
        "warning": (
            "Confirm with an approval-gated bidirectional sweep and step "
            "response before deployment."
        ),
    }
