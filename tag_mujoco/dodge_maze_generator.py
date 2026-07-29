"""Generate TAG maze layouts that require active hole dodging.

The historical generator deliberately kept holes off the solution cells. That
is useful for baseline route following, but it lets a policy learn to ride walls
through corridors without practicing the core hardware skill: stay close to a
safe reference path while bending around hazards.

This module keeps the old generator intact and builds staged curriculum families
on top of it:

1. generate a wide-cell maze with a normal centerline route;
2. optionally stop wrong branches with blocker holes;
3. optionally place route hazards near the old centerline;
4. ask the continuous finite-ball planner to create a safe path;
5. store both the reference route and the replanned safe path.
"""

from __future__ import annotations

import json
import math
import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
from PIL import Image, ImageDraw

try:
    from .maze_generator import HOLE_RADIUS, generate_maze
    from .maze_layout import save_json_layout
    from .route_planner import (
        PlannerConfig,
        apply_safe_route,
        resample_polyline,
        signed_ball_clearance,
        signed_hole_clearance,
        validate_route,
    )
except ImportError:  # pragma: no cover - script execution from package dir.
    from maze_generator import HOLE_RADIUS, generate_maze  # type: ignore
    from maze_layout import save_json_layout  # type: ignore
    from route_planner import (  # type: ignore
        PlannerConfig,
        apply_safe_route,
        resample_polyline,
        signed_ball_clearance,
        signed_hole_clearance,
        validate_route,
    )


@dataclass(frozen=True)
class DodgeMazeConfig:
    columns: int = 7
    rows: int = 6
    loop_fraction: float = 0.0
    branch_holes: int = 0
    dodge_holes: int = 2
    block_wrong_branches: bool = True
    max_branch_blocker_holes: int = 64
    dodge_hole_offset_m: float = 0.006
    edge_jitter_fraction: float = 0.04


@dataclass(frozen=True)
class CurriculumStage:
    name: str
    dataset_id: str
    manifest_name: str
    file_prefix: str
    difficulty_band: str
    config: DodgeMazeConfig


STAGES: dict[str, CurriculumStage] = {
    "progress": CurriculumStage(
        name="singlepath_progress",
        dataset_id="tag_singlepath_progress_v1",
        manifest_name="maze_splits_progress.json",
        file_prefix="progress_maze_seed",
        difficulty_band="singlepath_progress",
        config=DodgeMazeConfig(
            block_wrong_branches=False,
            dodge_holes=0,
        ),
    ),
    "branch": CurriculumStage(
        name="singlepath_branch_blockers",
        dataset_id="tag_singlepath_branch_blockers_v1",
        manifest_name="maze_splits_branch_blockers.json",
        file_prefix="branch_blocker_maze_seed",
        difficulty_band="branch_blockers",
        config=DodgeMazeConfig(
            block_wrong_branches=True,
            dodge_holes=0,
        ),
    ),
    "dodge": CurriculumStage(
        name="easy_dodge_holes",
        dataset_id="tag_dodge_curriculum_v1",
        manifest_name="maze_splits_dodge.json",
        file_prefix="dodge_maze_seed",
        difficulty_band="dodge",
        config=DodgeMazeConfig(),
    ),
}


def _cell_center(layout: dict[str, Any], cell: Iterable[int]) -> list[float]:
    column, row = [int(value) for value in cell]
    return [
        0.5 * (layout["column_edges"][column] + layout["column_edges"][column + 1]),
        0.5 * (layout["row_edges"][row] + layout["row_edges"][row + 1]),
    ]


def _polyline_min_clearance(layout: dict[str, Any], points: list[list[float]]) -> float:
    route = resample_polyline(points, 0.002)
    return float(np.min(signed_ball_clearance(layout, route)))


def _connected_neighbors_from_layout(
    layout: dict[str, Any], cell: tuple[int, int]
) -> list[tuple[int, int]]:
    """Return grid neighbors reachable without crossing a stored wall."""

    columns = int(layout["grid_columns"])
    rows = int(layout["grid_rows"])
    horizontal = {tuple(wall) for wall in layout["grid_horizontal_walls"]}
    vertical = {tuple(wall) for wall in layout["grid_vertical_walls"]}
    column, row = cell
    neighbors = []
    for next_column, next_row in (
        (column + 1, row),
        (column - 1, row),
        (column, row + 1),
        (column, row - 1),
    ):
        if not (0 <= next_column < columns and 0 <= next_row < rows):
            continue
        if column != next_column:
            blocked = (max(column, next_column), row) in vertical
        else:
            blocked = (column, max(row, next_row)) in horizontal
        if not blocked:
            neighbors.append((next_column, next_row))
    return neighbors


