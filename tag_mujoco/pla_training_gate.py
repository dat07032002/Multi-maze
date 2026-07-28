"""Decision gate for bounded PLA adaptation experiments."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping


def evaluate_gate(
    baseline_canonical: Mapping[str, Any],
    baseline_robust: Mapping[str, Any],
    candidate_canonical: Mapping[str, Any],
    candidate_robust: Mapping[str, Any],
) -> dict[str, Any]:
    def metric(result: Mapping[str, Any], name: str) -> float:
        return float(result["summary"][name])

    robust_completion_gain = metric(
        candidate_robust, "completion_rate"
    ) - metric(baseline_robust, "completion_rate")
    robust_fall_reduction = metric(
        baseline_robust, "fall_rate"
    ) - metric(candidate_robust, "fall_rate")
    canonical_completion_change = metric(
        candidate_canonical, "completion_rate"
    ) - metric(baseline_canonical, "completion_rate")

    baseline_hard = baseline_canonical.get("by_difficulty", {}).get("hard")
    candidate_hard = candidate_canonical.get("by_difficulty", {}).get("hard")
    hard_progress_change = None
    hard_progress_pass = False
    if baseline_hard is not None and candidate_hard is not None:
        hard_progress_change = float(
            candidate_hard["mean_max_route_completion"]
        ) - float(baseline_hard["mean_max_route_completion"])
        hard_progress_pass = hard_progress_change >= -0.05

    robust_pass = robust_completion_gain >= 0.05 or robust_fall_reduction >= 0.05
    canonical_pass = canonical_completion_change >= -0.03
    passed = robust_pass and canonical_pass and hard_progress_pass
    return {
        "schema_version": 1,
        "passed": passed,
        "criteria": {
            "robust_improvement": {
                "passed": robust_pass,
                "completion_gain": robust_completion_gain,
                "fall_rate_reduction": robust_fall_reduction,
                "required_either": 0.05,
            },
            "canonical_retention": {
                "passed": canonical_pass,
                "completion_change": canonical_completion_change,
                "minimum_change": -0.03,
            },
            "hard_band_retention": {
                "passed": hard_progress_pass,
                "mean_max_route_completion_change": hard_progress_change,
                "minimum_change": -0.05,
            },
        },
    }


def _read(path: Path) -> dict[str, Any]:
    result = json.loads(path.read_text(encoding="utf-8"))
    if not result.get("completed", False):
        raise ValueError(f"Evaluation is incomplete: {path}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-canonical", type=Path, required=True)
    parser.add_argument("--baseline-robust", type=Path, required=True)
    parser.add_argument("--candidate-canonical", type=Path, required=True)
    parser.add_argument("--candidate-robust", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = evaluate_gate(
        _read(args.baseline_canonical),
        _read(args.baseline_robust),
        _read(args.candidate_canonical),
        _read(args.candidate_robust),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
