"""Generate reproducible, full-board mazes with one valid solution route."""

from __future__ import annotations

import collections
import math
import random
from typing import Dict, Iterable, List, Sequence, Set, Tuple


Cell = Tuple[int, int]
BOARD_WIDTH = 0.259
BOARD_HEIGHT = 0.229
BALL_RADIUS = 0.006
HOLE_RADIUS = 0.0075
WALL_THICKNESS = 0.0022
WALL_HEIGHT = 0.012


def _neighbors(cell: Cell, columns: int, rows: int) -> Iterable[Cell]:
    column, row = cell
    for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        candidate = column + dc, row + dr
        if 0 <= candidate[0] < columns and 0 <= candidate[1] < rows:
            yield candidate


def _remove_wall(
    first: Cell,
    second: Cell,
    horizontal: Set[Tuple[int, int]],
    vertical: Set[Tuple[int, int]],
) -> None:
    c0, r0 = first
    c1, r1 = second
    if c0 != c1:
        vertical.discard((max(c0, c1), r0))
    else:
        horizontal.discard((c0, max(r0, r1)))


def _connected_neighbors(
    cell: Cell,
    columns: int,
    rows: int,
    horizontal: Set[Tuple[int, int]],
    vertical: Set[Tuple[int, int]],
) -> Iterable[Cell]:
    c0, r0 = cell
    for c1, r1 in _neighbors(cell, columns, rows):
        if c0 != c1:
            blocked = (max(c0, c1), r0) in vertical
        else:
            blocked = (c0, max(r0, r1)) in horizontal
        if not blocked:
            yield c1, r1


def _shortest_path(
    start: Cell,
    goal: Cell,
    columns: int,
    rows: int,
    horizontal: Set[Tuple[int, int]],
    vertical: Set[Tuple[int, int]],
) -> List[Cell]:
    queue = collections.deque([start])
    parent: Dict[Cell, Cell | None] = {start: None}
    while queue:
        cell = queue.popleft()
        if cell == goal:
            break
        for neighbor in _connected_neighbors(
            cell, columns, rows, horizontal, vertical
        ):
            if neighbor not in parent:
                parent[neighbor] = cell
                queue.append(neighbor)
    if goal not in parent:
        raise RuntimeError("Generated maze has no start-to-goal path")
    path = []
    cell: Cell | None = goal
    while cell is not None:
        path.append(cell)
        cell = parent[cell]
    return list(reversed(path))


def _compress_waypoints(cells: Sequence[Cell]) -> List[Cell]:
    if len(cells) <= 2:
        return list(cells)
    result = [cells[0]]
    previous_direction = (
        cells[1][0] - cells[0][0],
        cells[1][1] - cells[0][1],
    )
    for index in range(1, len(cells) - 1):
        direction = (
            cells[index + 1][0] - cells[index][0],
            cells[index + 1][1] - cells[index][1],
        )
        if direction != previous_direction:
            result.append(cells[index])
        previous_direction = direction
    result.append(cells[-1])
    return result


