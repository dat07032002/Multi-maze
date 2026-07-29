"""Fit the residual actuator lag left over after the modeled driver behavior.

The 2026-07-27 step campaign measured a camera-observed end-to-end t90 of roughly
0.23 s at Hiwonder command 80. That figure is *not* pure servo dynamics: it
contains the 30 Hz driver tick, the 20-servo-unit-per-tick slew limit, the
linkage, the camera, and the estimator. The simulator already models the tick
quantization, the slew limit, and one control step of observation delay, so
adding the measured 33 ms / 86 ms first-order fit on top counted the same rate
limit twice and made the simulated board about 1.6x more sluggish than the real
one.

This tool measures what the modeled driver already accounts for, then fits the
one remaining free parameter -- `response_time_constant_seconds` -- so the
modeled camera-observed t90 matches the measurement. Run it whenever the driver
model, control rate, or observation delay changes:

    python -m tag_mujoco.fit_actuator_response

It writes a report next to the sysid data and prints the recommended constants.
`tests/test_actuator_response_timing.py` asserts the committed values still
reproduce the measured timing.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

import numpy as np

try:
    from .actuator_model import HiwonderActuatorModel
    from .system_config import ActuatorConfig, CameraConfig, SystemConfig
except ImportError:  # Preserve direct-script execution from this directory.
    from actuator_model import HiwonderActuatorModel
    from system_config import ActuatorConfig, CameraConfig, SystemConfig


HERE = Path(__file__).resolve().parent
DEFAULT_SYSID = HERE.parent / "docs" / "sysid_actuator_step80_2026-07-27.json"
DEFAULT_REPORT = HERE.parent / "docs" / "actuator_response_residual_fit.json"

# The superseded values, kept so the report can quantify the double count.
SUPERSEDED_DELAY_SECONDS = 0.033
SUPERSEDED_RESPONSE_SECONDS = 0.086


# Minimum ratio between the dominant and the secondary axis response for the
# "dominant t90" of a condition to be trustworthy. Axis 1 negative moves both
# angles by the same amount to within 1% -- the near-singular negative command
# map -- so which angle is "dominant" there is a coin flip, and its two
# candidate t90 values differ by 3x (91 ms vs 275 ms). Timing fitted through
# that condition is fitting an argmax tie, not the mechanism.
DEFAULT_DOMINANCE_RATIO = 1.5


def measured_dominant_t90(
    sysid: Mapping[str, Any],
    *,
    dominance_ratio: float = 0.0,
) -> List[Dict[str, Any]]:
    """Return the dominant-axis t90 for every measured axis and direction.

    The dominant axis is the one with the largest absolute median change, which
    is the same convention the sysid document uses for its "dominant t90"
    column. Conditions whose two axes respond within ``dominance_ratio`` of each
    other are excluded as ambiguous.
    """

    rows: List[Dict[str, Any]] = []
    for session in sysid["sessions"]:
        for direction, record in session["directions"].items():
            change = np.abs(np.asarray(record["median_change_rad"], dtype=np.float64))
            dominant = int(np.argmax(change))
            key = ("alpha_rad", "beta_rad")[dominant]
            t90 = record["timing"][key]["t90_seconds"]
            if t90 is None:
                continue
            ratio = float(change.max() / max(change.min(), 1e-12))
            row = {
                "axis": int(session["axis"]),
                "direction": str(direction),
                "command": float(record["command"]),
                "dominant_angle": key,
                "dominance_ratio": ratio,
                "measured_t90_seconds": float(t90),
            }
            if ratio < dominance_ratio:
                row["excluded_as_ambiguous"] = True
                continue
            rows.append(row)
    if not rows:
        raise ValueError("No usable t90 crossings found in the sysid record")
    return rows


def simulate_step_response(
    config: ActuatorConfig,
    *,
    axis: int,
    command: float,
    control_rate_hz: float,
    observation_delay_steps: int,
    horizon_seconds: float = 3.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Return observation timestamps and both board angles for a command step.

    The returned series is what a camera sampling at the control rate would see,
    including the modeled observation delay, so it is directly comparable to the
    hardware measurement.
    """

    scale = np.asarray(config.policy_command_scale, dtype=np.float64)
    sign = np.asarray(config.policy_command_sign, dtype=np.float64)
    action = np.zeros(2, dtype=np.float64)
    action[axis - 1] = command / (scale[axis - 1] * sign[axis - 1])
    if abs(action[axis - 1]) > 1.0:
        raise ValueError(
            f"Command {command} exceeds the normalized action range on axis {axis}"
        )

    actuator = HiwonderActuatorModel(config)
    dt = 1.0 / float(control_rate_hz)
    steps = max(2, int(round(horizon_seconds / dt)))
    angles = np.zeros((steps, 2), dtype=np.float64)
    for index in range(steps):
        actuator.submit_action(action)
        angles[index] = actuator.step(dt)

    delay = max(0, int(observation_delay_steps))
    if delay:
        angles = np.concatenate([np.zeros((delay, 2)), angles[:-delay]], axis=0)
    times = (np.arange(steps, dtype=np.float64) + 1.0) * dt
    return times, angles


