"""Baseline what the simulator believes about board tilt authority.

This exists because `board_rad_per_command_*` reads as a measurement and is
not one. It is a local slope fitted near |command|=80 from camera-derived board
angles (`docs/sysid_actuator_step80_2026-07-27.json`, median changes of 0.21 to
0.71 degrees against a 0.05 degree resolution floor), then applied at the policy
limit of command 180 -- a 2.25x extrapolation, on a mechanism the same campaign
describes as directionally ambiguous at command 40 because of preload and
backlash.

Board angle sets every dynamic limit that matters: achievable lateral
acceleration, minimum turn radius, stopping distance, and therefore which routes
are trackable at all. Before re-measuring it on hardware, this module states
precisely what the shipped model currently predicts, in the unit the bench will
actually read -- millimetres of edge lift, not radians.

The discrimination is coarse enough to settle with a ruler. At command 80 the
shipped calibration predicts 3.2 mm of lift across the 259 mm board; if full
command instead produced the assumed 10 degree limit, the same command would
lift the edge 20.1 mm.

Nothing here touches MuJoCo. It drives `HiwonderActuatorModel` directly, so it
runs anywhere and measures the actuator chain in isolation:

    python -m tag_mujoco.actuator_authority --output docs/actuator_authority.json

Two behaviours of the model matter when reading the output. Actions saturate at
|action| = 0.75, not 1.0, because the learner scales by 240 and the bridge then
clamps to 180 -- everything above 0.75 is the same command. And the driver
rate-limits to 20 servo units per 30 Hz tick, so a full tilt reversal spans 540
units and cannot complete faster than 0.9 s regardless of what the policy asks
for.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Sequence

import numpy as np

try:
    from .actuator_model import HiwonderActuatorModel
    from .policy_contract import TagPolicyContract
    from .system_config import ActuatorConfig
except ImportError:  # Preserve direct-script execution from this directory.
    from actuator_model import HiwonderActuatorModel
    from policy_contract import TagPolicyContract
    from system_config import ActuatorConfig


# Physics timestep used by the simulator (`model_builder.py` MJCF option).
# The actuator is stepped at this rate inside the control-step loop.
DEFAULT_PHYSICS_DT = 0.001

# Rolling solid sphere on an incline: a = (5/7) g sin(theta). Used to translate
# a board angle into the dynamic limits that actually decide route feasibility.
ROLLING_SPHERE_FACTOR = 5.0 / 7.0
GRAVITY_MPS2 = 9.81

# Observed ball speed range from the 500k nominal pilot, quoted in
# `docs/NOMINAL_AB_ARMS_2026-07-28.md`. Turn radius and stopping distance are
# reported across this range because both scale with v^2.
OBSERVED_SPEEDS_MPS = (0.016, 0.041)


def edge_lift_mm(angle_rad: float, span_m: float) -> float:
    """Return the vertical rise of the board edge for a tilt, in millimetres.

    This is the bench's primary reference: it depends on no camera, no
    estimator, and no code. 1 mm of lift across the 259 mm span is 0.221
    degrees, which is finer than the disagreement being investigated.
    """

    return 1000.0 * span_m * math.tan(float(angle_rad))


def angle_from_edge_lift(lift_mm: float, span_m: float) -> float:
    """Inverse of `edge_lift_mm`, for converting bench readings back to angle."""

    return math.atan((float(lift_mm) / 1000.0) / span_m)


def action_for_command(command: float, config: ActuatorConfig, axis: int = 0) -> float:
    """Return the action that produces a given signed Hiwonder command.

    The learner scales by `policy_command_scale` and applies
    `policy_command_sign`; the bridge clamp is applied afterwards, so commands
    beyond `policy_command_limit` are unreachable and this returns the action
    that lands exactly on the clamp.
    """

    scale = float(config.policy_command_scale[axis])
    sign = float(config.policy_command_sign[axis])
    limit = float(config.policy_command_limit[axis])
    reachable = float(np.clip(command, -limit, limit))
    return reachable / (scale * sign)


def settle(
    model: HiwonderActuatorModel,
    action: Sequence[float],
    dt: float = DEFAULT_PHYSICS_DT,
    maximum_seconds: float = 6.0,
    tolerance_rad: float = 1e-12,
) -> Dict[str, Any]:
    """Hold an action until the board target stops moving.

    The action is re-submitted every step deliberately. `ActuatorConfig` sets
    `command_timeout_seconds` to 1.0 with `timeout_go_home`, and a full tilt
    reversal takes 0.9 s, so a single submit followed by a long step loop would
    silently trip the timeout and drive the model home mid-measurement.
    """

    # Sample over two driver ticks, not one. The driver advances at
    # `update_rate_hz` while this loop steps at `dt`, so a check aligned to a
    # single tick period can land entirely between ticks, observe no change, and
    # declare convergence before the actuator has moved at all.
    tick_steps = max(1, int(math.ceil(1.0 / (model.config.update_rate_hz * dt))))
    check_interval = 2 * tick_steps
    previous = model.board_target_angles
    elapsed = 0.0
    steps = 0
    samples = 0
    while elapsed < maximum_seconds:
        model.submit_action(action)
        current = model.step(dt)
        elapsed += dt
        steps += 1
        if steps % check_interval == 0:
            samples += 1
            if (
                samples >= 2
                and float(np.max(np.abs(current - previous))) <= tolerance_rad
            ):
                break
            previous = current.copy()
    angles = model.board_target_angles
    return {
        "action": [float(value) for value in action],
        "angles_rad": angles.tolist(),
        "angles_deg": [math.degrees(value) for value in angles],
        "servo_positions": model.commanded_servo_positions.tolist(),
        "settle_seconds": elapsed,
        "converged": elapsed < maximum_seconds,
    }


def transition_time_to_fraction(
    config: ActuatorConfig,
    start_action: Sequence[float],
    end_action: Sequence[float],
    fraction: float = 0.9,
    dt: float = DEFAULT_PHYSICS_DT,
    maximum_seconds: float = 6.0,
) -> Dict[str, Any]:
    """Time for the board target to cover `fraction` of a commanded change.

    Reported per axis. The binding constraint is `max_step_per_tick`, not servo
    dynamics: 20 units per 30 Hz tick across a 540-unit full reversal cannot
    complete in under 0.9 s, which is 36.9 mm of ball travel at the observed
    0.041 m/s cruise speed. This is the number that makes bang-bang control the
    rational strategy rather than a pathology.
    """

    model = HiwonderActuatorModel(config)
    settle(model, start_action, dt=dt, maximum_seconds=maximum_seconds)
    start_angles = model.board_target_angles

    probe = HiwonderActuatorModel(config)
    settle(probe, start_action, dt=dt, maximum_seconds=maximum_seconds)
    settle(probe, end_action, dt=dt, maximum_seconds=maximum_seconds)
    end_angles = probe.board_target_angles

    total_change = end_angles - start_angles
    reached = [None, None]
    elapsed = 0.0
    while elapsed < maximum_seconds and any(value is None for value in reached):
        model.submit_action(end_action)
        current = model.step(dt)
        elapsed += dt
        for axis in range(2):
            if reached[axis] is not None:
                continue
            if abs(total_change[axis]) <= 1e-12:
                reached[axis] = 0.0
                continue
            progress = (current[axis] - start_angles[axis]) / total_change[axis]
            if progress >= fraction:
                reached[axis] = elapsed
    return {
        "start_action": [float(value) for value in start_action],
        "end_action": [float(value) for value in end_action],
        "fraction": fraction,
        "start_angles_deg": [math.degrees(value) for value in start_angles],
        "end_angles_deg": [math.degrees(value) for value in end_angles],
        "seconds_per_axis": reached,
        "servo_units_travelled": float(
            np.max(
                np.abs(
                    np.asarray(end_action) - np.asarray(start_action)
                )
            )
            * config.policy_command_scale[0]
            * config.command_scale[0]
        ),
    }


def stiction_dead_band(
    config: ActuatorConfig,
    dt: float = DEFAULT_PHYSICS_DT,
    resolution: float = 0.001,
) -> Dict[str, Any]:
    """Smallest |action| per axis and direction that moves the board at all.

    `stiction_command_positive/negative` are described in `ActuatorConfig` as
    conservative priors rather than measurements, and they are asymmetric per
    axis (10/40 and 40/10). Below these the commanded servo offset produces
    exactly zero board motion, which is a hard floor on fine control that the
    bench should confirm or refute.
    """

    def moves(axis: int, signed_magnitude: float) -> bool:
        action = [0.0, 0.0]
        action[axis] = signed_magnitude
        model = HiwonderActuatorModel(config)
        result = settle(model, action, dt=dt, maximum_seconds=2.0)
        return max(abs(value) for value in result["angles_rad"]) > 1e-12

    bands: Dict[str, Any] = {}
    for axis in range(2):
        for direction, label in ((1.0, "positive"), (-1.0, "negative")):
            # Response is monotonic in |action| -- a larger command produces a
            # larger servo offset and can only cross the stiction threshold,
            # never fall back below it -- so bisect rather than scan.
            if not moves(axis, direction):
                bands[f"axis{axis + 1}_{label}"] = {
                    "first_moving_action": None,
                    "first_moving_command": None,
                }
                continue
            low, high = 0.0, 1.0
            while high - low > resolution:
                middle = 0.5 * (low + high)
                if moves(axis, direction * middle):
                    high = middle
                else:
                    low = middle
            bands[f"axis{axis + 1}_{label}"] = {
                "first_moving_action": high,
                "first_moving_command": high * config.policy_command_scale[axis],
            }
    return bands


def dynamic_limits(angle_rad: float) -> Dict[str, Any]:
    """Lateral acceleration, turn radius and stopping distance for a tilt.

    `docs/NOMINAL_AB_ARMS_2026-07-28.md` rejected "dynamically infeasible
    routes" using 1.22 m/s^2, computed at the assumed 10 degree board limit
    rather than at any measured angle. Recomputing this from whatever the board
    actually reaches is the point of the Monday session.
    """

    acceleration = ROLLING_SPHERE_FACTOR * GRAVITY_MPS2 * math.sin(abs(angle_rad))
    limits: Dict[str, Any] = {
        "board_angle_deg": math.degrees(angle_rad),
        "lateral_acceleration_mps2": acceleration,
    }
    for speed in OBSERVED_SPEEDS_MPS:
        key = f"speed_{speed:.3f}mps"
        if acceleration <= 0.0:
            limits[key] = {"minimum_turn_radius_mm": None, "stopping_distance_mm": None}
            continue
        limits[key] = {
            "minimum_turn_radius_mm": 1000.0 * speed * speed / acceleration,
            "stopping_distance_mm": 1000.0 * speed * speed / (2.0 * acceleration),
        }
    return limits


def sweep(
    config: ActuatorConfig,
    contract: TagPolicyContract,
    dt: float = DEFAULT_PHYSICS_DT,
    points: int = 21,
) -> Dict[str, Any]:
    """Steady-state board angle across the action range, per axis and combined."""

    magnitudes = np.linspace(-1.0, 1.0, points)
    modes = {
        "axis1_only": lambda value: [value, 0.0],
        "axis2_only": lambda value: [0.0, value],
        "both_axes": lambda value: [value, value],
    }
    results: Dict[str, List[Dict[str, Any]]] = {}
    for name, build in modes.items():
        rows = []
        for magnitude in magnitudes:
            action = build(float(magnitude))
            model = HiwonderActuatorModel(config)
            settled = settle(model, action, dt=dt)
            commands = [
                float(
                    np.clip(
                        action[axis]
                        * config.policy_command_scale[axis]
                        * config.policy_command_sign[axis],
                        -config.policy_command_limit[axis],
                        config.policy_command_limit[axis],
                    )
                )
                for axis in range(2)
            ]
            rows.append(
                {
                    "action": action,
                    "commands": commands,
                    "angles_deg": settled["angles_deg"],
                    "edge_lift_mm": [
                        edge_lift_mm(
                            math.radians(settled["angles_deg"][0]),
                            contract.board_width_m,
                        ),
                        edge_lift_mm(
                            math.radians(settled["angles_deg"][1]),
                            contract.board_height_m,
                        ),
                    ],
                    "servo_positions": settled["servo_positions"],
                }
            )
        results[name] = rows
    return results


def command_levels(
    config: ActuatorConfig,
    contract: TagPolicyContract,
    levels: Sequence[float] = (40.0, 80.0, 120.0, 180.0),
    dt: float = DEFAULT_PHYSICS_DT,
) -> List[Dict[str, Any]]:
    """Predictions at the command levels the bench will actually visit.

    40 and 80 were measured in the 2026-07-27 campaign. 120 is
    `protocols.py:HARD_COMMAND_LIMIT`. 180 is the policy's operating point and
    has never been measured.
    """

    rows = []
    for level in levels:
        action_value = action_for_command(level, config)
        action = [action_value, action_value]
        model = HiwonderActuatorModel(config)
        settled = settle(model, action, dt=dt)
        angles_rad = [math.radians(value) for value in settled["angles_deg"]]
        rows.append(
            {
                "command": float(level),
                "action_per_axis": action_value,
                "reachable": abs(level) <= config.policy_command_limit[0],
                "angles_deg": settled["angles_deg"],
                "edge_lift_mm": [
                    edge_lift_mm(angles_rad[0], contract.board_width_m),
                    edge_lift_mm(angles_rad[1], contract.board_height_m),
                ],
                "dynamic_limits": dynamic_limits(max(angles_rad, key=abs)),
            }
        )
    return rows


def authority_envelope(
    config: ActuatorConfig,
    contract: TagPolicyContract,
    dt: float = DEFAULT_PHYSICS_DT,
) -> Dict[str, Any]:
    """Reachable board angles at the four corners of the saturated action square.

    "Maximum tilt" is not a single number here. The identified command maps are
    strongly cross-coupled -- driving both motors positive puts
    `board_rad_per_command_positive` rows 7.950e-5 and -9.535e-5 against each
    other on alpha, which very nearly cancels, while beta adds. So the same
    command magnitude produces 0.16 degrees on one axis and 2.07 on the other
    depending only on the sign combination.

    Route feasibility depends on the worst direction the controller may need,
    not the best, so the per-axis maximum across corners is reported alongside
    the corners themselves. On hardware this is also the cheapest asymmetry to
    check: the four corners have visibly different edge lifts.
    """

    saturation = action_for_command(float(config.policy_command_limit[0]), config)
    corners = []
    for sign_1 in (1.0, -1.0):
        for sign_2 in (1.0, -1.0):
            action = [sign_1 * saturation, sign_2 * saturation]
            model = HiwonderActuatorModel(config)
            settled = settle(model, action, dt=dt)
            angles_rad = [math.radians(value) for value in settled["angles_deg"]]
            corners.append(
                {
                    "action": action,
                    "commands": [
                        float(
                            action[axis]
                            * config.policy_command_scale[axis]
                            * config.policy_command_sign[axis]
                        )
                        for axis in range(2)
                    ],
                    "angles_deg": settled["angles_deg"],
                    "edge_lift_mm": [
                        edge_lift_mm(angles_rad[0], contract.board_width_m),
                        edge_lift_mm(angles_rad[1], contract.board_height_m),
                    ],
                }
            )
    maxima = [
        max(abs(corner["angles_deg"][axis]) for corner in corners) for axis in range(2)
    ]
    return {
        "corners": corners,
        "maximum_abs_angle_deg": maxima,
        "weakest_axis_deg": min(maxima),
        "weakest_axis_dynamic_limits": dynamic_limits(math.radians(min(maxima))),
        "strongest_axis_dynamic_limits": dynamic_limits(math.radians(max(maxima))),
    }


def build_report(
    config: ActuatorConfig | None = None,
    contract: TagPolicyContract | None = None,
    dt: float = DEFAULT_PHYSICS_DT,
) -> Dict[str, Any]:
    """Assemble the full baseline report."""

    config = config or ActuatorConfig()
    contract = contract or TagPolicyContract()

    saturation_action = action_for_command(
        float(config.policy_command_limit[0]), config
    )
    full = [saturation_action, saturation_action]
    home = [0.0, 0.0]

    return {
        "schema_version": 1,
        "method": (
            "simulator baseline; HiwonderActuatorModel driven directly, no MuJoCo. "
            "Predictions only -- this states what the shipped calibration believes, "
            "not what the hardware does."
        ),
        "source": {
            "board_rad_per_command_positive": [
                list(row) for row in config.board_rad_per_command_positive
            ],
            "board_rad_per_command_negative": [
                list(row) for row in config.board_rad_per_command_negative
            ],
            "fitted_at_command": 80.0,
            "applied_at_command": float(config.policy_command_limit[0]),
            "extrapolation_factor": float(config.policy_command_limit[0]) / 80.0,
            "provenance": (
                "camera-derived board angles via IPPE planar PnP; see "
                "docs/sysid_actuator_step80_2026-07-27.json"
            ),
        },
        "geometry": {
            "board_width_m": contract.board_width_m,
            "board_height_m": contract.board_height_m,
            "mm_lift_per_degree_width": edge_lift_mm(
                math.radians(1.0), contract.board_width_m
            ),
            "degrees_per_mm_lift_width": math.degrees(
                angle_from_edge_lift(1.0, contract.board_width_m)
            ),
        },
        "saturation": {
            "action_at_command_limit": saturation_action,
            "note": (
                "Actions saturate at |action| = 0.75 because the learner scales by "
                "240 and the bridge clamps to 180. Above that every action is the "
                "same command."
            ),
        },
        "authority_envelope": authority_envelope(config, contract, dt=dt),
        "command_levels": command_levels(config, contract, dt=dt),
        "sweep": sweep(config, contract, dt=dt),
        "stiction_dead_band": stiction_dead_band(config, dt=dt),
        "timing": {
            "step_from_home": transition_time_to_fraction(config, home, full, dt=dt),
            "half_reversal": transition_time_to_fraction(
                config, home, [-value for value in full], dt=dt
            ),
            "full_reversal": transition_time_to_fraction(
                config, full, [-value for value in full], dt=dt
            ),
        },
    }


def _format_table(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    geometry = report["geometry"]
    lines.append("Simulator actuator authority -- PREDICTIONS, not measurements")
    lines.append(
        f"  calibration fitted at command {report['source']['fitted_at_command']:.0f}, "
        f"applied at {report['source']['applied_at_command']:.0f} "
        f"({report['source']['extrapolation_factor']:.2f}x extrapolation)"
    )
    lines.append(
        f"  board {geometry['board_width_m'] * 1000:.0f} x "
        f"{geometry['board_height_m'] * 1000:.0f} mm; "
        f"1 deg = {geometry['mm_lift_per_degree_width']:.1f} mm lift, "
        f"1 mm lift = {geometry['degrees_per_mm_lift_width']:.3f} deg"
    )
    lines.append("")
    envelope = report["authority_envelope"]
    lines.append("Authority envelope at saturation (four action-square corners)")
    lines.append(
        f"  {'cmd1':>6} {'cmd2':>6} {'axis1 deg':>10} {'axis2 deg':>10} "
        f"{'lift1 mm':>9} {'lift2 mm':>9}"
    )
    for corner in envelope["corners"]:
        lines.append(
            f"  {corner['commands'][0]:6.0f} {corner['commands'][1]:6.0f} "
            f"{corner['angles_deg'][0]:10.3f} {corner['angles_deg'][1]:10.3f} "
            f"{corner['edge_lift_mm'][0]:9.2f} {corner['edge_lift_mm'][1]:9.2f}"
        )
    lines.append(
        f"  max |angle| per axis: {envelope['maximum_abs_angle_deg'][0]:.3f} deg, "
        f"{envelope['maximum_abs_angle_deg'][1]:.3f} deg"
    )
    weakest = envelope["weakest_axis_dynamic_limits"]
    strongest = envelope["strongest_axis_dynamic_limits"]
    lines.append(
        f"  weakest axis {weakest['board_angle_deg']:.3f} deg -> "
        f"a = {weakest['lateral_acceleration_mps2']:.4f} m/s2; "
        f"strongest {strongest['board_angle_deg']:.3f} deg -> "
        f"a = {strongest['lateral_acceleration_mps2']:.4f} m/s2"
    )
    for label, entry in (("weakest", weakest), ("strongest", strongest)):
        fast = entry[f"speed_{OBSERVED_SPEEDS_MPS[1]:.3f}mps"]
        if fast["minimum_turn_radius_mm"] is not None:
            lines.append(
                f"    {label} @ {OBSERVED_SPEEDS_MPS[1]:.3f} m/s: "
                f"turn radius {fast['minimum_turn_radius_mm']:.1f} mm, "
                f"stopping {fast['stopping_distance_mm']:.1f} mm"
            )
    lines.append("")
    lines.append("Command levels (both axes driven together)")
    lines.append(
        f"  {'cmd':>5} {'action':>7} {'axis1 deg':>10} {'axis2 deg':>10} "
        f"{'lift1 mm':>9} {'lift2 mm':>9} {'a m/s2':>8}"
    )
    for row in report["command_levels"]:
        marker = "" if row["reachable"] else "  (clamped)"
        lines.append(
            f"  {row['command']:5.0f} {row['action_per_axis']:7.4f} "
            f"{row['angles_deg'][0]:10.3f} {row['angles_deg'][1]:10.3f} "
            f"{row['edge_lift_mm'][0]:9.2f} {row['edge_lift_mm'][1]:9.2f} "
            f"{row['dynamic_limits']['lateral_acceleration_mps2']:8.4f}{marker}"
        )
    lines.append("")
    lines.append("Transition timing (seconds to 90% of commanded change)")
    for name, entry in report["timing"].items():
        seconds = entry["seconds_per_axis"]
        rendered = ", ".join(
            "n/a" if value is None else f"{value:.3f}s" for value in seconds
        )
        lines.append(f"  {name:16s} {rendered}")
    lines.append("")
    lines.append("Stiction dead band (smallest action producing any board motion)")
    for key, entry in report["stiction_dead_band"].items():
        action = entry["first_moving_action"]
        command = entry["first_moving_command"]
        if action is None:
            lines.append(f"  {key:18s} no motion at any action")
        else:
            lines.append(
                f"  {key:18s} |action| >= {action:.3f}  (command {command:.1f})"
            )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, help="Write the machine-readable report here."
    )
    parser.add_argument(
        "--dt",
        type=float,
        default=DEFAULT_PHYSICS_DT,
        help="Integration step for the actuator model (default: simulator physics dt).",
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Suppress the human-readable table."
    )
    args = parser.parse_args(argv)

    report = build_report(dt=args.dt)
    if not args.quiet:
        print(_format_table(report))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        if not args.quiet:
            print(f"\nWrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