def generate_maze(
    seed: int,
    columns: int = 12,
    rows: int = 10,
    loop_fraction: float = 0.01,
    desired_holes: int = 30,
    start: Cell | None = None,
    goal: Cell | None = None,
    edge_jitter_fraction: float = 0.10,
) -> dict:
    """Generate a dense maze, add limited loops, then place nearby hazards."""
    if columns < 3 or rows < 3:
        raise ValueError("Maze grid must be at least 3 by 3")
    rng = random.Random(seed)
    horizontal: Set[Tuple[int, int]] = {
        (column, boundary)
        for column in range(columns)
        for boundary in range(1, rows)
    }
    vertical: Set[Tuple[int, int]] = {
        (boundary, row)
        for boundary in range(1, columns)
        for row in range(rows)
    }

    # Randomized depth-first traversal creates a fully connected perfect maze.
    start_tree = (rng.randrange(columns), rng.randrange(rows))
    visited = {start_tree}
    stack = [start_tree]
    while stack:
        current = stack[-1]
        unvisited = [
            cell
            for cell in _neighbors(current, columns, rows)
            if cell not in visited
        ]
        if not unvisited:
            stack.pop()
            continue
        next_cell = rng.choice(unvisited)
        _remove_wall(current, next_cell, horizontal, vertical)
        visited.add(next_cell)
        stack.append(next_cell)

    # A few extra openings reduce the chance that one mistake forces a reset.
    remaining = [("h", wall) for wall in horizontal] + [
        ("v", wall) for wall in vertical
    ]
    rng.shuffle(remaining)
    extra_openings = round(loop_fraction * (columns * (rows - 1) + rows * (columns - 1)))
    for orientation, wall in remaining[:extra_openings]:
        (horizontal if orientation == "h" else vertical).discard(wall)

    start = start or (0, rows - 1)
    goal = goal or (columns - 1, 0)
    if start == goal:
        raise ValueError("Maze start and goal must differ")
    for name, cell in (("start", start), ("goal", goal)):
        if not (0 <= cell[0] < columns and 0 <= cell[1] < rows):
            raise ValueError(f"Maze {name} cell is outside the grid: {cell}")
    edge_jitter_fraction = float(edge_jitter_fraction)
    if not 0.0 <= edge_jitter_fraction <= 0.10:
        raise ValueError("edge_jitter_fraction must be in [0, 0.10]")
    solution_cells = _shortest_path(
        start, goal, columns, rows, horizontal, vertical
    )
    solution_set = set(solution_cells)

    cell_width = BOARD_WIDTH / columns
    cell_height = BOARD_HEIGHT / rows
    # Small seeded variations make the maze resemble the irregular original
    # geometry while preserving safe minimum corridor widths and fixed borders.
    column_edges = [0.0] + [
        index * cell_width
        + rng.uniform(-edge_jitter_fraction, edge_jitter_fraction) * cell_width
        for index in range(1, columns)
    ] + [BOARD_WIDTH]
    row_edges = [0.0] + [
        index * cell_height
        + rng.uniform(-edge_jitter_fraction, edge_jitter_fraction) * cell_height
        for index in range(1, rows)
    ] + [BOARD_HEIGHT]

    def cell_center(cell: Cell) -> List[float]:
        column, row = cell
        return [
            0.5 * (column_edges[column] + column_edges[column + 1]),
            0.5 * (row_edges[row] + row_edges[row + 1]),
        ]

    compressed = _compress_waypoints(solution_cells)
    waypoints = [cell_center(cell) for cell in compressed]

    walls_h = [
        [column_edges[column], column_edges[column + 1], row_edges[boundary]]
        for column, boundary in sorted(horizontal)
    ]
    walls_v = [
        [row_edges[row], row_edges[row + 1], column_edges[boundary]]
        for boundary, row in sorted(vertical)
    ]

    # Place holes in branches not used by the selected solution. This preserves
    # a ball-clear route while still exposing hole geometry around the maze.
    hole_cells = [
        (column, row)
        for row in range(rows)
        for column in range(columns)
        if (column, row) not in solution_set and (column, row) not in (start, goal)
    ]
    rng.shuffle(hole_cells)

    def route_distance(cell: Cell) -> int:
        return min(
            abs(cell[0] - route_cell[0]) + abs(cell[1] - route_cell[1])
            for route_cell in solution_cells
        )

    # Farthest-point sampling spreads hazards over the whole board. The route
    # distance tie-break keeps them in nearby branches instead of remote zones.
    selected_holes: List[Cell] = []
    remaining_holes = list(hole_cells)
    while remaining_holes and len(selected_holes) < desired_holes:
        if not selected_holes:
            best = min(remaining_holes, key=route_distance)
        else:
            best = max(
                remaining_holes,
                key=lambda cell: (
                    min(
                        (cell[0] - chosen[0]) ** 2 + (cell[1] - chosen[1]) ** 2
                        for chosen in selected_holes
                    ),
                    -route_distance(cell),
                ),
            )
        selected_holes.append(best)
        remaining_holes.remove(best)
    holes = [cell_center(cell) for cell in selected_holes]

    return {
        "name": f"full_board_seed_{seed}",
        "generator": "dense_irregular_depth_first_grid_v2",
        "seed": seed,
        "board_width": BOARD_WIDTH,
        "board_height": BOARD_HEIGHT,
        "ball_radius": BALL_RADIUS,
        "wall_thickness": WALL_THICKNESS,
        "wall_height": WALL_HEIGHT,
        "grid_columns": columns,
        "grid_rows": rows,
        "column_edges": column_edges,
        "row_edges": row_edges,
        "grid_horizontal_walls": [list(wall) for wall in sorted(horizontal)],
        "grid_vertical_walls": [list(wall) for wall in sorted(vertical)],
        "start_cell": list(start),
        "goal_cell": list(goal),
        "generation_parameters": {
            "columns": columns,
            "rows": rows,
            "loop_fraction": loop_fraction,
            "desired_holes": desired_holes,
            "start": list(start),
            "goal": list(goal),
            "edge_jitter_fraction": edge_jitter_fraction,
        },
        "solution_cells": [list(cell) for cell in solution_cells],
        "hole_cells": [list(cell) for cell in selected_holes],
        "walls_h": walls_h,
        "walls_v": walls_v,
        "walls_angled": [],
        "holes": holes,
        "hole_radii": [HOLE_RADIUS] * len(holes),
        "waypoints": waypoints,
    }