def crossing_time(times: np.ndarray, series: np.ndarray, fraction: float) -> float | None:
    """Return the linearly interpolated time at which ``series`` first reaches
    ``fraction`` of its settled value.

    Interpolation matters because the simulated observation series is sampled at
    the 35 Hz control rate, which is 28.6 ms per sample against a 0.23 s target.
    Nearest-sample reporting would quantize the fit to about 12% of the value
    being fitted.
    """

    settled = float(series[-1])
    if abs(settled) < 1e-12:
        return None
    normalized = series / settled
    above = np.flatnonzero(normalized >= fraction)
    if above.size == 0:
        return None
    index = int(above[0])
    if index == 0:
        return float(times[0])
    previous, current = normalized[index - 1], normalized[index]
    if current == previous:
        return float(times[index])
    span = (fraction - previous) / (current - previous)
    return float(times[index - 1] + span * (times[index] - times[index - 1]))


def modeled_t90(
    config: ActuatorConfig,
    row: Mapping[str, Any],
    *,
    control_rate_hz: float,
    observation_delay_steps: int,
) -> float | None:
    times, angles = simulate_step_response(
        config,
        axis=int(row["axis"]),
        command=float(row["command"]),
        control_rate_hz=control_rate_hz,
        observation_delay_steps=observation_delay_steps,
    )
    column = 0 if row["dominant_angle"] == "alpha_rad" else 1
    return crossing_time(times, angles[:, column], 0.90)


