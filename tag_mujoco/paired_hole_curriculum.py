"""Build paired production-scale maze datasets for staged hole learning."""

from __future__ import annotations

import argparse
import copy
import hashlib
import itertools
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np

try:
    from .dodge_maze_generator import (
        _cell_center,
        _dodge_hole_point,
        _polyline_min_clearance,
        _select_branch_blocker_cells,
        _select_dodge_cells,
    )
    from .maze_generator import HOLE_RADIUS, generate_maze
    from .route_planner import PlannerConfig, apply_safe_route, validate_route
except ImportError:  # pragma: no cover
    from dodge_maze_generator import (  # type: ignore
        _cell_center,
        _dodge_hole_point,
        _polyline_min_clearance,
        _select_branch_blocker_cells,
        _select_dodge_cells,
    )
    from maze_generator import HOLE_RADIUS, generate_maze  # type: ignore
    from route_planner import PlannerConfig, apply_safe_route, validate_route  # type: ignore


VARIANTS = ("no_holes", "branch_holes", "easy_dodge", "mixed_holes")
DATASET_IDS = {
    name: f"cyberrunner_paired_{name}_512train_64val_64test_v1"
    for name in VARIANTS
}


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _without_holes(layout: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(layout))
    result["holes"] = []
    result["hole_radii"] = []
    result["hole_cells"] = []
    result.pop("dodge_curriculum", None)
    return result


def _with_branch_holes(layout: Mapping[str, Any]) -> dict[str, Any]:
    result = _without_holes(layout)
    cells = _select_branch_blocker_cells(result, 64)
    for cell in cells:
        result["hole_cells"].append(list(cell))
        result["holes"].append(_cell_center(result, cell))
        result["hole_radii"].append(HOLE_RADIUS)
    result["paired_hole_curriculum"] = {
        "schema_version": 1,
        "variant": "branch_holes",
        "branch_blocker_cells": [list(cell) for cell in cells],
    }
    return result


def _route_hazard_variant(
    layout: Mapping[str, Any],
    *,
    seed: int,
    count: int,
    retain_branch_holes: bool,
    planner: PlannerConfig,
) -> dict[str, Any]:
    """Add deterministic route hazards and replan while preserving topology."""

    base = copy.deepcopy(dict(layout)) if retain_branch_holes else _without_holes(layout)
    reference = [list(point) for point in layout["waypoints"]]
    solution = [tuple(cell) for cell in layout["solution_cells"]]
    preferred = _select_dodge_cells(base, max(count, 1))
    interior = [tuple(cell) for cell in solution[2:-2]]
    sample_count = min(12, len(interior))
    sampled = (
        [
            interior[int(index)]
            for index in np.linspace(
                0, len(interior) - 1, sample_count, dtype=int
            )
        ]
        if interior
        else []
    )
    candidates = preferred + [cell for cell in sampled if cell not in preferred]

    # Try spatially separated route cells and several offsets. Some generated
    # corridors only have a viable side on one of these deterministic choices.
    attempts = itertools.islice(
        itertools.product(
            itertools.combinations(candidates, count),
            (0.006, 0.005, 0.004),
        ),
        48,
    )
    for cells, offset in attempts:
        candidate = copy.deepcopy(base)
        points = []
        for index, cell in enumerate(cells):
            point = _dodge_hole_point(
                candidate,
                solution,
                cell,
                seed + 7919 * index,
                offset,
            )
            candidate["hole_cells"].append(list(cell))
            candidate["holes"].append(point)
            candidate["hole_radii"].append(HOLE_RADIUS)
            points.append(point)
        if _polyline_min_clearance(candidate, reference) >= planner.safety_margin_m:
            continue
        try:
            routed, validation = apply_safe_route(candidate, planner)
        except (RuntimeError, ValueError):
            continue
        if not validation.passed:
            continue
        routed["reference_waypoints"] = reference
        routed["paired_hole_curriculum"] = {
            "schema_version": 1,
            "variant": "easy_dodge" if count == 1 else "mixed_holes",
            "source_seed": int(seed),
            "route_hole_cells": [list(cell) for cell in cells],
            "route_holes": points,
            "retained_branch_holes": bool(retain_branch_holes),
            "safe_route_min_clearance_m": validation.minimum_clearance_m,
        }
        return routed
    raise RuntimeError(
        f"Could not place {count} safe route hazard(s) for paired seed {seed}"
    )


