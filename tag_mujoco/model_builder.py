"""Procedurally build a MuJoCo model of the current TAG maze."""

from __future__ import annotations

import math
from html import escape
from typing import Any, Dict, Iterable, List, Sequence, Tuple


FLOOR_THICKNESS = 0.006
FLOOR_STRIP_HEIGHT = 0.0015
WALL_THICKNESS = 0.0022
WALL_HEIGHT = 0.012
OUTER_WALL_THICKNESS = 0.003
MIN_WALL_LENGTH = 0.0015
BOARD_CENTER_Z = 0.0
TILT_LIMIT_RAD = math.radians(10.0)


def _fmt(values: Iterable[float]) -> str:
    return " ".join(f"{value:.9g}" for value in values)


def _merge_intervals(
    intervals: Sequence[Tuple[float, float]], lower: float, upper: float
) -> List[Tuple[float, float]]:
    clipped = sorted(
        (max(lower, start), min(upper, end))
        for start, end in intervals
        if end > lower and start < upper
    )
    merged: List[Tuple[float, float]] = []
    for start, end in clipped:
        if end <= start:
            continue
        if merged and start <= merged[-1][1] + 1e-9:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _floor_spans(
    width: float,
    height: float,
    holes: Sequence[Sequence[float]],
    radii: Sequence[float],
    strip_height: float = FLOOR_STRIP_HEIGHT,
) -> Iterable[Tuple[float, float, float, float]]:
    """Yield supported rectangles as x0, x1, y0, y1 around circular holes."""
    rows = max(1, math.ceil(height / max(strip_height, 1e-6)))
    for row in range(rows):
        y0 = row * height / rows
        y1 = (row + 1) * height / rows
        yc = 0.5 * (y0 + y1)
        cuts: List[Tuple[float, float]] = []
        for (cx, cy), radius in zip(holes, radii):
            dy = abs(yc - cy)
            if dy >= radius:
                continue
            half_chord = math.sqrt(max(0.0, radius * radius - dy * dy))
            cuts.append((cx - half_chord, cx + half_chord))
        cuts = _merge_intervals(cuts, 0.0, width)
        cursor = 0.0
        for start, end in cuts:
            if start - cursor > 1e-5:
                yield cursor, start, y0, y1
            cursor = max(cursor, end)
        if width - cursor > 1e-5:
            yield cursor, width, y0, y1


def _box_geom(
    name: str,
    center: Tuple[float, float, float],
    half_size: Tuple[float, float, float],
    rgba: str,
    euler_z: float = 0.0,
    collision: bool = True,
    geom_class: str = "",
) -> str:
    attrs = [
        f'name="{escape(name)}"',
        'type="box"',
        f'pos="{_fmt(center)}"',
        f'size="{_fmt(half_size)}"',
        f'rgba="{rgba}"',
    ]
    if abs(euler_z) > 1e-12:
        attrs.append(f'euler="0 0 {euler_z:.9g}"')
    if not collision:
        attrs.extend(['contype="0"', 'conaffinity="0"', 'mass="0"'])
    if geom_class:
        attrs.append(f'class="{escape(geom_class)}"')
    return "<geom " + " ".join(attrs) + "/>"


def _wall_geom(
    name: str,
    p0: Tuple[float, float],
    p1: Tuple[float, float],
    width: float,
    height: float,
    board_width: float,
    board_height: float,
) -> str | None:
    dx = p1[0] - p0[0]
    dy = p1[1] - p0[1]
    length = math.hypot(dx, dy)
    if length < MIN_WALL_LENGTH:
        return None
    center = (
        0.5 * (p0[0] + p1[0]) - board_width / 2.0,
        0.5 * (p0[1] + p1[1]) - board_height / 2.0,
        height / 2.0,
    )
    return _box_geom(
        name,
        center,
        (length / 2.0, width / 2.0, height / 2.0),
        "0.72 0.55 0.31 1",
        math.atan2(dy, dx),
        geom_class="wall",
    )


