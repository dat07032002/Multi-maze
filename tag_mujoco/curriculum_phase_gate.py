"""Promotion gates for the paired no-hole-to-hole curriculum."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

try:
    from .gate_criteria import MAXIMUM_COMPLETION_LOSS, MAXIMUM_PROGRESS_LOSS
except ImportError:
    from gate_criteria import MAXIMUM_COMPLETION_LOSS, MAXIMUM_PROGRESS_LOSS


CRITERIA = {
    1: dict(completion=0.80, falls=0.05, progress=0.90, band=0.70),
    2: dict(completion=0.90, falls=0.05, progress=0.95, band=0.85),
    3: dict(completion=0.90, falls=0.10, progress=0.94, band=0.80),
    4: dict(completion=0.80, falls=0.15, progress=0.90, band=0.70),
    5: dict(completion=0.90, falls=0.10, progress=0.95, band=0.85),
}


def evaluate_phase_gate(
    phase: int,
    candidate: Mapping[str, Any],
    *,
    retention_baseline: Mapping[str, Any] | None = None,
    retention_candidate: Mapping[str, Any] | None = None,
    minimum_episodes: int = 192,
) -> dict[str, Any]:
    """Evaluate mastery plus optional previous-phase retention."""

    if phase not in CRITERIA:
        raise ValueError(f"Phase must be in {sorted(CRITERIA)}")
    limits = CRITERIA[phase]
    summary = candidate["summary"]
    band_rates = {
        str(name): float(values["completion_rate"])
        for name, values in candidate.get("by_difficulty", {}).items()
    }
    minimum_band = min(band_rates.values()) if band_rates else None
    checks = {
        "episodes": int(summary["episodes"]) >= minimum_episodes,
        "completion": float(summary["completion_rate"]) >= limits["completion"],
        "falls": float(summary["fall_rate"]) <= limits["falls"],
        "progress": (
            float(summary["mean_max_route_completion"]) >= limits["progress"]
        ),
        "difficulty_bands": (
            minimum_band is not None and minimum_band >= limits["band"]
        ),
    }

    retention = None
    if phase >= 3:
        if retention_baseline is None or retention_candidate is None:
            checks["retention_evaluated"] = False
        else:
            baseline = retention_baseline["summary"]
            current = retention_candidate["summary"]
            completion_delta = float(current["completion_rate"]) - float(
                baseline["completion_rate"]
            )
            progress_delta = float(current["mean_max_route_completion"]) - float(
                baseline["mean_max_route_completion"]
            )
            retention = {
                "completion_delta": completion_delta,
                "progress_delta": progress_delta,
                "maximum_completion_loss": MAXIMUM_COMPLETION_LOSS,
                "maximum_progress_loss": MAXIMUM_PROGRESS_LOSS,
                "passed": (
                    completion_delta >= -MAXIMUM_COMPLETION_LOSS
                    and progress_delta >= -MAXIMUM_PROGRESS_LOSS
                ),
            }
            checks["retention_evaluated"] = True
            checks["retention"] = retention["passed"]

    return {
        "schema_version": 1,
        "phase": phase,
        "passed": all(checks.values()),
        "checks": checks,
        "thresholds": limits,
        "metrics": {
            "episodes": int(summary["episodes"]),
            "completion_rate": float(summary["completion_rate"]),
            "fall_rate": float(summary["fall_rate"]),
            "mean_max_route_completion": float(
                summary["mean_max_route_completion"]
            ),
            "minimum_band_completion": minimum_band,
            "band_completion_rates": band_rates,
        },
        "retention": retention,
    }


def _read(path: Path) -> dict[str, Any]:
    result = json.loads(path.read_text(encoding="utf-8"))
    if not result.get("completed", False):
        raise ValueError(f"Evaluation is incomplete: {path}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", type=int, choices=sorted(CRITERIA), required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--retention-baseline", type=Path)
    parser.add_argument("--retention-candidate", type=Path)
    parser.add_argument("--minimum-episodes", type=int, default=192)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if bool(args.retention_baseline) != bool(args.retention_candidate):
        parser.error("Both retention evaluation paths must be provided together")
    result = evaluate_phase_gate(
        args.phase,
        _read(args.candidate),
        retention_baseline=(
            _read(args.retention_baseline) if args.retention_baseline else None
        ),
        retention_candidate=(
            _read(args.retention_candidate) if args.retention_candidate else None
        ),
        minimum_episodes=args.minimum_episodes,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
