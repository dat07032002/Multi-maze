"""Pure helpers for aggregating held-out TAG policy evaluations."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Iterable, Mapping

import numpy as np


def evaluation_env_overrides(
    mode: str,
    randomization_strength: float | None = None,
    randomization_groups: str = "all",
) -> dict[str, bool | float | str]:
    """Return comparable environment settings for held-out evaluation."""

    if mode not in {"canonical", "robust"}:
        raise ValueError(f"Unsupported evaluation mode: {mode}")
    robust = mode == "robust"
    if randomization_strength is not None:
        randomization_strength = float(randomization_strength)
        if not robust:
            raise ValueError(
                "A randomization strength is only valid for robust evaluation"
            )
        if not 0.0 < randomization_strength <= 1.0:
            raise ValueError("Randomization strength must be in (0, 1]")
    overrides: dict[str, bool | float | str] = {
        "maze_manifest": "",
        "maze_split": "",
        "maze_sampling": "uniform",
        # Both protocols measure the full task. Robustness only changes the
        # plant, not the amount of route the policy is required to solve.
        "random_start": False,
        "continuous_path": False,
        "continuous_curriculum": False,
        "randomize_plant": robust,
        "start_curriculum": False,
        "randomization_curriculum": False,
        "randomization_groups": randomization_groups,
    }
    if robust and randomization_strength is not None:
        # Reuse the curriculum interpolation machinery as a fixed-strength
        # sampler. A zero expansion step prevents the value from changing.
        overrides.update(
            {
                "randomization_curriculum": True,
                "randomization_initial_strength": randomization_strength,
                "randomization_expand_step": 0.0,
            }
        )
    return overrides


def _mean(values: Iterable[float]) -> float | None:
    finite = [float(value) for value in values if np.isfinite(value)]
    return float(np.mean(finite)) if finite else None


def episode_record(
    episode: Mapping[str, np.ndarray],
    *,
    layout: str,
    layout_seed: int,
    difficulty_score: float,
    difficulty_band: str,
    evaluation_seed: int,
) -> dict[str, Any]:
    """Convert one Embodied episode into stable navigation metrics."""

    rewards = np.asarray(episode["reward"], dtype=np.float64)
    progress = np.asarray(episode["log_progress"], dtype=np.float64).reshape(-1)
    cross_track = np.asarray(
        episode["log_cross_track_error"], dtype=np.float64
    ).reshape(-1)
    clearance_cost = np.asarray(
        episode["log_clearance_cost"], dtype=np.float64
    ).reshape(-1)
    min_clearance = np.asarray(
        episode["log_min_clearance"], dtype=np.float64
    ).reshape(-1)
    success = bool(np.asarray(episode["log_success"]).sum() > 0.0)
    fall = bool(np.asarray(episode["log_fall_cost"]).sum() > 0.0)
    actions = np.asarray(episode["action"], dtype=np.float64)
    if not np.all(np.isfinite(actions)):
        raise ValueError(f"Policy emitted a non-finite action on {layout}")

    if success:
        reason = "goal_reached"
    elif fall:
        reason = "ball_fell"
    else:
        reason = "time_limit"

    record = {
        "layout": layout,
        "layout_seed": int(layout_seed),
        "difficulty_score": float(difficulty_score),
        "difficulty_band": str(difficulty_band),
        "evaluation_seed": int(evaluation_seed),
        "success": success,
        "fall": fall,
        "termination_reason": reason,
        "steps": int(max(0, len(rewards) - 1)),
        "return": float(rewards.sum()),
        "final_route_completion": float(progress[-1]),
        "max_route_completion": float(np.max(progress)),
        "mean_cross_track_error_m": _mean(cross_track),
        "mean_clearance_cost": _mean(clearance_cost),
        "minimum_clearance_m": float(np.min(min_clearance)),
    }
    record["domain_randomization"] = {
        key.removeprefix("log_"): float(np.asarray(value).reshape(-1)[0])
        for key, value in episode.items()
        if key.startswith("log_dr_")
    }
    return record


def _aggregate(records: list[Mapping[str, Any]]) -> dict[str, Any]:
    successful_steps = [item["steps"] for item in records if item["success"]]
    return {
        "episodes": len(records),
        "completion_rate": _mean(float(item["success"]) for item in records),
        "fall_rate": _mean(float(item["fall"]) for item in records),
        "mean_max_route_completion": _mean(
            item["max_route_completion"] for item in records
        ),
        "mean_final_route_completion": _mean(
            item["final_route_completion"] for item in records
        ),
        "mean_cross_track_error_m": _mean(
            item["mean_cross_track_error_m"]
            for item in records
            if item["mean_cross_track_error_m"] is not None
        ),
        "minimum_clearance_m": (
            min(float(item["minimum_clearance_m"]) for item in records)
            if records
            else None
        ),
        "mean_return": _mean(item["return"] for item in records),
        "mean_steps_to_goal": _mean(successful_steps),
    }


def summarize_records(records: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Aggregate overall and per-difficulty metrics."""

    by_band: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for record in records:
        by_band[str(record["difficulty_band"])].append(record)
    return {
        "summary": _aggregate(records),
        "by_difficulty": {
            band: _aggregate(items) for band, items in sorted(by_band.items())
        },
    }


