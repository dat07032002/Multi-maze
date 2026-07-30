"""Build deterministic one-online-map-at-a-time curriculum manifests."""

from __future__ import annotations

import argparse
import json
import math
import shutil
from pathlib import Path
from typing import Any, Mapping

import numpy as np

try:
    from .maze_dataset import file_sha256, load_manifest
    from .maze_layout import load_json_layout
except ImportError:
    from maze_dataset import file_sha256, load_manifest
    from maze_layout import load_json_layout


def maneuver_features(layout: Mapping[str, Any], metadata: Mapping[str, Any]) -> dict[str, Any]:
    points = np.asarray(layout["waypoints"], dtype=np.float64)
    vectors = np.diff(points, axis=0)
    lengths = np.linalg.norm(vectors, axis=1)
    directions = vectors / np.maximum(lengths[:, None], 1e-12)
    turns = int(
        sum(
            float(np.dot(first, second)) < math.cos(math.radians(20.0))
            for first, second in zip(directions, directions[1:])
        )
    )
    route_length = float(lengths.sum())
    initial = directions[0]
    initial_axis = (
        "x+" if abs(initial[0]) >= abs(initial[1]) and initial[0] >= 0 else
        "x-" if abs(initial[0]) >= abs(initial[1]) else
        "y+" if initial[1] >= 0 else "y-"
    )
    holes = len(layout.get("holes", ()))
    clearance = float(metadata.get("minimum_clearance_m", 1.0))
    return {
        "turn_count": turns,
        "route_length_m": route_length,
        "hole_count": holes,
        "minimum_clearance_m": clearance,
        "initial_direction": initial_axis,
        "tokens": [
            f"turns:{min(4, turns // 4)}",
            f"length:{min(4, int(route_length / 0.25))}",
            f"holes:{0 if holes == 0 else 1 if holes <= 8 else 2 if holes <= 20 else 3}",
            f"clearance:{0 if clearance >= 0.010 else 1 if clearance >= 0.006 else 2}",
            f"initial:{initial_axis}",
        ],
    }


def skill_coverage_order(
    source_dir: Path,
    train: list[str],
    metadata: Mapping[str, Mapping[str, Any]],
    *,
    candidate_window: int = 16,
) -> tuple[list[str], dict[str, dict[str, Any]]]:
    """Choose easy candidates while preferring not-yet-seen maneuver tokens."""

    features = {
        relative: maneuver_features(
            load_json_layout(source_dir / relative), metadata[relative]
        )
        for relative in train
    }
    remaining = set(train)
    covered: set[str] = set()
    ordered: list[str] = []
    while remaining:
        easiest = sorted(
            remaining,
            key=lambda relative: (
                float(metadata[relative].get("difficulty_score", 0.5)),
                int(metadata[relative].get("seed", 0)),
                relative,
            ),
        )[: max(1, int(candidate_window))]
        selected = min(
            easiest,
            key=lambda relative: (
                -len(set(features[relative]["tokens"]) - covered),
                float(metadata[relative].get("difficulty_score", 0.5)),
                int(metadata[relative].get("seed", 0)),
                relative,
            ),
        )
        ordered.append(selected)
        covered.update(features[selected]["tokens"])
        remaining.remove(selected)
    return ordered, features


def build_sequential_manifests(
    source_manifest: Path,
    output_root: Path,
    *,
    limit: int | None = None,
    candidate_window: int = 16,
) -> list[Path]:
    source_manifest = source_manifest.resolve()
    source_dir = source_manifest.parent
    source = load_manifest(source_manifest)
    output_root = output_root.resolve()
    stages_root = output_root / "stages"
    layouts_root = stages_root / "layouts"
    layouts_root.mkdir(parents=True, exist_ok=True)
    stages_root.mkdir(parents=True, exist_ok=True)

    all_entries = []
    for split in ("train", "validation", "test"):
        all_entries.extend(source[split])
    if len({Path(item).name for item in all_entries}) != len(all_entries):
        raise ValueError("Sequential curriculum requires unique layout basenames")

    copied_names: dict[str, str] = {}
    copied_metadata: dict[str, dict[str, Any]] = {}
    for relative in all_entries:
        destination_relative = f"layouts/{Path(relative).name}"
        destination = stages_root / destination_relative
        shutil.copy2(source_dir / relative, destination)
        item = dict(source["metadata"][relative])
        item["sha256"] = file_sha256(destination)
        copied_names[relative] = destination_relative
        copied_metadata[destination_relative] = item

    order, features = skill_coverage_order(
        source_dir,
        list(source["train"]),
        source["metadata"],
        candidate_window=candidate_window,
    )
    if limit is not None:
        if limit <= 0:
            raise ValueError("limit must be positive")
        order = order[:limit]
    source_id = str(source.get("dataset_id", "tag_dataset"))
    order_report = {
        "schema_version": 1,
        "source_dataset_id": source_id,
        "ordering_policy": "easy-window with greedy new-maneuver-token coverage",
        "candidate_window": int(candidate_window),
        "maps": [
            {
                "stage": index,
                "source_layout": relative,
                "layout": copied_names[relative],
                "features": features[relative],
            }
            for index, relative in enumerate(order, start=1)
        ],
    }
    (output_root / "map_order.json").write_text(
        json.dumps(order_report, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )

    outputs: list[Path] = []
    for index, current in enumerate(order, start=1):
        current_relative = copied_names[current]
        previous = [copied_names[item] for item in order[: index - 1]]
        manifest = {
            "schema_version": 2,
            "dataset_id": f"{source_id}_sequential_map_{index:04d}_v1",
            "source_dataset_id": source_id,
            "sequential_stage": index,
            "online_map_count": 1,
            "current_map": current_relative,
            "smoke": [current_relative],
            "train": [current_relative],
            "dev": [current_relative],
            "seen": previous + [current_relative],
            "validation": [copied_names[item] for item in source["validation"]],
            "test": [copied_names[item] for item in source["test"]],
            "metadata": copied_metadata,
        }
        if previous:
            manifest["rehearsal"] = previous
        path = stages_root / f"stage_{index:04d}.json"
        path.write_text(
            json.dumps(manifest, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        load_manifest(path)
        outputs.append(path)
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("artifacts/sequential_maps"),
    )
    parser.add_argument("--limit", type=int)
    parser.add_argument("--candidate-window", type=int, default=16)
    args = parser.parse_args()
    outputs = build_sequential_manifests(
        args.source_manifest,
        args.output_root,
        limit=args.limit,
        candidate_window=args.candidate_window,
    )
    print(json.dumps({"stages": len(outputs), "first": str(outputs[0])}, indent=2))


if __name__ == "__main__":
    main()
