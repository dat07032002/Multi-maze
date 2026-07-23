"""Build the deterministic 40/8/8 multi-maze dataset and immutable manifest."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

try:
    from .maze_dataset import file_sha256
    from .maze_generator import generate_maze, validate_generated_layout
    from .maze_layout import load_json_layout, save_json_layout
    from .route_planner import PlannerConfig, apply_safe_route, validate_route
except ImportError:
    from maze_dataset import file_sha256
    from maze_generator import generate_maze, validate_generated_layout
    from maze_layout import load_json_layout, save_json_layout
    from route_planner import PlannerConfig, apply_safe_route, validate_route


HERE = Path(__file__).resolve().parent
GENERATED = HERE / "generated_mazes"
MANIFEST = HERE / "maze_splits.json"
GENERATOR_VERSION = "dense_irregular_depth_first_grid_v2+finite_ball_route_v1"


def _candidate_seeds(primary: int, start: int) -> Iterable[int]:
    yield primary
    yield from range(start, start + 10000)


def _turn_count(layout: Dict[str, Any]) -> int:
    cells = [tuple(cell) for cell in layout["solution_cells"]]
    directions = [
        (second[0] - first[0], second[1] - first[1])
        for first, second in zip(cells, cells[1:])
    ]
    return sum(first != second for first, second in zip(directions, directions[1:]))


def _dead_end_count(layout: Dict[str, Any]) -> int:
    columns = int(layout["grid_columns"])
    rows = int(layout["grid_rows"])
    horizontal = {tuple(wall) for wall in layout["grid_horizontal_walls"]}
    vertical = {tuple(wall) for wall in layout["grid_vertical_walls"]}
    dead_ends = 0
    for column in range(columns):
        for row in range(rows):
            degree = 0
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                other_c, other_r = column + dc, row + dr
                if not (0 <= other_c < columns and 0 <= other_r < rows):
                    continue
                blocked = (
                    (max(column, other_c), row) in vertical
                    if dc
                    else (column, max(row, other_r)) in horizontal
                )
                degree += int(not blocked)
            dead_ends += int(degree == 1)
    return dead_ends


def _difficulty(layout: Dict[str, Any], route_length_m: float) -> Tuple[float, str, Dict[str, Any]]:
    solution_cells = len(layout["solution_cells"])
    turns = _turn_count(layout)
    dead_ends = _dead_end_count(layout)
    route_component = min(max((route_length_m - 0.35) / 1.25, 0.0), 1.0)
    turn_component = min(turns / 55.0, 1.0)
    dead_end_component = min(dead_ends / 24.0, 1.0)
    score = 0.50 * route_component + 0.35 * turn_component + 0.15 * dead_end_component
    score = float(round(score, 6))
    band = "easy" if score < 0.34 else "medium" if score < 0.67 else "hard"
    return score, band, {
        "solution_cell_count": solution_cells,
        "turn_count": turns,
        "dead_end_count": dead_ends,
    }


def _build_one(seed: int, planner: PlannerConfig) -> Tuple[Path, Dict[str, Any]]:
    path = GENERATED / f"maze_seed_{seed}.json"
    if path.is_file():
        layout = load_json_layout(path)
        if int(layout.get("seed", -1)) != seed:
            raise ValueError(f"Existing layout seed mismatch in {path}")
        route_validation = validate_route(layout, layout["waypoints"], planner)
        planner_metadata = layout.get("route_planner", {})
        metadata_matches = math.isclose(
            float(planner_metadata.get("safety_margin_m", -1.0)),
            planner.safety_margin_m,
        )
    else:
        layout = generate_maze(seed)
        route_validation = validate_route(layout, layout["waypoints"], planner)
        metadata_matches = False
    generated_validation = validate_generated_layout(layout)
    if not generated_validation["passed"]:
        raise RuntimeError(f"Generated maze {seed} failed structural validation")
    if not route_validation.passed or not metadata_matches:
        layout, route_validation = apply_safe_route(layout, planner)
    if not route_validation.passed:
        raise RuntimeError(f"Generated maze {seed} has no finite-ball-safe route")
    if not path.is_file() or not metadata_matches:
        save_json_layout(layout, path)
    route_validation = validate_route(layout, layout["waypoints"], planner)
    score, band, features = _difficulty(layout, route_validation.route_length_m)
    return path, {
        "seed": seed,
        "difficulty_score": score,
        "difficulty_band": band,
        "route_length_m": route_validation.route_length_m,
        "minimum_clearance_m": route_validation.minimum_clearance_m,
        "required_clearance_m": route_validation.required_margin_m,
        "hole_count": len(layout["holes"]),
        "wall_segment_count": len(layout["walls_h"]) + len(layout["walls_v"]),
        **features,
        "sha256": file_sha256(path),
    }


def _select(count: int, primary: int, start: int, used: set[int], planner: PlannerConfig):
    selected: List[Tuple[Path, Dict[str, Any]]] = []
    for seed in _candidate_seeds(primary, start):
        if seed in used:
            continue
        try:
            item = _build_one(seed, planner)
        except (RuntimeError, ValueError):
            continue
        selected.append(item)
        used.add(seed)
        if len(selected) == count:
            return selected
    raise RuntimeError(f"Could not generate {count} valid unique mazes")


def _assign_relative_bands(entries: List[Tuple[Path, Dict[str, Any]]]) -> None:
    """Label within-split tertiles while retaining the absolute difficulty score."""
    ranked = sorted(entries, key=lambda item: (item[1]["difficulty_score"], item[1]["seed"]))
    count = len(ranked)
    for rank, (_, metadata) in enumerate(ranked):
        fraction = rank / max(count, 1)
        metadata["difficulty_band"] = (
            "easy" if fraction < 1.0 / 3.0 else "medium" if fraction < 2.0 / 3.0 else "hard"
        )
        metadata["difficulty_percentile_within_split"] = round(
            rank / max(count - 1, 1), 6
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-count", type=int, default=40)
    parser.add_argument("--validation-count", type=int, default=8)
    parser.add_argument("--test-count", type=int, default=8)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    args = parser.parse_args()
    GENERATED.mkdir(parents=True, exist_ok=True)
    planner = PlannerConfig()
    used: set[int] = set()
    splits = {
        "train": _select(args.train_count, 970, 10000, used, planner),
        "validation": _select(args.validation_count, 1024, 20000, used, planner),
        "test": _select(args.test_count, 765, 30000, used, planner),
    }
    for entries in splits.values():
        _assign_relative_bands(entries)

    def relative(path: Path) -> str:
        return path.relative_to(HERE).as_posix()

    metadata = {
        relative(path): item
        for entries in splits.values()
        for path, item in entries
    }
    train_paths = [relative(path) for path, _ in splits["train"]]
    manifest = {
        "schema_version": 2,
        "dataset_id": "cyberrunner_fixed_board_40train_8val_8test_v1",
        "generator_version": GENERATOR_VERSION,
        "split_policy": "disjoint deterministic seeds; validation and test never enter replay",
        "smoke": [train_paths[0]],
        "train": train_paths,
        "validation": [relative(path) for path, _ in splits["validation"]],
        "test": [relative(path) for path, _ in splits["test"]],
        "metadata": metadata,
    }
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    bands = {
        split: {
            band: sum(item["difficulty_band"] == band for _, item in entries)
            for band in ("easy", "medium", "hard")
        }
        for split, entries in splits.items()
    }
    print(json.dumps({"manifest": str(args.manifest), "counts": {key: len(value) for key, value in splits.items()}, "difficulty_bands": bands}, indent=2))


if __name__ == "__main__":
    main()
