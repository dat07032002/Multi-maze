from __future__ import annotations

import unittest
from pathlib import Path

import numpy as np

from cyberrunner_mujoco.maze_generator import generate_maze
from cyberrunner_mujoco.route_planner import (
    PlannerConfig,
    apply_safe_route,
    signed_ball_clearance,
    validate_route,
)
from cyberrunner_mujoco.maze_layout import (
    DEFAULT_WALL_HEIGHT_M,
    DEFAULT_WALL_THICKNESS_M,
    load_json_layout,
)
from cyberrunner_mujoco.model_builder import WALL_THICKNESS


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


if __name__ == "__main__":
    unittest.main()