def _wrong_branch_components(layout: dict[str, Any]) -> list[list[tuple[int, int]]]:
    """Collect non-solution branches connected to the one solution corridor."""

    solution = [tuple(cell) for cell in layout["solution_cells"]]
    solution_set = set(solution)
    visited: set[tuple[int, int]] = set()
    branches: list[list[tuple[int, int]]] = []
    for route_cell in solution:
        for neighbor in _connected_neighbors_from_layout(layout, route_cell):
            if neighbor in solution_set or neighbor in visited:
                continue
            branch = []
            stack = [neighbor]
            visited.add(neighbor)
            while stack:
                current = stack.pop()
                branch.append(current)
                for next_cell in _connected_neighbors_from_layout(layout, current):
                    if next_cell in solution_set or next_cell in visited:
                        continue
                    visited.add(next_cell)
                    stack.append(next_cell)
            branches.append(branch)
    return branches


def _select_branch_blocker_cells(
    layout: dict[str, Any], max_count: int
) -> list[tuple[int, int]]:
    """Place one hole near the entrance of each wrong branch."""

    if max_count <= 0:
        return []
    start = tuple(layout["start_cell"])
    goal = tuple(layout["goal_cell"])
    branches = _wrong_branch_components(layout)
    # Longer branches get priority if a future config caps blockers below the
    # number of wrong turns. Each branch list starts at its solution-corridor
    # entrance, so branch[0] is the best "do not enter" cell.
    branches.sort(key=len, reverse=True)
    selected = []
    for branch in branches:
        entrance = branch[0]
        if entrance in (start, goal) or entrance in selected:
            continue
        selected.append(entrance)
        if len(selected) >= max_count:
            break
    return selected


def _clamp_to_cell(
    layout: dict[str, Any], point: np.ndarray, cell: tuple[int, int]
) -> np.ndarray:
    column, row = cell
    # Keep the physical hole inside the nominal cell. The route planner still
    # treats the finite ball and walls exactly, so this is just geometry hygiene.
    margin = HOLE_RADIUS + 0.001
    x_min = float(layout["column_edges"][column]) + margin
    x_max = float(layout["column_edges"][column + 1]) - margin
    y_min = float(layout["row_edges"][row]) + margin
    y_max = float(layout["row_edges"][row + 1]) - margin
    if x_min < x_max:
        point[0] = float(np.clip(point[0], x_min, x_max))
    if y_min < y_max:
        point[1] = float(np.clip(point[1], y_min, y_max))
    return point


def _dodge_hole_point(
    layout: dict[str, Any],
    solution: Sequence[tuple[int, int]],
    cell: tuple[int, int],
    seed: int,
    offset_m: float,
) -> list[float]:
    """Offset a route hazard so the old centerline fails but one side remains viable."""

    center = np.asarray(_cell_center(layout, cell), dtype=np.float64)
    index = solution.index(cell)
    if 0 < index < len(solution) - 1:
        before = np.asarray(_cell_center(layout, solution[index - 1]), dtype=np.float64)
        after = np.asarray(_cell_center(layout, solution[index + 1]), dtype=np.float64)
    elif index == 0:
        before = center
        after = np.asarray(_cell_center(layout, solution[index + 1]), dtype=np.float64)
    else:
        before = np.asarray(_cell_center(layout, solution[index - 1]), dtype=np.float64)
        after = center
    direction = after - before
    norm = float(np.linalg.norm(direction))
    if norm <= 1e-9:
        return center.tolist()
    perpendicular = np.asarray((-direction[1], direction[0]), dtype=np.float64) / norm
    column, row = cell
    cell_width = float(layout["column_edges"][column + 1] - layout["column_edges"][column])
    cell_height = float(layout["row_edges"][row + 1] - layout["row_edges"][row])
    offset = min(float(offset_m), 0.25 * min(cell_width, cell_height))
    sign = 1.0 if (seed + column * 17 + row * 31) % 2 == 0 else -1.0
    return _clamp_to_cell(layout, center + sign * offset * perpendicular, cell).tolist()


def _select_dodge_cells(layout: dict[str, Any], count: int) -> list[tuple[int, int]]:
    solution = [tuple(cell) for cell in layout["solution_cells"]]
    if len(solution) < count + 4:
        raise ValueError("Route is too short for dodge-hole placement")
    # Spread route hazards along the interior. Avoid first/last cells because
    # start and goal need a calm basin for reset and success detection.
    interior = solution[2:-2]
    indices = np.linspace(0, len(interior) - 1, count, dtype=int)
    selected: list[tuple[int, int]] = []
    for index in indices:
        cell = interior[int(index)]
        if cell not in selected:
            selected.append(cell)
    return selected


