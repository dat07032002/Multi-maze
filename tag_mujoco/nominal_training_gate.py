"""Decision and mastery gates for nominal full-start training."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping


def evaluate_nominal_gate(
    baseline: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    minimum_mastery_episodes: int = 192,
) -> dict[str, Any]:
    """Evaluate bounded continuation and nominal-mastery criteria."""

    baseline_summary = baseline["summary"]
    candidate_summary = candidate["summary"]
    completion_gain = float(candidate_summary["completion_rate"]) - float(
        baseline_summary["completion_rate"]
    )
    fall_reduction = float(baseline_summary["fall_rate"]) - float(
        candidate_summary["fall_rate"]
    )

    baseline_hard = baseline.get("by_difficulty", {}).get("hard")
    candidate_hard = candidate.get("by_difficulty", {}).get("hard")
    hard_progress_change = None
    hard_retention = False
    hard_completion = None
    if baseline_hard is not None and candidate_hard is not None:
        hard_progress_change = float(
            candidate_hard["mean_max_route_completion"]
        ) - float(baseline_hard["mean_max_route_completion"])
        hard_retention = hard_progress_change >= -0.05
        hard_completion = float(candidate_hard["completion_rate"])

    bands = candidate.get("by_difficulty", {})
    band_completion = {
        str(name): float(values["completion_rate"])
        for name, values in bands.items()
    }
    minimum_band_completion = (
        min(band_completion.values()) if band_completion else None
    )
    episodes = int(candidate_summary["episodes"])
    pilot_improved = completion_gain >= 0.03 or fall_reduction >= 0.03
    continue_nominal = episodes >= 64 and pilot_improved and hard_retention

    mastery_checks = {
        "confirmation_episodes": episodes >= minimum_mastery_episodes,
        "overall_completion": float(candidate_summary["completion_rate"]) >= 0.90,
        "overall_falls": float(candidate_summary["fall_rate"]) <= 0.10,
        "overall_max_progress": (
            float(candidate_summary["mean_max_route_completion"]) >= 0.95
        ),
        "hard_completion": (
            hard_completion is not None and hard_completion >= 0.80
        ),
        "all_band_completion": (
            minimum_band_completion is not None
            and minimum_band_completion >= 0.75
        ),
    }
    mastery_passed = all(mastery_checks.values())
    return {
        "schema_version": 1,
        "passed": mastery_passed,
        "continue_nominal": continue_nominal,
        "criteria": {
            "bounded_pilot": {
                "passed": continue_nominal,
                "completion_gain": completion_gain,
                "fall_rate_reduction": fall_reduction,
                "required_either": 0.03,
                "hard_max_progress_change": hard_progress_change,
                "minimum_hard_progress_change": -0.05,
                "minimum_episodes": 64,
            },
            "nominal_mastery": {
                "passed": mastery_passed,
                "checks": mastery_checks,
                "episodes": episodes,
                "minimum_mastery_episodes": minimum_mastery_episodes,
                "completion_rate": float(candidate_summary["completion_rate"]),
                "maximum_fall_rate": 0.10,
                "fall_rate": float(candidate_summary["fall_rate"]),
                "mean_max_route_completion": float(
                    candidate_summary["mean_max_route_completion"]
                ),
                "hard_completion_rate": hard_completion,
                "minimum_band_completion_rate": minimum_band_completion,
                "band_completion_rates": band_completion,
            },
        },
    }


def _read(path: Path) -> dict[str, Any]:
    result = json.loads(path.read_text(encoding="utf-8"))
    if not result.get("completed", False):
        raise ValueError(f"Evaluation is incomplete: {path}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--minimum-mastery-episodes", type=int, default=192)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.minimum_mastery_episodes < 64:
        parser.error("--minimum-mastery-episodes must be at least 64")

    result = evaluate_nominal_gate(
        _read(args.baseline),
        _read(args.candidate),
        minimum_mastery_episodes=args.minimum_mastery_episodes,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
