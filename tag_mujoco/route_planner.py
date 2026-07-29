"""Clearance-aware route planning for a finite-radius TAG ball."""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import numpy as np


Point = Tuple[float, float]


@dataclass(frozen=True)
class PlannerConfig:
    grid_resolution_m: float = 0.002
    safety_margin_m: float = 0.0015
    route_spacing_m: float = 0.012
    clearance_cost_weight: float = 0.35
    clearance_cost_scale_m: float = 0.008
    corner_rounding_radius_m: float = 0.006
    corner_rounding_samples: int = 5


@dataclass(frozen=True)
class RouteValidation:
    passed: bool
    minimum_clearance_m: float
    required_margin_m: float
    sampled_points: int
    route_length_m: float


def _distance_to_segment(points: np.ndarray, start: Point, end: Point) -> np.ndarray:
    start_array = np.asarray(start, dtype=np.float64)
    vector = np.asarray(end, dtype=np.float64) - start_array
    length_squared = float(np.dot(vector, vector))
    if length_squared <= 1e-18:
        return np.linalg.norm(points - start_array, axis=-1)
    fraction = np.sum((points - start_array) * vector, axis=-1) / length_squared
    fraction = np.clip(fraction, 0.0, 1.0)
    projection = start_array + fraction[..., None] * vector
    return np.linalg.norm(points - projection, axis=-1)


def signed_ball_clearance(layout: Dict[str, Any], points: np.ndarray) -> np.ndarray:
    """Return clearance between the ball surface and the nearest obstacle.

    Positive values are collision free. Zero means contact. Negative values
    mean that the finite-radius ball overlaps a wall, hole, or board boundary.
    """
    points = np.asarray(points, dtype=np.float64)
    if points.shape[-1] != 2:
        raise ValueError(f"Expected points ending in XY, received {points.shape}")
    width = float(layout["board_width"])
    height = float(layout["board_height"])
    ball_radius = float(layout["ball_radius"])
    wall_half = 0.5 * float(layout.get("wall_thickness", 0.0022))

    clearance = np.minimum.reduce(
        (
            points[..., 0],
            width - points[..., 0],
            points[..., 1],
            height - points[..., 1],
        )
    ) - ball_radius

    for x0, x1, y in layout.get("walls_h", []):
        distance = _distance_to_segment(points, (x0, y), (x1, y))
        clearance = np.minimum(clearance, distance - wall_half - ball_radius)
    for y0, y1, x in layout.get("walls_v", []):
        distance = _distance_to_segment(points, (x, y0), (x, y1))
        clearance = np.minimum(clearance, distance - wall_half - ball_radius)
    for x0, y0, x1, y1 in layout.get("walls_angled", []):
        distance = _distance_to_segment(points, (x0, y0), (x1, y1))
        clearance = np.minimum(clearance, distance - wall_half - ball_radius)
    for (x, y), radius in zip(
        layout.get("holes", []), layout.get("hole_radii", [])
    ):
        distance = np.linalg.norm(points - np.asarray((x, y)), axis=-1)
        clearance = np.minimum(clearance, distance - float(radius) - ball_radius)
    return clearance


def signed_hole_clearance(layout: Dict[str, Any], points: np.ndarray) -> np.ndarray:
    """Return clearance between the ball surface and the nearest hole only.

    Deliberately excludes walls and the board boundary. Touching a wall is not a
    failure, it merely blocks, and normal corridor travel runs within a few
    millimetres of one, so a wall-inclusive signal would penalize simply being
    in a corridor. Falling into a hole is the failure this measures.
    """
    points = np.asarray(points, dtype=np.float64)
    if points.shape[-1] != 2:
        raise ValueError(f"Expected points ending in XY, received {points.shape}")
    ball_radius = float(layout["ball_radius"])
    holes = layout.get("holes", [])
    if not holes:
        return np.full(points.shape[:-1], np.inf, dtype=np.float64)
    clearance = np.full(points.shape[:-1], np.inf, dtype=np.float64)
    for (x, y), radius in zip(holes, layout.get("hole_radii", [])):
        distance = np.linalg.norm(points - np.asarray((x, y)), axis=-1)
        clearance = np.minimum(clearance, distance - float(radius) - ball_radius)
    return clearance


