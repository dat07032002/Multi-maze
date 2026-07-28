"""Quality-gate a real trajectory fit and activate it for TAG simulation."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
DEFAULT_OUTPUT = HERE / "identified_dynamics.json"


def build_override(fit, source="", force=False, ball_radius_m=0.006):
    quality = fit["quality_gate"]
    if not quality["free_roll_usable"] and not force:
        raise ValueError(
            "Free-roll quality gate failed: " + "; ".join(quality["warnings"])
        )
    free_roll = fit["free_roll"]
    rolling_mu = float(free_roll["rolling_resistance_mps2"]) / 9.81
    rolling_length_m = rolling_mu * float(ball_radius_m)
    restitution = fit["wall_impacts"]["median"]
    restitution_usable = quality["restitution_usable"] and restitution is not None
    result = {
        "schema_version": 1,
        "active": True,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source_fit": str(source),
        "forced_below_quality_gate": bool(force and not quality["free_roll_usable"]),
        "linear_ball_damping_per_second": {
            "value": float(free_roll["linear_damping_per_second"]),
            "range": [
                0.6 * float(free_roll["linear_damping_per_second"]),
                1.4 * float(free_roll["linear_damping_per_second"]),
            ],
        },
        "rolling_resistance_coefficient": {
            "value": rolling_mu,
            "range": [0.5 * rolling_mu, 1.5 * rolling_mu],
            "unit": "dimensionless",
        },
        "rolling_friction_length_m": {
            "value": rolling_length_m,
            "range": [0.5 * rolling_length_m, 1.5 * rolling_length_m],
            "unit": "m",
            "derivation": "rolling resistance coefficient multiplied by ball radius",
        },
        "wall_restitution": {
            "value": float(restitution) if restitution_usable else None,
            "range": (
                [
                    float(fit["wall_impacts"]["p10"]),
                    float(fit["wall_impacts"]["p90"]),
                ]
                if restitution_usable
                else None
            ),
            "applied": bool(restitution_usable),
        },
        "tilt_acceleration_mps2_per_rad": free_roll[
            "tilt_acceleration_mps2_per_rad"
        ],
        "fit_quality": quality,
    }
    return result


def main(args=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fit", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--ball-radius-m", type=float, default=0.006)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Activate a below-threshold free-roll fit and mark it forced.",
    )
    parsed = parser.parse_args(args)
    fit = json.loads(parsed.fit.read_text(encoding="utf-8"))
    result = build_override(
        fit,
        source=parsed.fit.resolve(),
        force=parsed.force,
        ball_radius_m=parsed.ball_radius_m,
    )
    parsed.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"Wrote {parsed.output}; new simulator processes will load it.")


if __name__ == "__main__":
    main()
