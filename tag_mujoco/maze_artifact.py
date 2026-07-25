"""Export one maze definition into simulation, route, preview, and STL artifacts.

The generated mesh is deliberately marked as a prototype until the physical
TAG insert mounting interface has been measured.  This prevents the known
259 x 229 mm playable area from being mistaken for a complete mounting CAD
specification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from PIL import Image, ImageDraw

try:
    from .maze_layout import load_json_layout, save_json_layout
    from .model_builder import _floor_spans, build_mjcf
    from .route_planner import PlannerConfig, validate_route
except ImportError:
    from maze_layout import load_json_layout, save_json_layout
    from model_builder import _floor_spans, build_mjcf
    from route_planner import PlannerConfig, validate_route


@dataclass(frozen=True)
class PrintConfig:
    """Provisional printable geometry; mounting dimensions remain unconfirmed."""

    floor_thickness_m: float = 0.003
    floor_strip_height_m: float = 0.0015
    minimum_feature_m: float = 0.0012
    mounting_interface_confirmed: bool = False
    include_outer_rim: bool = False
    outer_rim_thickness_m: float = 0.003


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_print_geometry(
    layout: dict[str, Any], config: PrintConfig = PrintConfig()
) -> dict[str, Any]:
    errors: list[str] = []
    width = float(layout["board_width"])
    height = float(layout["board_height"])
    wall_thickness = float(layout["wall_thickness"])
    wall_height = float(layout["wall_height"])
    if not math.isclose(width, 0.259, abs_tol=1e-9):
        errors.append(f"playable width is {width:.6f} m, expected 0.259 m")
    if not math.isclose(height, 0.229, abs_tol=1e-9):
        errors.append(f"playable height is {height:.6f} m, expected 0.229 m")
    if wall_thickness < config.minimum_feature_m:
        errors.append("wall thickness is below the provisional printable feature limit")
    if wall_height <= 0.0 or config.floor_thickness_m <= 0.0:
        errors.append("wall height and floor thickness must be positive")
    if len(layout["holes"]) != len(layout["hole_radii"]):
        errors.append("hole centers and radii have different lengths")
    for index, ((x, y), radius) in enumerate(
        zip(layout["holes"], layout["hole_radii"])
    ):
        if radius <= 0.0:
            errors.append(f"hole {index} has a non-positive radius")
        if not (radius <= x <= width - radius and radius <= y <= height - radius):
            errors.append(f"hole {index} intersects the playable boundary")
    route = validate_route(layout, layout["waypoints"], PlannerConfig())
    if not route.passed:
        errors.append(
            "route fails finite-ball clearance: "
            f"{route.minimum_clearance_m:.6f} m < {route.required_margin_m:.6f} m"
        )
    return {
        "passed": not errors,
        "errors": errors,
        "playable_dimensions_m": [width, height],
        "floor_thickness_m": config.floor_thickness_m,
        "wall_thickness_m": wall_thickness,
        "wall_height_m": wall_height,
        "route_minimum_clearance_m": route.minimum_clearance_m,
        "route_required_clearance_m": route.required_margin_m,
        "mounting_interface_confirmed": config.mounting_interface_confirmed,
        "print_status": (
            "final_fit_candidate"
            if config.mounting_interface_confirmed and not errors
            else "prototype_only"
        ),
    }


class TriangleMesh:
    def __init__(self):
        self.triangles: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []

    def add_box(
        self,
        center_xy: Iterable[float],
        size_xy: Iterable[float],
        z0: float,
        z1: float,
        angle_rad: float = 0.0,
    ) -> None:
        cx, cy = map(float, center_xy)
        sx, sy = map(float, size_xy)
        local = np.asarray(
            [(-sx / 2, -sy / 2), (sx / 2, -sy / 2),
             (sx / 2, sy / 2), (-sx / 2, sy / 2)],
            dtype=np.float64,
        )
        cosine, sine = math.cos(angle_rad), math.sin(angle_rad)
        rotation = np.asarray(((cosine, -sine), (sine, cosine)))
        xy = local @ rotation.T + np.asarray((cx, cy))
        vertices = [
            np.asarray((xy[index, 0], xy[index, 1], z), dtype=np.float64)
            for z in (z0, z1)
            for index in range(4)
        ]
        faces = (
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7),
        )
        self.triangles.extend((vertices[a], vertices[b], vertices[c]) for a, b, c in faces)

    def write_ascii_stl(self, path: Path, solid_name: str) -> None:
        lines = [f"solid {solid_name}"]
        for first, second, third in self.triangles:
            normal = np.cross(second - first, third - first)
            length = float(np.linalg.norm(normal))
            normal = normal / length if length > 1e-12 else np.zeros(3)
            lines.append(f"  facet normal {normal[0]:.9g} {normal[1]:.9g} {normal[2]:.9g}")
            lines.append("    outer loop")
            for vertex in (first, second, third):
                lines.append(
                    f"      vertex {vertex[0]:.9g} {vertex[1]:.9g} {vertex[2]:.9g}"
                )
            lines.extend(("    endloop", "  endfacet"))
        lines.append(f"endsolid {solid_name}")
        path.write_text("\n".join(lines) + "\n", encoding="ascii")


def build_prototype_mesh(
    layout: dict[str, Any], config: PrintConfig = PrintConfig()
) -> TriangleMesh:
    mesh = TriangleMesh()
    width = float(layout["board_width"])
    height = float(layout["board_height"])
    floor_thickness = float(config.floor_thickness_m)
    wall_width = float(layout["wall_thickness"])
    wall_height = float(layout["wall_height"])

    for x0, x1, y0, y1 in _floor_spans(
        width,
        height,
        layout["holes"],
        layout["hole_radii"],
        config.floor_strip_height_m,
    ):
        mesh.add_box(
            ((x0 + x1) / 2.0, (y0 + y1) / 2.0),
            (x1 - x0, y1 - y0),
            0.0,
            floor_thickness,
        )

    def wall(start, end):
        x0, y0 = start
        x1, y1 = end
        length = math.hypot(x1 - x0, y1 - y0)
        if length >= config.minimum_feature_m:
            mesh.add_box(
                ((x0 + x1) / 2.0, (y0 + y1) / 2.0),
                (length, wall_width),
                floor_thickness,
                floor_thickness + wall_height,
                math.atan2(y1 - y0, x1 - x0),
            )

    for x0, x1, y in layout["walls_h"]:
        wall((x0, y), (x1, y))
    for y0, y1, x in layout["walls_v"]:
        wall((x, y0), (x, y1))
    for x0, y0, x1, y1 in layout["walls_angled"]:
        wall((x0, y0), (x1, y1))

    if config.include_outer_rim:
        rim = config.outer_rim_thickness_m
        wall((0.0, 0.0), (width, 0.0))
        wall((width, 0.0), (width, height))
        wall((width, height), (0.0, height))
        wall((0.0, height), (0.0, 0.0))
    return mesh


def render_preview(layout: dict[str, Any], path: Path, pixels_per_meter: int = 2400) -> None:
    width = float(layout["board_width"])
    height = float(layout["board_height"])
    image = Image.new("RGB", (round(width * pixels_per_meter), round(height * pixels_per_meter)), "#eee5d0")
    draw = ImageDraw.Draw(image)

    def point(x, y):
        return (x * pixels_per_meter, (height - y) * pixels_per_meter)

    wall_px = max(2, round(float(layout["wall_thickness"]) * pixels_per_meter))
    for x0, x1, y in layout["walls_h"]:
        draw.line((point(x0, y), point(x1, y)), fill="#70502c", width=wall_px)
    for y0, y1, x in layout["walls_v"]:
        draw.line((point(x, y0), point(x, y1)), fill="#70502c", width=wall_px)
    for x0, y0, x1, y1 in layout["walls_angled"]:
        draw.line((point(x0, y0), point(x1, y1)), fill="#70502c", width=wall_px)
    for (x, y), radius in zip(layout["holes"], layout["hole_radii"]):
        cx, cy = point(x, y)
        r = radius * pixels_per_meter
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill="#111111")
    route = [point(x, y) for x, y in layout["waypoints"]]
    draw.line(route, fill="#00a6c8", width=max(2, wall_px // 2), joint="curve")
    image.save(path)


def export_maze_artifact(
    layout_path: Path,
    output_root: Path,
    config: PrintConfig = PrintConfig(),
    *,
    overwrite: bool = False,
    request_final_fit: bool = False,
) -> Path:
    layout_path = layout_path.resolve()
    layout = load_json_layout(layout_path)
    validation = validate_print_geometry(layout, config)
    if not validation["passed"]:
        raise ValueError("Maze is not exportable: " + "; ".join(validation["errors"]))
    if request_final_fit and not config.mounting_interface_confirmed:
        raise RuntimeError(
            "Final-fit STL is blocked until the physical TAG mounting interface is measured"
        )

    destination = output_root.resolve() / layout_path.stem
    if destination.exists() and any(destination.iterdir()) and not overwrite:
        raise FileExistsError(f"Artifact directory is not empty: {destination}")
    destination.mkdir(parents=True, exist_ok=True)

    layout_output = destination / "layout.json"
    route_output = destination / "route.json"
    model_output = destination / "model.xml"
    preview_output = destination / "preview.png"
    mesh_output = destination / "maze_prototype.stl"
    metadata_output = destination / "metadata.json"

    save_json_layout(layout, layout_output)
    route_output.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "maze_id": layout_path.stem,
                "coordinate_frame": "lower_left_xy_m",
                "points": layout["waypoints"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    model_output.write_text(build_mjcf(layout), encoding="utf-8")
    render_preview(layout, preview_output)
    mesh = build_prototype_mesh(layout, config)
    mesh.write_ascii_stl(mesh_output, layout_path.stem)

    outputs = (layout_output, route_output, model_output, preview_output, mesh_output)
    metadata = {
        "schema_version": 1,
        "maze_id": layout_path.stem,
        "source_layout": str(layout_path),
        "single_source_of_truth": "layout.json",
        "print_config": asdict(config),
        "print_validation": validation,
        "final_fit_requested": bool(request_final_fit),
        "files": {
            item.name: {"sha256": _sha256(item), "bytes": item.stat().st_size}
            for item in outputs
        },
    }
    metadata_output.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("layout", type=Path)
    parser.add_argument("--output-root", type=Path, default=Path("printable_mazes"))
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--final-fit", action="store_true")
    args = parser.parse_args()
    destination = export_maze_artifact(
        args.layout,
        args.output_root,
        overwrite=args.overwrite,
        request_final_fit=args.final_fit,
    )
    print(f"Exported prototype maze package: {destination}")


if __name__ == "__main__":
    main()