def signed_wall_clearance(layout: Dict[str, Any], points: np.ndarray) -> np.ndarray:
    """Return clearance to walls and board boundary, deliberately excluding holes."""

    points = np.asarray(points, dtype=np.float64)
    if points.shape[-1] != 2:
        raise ValueError(f"Expected points ending in XY, received {points.shape}")
    width = float(layout["board_width"])
    height = float(layout["board_height"])
    ball_radius = float(layout["ball_radius"])
    wall_half = 0.5 * float(layout.get("wall_thickness", 0.0022))

    clearance = np.minimum.reduce(
        (
            points[..., 0],
            width - points[..., 0],
            points[..., 1],
            height - points[..., 1],
        )
    ) - ball_radius

    for x0, x1, y in layout.get("walls_h", []):
        distance = _distance_to_segment(points, (x0, y), (x1, y))
        clearance = np.minimum(clearance, distance - wall_half - ball_radius)
    for y0, y1, x in layout.get("walls_v", []):
        distance = _distance_to_segment(points, (x, y0), (x, y1))
        clearance = np.minimum(clearance, distance - wall_half - ball_radius)
    for x0, y0, x1, y1 in layout.get("walls_angled", []):
        distance = _distance_to_segment(points, (x0, y0), (x1, y1))
        clearance = np.minimum(clearance, distance - wall_half - ball_radius)
    return clearance


def _grid_axis(size: float, resolution: float) -> np.ndarray:
    count = max(2, int(math.floor(size / resolution)) + 1)
    return np.linspace(0.0, size, count, dtype=np.float64)


def _nearest_grid_index(axis: np.ndarray, value: float) -> int:
    return int(np.argmin(np.abs(axis - float(value))))


def _reconstruct(
    parent: Dict[Tuple[int, int], Tuple[int, int] | None],
    node: Tuple[int, int],
) -> List[Tuple[int, int]]:
    result = []
    while node is not None:
        result.append(node)
        node = parent[node]  # type: ignore[assignment]
    result.reverse()
    return result


def _segment_samples(start: np.ndarray, end: np.ndarray, spacing: float) -> np.ndarray:
    distance = float(np.linalg.norm(end - start))
    count = max(2, int(math.ceil(distance / max(spacing, 1e-6))) + 1)
    return np.linspace(start, end, count, dtype=np.float64)


def _segment_is_safe(
    layout: Dict[str, Any],
    start: np.ndarray,
    end: np.ndarray,
    margin: float,
    sample_spacing: float,
) -> bool:
    samples = _segment_samples(start, end, sample_spacing)
    return bool(np.all(signed_ball_clearance(layout, samples) >= margin - 1e-9))


def _smooth_path(
    layout: Dict[str, Any],
    points: np.ndarray,
    config: PlannerConfig,
) -> np.ndarray:
    if len(points) <= 2:
        return points
    result = [points[0]]
    anchor = 0
    while anchor < len(points) - 1:
        # A bounded lookahead keeps smoothing linear in route length. Testing
        # every later node from every anchor made maze generation unnecessarily
        # quadratic while offering no benefit across separate corridors.
        candidate = min(len(points) - 1, anchor + 24)
        while candidate > anchor + 1:
            if _segment_is_safe(
                layout,
                points[anchor],
                points[candidate],
                config.safety_margin_m,
                config.grid_resolution_m * 0.35,
            ):
                break
            candidate -= 1
        result.append(points[candidate])
        anchor = candidate
    return np.asarray(result, dtype=np.float64)


