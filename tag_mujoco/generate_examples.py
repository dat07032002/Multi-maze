"""Generate seeded full-board layouts, validate them, and render comparisons."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from maze_generator import generate_maze, validate_generated_layout
from maze_layout import load_layout, save_json_layout
from route_planner import PlannerConfig, apply_safe_route
from simulator import TagMazeSim


HERE = Path(__file__).resolve().parent
GENERATED = HERE / "generated_mazes"
OUTPUTS = HERE / "outputs"
# These seeds balance roughly 50 direction changes with enough branch cells to
# distribute 30 hazards across the board instead of packing them into clusters.
SEEDS = (970, 1024, 765)


def draw_blueprint(layout: dict, size=(600, 530)) -> Image.Image:
    width_px, height_px = size
    margin = 34
    board_width = float(layout["board_width"])
    board_height = float(layout["board_height"])
    scale = min(
        (width_px - 2 * margin) / board_width,
        (height_px - 2 * margin) / board_height,
    )
    x0 = (width_px - board_width * scale) / 2.0
    y0 = (height_px - board_height * scale) / 2.0

    def point(x, y):
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
    for (x, y), radius in zip(layout["holes"], layout["hole_radii"]):
        cx, cy = point(x, y)
        r = radius * scale
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#161616")
    route = [point(x, y) for x, y in layout["waypoints"]]
    draw.line(route, fill="#00a6c8", width=5, joint="curve")
    for cx, cy in route:
        draw.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill="#00a6c8")
    sx, sy = route[0]
    gx, gy = route[-1]
    draw.ellipse([sx - 9, sy - 9, sx + 9, sy + 9], fill="#26b34a", outline="white", width=2)
    draw.ellipse([gx - 9, gy - 9, gx + 9, gy + 9], fill="#df3b2f", outline="white", width=2)
    return image


def add_title(image: Image.Image, title: str) -> Image.Image:
    result = Image.new("RGB", (image.width, image.height + 38), "white")
    result.paste(image, (0, 38))
    ImageDraw.Draw(result).text((12, 12), title, fill="black")
    return result


def main() -> None:
    GENERATED.mkdir(parents=True, exist_ok=True)
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    original = load_layout()
    original_blueprint = add_title(
        draw_blueprint(original), "ORIGINAL: PLAN + RECORDED ROUTE"
    )
    original_blueprint.save(OUTPUTS / "original_maze_plan.png")
    original_sim = TagMazeSim(original)
    original_render = add_title(
        Image.fromarray(original_sim.render(width=600, height=530)),
        "ORIGINAL: MUJOCO REFERENCE",
    )
    original_render.save(OUTPUTS / "original_maze_mujoco.png")
    blueprints = [original_blueprint]
    renders = [original_render]
    validations = {
        "original_reference": {
            "wall_segment_count": (
                len(original["walls_h"])
                + len(original["walls_v"])
                + len(original["walls_angled"])
            ),
            "hole_count": len(original["holes"]),
            "waypoint_count": len(original["waypoints"]),
        }
    }
    for seed in SEEDS:
        layout = generate_maze(seed)
        validation = validate_generated_layout(layout)
        if not validation["passed"]:
            raise RuntimeError(f"Seed {seed} failed validation: {validation}")
        layout, route_validation = apply_safe_route(layout, PlannerConfig())
        validation["continuous_route_clearance"] = {
            "passed": route_validation.passed,
            "minimum_clearance_m": route_validation.minimum_clearance_m,
            "required_margin_m": route_validation.required_margin_m,
            "sampled_points": route_validation.sampled_points,
            "route_length_m": route_validation.route_length_m,
        }
        validation["passed"] = bool(validation["passed"] and route_validation.passed)
        path = GENERATED / f"maze_seed_{seed}.json"
        save_json_layout(layout, path)
        validations[str(seed)] = validation
        blueprints.append(
            add_title(draw_blueprint(layout), f"SEED {seed}: PLAN + COMPUTED ROUTE")
        )
        blueprints[-1].save(OUTPUTS / f"maze_seed_{seed}_plan.png")
        sim = TagMazeSim(layout)
        sim.save_xml(GENERATED / f"maze_seed_{seed}.xml")
        start = np.asarray(layout["waypoints"][0], dtype=float)
        sim.step(400)
        settled = sim.ball_board_position()
        validation["start_stable_on_level_board"] = bool(
            settled[2] > 0.0 and np.linalg.norm(settled[:2] - start) < 0.003
        )
        sim.reset(ball_xy=layout["holes"][0], settle_steps=0)
        sim.step(700)
        validation["physical_hole_allows_fall"] = bool(
            sim.ball_board_position()[2] < -sim.ball_radius
        )
        validation["passed"] = bool(
            validation["passed"]
            and validation["start_stable_on_level_board"]
            and validation["physical_hole_allows_fall"]
        )
        if not validation["passed"]:
            raise RuntimeError(f"Seed {seed} failed physics validation: {validation}")
        sim.reset()
        renders.append(
            add_title(
                Image.fromarray(sim.render(width=600, height=530)),
                f"SEED {seed}: MUJOCO PHYSICS MODEL",
            )
        )
        renders[-1].save(OUTPUTS / f"maze_seed_{seed}_mujoco.png")

    panel_width = blueprints[0].width
    panel_height = blueprints[0].height
    comparison = Image.new("RGB", (panel_width * len(blueprints), panel_height * 2), "white")
    for index, image in enumerate(blueprints):
        comparison.paste(image, (index * panel_width, 0))
    for index, image in enumerate(renders):
        comparison.paste(image, (index * panel_width, panel_height))
    comparison.save(OUTPUTS / "complex_maze_comparison.png")
    (OUTPUTS / "generated_maze_validation.json").write_text(
        json.dumps(validations, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(validations, indent=2))
    print(f"Saved {OUTPUTS / 'complex_maze_comparison.png'}")


if __name__ == "__main__":
    main()