def generate_dodge_maze(
    seed: int,
    config: DodgeMazeConfig = DodgeMazeConfig(),
    planner: PlannerConfig = PlannerConfig(),
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return a layout whose saved waypoints are the replanned safe path."""

    base = generate_maze(
        seed,
        columns=config.columns,
        rows=config.rows,
        loop_fraction=config.loop_fraction,
        desired_holes=config.branch_holes,
        edge_jitter_fraction=config.edge_jitter_fraction,
    )
    original_waypoints = [list(point) for point in base["waypoints"]]
    original_length = float(
        np.sum(np.linalg.norm(np.diff(np.asarray(original_waypoints), axis=0), axis=1))
    )

    branch_blocker_cells = (
        _select_branch_blocker_cells(base, config.max_branch_blocker_holes)
        if config.block_wrong_branches
        else []
    )
    existing_cells = {tuple(cell) for cell in base["hole_cells"]}
    for cell in branch_blocker_cells:
        if cell not in existing_cells:
            base["hole_cells"].append(list(cell))
            base["holes"].append(_cell_center(base, cell))
            base["hole_radii"].append(HOLE_RADIUS)
            existing_cells.add(cell)

    solution = [tuple(cell) for cell in base["solution_cells"]]
    dodge_cells = _select_dodge_cells(base, config.dodge_holes) if config.dodge_holes else []
    dodge_hole_points = []
    for cell in dodge_cells:
        hole_point = _dodge_hole_point(
            base,
            solution,
            cell,
            seed,
            config.dodge_hole_offset_m,
        )
        base["hole_cells"].append(list(cell))
        base["holes"].append(hole_point)
        base["hole_radii"].append(HOLE_RADIUS)
        dodge_hole_points.append(hole_point)

    blocked_clearance = _polyline_min_clearance(base, original_waypoints)
    if dodge_cells and blocked_clearance >= planner.safety_margin_m:
        raise RuntimeError("Dodge holes did not invalidate the original route")

    routed, validation = apply_safe_route(base, planner)
    safe_length = validation.route_length_m
    if not validation.passed:
        raise RuntimeError(f"Dodge maze route is unsafe: {validation}")
    safe_route = np.asarray(routed["waypoints"], dtype=np.float64)
    safe_hole_clearance_raw = float(np.min(signed_hole_clearance(routed, safe_route)))
    safe_hole_clearance = (
        None if not math.isfinite(safe_hole_clearance_raw) else safe_hole_clearance_raw
    )
    routed["generator"] = "dense_irregular_depth_first_grid_v2_dodge_curriculum"
    routed["reference_waypoints"] = original_waypoints
    routed["dodge_curriculum"] = {
        "schema_version": 1,
        "seed": seed,
        "config": asdict(config),
        "planner": {
            "grid_resolution_m": planner.grid_resolution_m,
            "safety_margin_m": planner.safety_margin_m,
            "route_spacing_m": planner.route_spacing_m,
            "clearance_cost_weight": planner.clearance_cost_weight,
            "clearance_cost_scale_m": planner.clearance_cost_scale_m,
            "corner_rounding_radius_m": planner.corner_rounding_radius_m,
            "corner_rounding_samples": planner.corner_rounding_samples,
        },
        "single_solution_topology": config.loop_fraction == 0.0,
        "wrong_branch_count": len(_wrong_branch_components(base)),
        "branch_blocker_cells": [list(cell) for cell in branch_blocker_cells],
        "branch_blocker_holes": [_cell_center(base, cell) for cell in branch_blocker_cells],
        "dodge_hole_cells": [list(cell) for cell in dodge_cells],
        "dodge_holes": dodge_hole_points,
        "original_route_min_clearance_m": blocked_clearance,
        "safe_route_min_clearance_m": validation.minimum_clearance_m,
        "safe_route_min_hole_clearance_m": safe_hole_clearance,
        "original_route_length_m": original_length,
        "safe_route_length_m": safe_length,
        "safe_route_extra_m": safe_length - original_length,
        "route_validation": {
            "passed": validation.passed,
            "minimum_clearance_m": validation.minimum_clearance_m,
            "required_margin_m": validation.required_margin_m,
            "sampled_points": validation.sampled_points,
            "route_length_m": validation.route_length_m,
        },
    }
    return routed, routed["dodge_curriculum"]


def _draw_polyline(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[float, float]],
    *,
    fill: str,
    width: int,
    dashed: bool = False,
) -> None:
    if not dashed:
        draw.line(points, fill=fill, width=width, joint="curve")
        return
    for start, end in zip(points, points[1:]):
        sx, sy = start
        ex, ey = end
        length = math.hypot(ex - sx, ey - sy)
        if length <= 1e-6:
            continue
        segments = max(1, int(length / 12))
        for index in range(segments):
            if index % 2:
                continue
            a = index / segments
            b = (index + 1) / segments
            draw.line(
                (
                    (sx + (ex - sx) * a, sy + (ey - sy) * a),
                    (sx + (ex - sx) * b, sy + (ey - sy) * b),
                ),
                fill=fill,
                width=width,
            )


def render_dodge_preview(
    layout: dict[str, Any],
    path: Path,
    size: tuple[int, int] = (900, 800),
) -> None:
    """Render walls, holes, blocked centerline, and replanned safe path."""

    width_px, height_px = size
    margin = 44
    board_width = float(layout["board_width"])
    board_height = float(layout["board_height"])
    scale = min(
        (width_px - 2 * margin) / board_width,
        (height_px - 2 * margin) / board_height,
    )
    x0 = (width_px - board_width * scale) / 2.0
    y0 = (height_px - board_height * scale) / 2.0

    def point(x: float, y: float) -> tuple[float, float]:
        return x0 + x * scale, y0 + (board_height - y) * scale

    image = Image.new("RGB", size, "#f6f0df")
    draw = ImageDraw.Draw(image)
    draw.rectangle(
        [point(0, board_height), point(board_width, 0)],
        fill="#e7d5ad",
        outline="#4a2e18",
        width=7,
    )
    wall_width = max(3, round(float(layout.get("wall_thickness", 0.0022)) * scale))
    for start_x, end_x, y in layout["walls_h"]:
        draw.line([point(start_x, y), point(end_x, y)], fill="#5a351b", width=wall_width)
    for start_y, end_y, x in layout["walls_v"]:
        draw.line([point(x, start_y), point(x, end_y)], fill="#5a351b", width=wall_width)
    for x0a, y0a, x1a, y1a in layout.get("walls_angled", []):
        draw.line([point(x0a, y0a), point(x1a, y1a)], fill="#5a351b", width=wall_width)

    dodge_holes = {
        tuple(round(value, 9) for value in hole)
        for hole in layout.get("dodge_curriculum", {}).get("dodge_holes", [])
    }
    branch_blocker_holes = {
        tuple(round(value, 9) for value in hole)
        for hole in layout.get("dodge_curriculum", {}).get("branch_blocker_holes", [])
    }
    for (x, y), radius in zip(layout["holes"], layout["hole_radii"]):
        cx, cy = point(x, y)
        r = radius * scale
        color = "#111111"
        outline = None
        outline_width = 1
        if tuple(round(value, 9) for value in (x, y)) in dodge_holes:
            outline = "#ff3030"
            outline_width = 6
        if tuple(round(value, 9) for value in (x, y)) in branch_blocker_holes:
            outline = "#8a2be2"
            outline_width = 6
        draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            fill=color,
            outline=outline,
            width=outline_width,
        )

    reference = [point(x, y) for x, y in layout["reference_waypoints"]]
    safe = [point(x, y) for x, y in layout["waypoints"]]
    _draw_polyline(draw, reference, fill="#ff8c00", width=5, dashed=True)
    _draw_polyline(draw, safe, fill="#00a6c8", width=7)
    for cx, cy in safe[:: max(1, len(safe) // 24)]:
        draw.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill="#00a6c8")
    sx, sy = safe[0]
    gx, gy = safe[-1]
    draw.ellipse([sx - 11, sy - 11, sx + 11, sy + 11], fill="#26b34a", outline="white", width=2)
    draw.ellipse([gx - 11, gy - 11, gx + 11, gy + 11], fill="#df3b2f", outline="white", width=2)

    draw.rectangle([8, 8, 470, 114], fill="white", outline="#222222")
    draw.text((20, 20), "cyan: replanned safe path", fill="#006f87")
    draw.text((20, 42), "orange dashed: original blocked path", fill="#a45b00")
    draw.text((20, 64), "red-ring holes: dodge-required hazards", fill="#c02020")
    draw.text((20, 86), "purple-ring holes: wrong-branch blockers", fill="#6a1bb4")
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def generate_dodge_curriculum_set(
    output_dir: Path,
    preview_dir: Path,
    *,
    seeds: Iterable[int],
    count: int,
    config: DodgeMazeConfig = DodgeMazeConfig(),
    planner: PlannerConfig = PlannerConfig(),
    dataset_id: str = STAGES["dodge"].dataset_id,
    curriculum_stage: str = STAGES["dodge"].name,
    difficulty_band: str = STAGES["dodge"].difficulty_band,
    file_prefix: str = STAGES["dodge"].file_prefix,
    manifest_name: str = STAGES["dodge"].manifest_name,
) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)
    generated = []
    accepted_count = 0
    for seed in seeds:
        if accepted_count >= count:
            break
        try:
            layout, metadata = generate_dodge_maze(seed, config, planner)
        except Exception as error:
            generated.append(
                {
                    "seed": seed,
                    "accepted": False,
                    "error": str(error),
                }
            )
            continue
        layout_path = output_dir / f"{file_prefix}_{seed}.json"
        preview_path = preview_dir / f"{file_prefix}_{seed}_overlay.png"
        save_json_layout(layout, layout_path)
        render_dodge_preview(layout, preview_path)
        generated.append(
            {
                "seed": seed,
                "accepted": True,
                "layout": str(layout_path),
                "preview": str(preview_path),
                **metadata,
            }
        )
        accepted_count += 1
    accepted = [entry for entry in generated if entry["accepted"]]
    relatives = [Path(entry["layout"]).name for entry in accepted]
    metadata = {}
    for entry, relative in zip(accepted, relatives):
        digest = hashlib.sha256(
            (output_dir / relative).read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest()
        metadata[relative] = {
            "seed": entry["seed"],
            "difficulty_score": 0.25
            + 0.75
            * min(1.0, max(0.0, float(entry["safe_route_length_m"]) / 0.80)),
            "difficulty_band": difficulty_band,
            "curriculum_stage": curriculum_stage,
            "dodge_hole_count": len(entry["dodge_hole_cells"]),
            "branch_blocker_count": len(entry["branch_blocker_cells"]),
            "single_solution_topology": bool(entry["single_solution_topology"]),
            "original_route_min_clearance_m": entry["original_route_min_clearance_m"],
            "safe_route_min_clearance_m": entry["safe_route_min_clearance_m"],
            "safe_route_min_hole_clearance_m": entry["safe_route_min_hole_clearance_m"],
            "route_length_m": entry["safe_route_length_m"],
            "sha256": digest,
        }
    train = relatives[:-2] if len(relatives) >= 4 else relatives
    validation = relatives[-2:-1] if len(relatives) >= 2 else relatives[:1]
    test = relatives[-1:] if len(relatives) >= 1 else relatives[:1]
    smoke = train[: min(2, len(train))]
    dev = train[: min(4, len(train))]
    manifest_path = output_dir / manifest_name
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "dataset_id": dataset_id,
                "split_policy": (
                    f"small generated preview set; {curriculum_stage} layouts; "
                    "validation/test excluded from train"
                ),
                "config": asdict(config),
                "planner": {
                    "grid_resolution_m": planner.grid_resolution_m,
                    "safety_margin_m": planner.safety_margin_m,
                    "route_spacing_m": planner.route_spacing_m,
                    "clearance_cost_weight": planner.clearance_cost_weight,
                    "clearance_cost_scale_m": planner.clearance_cost_scale_m,
                    "corner_rounding_radius_m": planner.corner_rounding_radius_m,
                    "corner_rounding_samples": planner.corner_rounding_samples,
                },
                "smoke": smoke,
                "train": train,
                "dev": dev,
                "validation": validation,
                "test": test,
                "metadata": metadata,
                "entries": generated,
            },
            indent=2,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return generated


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("tag_mujoco/generated_dodge_mazes"))
    parser.add_argument("--preview-dir", type=Path, default=Path("artifacts/dodge_maze_previews"))
    parser.add_argument("--stage", choices=sorted(STAGES), default="dodge")
    parser.add_argument("--seed-start", type=int, default=40000)
    parser.add_argument("--seed-count", type=int, default=80)
    parser.add_argument("--count", type=int, default=6)
    args = parser.parse_args()
    stage = STAGES[args.stage]

    entries = generate_dodge_curriculum_set(
        args.output_dir,
        args.preview_dir,
        seeds=range(args.seed_start, args.seed_start + args.seed_count),
        count=args.count,
        config=stage.config,
        dataset_id=stage.dataset_id,
        curriculum_stage=stage.name,
        difficulty_band=stage.difficulty_band,
        file_prefix=stage.file_prefix,
        manifest_name=stage.manifest_name,
    )
    accepted = [entry for entry in entries if entry["accepted"]]
    print(json.dumps({"accepted": len(accepted), "entries": entries}, indent=2))


if __name__ == "__main__":
    main()