def validate_generated_layout(layout: dict) -> dict:
    width = float(layout["board_width"])
    height = float(layout["board_height"])
    fixed_dimensions = math.isclose(width, BOARD_WIDTH) and math.isclose(
        height, BOARD_HEIGHT
    )
    holes_inside = all(
        radius < x < width - radius and radius < y < height - radius
        for (x, y), radius in zip(layout["holes"], layout["hole_radii"])
    )
    columns = int(layout["grid_columns"])
    rows = int(layout["grid_rows"])
    solution = [tuple(cell) for cell in layout["solution_cells"]]
    solution_set = set(solution)
    hole_cells = {tuple(cell) for cell in layout["hole_cells"]}
    route_clear = solution_set.isdisjoint(hole_cells)
    waypoints_inside = all(
        layout["ball_radius"] <= x <= width - layout["ball_radius"]
        and layout["ball_radius"] <= y <= height - layout["ball_radius"]
        for x, y in layout["waypoints"]
    )

    horizontal = {tuple(wall) for wall in layout["grid_horizontal_walls"]}
    vertical = {tuple(wall) for wall in layout["grid_vertical_walls"]}
    route_connected = bool(solution) and solution[0] == tuple(layout["start_cell"])
    route_connected = route_connected and solution[-1] == tuple(layout["goal_cell"])
    for first, second in zip(solution, solution[1:]):
        c0, r0 = first
        c1, r1 = second
        adjacent = abs(c1 - c0) + abs(r1 - r0) == 1
        blocked = (
            (max(c0, c1), r0) in vertical
            if c0 != c1
            else (c0, max(r0, r1)) in horizontal
        )
        route_connected = route_connected and adjacent and not blocked
    center_x, center_y = width / 2.0, height / 2.0
    center_covered = any(
        x0 <= center_x <= x1 and abs(y - center_y) < height / layout["grid_rows"]
        for x0, x1, y in layout["walls_h"]
    ) or any(
        y0 <= center_y <= y1 and abs(x - center_x) < width / layout["grid_columns"]
        for y0, y1, x in layout["walls_v"]
    )
    return {
        "fixed_dimensions": fixed_dimensions,
        "holes_inside_board": holes_inside,
        "center_used_by_maze": center_covered,
        "solution_route_connected": route_connected,
        "solution_route_clear_of_holes": route_clear,
        "waypoints_inside_board": waypoints_inside,
        "solution_cell_count": len(layout["solution_cells"]),
        "waypoint_count": len(layout["waypoints"]),
        "hole_count": len(layout["holes"]),
        "wall_segment_count": len(layout["walls_h"]) + len(layout["walls_v"]),
        "passed": (
            fixed_dimensions
            and holes_inside
            and center_covered
            and route_connected
            and route_clear
            and waypoints_inside
        ),
    }
