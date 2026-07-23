"""Load the existing custom-maze layout without importing the ROS package."""

from __future__ import annotations

import runpy
import json
from pathlib import Path
from typing import Any, Dict


HERE = Path(__file__).resolve().parent
DEFAULT_LAYOUT_PATH = (
    HERE.parent
    / "cyberrunner_dreamer"
    / "cyberrunner_dreamer"
    / "cyberrunner_layout_custom.py"
)


def load_layout(path: Path = DEFAULT_LAYOUT_PATH) -> Dict[str, Any]:
    namespace = runpy.run_path(str(path))
    layout = namespace["cyberrunner_dxf_layout"]
    required = {
        "board_width",
        "board_height",
        "ball_radius",
        "walls_h",
        "walls_v",
        "walls_angled",
        "holes",
        "hole_radii",
        "waypoints",
    }
    missing = required.difference(layout)
    if missing:
        raise KeyError(f"Layout is missing required keys: {sorted(missing)}")
    if len(layout["holes"]) != len(layout["hole_radii"]):
        raise ValueError("Each hole must have exactly one radius")
    return layout


def load_json_layout(path: Path) -> Dict[str, Any]:
    layout = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "board_width",
        "board_height",
        "ball_radius",
        "walls_h",
        "walls_v",
        "walls_angled",
        "holes",
        "hole_radii",
        "waypoints",
    }
    missing = required.difference(layout)
    if missing:
        raise KeyError(f"Layout is missing required keys: {sorted(missing)}")
    return layout


def save_json_layout(layout: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(layout, indent=2) + "\n", encoding="utf-8")