def _residuals(
    config: ActuatorConfig,
    rows: Sequence[Mapping[str, Any]],
    *,
    control_rate_hz: float,
    observation_delay_steps: int,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in rows:
        modeled = modeled_t90(
            config,
            row,
            control_rate_hz=control_rate_hz,
            observation_delay_steps=observation_delay_steps,
        )
        out.append(
            {
                **row,
                "modeled_t90_seconds": modeled,
                "error_seconds": (
                    None if modeled is None else modeled - row["measured_t90_seconds"]
                ),
            }
        )
    return out


def _median_absolute_error(rows: Sequence[Mapping[str, Any]]) -> float:
    errors = [
        abs(float(row["error_seconds"]))
        for row in rows
        if row["error_seconds"] is not None
    ]
    return float(np.median(errors)) if errors else float("inf")


def fit(
    sysid: Mapping[str, Any],
    *,
    base: ActuatorConfig | None = None,
    control_rate_hz: float | None = None,
    observation_delay_steps: int | None = None,
    candidates: np.ndarray | None = None,
    dominance_ratio: float = DEFAULT_DOMINANCE_RATIO,
) -> Dict[str, Any]:
    """Fit the residual response time constant with zero residual pure delay.

    Pure delay is held at zero because the modeled 30 Hz tick and the modeled
    observation delay already supply the transport the measurement attributed to
    a 33 ms pure delay. Any genuinely un-modeled command-path transport is
    covered by the randomization range rather than the nominal value.
    """

    defaults = SystemConfig()
    base = base if base is not None else ActuatorConfig()
    control_rate_hz = (
        control_rate_hz if control_rate_hz is not None else defaults.control_rate_hz
    )
    observation_delay_steps = (
        observation_delay_steps
        if observation_delay_steps is not None
        else CameraConfig().observation_delay_steps
    )
    if candidates is None:
        candidates = np.round(np.arange(0.0, 0.1005, 0.001), 4)

    rows = measured_dominant_t90(sysid, dominance_ratio=dominance_ratio)
    all_rows = measured_dominant_t90(sysid, dominance_ratio=0.0)

    slew_only = replace(
        base, total_delay_seconds=0.0, response_time_constant_seconds=1e-6
    )
    superseded = replace(
        base,
        total_delay_seconds=SUPERSEDED_DELAY_SECONDS,
        response_time_constant_seconds=SUPERSEDED_RESPONSE_SECONDS,
    )

    scored: List[Dict[str, Any]] = []
    for value in candidates:
        candidate = replace(
            base,
            total_delay_seconds=0.0,
            response_time_constant_seconds=float(max(value, 1e-6)),
        )
        detail = _residuals(
            candidate,
            rows,
            control_rate_hz=control_rate_hz,
            observation_delay_steps=observation_delay_steps,
        )
        scored.append(
            {
                "response_time_constant_seconds": float(value),
                "median_absolute_error_seconds": _median_absolute_error(detail),
            }
        )
    best = min(scored, key=lambda item: item["median_absolute_error_seconds"])

    def view(config: ActuatorConfig) -> Dict[str, Any]:
        detail = _residuals(
            config,
            rows,
            control_rate_hz=control_rate_hz,
            observation_delay_steps=observation_delay_steps,
        )
        return {
            "total_delay_seconds": config.total_delay_seconds,
            "response_time_constant_seconds": config.response_time_constant_seconds,
            "median_absolute_error_seconds": _median_absolute_error(detail),
            "per_condition": detail,
        }

    fitted = replace(
        base,
        total_delay_seconds=0.0,
        response_time_constant_seconds=float(
            max(best["response_time_constant_seconds"], 1e-6)
        ),
    )
    return {
        "schema_version": 2,
        "control_rate_hz": float(control_rate_hz),
        "observation_delay_steps": int(observation_delay_steps),
        "dominance_ratio_threshold": float(dominance_ratio),
        "conditions_used": [
            f"axis{row['axis']}_{row['direction']}" for row in rows
        ],
        "conditions_excluded_as_ambiguous": [
            f"axis{row['axis']}_{row['direction']}"
            for row in all_rows
            if row not in rows
        ],
        "measured_median_t90_seconds": float(
            np.median([row["measured_t90_seconds"] for row in rows])
        ),
        "measured_median_t90_all_conditions_seconds": float(
            np.median([row["measured_t90_seconds"] for row in all_rows])
        ),
        "driver_model_only": view(slew_only),
        "superseded_double_counted": view(superseded),
        "fitted_residual": view(fitted),
        "committed": view(base),
        "recommended": {
            "total_delay_seconds": 0.0,
            "response_time_constant_seconds": fitted.response_time_constant_seconds,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sysid", type=Path, default=DEFAULT_SYSID)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument(
        "--dominance-ratio", type=float, default=DEFAULT_DOMINANCE_RATIO
    )
    args = parser.parse_args()

    sysid = json.loads(args.sysid.read_text(encoding="utf-8"))
    report = fit(sysid, dominance_ratio=args.dominance_ratio)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    measured = report["measured_median_t90_seconds"]
    print(f"conditions used:     {report['conditions_used']}")
    print(f"excluded (ambiguous):{report['conditions_excluded_as_ambiguous']}")
    print(f"measured median dominant t90:      {measured * 1000:7.1f} ms")
    for name in ("driver_model_only", "superseded_double_counted", "committed", "fitted_residual"):
        view = report[name]
        print(
            f"{name:26s} delay={view['total_delay_seconds'] * 1000:5.1f} ms "
            f"tau={view['response_time_constant_seconds'] * 1000:5.1f} ms "
            f"median |error|={view['median_absolute_error_seconds'] * 1000:6.1f} ms"
        )
    print(f"\nrecommended: {report['recommended']}")
    print(f"report written to {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
