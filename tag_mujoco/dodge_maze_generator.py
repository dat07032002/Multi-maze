"""Generate TAG maze layouts that require active hole dodging.

The historical generator deliberately kept holes off the solution cells. That
is useful for baseline route following, but it lets a policy learn to ride walls
through corridors without practicing the core hardware skill: stay close to a
safe reference path while bending around hazards.

This module keeps the old generator intact and builds a second curriculum family
on top of it:

1. generate a wide-cell maze with a normal centerline route;
2. place a small number of holes directly on interior route cells;
3. ask the continuous finite-ball planner to create a new safe path around them;
4. store both the blocked reference route and the replanned safe path.
"""

from __future__ import annotations

import json
import math
import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

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
    loop_fraction: float = 0.10
    branch_holes: int = 6
    dodge_holes: int = 2
    edge_jitter_fraction: float = 0.04


def _cell_center(layout: dict[str, Any], cell: Iterable[int]) -> list[float]:
    column, row = [int(value) for value in cell]
    return [
        0.5 * (layout["column_edges"][column] + layout["column_edges"][column + 1]),
        0.5 * (layout["row_edges"][row] + layout["row_edges"][row + 1]),
    ]


def _polyline_min_clearance(layout: dict[str, Any], points: list[list[float]]) -> float:
    route = resample_polyline(points, 0.002)
    return float(np.min(signed_ball_clearance(layout, route)))


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

    dodge_cells = _select_dodge_cells(base, config.dodge_holes)
    existing_cells = {tuple(cell) for cell in base["hole_cells"]}
    for cell in dodge_cells:
        if cell not in existing_cells:
            base["hole_cells"].append(list(cell))
            base["holes"].append(_cell_center(base, cell))
            base["hole_radii"].append(HOLE_RADIUS)

    blocked_clearance = _polyline_min_clearance(base, original_waypoints)
    if blocked_clearance >= planner.safety_margin_m:
        raise RuntimeError("Dodge holes did not invalidate the original route")

    routed, validation = apply_safe_route(base, planner)
    safe_length = validation.route_length_m
    if not validation.passed:
        raise RuntimeError(f"Dodge maze route is unsafe: {validation}")
    safe_route = np.asarray(routed["waypoints"], dtype=np.float64)
    dodge_hole_points = np.asarray([_cell_center(base, cell) for cell in dodge_cells])
    safe_hole_clearance = float(np.min(signed_hole_clearance(routed, safe_route)))
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
        "dodge_hole_cells": [list(cell) for cell in dodge_cells],
        "dodge_holes": dodge_hole_points.tolist(),
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
    for (x, y), radius in zip(layout["holes"], layout["hole_radii"]):
        cx, cy = point(x, y)
        r = radius * scale
        color = "#111111"
        outline = None
        outline_width = 1
        if tuple(round(value, 9) for value in (x, y)) in dodge_holes:
            outline = "#ff3030"
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

    draw.rectangle([8, 8, 430, 92], fill="white", outline="#222222")
    draw.text((20, 20), "cyan: replanned safe path", fill="#006f87")
    draw.text((20, 42), "orange dashed: original blocked path", fill="#a45b00")
    draw.text((20, 64), "red-ring holes: dodge-required hazards", fill="#c02020")
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
        layout_path = output_dir / f"dodge_maze_seed_{seed}.json"
        preview_path = preview_dir / f"dodge_maze_seed_{seed}_overlay.png"
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
            "difficulty_band": "dodge",
            "curriculum_stage": "easy_dodge_holes",
            "dodge_hole_count": len(entry["dodge_hole_cells"]),
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
    manifest_path = output_dir / "maze_splits_dodge.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "dataset_id": "tag_dodge_curriculum_v1",
                "split_policy": (
                    "small generated preview set; route-hazard dodge layouts; "
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
    parser.add_argument("--seed-start", type=int, default=40000)
    parser.add_argument("--seed-count", type=int, default=80)
    parser.add_argument("--count", type=int, default=6)
    args = parser.parse_args()

    entries = generate_dodge_curriculum_set(
        args.output_dir,
        args.preview_dir,
        seeds=range(args.seed_start, args.seed_start + args.seed_count),
        count=args.count,
    )
    accepted = [entry for entry in entries if entry["accepted"]]
    print(json.dumps({"accepted": len(accepted), "entries": entries}, indent=2))


if __name__ == "__main__":
    main()
