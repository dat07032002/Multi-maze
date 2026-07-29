"""Offline weakness slicing for finalized adaptation episode records."""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
from typing import Any, Iterable, Mapping


def _bucket(
    value: float,
    edges: tuple[float, ...],
    labels: tuple[str, ...],
) -> str:
    for edge, label in zip(edges, labels):
        if value < edge:
            return label
    return labels[-1]


def episode_slices(record: Mapping[str, Any]) -> dict[str, str]:
    """Map an episode summary to stable, interpretable weakness slices."""
    return {
        "turn": _bucket(
            abs(float(record.get("maximum_turn_angle_deg", 0.0))),
            (20.0, 45.0, 75.0),
            ("straight", "moderate", "sharp", "hairpin"),
        ),
        "entry_speed": _bucket(
            float(record.get("maximum_entry_speed_mps", 0.0)),
            (0.03, 0.07, 0.12),
            ("slow", "medium", "fast", "very_fast"),
        ),
        "hole_clearance": _bucket(
            float(record.get("minimum_hole_clearance_m", 1.0)),
            (0.003, 0.008, 0.015),
            ("critical", "warning", "near", "clear"),
        ),
        "camera": (
            "low_confidence"
            if float(record.get("minimum_camera_confidence", 1.0)) < 0.5
            else "normal"
        ),
        "actuator_reversal": (
            "reversal"
            if bool(record.get("actuator_direction_reversal", False))
            else "no_reversal"
        ),
        "difficulty": str(record.get("difficulty_band", "unknown")),
    }


def analyze_weaknesses(
    episodes: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Rank episode slices by failures, interventions, and lost progress."""
    groups: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    episode_list = list(episodes)
    for episode in episode_list:
        for dimension, value in episode_slices(episode).items():
            groups[(dimension, value)].append(episode)

    slices = []
    for (dimension, value), items in groups.items():
        count = len(items)
        completion = (
            sum(bool(item.get("success", False)) for item in items) / count
        )
        falls = sum(bool(item.get("fall", False)) for item in items) / count
        interventions = sum(
            float(item.get("intervention_count", 0)) for item in items
        ) / count
        progress = sum(
            float(item.get("max_route_completion", 0.0)) for item in items
        ) / count
        severity = (1.0 - completion) + falls + 0.05 * interventions + (
            1.0 - progress
        )
        slices.append(
            {
                "dimension": dimension,
                "value": value,
                "episodes": count,
                "completion_rate": completion,
                "fall_rate": falls,
                "interventions_per_episode": interventions,
                "mean_max_route_completion": progress,
                "weakness_severity": severity,
            }
        )
    slices.sort(
        key=lambda item: (item["weakness_severity"], item["episodes"]),
        reverse=True,
    )
    return {
        "schema_version": 1,
        "episodes": len(episode_list),
        "slices_worst_first": slices,
    }


def analyze_file(path: Path) -> dict[str, Any]:
    """Load a finalized episodes JSONL file and analyze its weaknesses."""
    episodes = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return analyze_weaknesses(episodes)
