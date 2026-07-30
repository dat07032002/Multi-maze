"""Generate deterministic short courses for universal TAG control skills.

The generated labels live only in manifest metadata. The policy observation
remains the deployed image/state/relative-route contract and never contains a
skill or course identifier.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Iterable

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


SKILL_FAMILIES = (
    "stabilize",
    "straight",
    "turn",
    "compound",
    "recovery",
    "hazard",
)
GENERATOR_VERSION = "tag_universal_skill_courses_v1"


def _rotate(points: Iterable[Iterable[float]], quarter_turns: int) -> np.ndarray:
    angle = 0.5 * math.pi * (quarter_turns % 4)
    rotation = np.asarray(
        ((math.cos(angle), -math.sin(angle)), (math.sin(angle), math.cos(angle))),
        dtype=np.float64,
    )
    center = np.asarray((BOARD_WIDTH / 2.0, BOARD_HEIGHT / 2.0))
    return np.asarray(tuple(points), dtype=np.float64) @ rotation.T + center


def _base_route(family: str, variant: int) -> np.ndarray:
    side = -1.0 if (variant // 4) % 2 else 1.0
    if family == "stabilize":
        points = ((-0.035, 0.0), (0.035, 0.0))
    elif family in {"straight", "recovery"}:
        length = (0.115, 0.130, 0.145)[(variant // 8) % 3]
        points = ((-0.5 * length, 0.0), (0.5 * length, 0.0))
    elif family == "turn":
        points = ((-0.065, 0.0), (0.0, 0.0), (0.0, side * 0.065))
    elif family == "compound":
        points = (
            (-0.072, -side * 0.025),
            (-0.025, -side * 0.025),
            (0.025, side * 0.025),
            (0.072, side * 0.025),
        )
    elif family == "hazard":
        points = (
            (-0.075, 0.0),
            (-0.030, side * 0.026),
            (0.030, side * 0.026),
            (0.075, 0.0),
        )
    else:
        raise ValueError(f"Unknown skill family: {family}")
    return _rotate(points, variant % 4)


def reset_conditions(family: str, variant: int) -> dict[str, Any]:
    """Return reproducible route-relative initial conditions for one course."""

    sign = -1.0 if variant % 2 else 1.0
    speed = (0.0, 0.015, 0.030)[(variant // 2) % 3]
    tilt = math.radians((0.0, 1.0, 2.0)[(variant // 3) % 3])
    conditions: dict[str, Any] = {
        "progress_fraction": 0.0,
        "lateral_offset_m": 0.0,
        "tangent_velocity_mps": 0.0,
        "normal_velocity_mps": 0.0,
        "board_tilt_rad": [0.0, 0.0],
    }
    if family == "stabilize":
        conditions.update(
            tangent_velocity_mps=sign * speed,
            normal_velocity_mps=-sign * 0.5 * speed,
            board_tilt_rad=[sign * tilt, -sign * 0.5 * tilt],
        )
    elif family in {"turn", "compound", "hazard"}:
        conditions["tangent_velocity_mps"] = speed
    elif family == "recovery":
        conditions.update(
            progress_fraction=0.20,
            lateral_offset_m=sign * (0.003 + 0.0015 * ((variant // 2) % 3)),
            tangent_velocity_mps=0.5 * speed,
            normal_velocity_mps=-sign * speed,
        )
    else:
        conditions["tangent_velocity_mps"] = 0.5 * speed
    return conditions


def build_skill_layout(
    family: str,
    variant: int,
    *,
    planner: PlannerConfig = PlannerConfig(),
) -> tuple[dict[str, Any], dict[str, Any]]:
    if family not in SKILL_FAMILIES:
        raise ValueError(f"Unknown skill family {family!r}")
    route = _base_route(family, variant)
    holes: list[list[float]] = []
    radii: list[float] = []
    if family == "hazard":
        holes = [[BOARD_WIDTH / 2.0, BOARD_HEIGHT / 2.0]]
        radii = [HOLE_RADIUS]
    layout: dict[str, Any] = {
        "name": f"skill_{family}_{variant:04d}",
        "generator": GENERATOR_VERSION,
        "seed": 500_000 + SKILL_FAMILIES.index(family) * 10_000 + variant,
        "board_width": BOARD_WIDTH,
        "board_height": BOARD_HEIGHT,
        "ball_radius": BALL_RADIUS,
        "wall_thickness": WALL_THICKNESS,
        "wall_height": WALL_HEIGHT,
        "walls_h": [],
        "walls_v": [],
        "walls_angled": [],
        "holes": holes,
        "hole_radii": radii,
        "waypoints": route.tolist(),
        "skill_course": {
            "family": family,
            "variant": variant,
            "quarter_turns": variant % 4,
            "mirrored": bool((variant // 4) % 2),
        },
    }
    route = smooth_safe_route(layout, route, planner)
    layout["waypoints"] = route.tolist()
    validation = validate_route(layout, route, planner)
    if not validation.passed:
        raise RuntimeError(
            f"Unsafe {family} skill course {variant}: {validation}"
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
    metadata = {
        "seed": layout["seed"],
        "difficulty_score": round(min(1.0, 0.15 + 0.12 * SKILL_FAMILIES.index(family)), 6),
        "difficulty_band": (
            "easy" if family in {"stabilize", "straight"} else
            "medium" if family in {"turn", "compound"} else "hard"
        ),
        "route_length_m": validation.route_length_m,
        "minimum_clearance_m": validation.minimum_clearance_m,
        "required_clearance_m": validation.required_margin_m,
        "hole_count": len(holes),
        "wall_segment_count": 0,
        "skill_family": family,
        "condition_id": f"{family}_{variant:04d}",
        "reset_conditions": reset_conditions(family, variant),
        "policy_observation_contains_labels": False,
    }
    return layout, metadata


def build_skill_dataset(
    output_root: Path,
    *,
    train_count: int = 16,
    validation_count: int = 4,
    test_count: int = 4,
) -> dict[str, Path]:
    if min(train_count, validation_count, test_count) <= 0:
        raise ValueError("Every skill split must contain at least one course")
    output_root = output_root.resolve()
    outputs: dict[str, Path] = {}
    for family in SKILL_FAMILIES:
        family_root = output_root / family
        family_root.mkdir(parents=True, exist_ok=True)
        total = train_count + validation_count + test_count
        entries: list[str] = []
        metadata: dict[str, dict[str, Any]] = {}
        for variant in range(total):
            layout, item = build_skill_layout(family, variant)
            relative = f"course_{variant:04d}.json"
            path = family_root / relative
            save_json_layout(layout, path)
            item["sha256"] = file_sha256(path)
            entries.append(relative)
            metadata[relative] = item
        train_end = train_count
        validation_end = train_end + validation_count
        manifest = {
            "schema_version": 2,
            "dataset_id": f"tag_universal_skill_{family}_v1",
            "generator_version": GENERATOR_VERSION,
            "skill_family": family,
            "smoke": entries[: min(2, train_count)],
            "train": entries[:train_end],
            "dev": entries[: min(4, train_count)],
            "validation": entries[train_end:validation_end],
            "test": entries[validation_end:],
            "metadata": metadata,
        }
        manifest_path = family_root / "maze_splits.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        load_manifest(manifest_path)
        outputs[family] = manifest_path
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("artifacts/universal_skills"),
    )
    parser.add_argument("--train-count", type=int, default=16)
    parser.add_argument("--validation-count", type=int, default=4)
    parser.add_argument("--test-count", type=int, default=4)
    args = parser.parse_args()
    outputs = build_skill_dataset(
        args.output_root,
        train_count=args.train_count,
        validation_count=args.validation_count,
        test_count=args.test_count,
    )
    print(json.dumps({key: str(value) for key, value in outputs.items()}, indent=2))


if __name__ == "__main__":
    main()