def _record_key(record: Mapping[str, Any]) -> tuple[str, int]:
    return str(record["layout"]), int(record["evaluation_seed"])


def _exact_two_sided_binomial_pvalue(successes: int, trials: int) -> float | None:
    if trials <= 0:
        return None
    observed = min(successes, trials - successes)
    probability = 0.0
    for count in range(observed + 1):
        probability += math.comb(trials, count) * (0.5 ** trials)
    return float(min(1.0, 2.0 * probability))


def paired_comparison(
    baseline_records: list[Mapping[str, Any]],
    candidate_records: list[Mapping[str, Any]],
    *,
    bootstrap_samples: int = 20000,
    seed: int = 0,
) -> dict[str, Any]:
    """Compare two evaluations on matched ``(layout, evaluation_seed)`` pairs."""

    baseline_by_key = {_record_key(record): record for record in baseline_records}
    candidate_by_key = {_record_key(record): record for record in candidate_records}
    keys = sorted(set(baseline_by_key).intersection(candidate_by_key))
    if not keys:
        raise ValueError("Paired comparison requires at least one matched record")

    base_success = np.asarray(
        [bool(baseline_by_key[key]["success"]) for key in keys], dtype=np.bool_
    )
    cand_success = np.asarray(
        [bool(candidate_by_key[key]["success"]) for key in keys], dtype=np.bool_
    )
    base_fall = np.asarray(
        [bool(baseline_by_key[key]["fall"]) for key in keys], dtype=np.bool_
    )
    cand_fall = np.asarray(
        [bool(candidate_by_key[key]["fall"]) for key in keys], dtype=np.bool_
    )
    base_progress = np.asarray(
        [float(baseline_by_key[key]["max_route_completion"]) for key in keys],
        dtype=np.float64,
    )
    cand_progress = np.asarray(
        [float(candidate_by_key[key]["max_route_completion"]) for key in keys],
        dtype=np.float64,
    )
    progress_delta = cand_progress - base_progress

    success_gained = int(np.logical_and(~base_success, cand_success).sum())
    success_lost = int(np.logical_and(base_success, ~cand_success).sum())
    fall_gained = int(np.logical_and(~base_fall, cand_fall).sum())
    fall_removed = int(np.logical_and(base_fall, ~cand_fall).sum())

    rng = np.random.default_rng(seed)
    sample_count = max(0, int(bootstrap_samples))
    if sample_count:
        indices = rng.integers(0, len(keys), size=(sample_count, len(keys)))
        means = progress_delta[indices].mean(axis=1)
        progress_ci = np.quantile(means, [0.025, 0.975]).astype(float).tolist()
        progress_p_mean_negative = float(np.mean(means < 0.0))
    else:
        progress_ci = None
        progress_p_mean_negative = None

    return {
        "schema_version": 1,
        "paired_episodes": len(keys),
        "unpaired_baseline": len(baseline_by_key) - len(keys),
        "unpaired_candidate": len(candidate_by_key) - len(keys),
        "success_mcnemar": {
            "gained": success_gained,
            "lost": success_lost,
            "exact_two_sided_p": _exact_two_sided_binomial_pvalue(
                success_gained, success_gained + success_lost
            ),
        },
        "fall_mcnemar": {
            "gained": fall_gained,
            "removed": fall_removed,
            "exact_two_sided_p": _exact_two_sided_binomial_pvalue(
                fall_gained, fall_gained + fall_removed
            ),
        },
        "progress_bootstrap": {
            "mean_delta": float(progress_delta.mean()),
            "median_delta": float(np.median(progress_delta)),
            "positive_pairs": int((progress_delta > 0.0).sum()),
            "negative_pairs": int((progress_delta < 0.0).sum()),
            "unchanged_pairs": int((progress_delta == 0.0).sum()),
            "mean_delta_95ci": progress_ci,
            "p_mean_delta_negative": progress_p_mean_negative,
            "bootstrap_samples": sample_count,
            "seed": int(seed),
        },
    }