def _compress_grid_path(points: np.ndarray) -> np.ndarray:
    """Remove nodes that continue in the same quantized grid direction."""
    if len(points) <= 2:
        return points
    vectors = np.diff(points, axis=0)
    directions = np.sign(vectors).astype(np.int8)
    keep = [0]
    for index in range(1, len(points) - 1):
        if not np.array_equal(directions[index], directions[index - 1]):
            keep.append(index)
    keep.append(len(points) - 1)
    return points[np.asarray(keep, dtype=np.int64)]


def resample_polyline(points: Sequence[Sequence[float]], spacing_m: float) -> np.ndarray:
    points_array = np.asarray(points, dtype=np.float64)
    if points_array.ndim != 2 or points_array.shape[1] != 2 or len(points_array) < 2:
        raise ValueError("A route requires at least two XY points")
    vectors = np.diff(points_array, axis=0)
    lengths = np.linalg.norm(vectors, axis=1)
    if np.any(lengths <= 1e-9):
        raise ValueError("Route contains duplicate consecutive points")
    cumulative = np.concatenate(([0.0], np.cumsum(lengths)))
    total = float(cumulative[-1])
    distances = np.arange(0.0, total, spacing_m, dtype=np.float64)
    if not len(distances) or not math.isclose(float(distances[-1]), total):
        distances = np.concatenate((distances, [total]))
    result = []
    for distance in distances:
        index = min(
            len(lengths) - 1,
            int(np.searchsorted(cumulative, distance, side="right") - 1),
        )
        fraction = (distance - cumulative[index]) / lengths[index]
        result.append(points_array[index] + fraction * vectors[index])
    return np.asarray(result, dtype=np.float64)


def rounded_polyline(
    points: Sequence[Sequence[float]],
    radius_m: float = 0.006,
    samples_per_corner: int = 5,
) -> np.ndarray:
    """Replace sharp polyline corners with sampled quadratic Bézier turns."""

    points_array = np.asarray(points, dtype=np.float64)
    if points_array.ndim != 2 or points_array.shape[1] != 2 or len(points_array) < 3:
        return points_array
    radius_m = max(0.0, float(radius_m))
    samples_per_corner = max(2, int(samples_per_corner))
    if radius_m <= 1e-9:
        return points_array

    result = [points_array[0]]
    for previous, corner, following in zip(
        points_array[:-2], points_array[1:-1], points_array[2:]
    ):
        incoming = corner - previous
        outgoing = following - corner
        incoming_length = float(np.linalg.norm(incoming))
        outgoing_length = float(np.linalg.norm(outgoing))
        if incoming_length <= 1e-9 or outgoing_length <= 1e-9:
            continue
        incoming_unit = incoming / incoming_length
        outgoing_unit = outgoing / outgoing_length
        # Straight sections do not need rounding; U-turns are not produced by
        # the route planner and are safer left untouched if they appear.
        turn_strength = 1.0 - abs(float(np.dot(incoming_unit, outgoing_unit)))
        setback = min(radius_m, 0.45 * incoming_length, 0.45 * outgoing_length)
        if turn_strength <= 1e-3 or setback <= 1e-6:
            result.append(corner)
            continue
        entry = corner - incoming_unit * setback
        exit = corner + outgoing_unit * setback
        if float(np.linalg.norm(result[-1] - entry)) > 1e-9:
            result.append(entry)
        for index in range(1, samples_per_corner):
            t = index / samples_per_corner
            curve = (1 - t) ** 2 * entry + 2 * (1 - t) * t * corner + t**2 * exit
            if float(np.linalg.norm(result[-1] - curve)) > 1e-9:
                result.append(curve)
        if float(np.linalg.norm(result[-1] - exit)) > 1e-9:
            result.append(exit)
    if float(np.linalg.norm(result[-1] - points_array[-1])) > 1e-9:
        result.append(points_array[-1])
    return np.asarray(result, dtype=np.float64)


