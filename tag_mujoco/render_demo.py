"""Render the reconstructed board and two physics states for visual inspection."""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

from simulator import TagMazeSim


HERE = Path(__file__).resolve().parent
OUTPUTS = HERE / "outputs"


def _save(image, name: str) -> Path:
    path = OUTPUTS / name
    Image.fromarray(image).save(path)
    return path


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    sim = TagMazeSim()

    sim.reset()
    level = sim.render()
    level_path = _save(level, "maze_level.png")

    sim.reset([0.105, 0.125])
    sim.set_tilt(math.radians(-5.0), math.radians(5.0))
    sim.step(900)
    tilted = sim.render()
    tilted_path = _save(tilted, "maze_tilted.png")

    hole = sim.layout["holes"][0]
    sim.reset(hole, settle_steps=0)
    before_hole = sim.render()
    sim.step(700)
    after_hole = sim.render()
    _save(before_hole, "hole_before.png")
    _save(after_hole, "hole_after.png")

    panels = [
        (Image.fromarray(level), "LEVEL BOARD / START POSITION"),
        (Image.fromarray(tilted), "BOARD TILTED / BALL ROLLING"),
        (Image.fromarray(before_hole), "BALL CENTERED OVER PHYSICAL HOLE"),
        (Image.fromarray(after_hole), "BALL FALLEN TO CATCH TRAY"),
    ]
    panel_width, panel_height = panels[0][0].size
    title_height = 42
    canvas = Image.new(
        "RGB", (panel_width * 2, (panel_height + title_height) * 2), "white"
    )
    draw = ImageDraw.Draw(canvas)
    for index, (panel, title) in enumerate(panels):
        col, row = index % 2, index // 2
        x = col * panel_width
        y = row * (panel_height + title_height)
        canvas.paste(panel, (x, y + title_height))
        draw.text((x + 14, y + 13), title, fill="black")
    overview_path = OUTPUTS / "simulation_overview.png"
    canvas.save(overview_path)

    print(f"Rendered {level_path}")
    print(f"Rendered {tilted_path}")
    print(f"Rendered {overview_path}")


if __name__ == "__main__":
    main()
