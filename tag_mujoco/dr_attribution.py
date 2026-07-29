"""Rank causal DR-family effects and scalar associations from policy evaluations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np


def _rank(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=np.float64)
    ranks[order] = np.arange(len(values), dtype=np.float64)
    for value in np.unique(values):
        mask = values == value
        ranks[mask] = float(np.mean(ranks[mask]))
    return ranks


def _spearman(left: list[float], right: list[float]) -> float | None:
    if len(left) < 8:
        return None
    x = _rank(np.asarray(left, dtype=np.float64))
    y = _rank(np.asarray(right, dtype=np.float64))
    if np.std(x) == 0.0 or np.std(y) == 0.0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def build_report(results: list[dict[str, Any]]) -> dict[str, Any]:
    canonical = next(item for item in results if item["mode"] == "canonical")
    baseline = canonical["summary"]
    family_impacts = []
    all_result = None
    for result in results:
        if result["mode"] != "robust":
            continue
        group = result["randomization_groups"]
        if group == "all":
            all_result = result
        summary = result["summary"]
        family_impacts.append(
            {
                "group": group,
                "completion_rate": summary["completion_rate"],
                "fall_rate": summary["fall_rate"],
                "mean_max_route_completion": summary[
                    "mean_max_route_completion"
                ],
                "delta_completion": (
                    summary["completion_rate"] - baseline["completion_rate"]
                ),
                "delta_fall": summary["fall_rate"] - baseline["fall_rate"],
                "delta_progress": (
                    summary["mean_max_route_completion"]
                    - baseline["mean_max_route_completion"]
                ),
            }
        )
    family_impacts.sort(
        key=lambda item: (
            item["delta_completion"],
            item["delta_progress"],
            -item["delta_fall"],
        )
    )

    scalar_associations = []
    if all_result is not None:
        episodes = all_result["episodes"]
        names = sorted(
            {
                name
                for episode in episodes
                for name in episode.get("domain_randomization", {})
            }
        )
        for name in names:
            values = [
                float(episode["domain_randomization"][name])
                for episode in episodes
            ]
            association = {
                "parameter": name,
                "spearman_success": _spearman(
                    values, [float(item["success"]) for item in episodes]
                ),
                "spearman_fall": _spearman(
                    values, [float(item["fall"]) for item in episodes]
                ),
                "spearman_progress": _spearman(
                    values,
                    [float(item["max_route_completion"]) for item in episodes],
                ),
                "sample_min": min(values),
                "sample_max": max(values),
            }
            scalar_associations.append(association)
        scalar_associations.sort(
            key=lambda item: abs(item["spearman_progress"] or 0.0),
            reverse=True,
        )

    return {
        "schema_version": 1,
        "checkpoint": canonical["checkpoint"],
        "checkpoint_sha256": canonical["checkpoint_sha256"],
        "trigger_step": canonical["trigger_step"],
        "split": canonical["split"],
        "seed": canonical["seed"],
        "randomization_strength": (
            all_result["randomization_strength"] if all_result else None
        ),
        "canonical": baseline,
        "family_impacts_worst_first": family_impacts,
        # These diagnose individual values but are observational. Family
        # ablations above are the causal result.
        "scalar_associations_observational": scalar_associations,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    results = [
        json.loads(path.read_text(encoding="utf-8")) for path in args.input
    ]
    report = build_report(results)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["family_impacts_worst_first"], indent=2))


if __name__ == "__main__":
    main()
