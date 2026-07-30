"""Promotion gate for one-online-map-at-a-time training stages."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping


def evaluate_map_gate(
    candidate: Mapping[str, Any],
    *,
    skill_gate: Mapping[str, Any],
    retention_baseline: Mapping[str, Any] | None = None,
    retention_candidate: Mapping[str, Any] | None = None,
    minimum_episodes: int = 20,
) -> dict[str, Any]:
    summary = candidate["summary"]
    checks = {
        "episodes": int(summary["episodes"]) >= minimum_episodes,
        "completion": float(summary["completion_rate"]) >= 0.90,
        "falls": float(summary["fall_rate"]) <= 0.10,
        "progress": float(summary["mean_max_route_completion"]) >= 0.95,
        "universal_skills": bool(skill_gate.get("passed", False)),
    }
    retention = None
    if bool(retention_baseline) != bool(retention_candidate):
        raise ValueError("Both retention reports must be supplied together")
    if retention_baseline is not None and retention_candidate is not None:
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
            "maximum_completion_loss": 0.05,
            "maximum_progress_loss": 0.02,
            "passed": (
                completion_delta >= -0.05 - 1e-12
                and progress_delta >= -0.02 - 1e-12
            ),
        }
        checks["prior_map_retention"] = retention["passed"]
    return {
        "schema_version": 1,
        "gate": "sequential_map",
        "passed": all(checks.values()),
        "checks": checks,
        "thresholds": {
            "minimum_episodes": minimum_episodes,
            "completion_rate": 0.90,
            "maximum_fall_rate": 0.10,
            "mean_max_route_completion": 0.95,
        },
        "metrics": {
            "episodes": int(summary["episodes"]),
            "completion_rate": float(summary["completion_rate"]),
            "fall_rate": float(summary["fall_rate"]),
            "mean_max_route_completion": float(
                summary["mean_max_route_completion"]
            ),
        },
        "retention": retention,
    }


def _read(path: Path, *, require_summary: bool = True) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("completed") is False:
        raise ValueError(f"Evaluation is incomplete: {path}")
    if require_summary and "summary" not in value:
        raise ValueError(f"Evaluation has no summary: {path}")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--skill-gate", type=Path, required=True)
    parser.add_argument("--retention-baseline", type=Path)
    parser.add_argument("--retention-candidate", type=Path)
    parser.add_argument("--minimum-episodes", type=int, default=20)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate_map_gate(
        _read(args.candidate),
        skill_gate=_read(args.skill_gate, require_summary=False),
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
