"""Competence and retention gate for cumulative master-course stages."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

try:
    from .gate_criteria import (
        MASTER_COURSE_RETENTION_COMPLETION_DROP,
        MAXIMUM_TRUSTED_CROSS_TRACK_M,
        REGRESSION_TOLERANCE,
    )
    from .master_course_generator import COURSE_STAGES, STAGE_BY_NAME
    from .maze_dataset import load_manifest
    from .training_monitor import (
        PlateauConfig,
        canonical_results_from_validation_root,
        plateau_state,
    )
except ImportError:
    from gate_criteria import (
        MASTER_COURSE_RETENTION_COMPLETION_DROP,
        MAXIMUM_TRUSTED_CROSS_TRACK_M,
        REGRESSION_TOLERANCE,
    )
    from master_course_generator import COURSE_STAGES, STAGE_BY_NAME
    from maze_dataset import load_manifest
    from training_monitor import (
        PlateauConfig,
        canonical_results_from_validation_root,
        plateau_state,
    )


MIN_EPISODES_PER_STAGE = 4
COMPLETION_FLOORS = {
    "foundation": 0.85,
    "turns": 0.80,
    "recovery": 0.75,
    "hazards": 0.70,
    "compound": 0.70,
}
FALL_CEILINGS = {
    "foundation": 0.05,
    "turns": 0.08,
    "recovery": 0.10,
    "hazards": 0.10,
    "compound": 0.10,
}
PROGRESS_FLOOR = 0.85
RETENTION_COMPLETION_DROP = MASTER_COURSE_RETENTION_COMPLETION_DROP


def _layout_key(value: str) -> str:
    return Path(value).name


def stage_training_trend(
    canonical_results: Any,
    config: PlateauConfig = PlateauConfig(),
) -> dict[str, Any]:
    """Summarize whether a stage improved on its own starting point.

    A static floor check cannot tell a stage that never learned from one that
    unlearned. The 150k foundation run is the worked example: canonical mean
    route completion started at 0.729 on the untrained checkpoint and sat at
    0.501 for three consecutive milestones, so every later checkpoint was worse
    than the one training began from. Promoting on a snapshot alone would have
    accepted that. This reads the same chronological canonical history the
    validation monitor writes and reports the regression, the plateau, and
    which checkpoint actually scored best.
    """

    state = plateau_state(canonical_results, config)
    history = state["history"]
    if not history:
        return {
            "evaluated": False,
            "regressed": False,
            "plateaued": False,
            "reasons": [],
            "history_length": 0,
            "best_trigger_step": None,
            "best_checkpoint": None,
        }
    baseline, latest = history[0], history[-1]
    completion_drop = float(baseline["completion_rate"]) - float(
        latest["completion_rate"]
    )
    progress_drop = float(baseline["mean_max_route_completion"]) - float(
        latest["mean_max_route_completion"]
    )
    reasons = []
    if completion_drop > REGRESSION_TOLERANCE:
        reasons.append(
            f"completion fell {completion_drop:.3f} below the stage baseline at "
            f"step {baseline['trigger_step']}"
        )
    if progress_drop > REGRESSION_TOLERANCE:
        reasons.append(
            f"route progress fell {progress_drop:.3f} below the stage baseline at "
            f"step {baseline['trigger_step']}"
        )
    return {
        "evaluated": True,
        "regressed": bool(reasons),
        "plateaued": bool(state["plateaued"]),
        "reasons": reasons,
        "history_length": len(history),
        "baseline_trigger_step": baseline["trigger_step"],
        "latest_trigger_step": latest["trigger_step"],
        "completion_drop": completion_drop,
        "progress_drop": progress_drop,
        "stale_count": state["stale_count"],
        "patience": state["patience"],
        "best_trigger_step": state["best_trigger_step"],
        "best_checkpoint": state["best_checkpoint"],
    }


def evaluate_master_course_gate(
    report: Mapping[str, Any],
    manifest: Mapping[str, Any],
    target_stage: str,
    *,
    baseline_report: Mapping[str, Any] | None = None,
    canonical_results: Any | None = None,
) -> dict[str, Any]:
    """Evaluate current-stage mastery, earlier-stage retention, and trend.

    `canonical_results` is the chronological canonical validation history for
    the stage, as produced by
    `training_monitor.canonical_results_from_validation_root`. When supplied, a
    stage that ended worse than it started cannot be promoted no matter how it
    scores against the static floors.
    """

    if target_stage not in STAGE_BY_NAME:
        raise ValueError(f"Unknown target stage {target_stage!r}")
    target_index = STAGE_BY_NAME[target_stage].index
    if int(manifest.get("curriculum_stage_index", -1)) != target_index:
        raise ValueError(
            "Target stage does not match manifest curriculum stage: "
            f"{target_stage!r} versus {manifest.get('curriculum_stage')!r}"
        )
    metadata = manifest.get("metadata", {})
    by_basename = {_layout_key(relative): item for relative, item in metadata.items()}
    if len(by_basename) != len(metadata):
        raise ValueError("Master-course manifest contains ambiguous layout basenames")
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    unknown: list[str] = []
    for episode in report.get("episodes", []):
        name = _layout_key(str(episode.get("layout", "")))
        item = by_basename.get(name)
        if item is None:
            unknown.append(name)
            continue
        grouped[str(item["course_stage"])].append(episode)
    if unknown:
        raise ValueError(
            "Evaluation contains layouts absent from manifest: "
            f"{sorted(set(unknown))}"
        )

    baseline_completion: dict[str, float] = {}
    if baseline_report is not None:
        baseline_grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for episode in baseline_report.get("episodes", []):
            item = by_basename.get(_layout_key(str(episode.get("layout", ""))))
            if item is not None:
                baseline_grouped[str(item["course_stage"])].append(episode)
        for name, episodes in baseline_grouped.items():
            baseline_completion[name] = sum(
                bool(item.get("success", False)) for item in episodes
            ) / len(episodes)

    results: dict[str, Any] = {}
    passed = True
    for stage in COURSE_STAGES[:target_index]:
        episodes = grouped.get(stage.name, [])
        count = len(episodes)
        completion = (
            sum(bool(item.get("success", False)) for item in episodes) / count
            if count else 0.0
        )
        falls = (
            sum(bool(item.get("fall", False)) for item in episodes) / count
            if count else 1.0
        )
        progress = (
            sum(float(item.get("max_route_completion", 0.0)) for item in episodes) / count
            if count else 0.0
        )
        # Route completion projects the ball onto the route, so it only measures
        # tracking while the ball is near it. Episodes that drifted further than
        # the corridor are not evidence of progress whatever they scored.
        untrusted = [
            item
            for item in episodes
            if float(item.get("mean_cross_track_error_m", 0.0))
            > MAXIMUM_TRUSTED_CROSS_TRACK_M
        ]
        completion_floor = COMPLETION_FLOORS[stage.name]
        if stage.name in baseline_completion:
            completion_floor = max(
                completion_floor,
                baseline_completion[stage.name] - RETENTION_COMPLETION_DROP,
            )
        reasons = []
        if count < MIN_EPISODES_PER_STAGE:
            reasons.append(f"requires at least {MIN_EPISODES_PER_STAGE} episodes")
        if completion < completion_floor:
            reasons.append(f"completion {completion:.3f} below {completion_floor:.3f}")
        if falls > FALL_CEILINGS[stage.name]:
            reasons.append(f"fall rate {falls:.3f} above {FALL_CEILINGS[stage.name]:.3f}")
        if progress < PROGRESS_FLOOR:
            reasons.append(f"route progress {progress:.3f} below {PROGRESS_FLOOR:.3f}")
        if untrusted:
            worst = max(
                float(item.get("mean_cross_track_error_m", 0.0)) for item in untrusted
            )
            reasons.append(
                f"{len(untrusted)} of {count} episodes drifted beyond the "
                f"{MAXIMUM_TRUSTED_CROSS_TRACK_M * 1000:.0f} mm route corridor, "
                f"worst {worst * 1000:.0f} mm, so their route progress is not "
                "evidence of tracking"
            )
        stage_passed = not reasons
        passed = passed and stage_passed
        results[stage.name] = {
            "episodes": count,
            "completion_rate": completion,
            "fall_rate": falls,
            "mean_max_route_completion": progress,
            "untrusted_progress_episodes": len(untrusted),
            "completion_floor": completion_floor,
            "passed": stage_passed,
            "reasons": reasons,
        }
    trend = stage_training_trend(canonical_results or [])
    if trend["regressed"]:
        passed = False
    return {
        "schema_version": 2,
        "gate": "master_course_competence_and_retention",
        "target_stage": target_stage,
        "passed": passed,
        "stages": results,
        "trend": trend,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--target-stage", choices=tuple(STAGE_BY_NAME), required=True)
    parser.add_argument("--baseline-report", type=Path)
    parser.add_argument(
        "--validation-root",
        type=Path,
        help=(
            "Stage validation directory. Supplying it refuses promotion for a "
            "stage that ended worse than the checkpoint it started from."
        ),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    manifest = load_manifest(args.manifest)
    baseline = (
        json.loads(args.baseline_report.read_text(encoding="utf-8"))
        if args.baseline_report else None
    )
    canonical = (
        canonical_results_from_validation_root(args.validation_root)
        if args.validation_root else None
    )
    result = evaluate_master_course_gate(
        report,
        manifest,
        args.target_stage,
        baseline_report=baseline,
        canonical_results=canonical,
    )
    text = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    raise SystemExit(0 if result["passed"] else 2)


if __name__ == "__main__":
    main()
