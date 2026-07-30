"""Build nested, difficulty-ordered no-hole training groups.

Early groups deliberately use uniform sampling. This gives every layout repeated
episodes and avoids the process-local PLR state that kept 512 layouts effectively
unseen throughout the previous full-start run.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping


GROUP_SIZES = (16, 32, 64, 128, 512)


def _first_move(layout: Mapping[str, Any]) -> tuple[int, int]:
    cells = layout["solution_cells"]
    if len(cells) < 2:
        raise ValueError("A grouped maze needs at least two solution cells")
    return (
        int(cells[1][0]) - int(cells[0][0]),
        int(cells[1][1]) - int(cells[0][1]),
    )


def balanced_easy_first_order(
    source_dir: Path,
    train: list[str],
    metadata: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    """Interleave the two initial route directions, easiest first.

    Production mazes all begin in the same corner, so balancing the first
    horizontal and vertical decisions prevents the smallest group from being
    dominated by only one initial action.
    """

    buckets: dict[tuple[int, int], list[str]] = {}
    for relative in train:
        layout = json.loads((source_dir / relative).read_text(encoding="utf-8"))
        buckets.setdefault(_first_move(layout), []).append(relative)
    if len(buckets) != 2:
        raise ValueError(f"Expected two initial route directions, got {sorted(buckets)}")
    for entries in buckets.values():
        entries.sort(
            key=lambda relative: (
                float(metadata[relative]["difficulty_score"]),
                int(metadata[relative]["seed"]),
            )
        )
    directions = sorted(buckets)
    ordered: list[str] = []
    for index in range(max(len(entries) for entries in buckets.values())):
        available = [
            (direction, buckets[direction][index])
            for direction in directions
            if index < len(buckets[direction])
        ]
        available.sort(
            key=lambda item: (
                float(metadata[item[1]]["difficulty_score"]),
                item[0],
            )
        )
        ordered.extend(relative for _, relative in available)
    if len(ordered) != len(train) or len(set(ordered)) != len(train):
        raise RuntimeError("Grouped ordering lost or duplicated training layouts")
    return ordered


def build_group_manifests(
    source_manifest: Path,
    group_sizes: tuple[int, ...] = GROUP_SIZES,
) -> dict[int, Path]:
    source_manifest = source_manifest.resolve()
    source_dir = source_manifest.parent
    manifest = json.loads(source_manifest.read_text(encoding="utf-8"))
    train = list(manifest["train"])
    metadata = manifest["metadata"]
    if max(group_sizes) != len(train):
        raise ValueError(
            f"Largest group {max(group_sizes)} must equal source train count {len(train)}"
        )
    if tuple(sorted(set(group_sizes))) != group_sizes:
        raise ValueError("Group sizes must be unique and increasing")
    order = balanced_easy_first_order(source_dir, train, metadata)
    outputs: dict[int, Path] = {}
    previous: set[str] = set()
    for size in group_sizes:
        selected = order[:size]
        selected_set = set(selected)
        if not previous.issubset(selected_set):
            raise RuntimeError("Grouped curriculum is not nested")
        previous = selected_set
        if size <= 64:
            dev = selected
        else:
            # Fixed, evenly spaced mastery subset of the layouts seen in this
            # stage. Held-out validation and test remain unchanged.
            indices = [
                round(index * (size - 1) / 63)
                for index in range(64)
            ]
            dev = [selected[index] for index in indices]
        grouped = dict(manifest)
        grouped.update(
            {
                "dataset_id": f"cyberrunner_paired_no_holes_group{size:03d}_v1",
                "grouping_policy": (
                    "nested easy-first groups with balanced initial route "
                    "directions; uniform episode sampling"
                ),
                "source_dataset_id": manifest["dataset_id"],
                "train": selected,
                "dev": dev,
                "smoke": selected[:2],
                "group": {
                    "size": size,
                    "sizes": list(group_sizes),
                    "order_index": {
                        relative: index for index, relative in enumerate(order)
                    },
                },
            }
        )
        output = source_dir / f"maze_splits_group_{size:03d}.json"
        output.write_text(
            json.dumps(grouped, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        outputs[size] = output
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-manifest",
        type=Path,
        default=Path(
            "artifacts/paired_hole_curriculum/no_holes/maze_splits.json"
        ),
    )
    args = parser.parse_args()
    for size, path in build_group_manifests(args.source_manifest).items():
        print(f"group{size:03d}: {path}")


if __name__ == "__main__":
    main()
