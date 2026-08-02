"""Promotion gate for universal skill-course checkpoints."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

try:
    from .gate_criteria import MAXIMUM_COMPLETION_LOSS, MAXIMUM_PROGRESS_LOSS
except ImportError:
    from gate_criteria import MAXIMUM_COMPLETION_LOSS, MAXIMUM_PROGRESS_LOSS


SKILL_THRESHOLDS = {
    "stabilize": {"completion": 0.95, "falls": 0.05, "progress": 0.95},
    "straight": {"completion": 0.95, "falls": 0.05, "progress": 0.95},
    "turn": {"completion": 0.95, "falls": 0.05, "progress": 0.95},
    "compound": {"completion": 0.90, "falls": 0.05, "progress": 0.95},
    "recovery": {"completion": 0.90, "falls": 0.05, "progress": 0.95},
    "hazard": {"completion": 0.90, "falls": 0.05, "progress": 0.95},
}


def evaluate_skill_gate(
    reports: Mapping[str, Mapping[str, Any]],
    *,
    minimum_episodes: int = 12,
    retention_baselines: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    unknown = set(reports).difference(SKILL_THRESHOLDS)
    if unknown:
        raise ValueError(f"Unknown skill reports: {sorted(unknown)}")
    if not reports:
        raise ValueError("At least one skill report is required")
    retention_baselines = retention_baselines or {}
    results = {}
    all_passed = True
    for skill, report in sorted(reports.items()):
        summary = report["summary"]
        limits = SKILL_THRESHOLDS[skill]
        checks = {
            "episodes": int(summary["episodes"]) >= minimum_episodes,
            "completion": float(summary["completion_rate"]) >= limits["completion"],
            "falls": float(summary["fall_rate"]) <= limits["falls"],
            "progress": float(summary["mean_max_route_completion"]) >= limits["progress"],
        }
        retention = None
        if skill in retention_baselines:
            baseline = retention_baselines[skill]["summary"]
            completion_delta = float(summary["completion_rate"]) - float(
                baseline["completion_rate"]
            )
            progress_delta = float(summary["mean_max_route_completion"]) - float(
                baseline["mean_max_route_completion"]
            )
            retention = {
                "completion_delta": completion_delta,
                "progress_delta": progress_delta,
                "maximum_completion_loss": MAXIMUM_COMPLETION_LOSS,
                "maximum_progress_loss": MAXIMUM_PROGRESS_LOSS,
            }
            retention["passed"] = (
                completion_delta >= -MAXIMUM_COMPLETION_LOSS - 1e-12
                and progress_delta >= -MAXIMUM_PROGRESS_LOSS - 1e-12
            )
            checks["retention"] = retention["passed"]
        passed = all(checks.values())
        all_passed = all_passed and passed
        results[skill] = {
            "passed": passed,
            "checks": checks,
            "thresholds": limits,
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
    return {
        "schema_version": 1,
        "gate": "universal_skill",
        "passed": all_passed,
        "minimum_episodes_per_skill": minimum_episodes,
        "skills": results,
    }


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("completed") is False:
        raise ValueError(f"Evaluation is incomplete: {path}")
    if "summary" not in value:
        raise ValueError(f"Evaluation has no summary: {path}")
    return value


def _named_reports(values: list[str]) -> dict[str, dict[str, Any]]:
    result = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"Expected SKILL=REPORT syntax: {value!r}")
        skill, filename = value.split("=", 1)
        if skill in result:
            raise ValueError(f"Duplicate skill report: {skill}")
        result[skill] = _read(Path(filename))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="append", required=True, metavar="SKILL=JSON")
    parser.add_argument("--retention-baseline", action="append", default=[], metavar="SKILL=JSON")
    parser.add_argument("--minimum-episodes", type=int, default=12)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate_skill_gate(
        _named_reports(args.report),
        minimum_episodes=args.minimum_episodes,
        retention_baselines=_named_reports(args.retention_baseline),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
