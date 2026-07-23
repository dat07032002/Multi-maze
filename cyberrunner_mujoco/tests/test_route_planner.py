from __future__ import annotations

import unittest

import numpy as np

from cyberrunner_mujoco.maze_generator import generate_maze
from cyberrunner_mujoco.route_planner import (
    PlannerConfig,
    apply_safe_route,
    signed_ball_clearance,
    validate_route,
)


class RoutePlannerTest(unittest.TestCase):
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

