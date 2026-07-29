"""Dreamer training, plateau, and policy weakness monitoring helpers."""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


CORE_TRAIN_KEYS = (
    "train/model_opt_loss",
    "train/actor_opt_loss",
    "train/extr_critic_critic_opt_loss",
    "train/model_opt_grad_norm",
    "train/actor_opt_grad_norm",
    "train/extr_critic_critic_opt_grad_norm",
)


@dataclass(frozen=True)
class PlateauConfig:
    patience: int = 3
    min_completion_delta: float = 0.01
    min_route_delta: float = 0.005
    max_fall_delta: float = 0.005


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                rows.append(item)
    return rows


def _is_nonfinite(value: Any) -> bool:
    return isinstance(value, float) and (math.isnan(value) or math.isinf(value))


def nonfinite_fields(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    failures = []
    for row in rows:
        step = row.get("step", row.get("trigger_step"))
        for key, value in row.items():
            if _is_nonfinite(value):
                failures.append({"step": step, "field": key, "value": str(value)})
    return failures


def dreamer_health(run_dir: Path, stale_checkpoint_seconds: float = 1800.0) -> dict[str, Any]:
    """Summarize live Dreamer health from the standard run directory files."""

    run_dir = Path(run_dir)
    metrics = read_jsonl(run_dir / "metrics.jsonl")
    latest = metrics[-1] if metrics else {}
    checkpoint = run_dir / "checkpoint.ckpt"
    stop_file = run_dir / "STOP_TRAINING"
    exit_status_files = sorted(run_dir.parent.glob(f"{run_dir.name}*.exit_status"))
    now = time.time()
    checkpoint_age = None
    if checkpoint.exists():
        checkpoint_age = max(0.0, now - checkpoint.stat().st_mtime)

    train_nonfinite = [
        item
        for item in nonfinite_fields(metrics)
        if str(item["field"]).startswith(("train/", "report/"))
    ]
    core_nonfinite = [
        item for item in train_nonfinite if item["field"] in CORE_TRAIN_KEYS
    ]
    warnings = []
    status = "healthy"
    if not metrics:
        warnings.append("metrics.jsonl is missing or empty")
        status = "waiting"
    if core_nonfinite:
        warnings.append("core Dreamer train loss/gradient contains NaN or Inf")
        status = "critical"
    elif train_nonfinite:
        warnings.append("diagnostic train/report fields contain NaN or Inf")
        if status == "healthy":
            status = "warning"
    if checkpoint_age is None:
        warnings.append("checkpoint.ckpt is missing")
        if status == "healthy":
            status = "warning"
    elif checkpoint_age > stale_checkpoint_seconds:
        warnings.append(f"checkpoint is stale: {checkpoint_age:.0f}s old")
        if status == "healthy":
            status = "warning"
    if stop_file.exists():
        warnings.append("STOP_TRAINING has been requested")
        status = "stopping"

    return {
        "schema_version": 1,
        "status": status,
        "run_dir": str(run_dir),
        "latest_step": latest.get("step"),
        "latest_episode_score": latest.get("episode/score"),
        "latest_success": latest.get("stats/sum_log_success"),
        "latest_fall": latest.get("stats/sum_log_fall_cost"),
        "replay_size": latest.get("replay/size"),
        "checkpoint_age_seconds": checkpoint_age,
        "exit_status_files": [str(path) for path in exit_status_files],
        "core_train": {key: latest.get(key) for key in CORE_TRAIN_KEYS},
        "nonfinite_count": len(train_nonfinite),
        "core_nonfinite_count": len(core_nonfinite),
        "warnings": warnings,
    }


def validation_rank(summary: dict[str, Any]) -> tuple[float, ...]:
    return (
        float(summary.get("completion_rate") or 0.0),
        -float(summary.get("fall_rate") or 0.0),
        float(summary.get("mean_max_route_completion") or 0.0),
        -float(summary.get("mean_cross_track_error_m") or 1e9),
    )


def meaningful_validation_improvement(
    best: dict[str, Any] | None,
    candidate: dict[str, Any],
    config: PlateauConfig = PlateauConfig(),
) -> bool:
    if best is None:
        return True
    best_summary = best["summary"] if "summary" in best else best
    cand_summary = candidate["summary"] if "summary" in candidate else candidate
    completion_gain = float(cand_summary.get("completion_rate") or 0.0) - float(
        best_summary.get("completion_rate") or 0.0
    )
    route_gain = float(cand_summary.get("mean_max_route_completion") or 0.0) - float(
        best_summary.get("mean_max_route_completion") or 0.0
    )
    fall_change = float(cand_summary.get("fall_rate") or 0.0) - float(
        best_summary.get("fall_rate") or 0.0
    )
    if completion_gain >= config.min_completion_delta:
        return True
    if route_gain >= config.min_route_delta and fall_change <= config.max_fall_delta:
        return True
    if validation_rank(cand_summary) > validation_rank(best_summary) and fall_change < 0:
        return True
    return False


def plateau_state(
    canonical_results: Iterable[dict[str, Any]],
    config: PlateauConfig = PlateauConfig(),
) -> dict[str, Any]:
    """Return validation-plateau state over chronological canonical results."""

    best: dict[str, Any] | None = None
    stale = 0
    history = []
    for result in sorted(canonical_results, key=lambda item: int(item["trigger_step"])):
        improved = meaningful_validation_improvement(best, result, config)
        if improved:
            best = result
            stale = 0
        else:
            stale += 1
        history.append(
            {
                "trigger_step": result["trigger_step"],
                "improved": improved,
                "stale_count": stale,
                "completion_rate": result["summary"]["completion_rate"],
                "fall_rate": result["summary"]["fall_rate"],
                "mean_max_route_completion": result["summary"][
                    "mean_max_route_completion"
                ],
            }
        )
    return {
        "schema_version": 1,
        "plateaued": stale >= config.patience if history else False,
        "stale_count": stale,
        "patience": config.patience,
        "best_trigger_step": None if best is None else best["trigger_step"],
        "best_checkpoint": None if best is None else best.get("checkpoint"),
        "history": history,
    }


def canonical_results_from_validation_root(validation_root: Path) -> list[dict[str, Any]]:
    results = []
    for path in sorted(Path(validation_root).glob("step_*/canonical.json")):
        try:
            result = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if result.get("completed"):
            results.append(result)
    return results


def validation_weakness_report(result: dict[str, Any], top_k: int = 8) -> dict[str, Any]:
    """Rank held-out policy weaknesses from a canonical/robust eval result."""

    episodes = list(result.get("episodes") or [])
    if not episodes:
        return {"schema_version": 1, "episodes": 0, "weaknesses": []}

    by_layout: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_band: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_progress_bin: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for episode in episodes:
        by_layout[str(episode.get("layout", "unknown"))].append(episode)
        by_band[str(episode.get("difficulty_band", "unknown"))].append(episode)
        progress = float(episode.get("max_route_completion") or 0.0)
        progress_bin = f"{int(min(0.999, max(0.0, progress)) * 10) * 10:02d}-{int(min(1.0, max(0.0, progress)) * 10 + 1) * 10:02d}%"
        by_progress_bin[progress_bin].append(episode)

    def summarize_group(kind: str, name: str, group: list[dict[str, Any]]) -> dict[str, Any]:
        count = len(group)
        failures = [ep for ep in group if not ep.get("success")]
        falls = [ep for ep in group if ep.get("fall")]
        progress_values = [float(ep.get("max_route_completion") or 0.0) for ep in group]
        cross_track = [
            float(ep.get("mean_cross_track_error_m") or 0.0) for ep in group
        ]
        clearances = [
            float(ep.get("minimum_clearance_m") or 0.0)
            for ep in group
            if ep.get("minimum_clearance_m") is not None
        ]
        failure_rate = len(failures) / count
        fall_rate = len(falls) / count
        mean_progress = statistics.fmean(progress_values) if progress_values else 0.0
        score = (
            4.0 * failure_rate
            + 3.0 * fall_rate
            + 2.0 * max(0.0, 1.0 - mean_progress)
            + (statistics.fmean(cross_track) if cross_track else 0.0) * 20.0
        )
        return {
            "kind": kind,
            "name": name,
            "episodes": count,
            "failure_rate": failure_rate,
            "fall_rate": fall_rate,
            "mean_max_route_completion": mean_progress,
            "mean_cross_track_error_m": (
                statistics.fmean(cross_track) if cross_track else None
            ),
            "minimum_clearance_m": min(clearances) if clearances else None,
            "weakness_score": score,
        }

    groups = []
    for kind, mapping in (
        ("layout", by_layout),
        ("difficulty_band", by_band),
        ("failure_progress_bin", by_progress_bin),
    ):
        for name, group in mapping.items():
            groups.append(summarize_group(kind, name, group))
    groups.sort(
        key=lambda item: (
            item["weakness_score"],
            item["episodes"],
            item["failure_rate"],
        ),
        reverse=True,
    )
    return {
        "schema_version": 1,
        "episodes": len(episodes),
        "source": result.get("checkpoint"),
        "trigger_step": result.get("trigger_step"),
        "mode": result.get("mode"),
        "weaknesses": groups[:top_k],
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--plateau-patience", type=int, default=3)
    parser.add_argument("--min-completion-delta", type=float, default=0.01)
    parser.add_argument("--min-route-delta", type=float, default=0.005)
    parser.add_argument("--max-fall-delta", type=float, default=0.005)
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    config = PlateauConfig(
        patience=args.plateau_patience,
        min_completion_delta=args.min_completion_delta,
        min_route_delta=args.min_route_delta,
        max_fall_delta=args.max_fall_delta,
    )
    health = dreamer_health(run_dir)
    canonical = canonical_results_from_validation_root(run_dir / "validation")
    plateau = plateau_state(canonical, config)
    latest_weakness = (
        validation_weakness_report(canonical[-1]) if canonical else None
    )
    report = {
        "schema_version": 1,
        "health": health,
        "plateau": plateau,
        "latest_weakness": latest_weakness,
    }
    if args.write:
        write_json(run_dir / "monitor_summary.json", report)
        if latest_weakness is not None:
            write_json(run_dir / "validation" / "latest_weakness_report.json", latest_weakness)
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
