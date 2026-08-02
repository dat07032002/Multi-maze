"""Generate a deterministic, cumulative multi-skill maze-course curriculum.

The course family is a geometry grammar rather than one fixed layout.  Every
variant preserves a declared skill sequence while mirroring, scaling, and
jittering the geometry.  Skill and zone labels are manifest-only metadata and
never cross the deployed policy observation boundary.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

try:
    from .maze_dataset import file_sha256, load_manifest
    from .maze_generator import (
        BALL_RADIUS,
        BOARD_HEIGHT,
        BOARD_WIDTH,
        HOLE_RADIUS,
        WALL_HEIGHT,
        WALL_THICKNESS,
    )
    from .maze_layout import save_json_layout
    from .route_planner import PlannerConfig, smooth_safe_route, validate_route
except ImportError:
    from maze_dataset import file_sha256, load_manifest
    from maze_generator import (
        BALL_RADIUS,
        BOARD_HEIGHT,
        BOARD_WIDTH,
        HOLE_RADIUS,
        WALL_HEIGHT,
        WALL_THICKNESS,
    )
    from maze_layout import save_json_layout
    from route_planner import PlannerConfig, smooth_safe_route, validate_route


GENERATOR_VERSION = "tag_master_course_grammar_v1"
DATASET_PREFIX = "tag_master_course"


@dataclass(frozen=True)
class CourseStage:
    index: int
    name: str
    skills: tuple[str, ...]
    route: tuple[tuple[float, float], ...]
    zones: tuple[tuple[str, int, int], ...]
    hazards: bool = False
    narrow_corridor: bool = False
    recovery_reset: bool = False


COURSE_STAGES = (
    CourseStage(
        1,
        "foundation",
        ("launch", "straight", "brake", "gentle_turn"),
        ((0.025, 0.190), (0.080, 0.190), (0.120, 0.180), (0.155, 0.155)),
        (
            ("launch", 0, 1),
            ("straight", 0, 1),
            ("brake", 1, 2),
            ("gentle_turn", 2, 3),
        ),
    ),
    CourseStage(
        2,
        "turns",
        ("launch", "straight", "gentle_turn", "sharp_turn", "s_curve"),
        (
            (0.025, 0.190), (0.080, 0.190), (0.105, 0.170),
            (0.105, 0.125), (0.132, 0.105), (0.160, 0.128),
            (0.188, 0.105), (0.188, 0.060), (0.230, 0.060),
        ),
        (
            ("launch", 0, 1), ("straight", 0, 1), ("gentle_turn", 1, 3),
            ("sharp_turn", 3, 4), ("s_curve", 4, 7), ("brake", 7, 8),
        ),
    ),
    CourseStage(
        3,
        "recovery",
        (
            "straight",
            "sharp_turn",
            "s_curve",
            "lateral_recovery",
            "velocity_recovery",
        ),
        (
            (0.025, 0.185), (0.078, 0.185), (0.102, 0.162),
            (0.102, 0.115), (0.132, 0.092), (0.162, 0.118),
            (0.192, 0.092), (0.225, 0.092),
        ),
        (
            ("straight", 0, 1), ("sharp_turn", 1, 3), ("s_curve", 3, 6),
            ("lateral_recovery", 3, 6), ("velocity_recovery", 3, 6),
        ),
        recovery_reset=True,
    ),
    CourseStage(
        4,
        "hazards",
        ("straight", "brake", "hole_avoidance", "narrow_corridor", "recovery"),
        (
            (0.025, 0.180), (0.075, 0.180), (0.105, 0.155),
            (0.135, 0.180), (0.165, 0.155), (0.195, 0.180),
            (0.225, 0.155),
        ),
        (
            ("straight", 0, 1), ("brake", 1, 2), ("hole_avoidance", 1, 6),
            ("narrow_corridor", 0, 1), ("recovery", 5, 6),
        ),
        hazards=True,
        narrow_corridor=True,
    ),
    CourseStage(
        5,
        "compound",
        (
            "launch", "straight", "brake", "gentle_turn", "sharp_turn",
            "s_curve", "narrow_corridor", "hole_avoidance", "recovery",
            "long_horizon",
        ),
        (
            (0.025, 0.195), (0.080, 0.195), (0.105, 0.175),
            (0.105, 0.135), (0.135, 0.112), (0.165, 0.135),
            (0.192, 0.110), (0.192, 0.070), (0.162, 0.045),
            (0.120, 0.045), (0.102, 0.075), (0.072, 0.075),
            (0.052, 0.045), (0.025, 0.045),
        ),
        (
            ("launch", 0, 1), ("straight", 0, 1), ("brake", 1, 2),
            ("gentle_turn", 1, 3), ("sharp_turn", 3, 4), ("s_curve", 4, 7),
            ("narrow_corridor", 8, 9), ("hole_avoidance", 9, 12),
            ("recovery", 10, 12), ("long_horizon", 0, 13),
        ),
        hazards=True,
        narrow_corridor=True,
    ),
)
STAGE_BY_NAME = {stage.name: stage for stage in COURSE_STAGES}


def _transform_route(
    route: Sequence[Sequence[float]], rng: np.random.Generator, variant: int
) -> np.ndarray:
    points = np.asarray(route, dtype=np.float64)
    center = np.asarray((BOARD_WIDTH / 2.0, BOARD_HEIGHT / 2.0))
    scale = np.asarray((rng.uniform(0.90, 1.08), rng.uniform(0.90, 1.08)))
    points = center + (points - center) * scale
    if variant % 2:
        points[:, 0] = BOARD_WIDTH - points[:, 0]
    if (variant // 2) % 2:
        points[:, 1] = BOARD_HEIGHT - points[:, 1]
    jitter = rng.uniform(-0.004, 0.004, size=points.shape)
    jitter[[0, -1]] *= 0.35
    points += jitter
    return points


def _segment_normal(start: np.ndarray, end: np.ndarray) -> np.ndarray:
    direction = end - start
    norm = float(np.linalg.norm(direction))
    if norm <= 1e-9:
        raise ValueError("Course route contains a zero-length segment")
    return np.asarray((-direction[1], direction[0])) / norm


def _hazards(
    route: np.ndarray, stage: CourseStage
) -> tuple[list[list[float]], list[float]]:
    if not stage.hazards:
        return [], []
    indices = (2, 4) if stage.name == "hazards" else (9, 10)
    route_samples = np.concatenate(
        [
            np.linspace(start, end, max(2, int(np.linalg.norm(end - start) / 0.001)))
            for start, end in zip(route, route[1:])
        ],
        axis=0,
    )
    holes: list[list[float]] = []
    for number, index in enumerate(indices):
        start, end = route[index], route[index + 1]
        center = 0.5 * (start + end)
        normal = _segment_normal(start, end)
        preferred = -1.0 if number % 2 else 1.0
        selected = None
        for side in (preferred, -preferred):
            for offset in (0.020, 0.023, 0.026, 0.029, 0.032):
                candidate = center + side * offset * normal
                edge_margin = HOLE_RADIUS + BALL_RADIUS + 0.002
                bounded = (
                    edge_margin <= candidate[0] <= BOARD_WIDTH - edge_margin
                    and edge_margin <= candidate[1] <= BOARD_HEIGHT - edge_margin
                )
                route_distance = float(
                    np.min(np.linalg.norm(route_samples - candidate, axis=1))
                )
                separated = all(
                    np.linalg.norm(candidate - np.asarray(other))
                    >= 2.0 * HOLE_RADIUS + 0.004
                    for other in holes
                )
                if bounded and route_distance >= 0.017 and separated:
                    selected = candidate
                    break
            if selected is not None:
                break
        if selected is None:
            raise RuntimeError(f"Could not place safe hazard beside route segment {index}")
        holes.append(selected.tolist())
    return holes, [HOLE_RADIUS] * len(holes)


def _corridor_walls(
    route: np.ndarray, stage: CourseStage
) -> tuple[list[list[float]], list[list[float]], list[list[float]]]:
    if not stage.narrow_corridor:
        return [], [], []
    index = 0 if stage.name == "hazards" else 8
    raw_start, raw_end = route[index], route[index + 1]
    # Leave open transitions at both ends. Full-length rails can approach a
    # neighboring leg of a folded course even when their own centerline is safe.
    start = raw_start + 0.20 * (raw_end - raw_start)
    end = raw_start + 0.80 * (raw_end - raw_start)
    normal = _segment_normal(start, end)
    half_width = 0.015
    walls_angled = []
    for side in (-1.0, 1.0):
        offset = side * half_width * normal
        first, second = start + offset, end + offset
        walls_angled.append(
            [float(first[0]), float(first[1]), float(second[0]), float(second[1])]
        )
    return [], [], walls_angled


def _geometry_is_finite_and_bounded(layout: Mapping[str, Any]) -> bool:
    margin = BALL_RADIUS + 0.001
    points: list[Sequence[float]] = list(layout["waypoints"]) + list(layout["holes"])
    for x0, y0, x1, y1 in layout["walls_angled"]:
        points.extend(((x0, y0), (x1, y1)))
    return all(
        len(point) == 2
        and all(math.isfinite(float(value)) for value in point)
        and margin <= float(point[0]) <= BOARD_WIDTH - margin
        and margin <= float(point[1]) <= BOARD_HEIGHT - margin
        for point in points
    )


def _reset_conditions(stage: CourseStage, variant: int) -> dict[str, Any]:
    conditions: dict[str, Any] = {
        "progress_fraction": 0.0,
        "lateral_offset_m": 0.0,
        "tangent_velocity_mps": 0.0,
        "normal_velocity_mps": 0.0,
        "board_tilt_rad": [0.0, 0.0],
    }
    if stage.recovery_reset:
        sign = -1.0 if variant % 2 else 1.0
        conditions.update(
            progress_fraction=0.35 + 0.05 * ((variant // 2) % 3),
            lateral_offset_m=sign * (0.003 + 0.0005 * ((variant // 3) % 3)),
            tangent_velocity_mps=0.008 + 0.004 * ((variant // 4) % 3),
            normal_velocity_mps=-sign * (0.012 + 0.004 * ((variant // 5) % 3)),
        )
    return conditions


def _zone_metadata(stage: CourseStage, route: np.ndarray) -> list[dict[str, Any]]:
    lengths = np.linalg.norm(np.diff(route, axis=0), axis=1)
    cumulative = np.concatenate(([0.0], np.cumsum(lengths)))
    total = max(float(cumulative[-1]), 1e-9)
    return [
        {
            "skill": name,
            "start_progress_fraction": float(cumulative[start] / total),
            "end_progress_fraction": float(cumulative[end] / total),
        }
        for name, start, end in stage.zones
    ]


def build_master_course_layout(
    stage_name: str,
    variant: int,
    *,
    seed_namespace: int = 800_000,
    planner: PlannerConfig = PlannerConfig(),
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build one validated course variant and its manifest-only metadata."""

    if stage_name not in STAGE_BY_NAME:
        raise ValueError(f"Unknown master-course stage {stage_name!r}")
    if variant < 0:
        raise ValueError("Course variant must be non-negative")
    stage = STAGE_BY_NAME[stage_name]
    seed = seed_namespace + stage.index * 100_000 + variant
    rng = np.random.default_rng(seed)
    blueprint_route = _transform_route(stage.route, rng, variant)
    holes, hole_radii = _hazards(blueprint_route, stage)
    walls_h, walls_v, walls_angled = _corridor_walls(blueprint_route, stage)
    layout: dict[str, Any] = {
        "name": f"master_{stage.name}_{variant:05d}",
        "generator": GENERATOR_VERSION,
        "seed": seed,
        "board_width": BOARD_WIDTH,
        "board_height": BOARD_HEIGHT,
        "ball_radius": BALL_RADIUS,
        "wall_thickness": WALL_THICKNESS,
        "wall_height": WALL_HEIGHT,
        "walls_h": walls_h,
        "walls_v": walls_v,
        "walls_angled": walls_angled,
        "holes": holes,
        "hole_radii": hole_radii,
        "waypoints": blueprint_route.tolist(),
        "master_course": {
            "stage_index": stage.index,
            "stage_name": stage.name,
            "variant": variant,
            "skills": list(stage.skills),
            "zones": _zone_metadata(stage, blueprint_route),
            "mirrored_x": bool(variant % 2),
            "mirrored_y": bool((variant // 2) % 2),
        },
    }
    if not _geometry_is_finite_and_bounded(layout):
        raise RuntimeError(f"Generated {stage.name} course {variant} is out of bounds")
    route = smooth_safe_route(layout, blueprint_route, planner)
    layout["waypoints"] = route.tolist()
    validation = validate_route(layout, route, planner)
    if not validation.passed:
        raise RuntimeError(
            f"Unsafe {stage.name} course {variant}: minimum clearance "
            f"{validation.minimum_clearance_m:.6f} m, required "
            f"{validation.required_margin_m:.6f} m"
        )
    layout["route_planner"] = {
        "grid_resolution_m": planner.grid_resolution_m,
        "safety_margin_m": planner.safety_margin_m,
        "route_spacing_m": planner.route_spacing_m,
        "clearance_cost_weight": planner.clearance_cost_weight,
        "clearance_cost_scale_m": planner.clearance_cost_scale_m,
        "corner_rounding_radius_m": planner.corner_rounding_radius_m,
        "corner_rounding_samples": planner.corner_rounding_samples,
    }
    difficulty = min(1.0, 0.10 + 0.17 * stage.index + 0.01 * (variant % 5))
    metadata = {
        "seed": seed,
        "difficulty_score": round(difficulty, 6),
        "difficulty_band": (
            "easy"
            if stage.index <= 2
            else ("medium" if stage.index <= 4 else "hard")
        ),
        "route_length_m": validation.route_length_m,
        "minimum_clearance_m": validation.minimum_clearance_m,
        "required_clearance_m": validation.required_margin_m,
        "hole_count": len(holes),
        "wall_segment_count": len(walls_h) + len(walls_v) + len(walls_angled),
        "course_stage": stage.name,
        "course_stage_index": stage.index,
        "skills": list(stage.skills),
        "condition_id": f"{stage.name}_{variant:05d}",
        "reset_conditions": _reset_conditions(stage, variant),
        "policy_observation_contains_labels": False,
    }
    return layout, metadata


def build_master_course_dataset(
    output_root: Path,
    *,
    train_per_stage: int = 32,
    validation_per_stage: int = 8,
    test_per_stage: int = 8,
) -> dict[str, Path]:
    """Build cumulative manifests; later stages retain every earlier family."""

    if min(train_per_stage, validation_per_stage, test_per_stage) <= 0:
        raise ValueError("Every split must contain at least one variant per stage")
    output_root = output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    cumulative = {"train": [], "validation": [], "test": []}
    cumulative_dev: list[str] = []
    cumulative_metadata: dict[str, dict[str, Any]] = {}
    outputs: dict[str, Path] = {}
    counts = {
        "train": train_per_stage,
        "validation": validation_per_stage,
        "test": test_per_stage,
    }
    variant_base = 0
    for stage in COURSE_STAGES:
        for split_index, split in enumerate(("train", "validation", "test")):
            stage_entries: list[str] = []
            for offset in range(counts[split]):
                variant = variant_base + split_index * 10_000 + offset
                layout, metadata = build_master_course_layout(stage.name, variant)
                relative = (
                    f"layouts/{stage.name}/{split}/"
                    f"master_{stage.name}_{split}_{offset:04d}.json"
                )
                path = output_root / relative
                save_json_layout(layout, path)
                metadata["sha256"] = file_sha256(path)
                cumulative[split].append(relative)
                stage_entries.append(relative)
                cumulative_metadata[relative] = metadata
            if split == "train":
                cumulative_dev.extend(stage_entries[: min(4, len(stage_entries))])
        dataset_id = f"{DATASET_PREFIX}_stage{stage.index}_{stage.name}_v1"
        manifest = {
            "schema_version": 2,
            "dataset_id": dataset_id,
            "generator_version": GENERATOR_VERSION,
            "curriculum_stage": stage.name,
            "curriculum_stage_index": stage.index,
            "cumulative_stages": [item.name for item in COURSE_STAGES[: stage.index]],
            "smoke": cumulative["train"][: min(4, len(cumulative["train"]))],
            "train": list(cumulative["train"]),
            "dev": list(cumulative_dev),
            "validation": list(cumulative["validation"]),
            "test": list(cumulative["test"]),
            "metadata": dict(cumulative_metadata),
        }
        manifest_path = output_root / f"stage_{stage.index:02d}_{stage.name}.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        load_manifest(manifest_path)
        outputs[stage.name] = manifest_path
        variant_base += 100_000
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root", type=Path, default=Path("artifacts/master_course_curriculum")
    )
    parser.add_argument("--train-per-stage", type=int, default=32)
    parser.add_argument("--validation-per-stage", type=int, default=8)
    parser.add_argument("--test-per-stage", type=int, default=8)
    args = parser.parse_args()
    outputs = build_master_course_dataset(
        args.output_root,
        train_per_stage=args.train_per_stage,
        validation_per_stage=args.validation_per_stage,
        test_per_stage=args.test_per_stage,
    )
    print(json.dumps({name: str(path) for name, path in outputs.items()}, indent=2))


if __name__ == "__main__":
    main()