def build_mjcf(layout: Dict[str, Any], model_params: Dict[str, Any] | None = None) -> str:
    model_params = model_params or {}
    width = float(layout["board_width"])
    height = float(layout["board_height"])
    ball_radius = float(layout["ball_radius"])
    wall_thickness = float(layout.get("wall_thickness", WALL_THICKNESS))
    wall_height = float(layout.get("wall_height", WALL_HEIGHT))
    ball_mass = float(model_params.get("ball_mass_kg", 0.011))
    floor_friction = tuple(model_params.get("floor_friction", (0.30, 0.015, 0.002)))
    wall_friction = tuple(model_params.get("wall_friction", (0.35, 0.020, 0.003)))
    ball_friction = tuple(model_params.get("ball_friction", (0.22, 0.012, 0.002)))
    wall_restitution = float(model_params.get("wall_restitution", 0.0))
    if wall_restitution <= 0.0:
        wall_damping_ratio = 1.0
    else:
        log_restitution = math.log(max(1.0e-6, min(0.999, wall_restitution)))
        wall_damping_ratio = -log_restitution / math.sqrt(
            math.pi**2 + log_restitution**2
        )
    actuator_kp = float(model_params.get("actuator_kp", 90.0))
    actuator_kv = float(model_params.get("actuator_kv", 8.0))
    start_x, start_y = map(float, layout["waypoints"][0])

    floor_geoms: List[str] = []
    for index, (x0, x1, y0, y1) in enumerate(
        _floor_spans(width, height, layout["holes"], layout["hole_radii"])
    ):
        floor_geoms.append(
            _box_geom(
                f"floor_{index}",
                (
                    0.5 * (x0 + x1) - width / 2.0,
                    0.5 * (y0 + y1) - height / 2.0,
                    -FLOOR_THICKNESS / 2.0,
                ),
                (
                    max(1e-6, 0.5 * (x1 - x0)),
                    max(1e-6, 0.5 * (y1 - y0)),
                    FLOOR_THICKNESS / 2.0,
                ),
                "0.70 0.63 0.48 1",
                geom_class="floor",
            )
        )

    wall_geoms: List[str] = []
    wall_index = 0
    for x0, x1, y in layout["walls_h"]:
        geom = _wall_geom(
            f"wall_h_{wall_index}",
            (float(x0), float(y)),
            (float(x1), float(y)),
            wall_thickness,
            wall_height,
            width,
            height,
        )
        if geom:
            wall_geoms.append(geom)
            wall_index += 1
    for y0, y1, x in layout["walls_v"]:
        geom = _wall_geom(
            f"wall_v_{wall_index}",
            (float(x), float(y0)),
            (float(x), float(y1)),
            wall_thickness,
            wall_height,
            width,
            height,
        )
        if geom:
            wall_geoms.append(geom)
            wall_index += 1
    for x0, y0, x1, y1 in layout["walls_angled"]:
        geom = _wall_geom(
            f"wall_a_{wall_index}",
            (float(x0), float(y0)),
            (float(x1), float(y1)),
            wall_thickness,
            wall_height,
            width,
            height,
        )
        if geom:
            wall_geoms.append(geom)
            wall_index += 1

    half_w = width / 2.0
    half_h = height / 2.0
    outer_geoms = [
        _box_geom(
            "rim_bottom",
            (0.0, -half_h - OUTER_WALL_THICKNESS / 2.0, WALL_HEIGHT / 2.0),
            (half_w + OUTER_WALL_THICKNESS, OUTER_WALL_THICKNESS / 2.0, WALL_HEIGHT / 2.0),
            "0.36 0.21 0.10 1",
            geom_class="wall",
        ),
        _box_geom(
            "rim_top",
            (0.0, half_h + OUTER_WALL_THICKNESS / 2.0, WALL_HEIGHT / 2.0),
            (half_w + OUTER_WALL_THICKNESS, OUTER_WALL_THICKNESS / 2.0, WALL_HEIGHT / 2.0),
            "0.36 0.21 0.10 1",
            geom_class="wall",
        ),
        _box_geom(
            "rim_left",
            (-half_w - OUTER_WALL_THICKNESS / 2.0, 0.0, WALL_HEIGHT / 2.0),
            (OUTER_WALL_THICKNESS / 2.0, half_h, WALL_HEIGHT / 2.0),
            "0.36 0.21 0.10 1",
            geom_class="wall",
        ),
        _box_geom(
            "rim_right",
            (half_w + OUTER_WALL_THICKNESS / 2.0, 0.0, WALL_HEIGHT / 2.0),
            (OUTER_WALL_THICKNESS / 2.0, half_h, WALL_HEIGHT / 2.0),
            "0.36 0.21 0.10 1",
            geom_class="wall",
        ),
    ]

    hole_markers = []
    for index, ((x, y), radius) in enumerate(
        zip(layout["holes"], layout["hole_radii"])
    ):
        hole_markers.append(
            f'<geom name="hole_marker_{index}" type="cylinder" '
            f'pos="{x - half_w:.9g} {y - half_h:.9g} {-FLOOR_THICKNESS - 0.0005:.9g}" '
            f'size="{float(radius):.9g} 0.0005" rgba="0.035 0.035 0.035 1" '
            'contype="0" conaffinity="0" mass="0"/>'
        )

    start_local = (start_x - half_w, start_y - half_h)
    goal_x, goal_y = map(float, layout["waypoints"][-1])
    goal_local = (goal_x - half_w, goal_y - half_h)
    model = f"""
<mujoco model="tag_custom_maze">
  <compiler angle="radian" inertiafromgeom="auto"/>
  <option timestep="0.001" gravity="0 0 -9.81" integrator="implicitfast" solver="Newton" iterations="12" tolerance="1e-9"/>
  <size nconmax="4000" njmax="12000"/>
  <visual>
    <global offwidth="900" offheight="800"/>
    <quality shadowsize="2048"/>
    <map znear="0.01" zfar="3"/>
  </visual>
  <default>
    <default class="floor">
      <geom condim="6" friction="{_fmt(floor_friction)}" solref="0.004 1" solimp="0.95 0.99 0.001" density="650"/>
    </default>
    <default class="wall">
      <geom condim="6" friction="{_fmt(wall_friction)}" solref="0.003 {wall_damping_ratio:.9g}" solimp="0.95 0.99 0.001" density="700"/>
    </default>
  </default>
  <worldbody>
    <light name="key" pos="0 -0.15 0.55" dir="0 0 -1" diffuse="0.9 0.9 0.9"/>
    <light name="fill" pos="-0.25 0.2 0.35" dir="0.4 -0.3 -1" diffuse="0.45 0.45 0.45"/>
    <camera name="top" pos="0 0 0.43" quat="1 0 0 0" mode="fixed" fovy="37"/>
    <geom name="catch_tray" type="box" pos="0 0 -0.085" size="0.18 0.16 0.004" rgba="0.08 0.08 0.09 1" friction="0.5 0.02 0.003"/>
    <body name="tilt_x_frame" pos="0 0 {BOARD_CENTER_Z:.9g}">
      <inertial pos="0 0 0" mass="0.02" diaginertia="0.0001 0.0001 0.0001"/>
      <joint name="tilt_x" type="hinge" axis="1 0 0" range="{-TILT_LIMIT_RAD:.9g} {TILT_LIMIT_RAD:.9g}" damping="0.8" armature="0.01"/>
      <body name="board" pos="0 0 0">
        <joint name="tilt_y" type="hinge" axis="0 1 0" range="{-TILT_LIMIT_RAD:.9g} {TILT_LIMIT_RAD:.9g}" damping="0.8" armature="0.01"/>
        {''.join(floor_geoms)}
        {''.join(hole_markers)}
        {''.join(wall_geoms)}
        {''.join(outer_geoms)}
        <site name="start" type="cylinder" pos="{start_local[0]:.9g} {start_local[1]:.9g} 0.0002" size="0.004 0.0002" rgba="0.1 0.75 0.2 0.75"/>
        <site name="goal" type="cylinder" pos="{goal_local[0]:.9g} {goal_local[1]:.9g} 0.00025" size="0.004 0.00025" rgba="0.9 0.1 0.08 0.8"/>
      </body>
    </body>
    <body name="ball" pos="{start_local[0]:.9g} {start_local[1]:.9g} {ball_radius + 0.001:.9g}">
      <freejoint name="ball_free"/>
      <geom name="ball_geom" type="sphere" condim="6" size="{ball_radius:.9g}" mass="{ball_mass:.9g}" rgba="0.10 0.24 0.92 1" friction="{_fmt(ball_friction)}" solref="0.0025 1" solimp="0.97 0.995 0.001"/>
    </body>
  </worldbody>
  <actuator>
    <position name="servo_x" joint="tilt_x" kp="{actuator_kp:.9g}" kv="{actuator_kv:.9g}" ctrlrange="{-TILT_LIMIT_RAD:.9g} {TILT_LIMIT_RAD:.9g}" forcerange="-30 30"/>
    <position name="servo_y" joint="tilt_y" kp="{actuator_kp:.9g}" kv="{actuator_kv:.9g}" ctrlrange="{-TILT_LIMIT_RAD:.9g} {TILT_LIMIT_RAD:.9g}" forcerange="-30 30"/>
  </actuator>
</mujoco>
"""
    return model.strip() + "\n"