def smooth_safe_route(
    layout: Dict[str, Any],
    points: Sequence[Sequence[float]],
    config: PlannerConfig = PlannerConfig(),
) -> np.ndarray:
    """Round corners when doing so preserves finite-ball route clearance."""

    base = np.asarray(points, dtype=np.float64)
    if (
        len(base) < 3
        or config.corner_rounding_radius_m <= 0.0
        or config.corner_rounding_samples <= 1
    ):
        return base
    rounded = rounded_polyline(
        base,
        radius_m=config.corner_rounding_radius_m,
        samples_per_corner=config.corner_rounding_samples,
    )
    if validate_route(layout, rounded, config).passed:
        return rounded
    # Fall back to progressively smaller turns before giving up. Safety matters
    # more than smoothing; the validator is the gate.
    for scale in (0.75, 0.50, 0.25):
        candidate = rounded_polyline(
            base,
            radius_m=config.corner_rounding_radius_m * scale,
            samples_per_corner=config.corner_rounding_samples,
        )
        if validate_route(layout, candidate, config).passed:
            return candidate
    return base


def plan_safe_route(
    layout: Dict[str, Any],
    config: PlannerConfig = PlannerConfig(),
    start: Iterable[float] | None = None,
    goal: Iterable[float] | None = None,
) -> np.ndarray:
    """Plan, smooth, and resample a route for the ball center."""
    start_array = np.asarray(
        tuple(start) if start is not None else layout["waypoints"][0],
        dtype=np.float64,
    )
    goal_array = np.asarray(
        tuple(goal) if goal is not None else layout["waypoints"][-1],
        dtype=np.float64,
    )

    # Generated layouts already carry a topologically valid route through open
    # cell connections. Prefer that route when it passes the stronger swept-ball
    # check, then remove only shortcuts that are continuously safe. This keeps
    # planning fast and prevents a grid search from selecting a different branch
    # merely because two corridors are close in Euclidean distance.
    seeded_route = np.asarray(layout.get("waypoints", ()), dtype=np.float64)
    if (
        start is None
        and goal is None
        and seeded_route.ndim == 2
        and seeded_route.shape[1:] == (2,)
        and len(seeded_route) >= 2
        and validate_route(layout, seeded_route, config).passed
    ):
        smoothed_seed = _smooth_path(layout, seeded_route, config)
        rounded_seed = smooth_safe_route(layout, smoothed_seed, config)
        if validate_route(layout, rounded_seed, config).passed:
            return rounded_seed

    xs = _grid_axis(float(layout["board_width"]), config.grid_resolution_m)
    ys = _grid_axis(float(layout["board_height"]), config.grid_resolution_m)
    xx, yy = np.meshgrid(xs, ys)
    grid_points = np.stack((xx, yy), axis=-1)
    clearance = signed_ball_clearance(layout, grid_points)
    safe = clearance >= config.safety_margin_m

    start_node = (
        _nearest_grid_index(ys, start_array[1]),
        _nearest_grid_index(xs, start_array[0]),
    )
    goal_node = (
        _nearest_grid_index(ys, goal_array[1]),
        _nearest_grid_index(xs, goal_array[0]),
    )
    if not safe[start_node]:
        raise ValueError(
            f"Start does not satisfy {config.safety_margin_m:.4f} m safety margin"
        )
    if not safe[goal_node]:
        raise ValueError(
            f"Goal does not satisfy {config.safety_margin_m:.4f} m safety margin"
        )

    moves = (
        (-1, 0),
        (1, 0),
        (0, -1),
        (0, 1),
        (-1, -1),
        (-1, 1),
        (1, -1),
        (1, 1),
    )
    queue: List[Tuple[float, float, Tuple[int, int]]] = []
    heapq.heappush(queue, (0.0, 0.0, start_node))
    cost = {start_node: 0.0}
    parent: Dict[Tuple[int, int], Tuple[int, int] | None] = {start_node: None}
    while queue:
        _, current_cost, current = heapq.heappop(queue)
        if current_cost > cost[current] + 1e-12:
            continue
        if current == goal_node:
            break
        row, column = current
        for dr, dc in moves:
            neighbor = row + dr, column + dc
            if not (0 <= neighbor[0] < len(ys) and 0 <= neighbor[1] < len(xs)):
                continue
            if not safe[neighbor]:
                continue
            if dr and dc and (not safe[row + dr, column] or not safe[row, column + dc]):
                continue
            step_length = math.hypot(
                xs[neighbor[1]] - xs[column], ys[neighbor[0]] - ys[row]
            )
            local_clearance = float(clearance[neighbor])
            penalty = config.clearance_cost_weight * math.exp(
                -max(0.0, local_clearance - config.safety_margin_m)
                / max(config.clearance_cost_scale_m, 1e-6)
            )
            candidate_cost = current_cost + step_length * (1.0 + penalty)
            if candidate_cost + 1e-12 >= cost.get(neighbor, math.inf):
                continue
            cost[neighbor] = candidate_cost
            parent[neighbor] = current
            heuristic = math.hypot(
                xs[neighbor[1]] - xs[goal_node[1]],
                ys[neighbor[0]] - ys[goal_node[0]],
            )
            heapq.heappush(
                queue, (candidate_cost + heuristic, candidate_cost, neighbor)
            )
    if goal_node not in parent:
        raise RuntimeError("No route satisfies the requested finite-ball clearance")

    node_path = _reconstruct(parent, goal_node)
    grid_path = np.asarray([(xs[column], ys[row]) for row, column in node_path])
    grid_path[0] = start_array
    grid_path[-1] = goal_array
    smoothed = _smooth_path(layout, _compress_grid_path(grid_path), config)
    rounded = smooth_safe_route(layout, smoothed, config)
    route = rounded
    validation = validate_route(layout, route, config)
    if not validation.passed:
        raise RuntimeError(
            "Planner produced an unsafe route: "
            f"minimum={validation.minimum_clearance_m:.6f} m, "
            f"required={validation.required_margin_m:.6f} m"
        )
    return route


