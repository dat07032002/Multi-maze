from __future__ import annotations

import unittest
from pathlib import Path

import numpy as np

from tag_mujoco.maze_generator import generate_maze
from tag_mujoco.route_planner import (
    PlannerConfig,
    apply_safe_route,
    rounded_polyline,
    signed_ball_clearance,
    smooth_safe_route,
    validate_route,
)
from tag_mujoco.maze_layout import (
    DEFAULT_WALL_HEIGHT_M,
    DEFAULT_WALL_THICKNESS_M,
    load_json_layout,
)
from tag_mujoco.model_builder import WALL_THICKNESS


class RoutePlannerTest(unittest.TestCase):
    def test_geometry_defaults_are_identical_for_planning_and_mujoco(self):
        layout = load_json_layout(
            Path(__file__).resolve().parents[1] / "generated_mazes" / "maze_seed_970.json"
        )
        self.assertEqual(layout["wall_thickness"], DEFAULT_WALL_THICKNESS_M)
        self.assertEqual(layout["wall_height"], DEFAULT_WALL_HEIGHT_M)
        self.assertEqual(WALL_THICKNESS, DEFAULT_WALL_THICKNESS_M)

    def test_hole_is_inflated_by_hole_and_ball_radius(self):
        layout = generate_maze(7)
        hole = np.asarray(layout["holes"][0], dtype=np.float64)
        hole_radius = float(layout["hole_radii"][0])
        ball_radius = float(layout["ball_radius"])
        point = hole + np.array([hole_radius + ball_radius + 0.003, 0.0])
        clearance = float(signed_ball_clearance(layout, point[None])[0])
        self.assertAlmostEqual(clearance, 0.003, places=6)

    def test_generated_routes_pass_swept_ball_validation(self):
        config = PlannerConfig()
        for seed in (7, 31, 970):
            with self.subTest(seed=seed):
                layout, validation = apply_safe_route(generate_maze(seed), config)
                self.assertTrue(validation.passed)
                self.assertGreaterEqual(
                    validation.minimum_clearance_m + 1e-9,
                    config.safety_margin_m,
                )
                self.assertTrue(validate_route(layout, layout["waypoints"], config).passed)

    def test_rounded_polyline_inserts_training_points_at_corners(self):
        route = np.asarray([[0.0, 0.0], [0.04, 0.0], [0.04, 0.04]])
        rounded = rounded_polyline(route, radius_m=0.010, samples_per_corner=5)
        self.assertGreater(len(rounded), len(route))
        self.assertTrue(np.allclose(rounded[0], route[0]))
        self.assertTrue(np.allclose(rounded[-1], route[-1]))
        # The original corner point should be replaced by nearby arc samples,
        # not retained as a sharp target.
        self.assertFalse(np.any(np.all(np.isclose(rounded, route[1]), axis=1)))

    def test_smooth_safe_route_preserves_clearance(self):
        layout = {
            "board_width": 0.12,
            "board_height": 0.12,
            "ball_radius": 0.006,
            "wall_thickness": 0.0022,
            "walls_h": [],
            "walls_v": [],
            "walls_angled": [],
            "holes": [],
            "hole_radii": [],
        }
        config = PlannerConfig(corner_rounding_radius_m=0.010)
        route = np.asarray([[0.02, 0.02], [0.08, 0.02], [0.08, 0.08]])
        smoothed = smooth_safe_route(layout, route, config)
        self.assertGreater(len(smoothed), len(route))
        self.assertTrue(validate_route(layout, smoothed, config).passed)


if __name__ == "__main__":
    unittest.main()