def transform_layout(
    layout: Mapping[str, Any],
    variant: str,
    *,
    seed: int,
    planner: PlannerConfig = PlannerConfig(),
) -> dict[str, Any]:
    """Return one paired curriculum variant of an existing layout."""

    if variant not in VARIANTS:
        raise ValueError(f"Unknown paired curriculum variant: {variant!r}")
    if variant == "no_holes":
        result = _without_holes(layout)
    elif variant == "branch_holes":
        result = _with_branch_holes(layout)
    elif variant == "easy_dodge":
        result = _route_hazard_variant(
            layout,
            seed=seed,
            count=1,
            retain_branch_holes=False,
            planner=planner,
        )
    else:
        result = _route_hazard_variant(
            _with_branch_holes(layout),
            seed=seed,
            count=2,
            retain_branch_holes=True,
            planner=planner,
        )

    validation = validate_route(result, result["waypoints"], planner)
    if not validation.passed:
        raise RuntimeError(f"Unsafe {variant} route for seed {seed}: {validation}")
    result["paired_hole_curriculum"] = {
        **result.get("paired_hole_curriculum", {}),
        "schema_version": 1,
        "variant": variant,
        "source_seed": int(seed),
        "hole_count": len(result.get("holes", [])),
        "route_validation": {
            "passed": True,
            "minimum_clearance_m": validation.minimum_clearance_m,
            "required_margin_m": validation.required_margin_m,
        },
    }
    return result


def build_paired_datasets(
    source_manifest: Path,
    output_root: Path,
    *,
    planner: PlannerConfig = PlannerConfig(),
) -> dict[str, Path]:
    """Materialize all paired variants with unchanged split membership."""

    source_manifest = source_manifest.resolve()
    source = json.loads(source_manifest.read_text(encoding="utf-8"))
    output_root.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, Path] = {}

    for variant in VARIANTS:
        variant_root = output_root / variant
        variant_root.mkdir(parents=True, exist_ok=True)
        metadata: dict[str, dict[str, Any]] = {}
        relatives = sorted(
            {
                relative
                for split in ("smoke", "train", "dev", "validation", "test")
                for relative in source.get(split, [])
            }
        )
        for relative in relatives:
            source_path = source_manifest.parent / relative
            source_layout = json.loads(source_path.read_text(encoding="utf-8"))
            source_metadata = dict(source["metadata"][relative])
            seed = int(source_metadata["seed"])
            transformed = transform_layout(
                source_layout, variant, seed=seed, planner=planner
            )
            destination = variant_root / Path(relative).name
            destination.write_text(
                json.dumps(transformed, indent=2, allow_nan=False) + "\n",
                encoding="utf-8",
            )
            output_name = destination.name
            metadata[output_name] = {
                **source_metadata,
                "sha256": _digest(destination),
                "source_layout": relative,
                "curriculum_phase": variant,
                "hole_count": len(transformed.get("holes", [])),
            }

        manifest = {
            "schema_version": 2,
            "dataset_id": DATASET_IDS[variant],
            "source_dataset_id": source["dataset_id"],
            "pairing_policy": (
                "identical source seed, walls, start, and goal across phases; "
                "only holes and the safe route may change"
            ),
            "split_policy": source["split_policy"],
            **{
                split: [Path(relative).name for relative in source.get(split, [])]
                for split in ("smoke", "train", "dev", "validation", "test")
            },
            "metadata": metadata,
        }
        manifest_path = variant_root / "maze_splits.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        outputs[variant] = manifest_path
    return outputs