def validate_route(
    layout: Dict[str, Any],
    route: Sequence[Sequence[float]],
    config: PlannerConfig = PlannerConfig(),
) -> RouteValidation:
    route_array = np.asarray(route, dtype=np.float64)
    if route_array.ndim != 2 or route_array.shape[1] != 2 or len(route_array) < 2:
        return RouteValidation(False, -math.inf, config.safety_margin_m, 0, 0.0)
    samples = []
    total = 0.0
    for start, end in zip(route_array, route_array[1:]):
        total += float(np.linalg.norm(end - start))
        segment = _segment_samples(
            start, end, max(0.0005, config.grid_resolution_m * 0.25)
        )
        samples.append(segment[:-1])
    samples.append(route_array[-1:])
    sampled = np.concatenate(samples, axis=0)
    clearance = signed_ball_clearance(layout, sampled)
    minimum = float(np.min(clearance))
    return RouteValidation(
        passed=bool(minimum >= config.safety_margin_m - 1e-9),
        minimum_clearance_m=minimum,
        required_margin_m=config.safety_margin_m,
        sampled_points=len(sampled),
        route_length_m=total,
    )


def apply_safe_route(
    layout: Dict[str, Any], config: PlannerConfig = PlannerConfig()
) -> Tuple[Dict[str, Any], RouteValidation]:
    updated = dict(layout)
    route = plan_safe_route(layout, config)
    updated["waypoints"] = route.tolist()
    updated["route_planner"] = {
        "grid_resolution_m": config.grid_resolution_m,
        "safety_margin_m": config.safety_margin_m,
        "route_spacing_m": config.route_spacing_m,
        "clearance_cost_weight": config.clearance_cost_weight,
        "clearance_cost_scale_m": config.clearance_cost_scale_m,
        "corner_rounding_radius_m": config.corner_rounding_radius_m,
        "corner_rounding_samples": config.corner_rounding_samples,
    }
    return updated, validate_route(updated, route, config)