def build_production_datasets(
    output_root: Path,
    *,
    seed_start: int = 50000,
    train_count: int = 512,
    validation_count: int = 64,
    test_count: int = 64,
    max_candidates: int = 4000,
    planner: PlannerConfig = PlannerConfig(),
) -> dict[str, Path]:
    """Generate wide paired topologies accepted only if every phase is safe."""

    required = train_count + validation_count + test_count
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    output_root.mkdir(parents=True, exist_ok=True)
    for variant in VARIANTS:
        (output_root / variant).mkdir(parents=True, exist_ok=True)

    for seed in range(seed_start, seed_start + max_candidates):
        if len(accepted) >= required:
            break
        base = generate_maze(
            seed,
            columns=7,
            rows=6,
            loop_fraction=0.0,
            desired_holes=0,
            edge_jitter_fraction=0.04,
        )
        try:
            variants = {
                variant: transform_layout(
                    base, variant, seed=seed, planner=planner
                )
                for variant in VARIANTS
            }
        except (RuntimeError, ValueError) as error:
            rejected.append({"seed": seed, "error": str(error)})
            continue

        filename = f"paired_maze_seed_{seed}.json"
        digests = {}
        for variant, layout in variants.items():
            destination = output_root / variant / filename
            destination.write_text(
                json.dumps(layout, indent=2, allow_nan=False) + "\n",
                encoding="utf-8",
            )
            digests[variant] = _digest(destination)
        route = np.asarray(variants["no_holes"]["waypoints"], dtype=np.float64)
        route_length = float(
            np.linalg.norm(np.diff(route, axis=0), axis=1).sum()
        )
        accepted.append(
            {
                "seed": seed,
                "filename": filename,
                "route_length_m": route_length,
                "digests": digests,
                "hole_counts": {
                    name: len(layout.get("holes", []))
                    for name, layout in variants.items()
                },
            }
        )
        if len(accepted) % 25 == 0 or len(accepted) == required:
            print(
                f"Accepted {len(accepted)}/{required} paired layouts "
                f"after {len(accepted) + len(rejected)} candidates.",
                flush=True,
            )

    if len(accepted) != required:
        raise RuntimeError(
            f"Generated only {len(accepted)}/{required} fully paired layouts "
            f"from {max_candidates} candidate seeds"
        )

    ranked = sorted(
        range(required),
        key=lambda index: (
            accepted[index]["route_length_m"],
            accepted[index]["seed"],
        ),
    )
    ranks = {index: rank for rank, index in enumerate(ranked)}
    for index, entry in enumerate(accepted):
        percentile = ranks[index] / max(1, required - 1)
        entry["difficulty_score"] = percentile
        entry["difficulty_band"] = (
            "easy"
            if percentile < 1 / 3
            else "medium"
            if percentile < 2 / 3
            else "hard"
        )

    train_entries = accepted[:train_count]
    validation_entries = accepted[
        train_count : train_count + validation_count
    ]
    test_entries = accepted[train_count + validation_count :]
    ordered_train = sorted(
        train_entries,
        key=lambda entry: (
            entry["difficulty_score"],
            entry["seed"],
        ),
    )
    dev_count = min(64, len(ordered_train))
    dev_indices = np.linspace(
        0, len(ordered_train) - 1, dev_count, dtype=int
    )
    dev_entries = [ordered_train[int(index)] for index in dev_indices]

    split_entries = {
        "smoke": train_entries[:2],
        "train": train_entries,
        "dev": dev_entries,
        "validation": validation_entries,
        "test": test_entries,
    }
    outputs = {}
    for variant in VARIANTS:
        metadata = {
            entry["filename"]: {
                "seed": entry["seed"],
                "difficulty_score": entry["difficulty_score"],
                "difficulty_band": entry["difficulty_band"],
                "route_length_m": entry["route_length_m"],
                "curriculum_phase": variant,
                "hole_count": entry["hole_counts"][variant],
                "sha256": entry["digests"][variant],
            }
            for entry in accepted
        }
        manifest = {
            "schema_version": 2,
            "dataset_id": DATASET_IDS[variant],
            "generator_version": "paired_wide_grid_hole_curriculum_v1",
            "pairing_policy": (
                "only candidate seeds with safe no-hole, branch-hole, "
                "easy-dodge, and mixed-hole variants are accepted"
            ),
            "split_policy": (
                "deterministic accepted-seed order; validation and test never "
                "enter training replay"
            ),
            **{
                name: [entry["filename"] for entry in entries]
                for name, entries in split_entries.items()
            },
            "metadata": metadata,
            "generation": {
                "seed_start": seed_start,
                "accepted": len(accepted),
                "rejected": len(rejected),
                "rejections": rejected,
            },
        }
        path = output_root / variant / "maze_splits.json"
        path.write_text(
            json.dumps(manifest, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        outputs[variant] = path
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-manifest",
        type=Path,
        help="Optional existing manifest to transform instead of generating paired topology.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("artifacts/paired_hole_curriculum"),
    )
    parser.add_argument("--seed-start", type=int, default=50000)
    parser.add_argument("--train-count", type=int, default=512)
    parser.add_argument("--validation-count", type=int, default=64)
    parser.add_argument("--test-count", type=int, default=64)
    parser.add_argument("--max-candidates", type=int, default=4000)
    args = parser.parse_args()
    if args.source_manifest:
        outputs = build_paired_datasets(args.source_manifest, args.output_root)
    else:
        outputs = build_production_datasets(
            args.output_root,
            seed_start=args.seed_start,
            train_count=args.train_count,
            validation_count=args.validation_count,
            test_count=args.test_count,
            max_candidates=args.max_candidates,
        )
    for variant, path in outputs.items():
        print(f"{variant}: {path}")


if __name__ == "__main__":
    main()
