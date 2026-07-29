import json
import unittest
from pathlib import Path

import numpy as np

from tag_mujoco.route_planner import (
    signed_ball_clearance,
    signed_hole_clearance,
    signed_wall_clearance,
)
from tag_mujoco.tag_env import (
    TaskConfig,
    hole_proximity_cost,
    path_tracking_cost,
    wall_riding_cost,
)

HERE = Path(__file__).resolve().parent
LAYOUT = HERE.parent / "generated_mazes_v2" / "maze_seed_20024.json"


class HoleProximityCostTests(unittest.TestCase):
    def test_default_configuration_charges_nothing(self):
        self.assertEqual(TaskConfig().hole_clearance_penalty, 0.0)

    def test_cost_is_zero_outside_the_warning_band(self):
        config = TaskConfig()
        self.assertEqual(hole_proximity_cost(config, config.hole_warning_m), 0.0)
        self.assertEqual(hole_proximity_cost(config, 0.050), 0.0)

    def test_cost_saturates_at_the_rim_and_beyond(self):
        config = TaskConfig()
        self.assertEqual(hole_proximity_cost(config, 0.0), 1.0)
        self.assertEqual(hole_proximity_cost(config, -0.010), 1.0)

    def test_cost_ramps_linearly_across_the_band(self):
        config = TaskConfig()
        half = hole_proximity_cost(config, 0.5 * config.hole_warning_m)
        self.assertAlmostEqual(half, 0.5)

    def test_a_layout_without_holes_never_charges(self):
        clearance = signed_hole_clearance({"ball_radius": 0.006}, np.zeros((1, 2)))
        self.assertTrue(np.isinf(clearance[0]))
        self.assertEqual(hole_proximity_cost(TaskConfig(), float(clearance[0])), 0.0)

    def test_nan_clearance_is_rejected(self):
        with self.assertRaises(ValueError):
            hole_proximity_cost(TaskConfig(), float("nan"))


class HoleClearanceIsHoleOnlyTests(unittest.TestCase):
    """The band must ignore walls, or it penalizes ordinary corridor travel."""

    def setUp(self):
        self.layout = json.loads(LAYOUT.read_text(encoding="utf-8"))

    def test_hole_clearance_is_never_tighter_than_combined_clearance(self):
        route = np.asarray(self.layout["waypoints"], dtype=np.float64)
        combined = signed_ball_clearance(self.layout, route)
        holes_only = signed_hole_clearance(self.layout, route)
        self.assertTrue(np.all(holes_only >= combined - 1e-12))

    def _costs(self, clearance):
        config = TaskConfig()
        return np.array(
            [hole_proximity_cost(config, float(value)) for value in clearance]
        )

    def test_walls_would_dominate_the_signal_if_they_were_included(self):
        # This route's tightest obstacle is a wall at about 2.5 mm. A
        # wall-inclusive band charges heavily for driving down a corridor, while
        # the hole-only band barely registers on the same points.
        route = np.asarray(self.layout["waypoints"], dtype=np.float64)
        combined = self._costs(signed_ball_clearance(self.layout, route))
        holes_only = self._costs(signed_hole_clearance(self.layout, route))
        self.assertGreater(combined.max(), 0.5)
        self.assertLess(holes_only.max(), 0.1)
        self.assertGreater(combined.mean(), 10 * holes_only.mean())

    def test_on_route_travel_costs_a_negligible_share_of_the_return(self):
        """Guard the calibration that makes this signal safe to add.

        A dense penalty is only useful if it stays quiet while the policy tracks
        the route. Measured across the validation split, a perfectly on-route
        ball has a mean cost of 0.0000 on the median layout and 0.0210 on the
        worst, so the bound below leaves headroom without allowing a term that
        taxes ordinary driving.
        """
        route = np.asarray(self.layout["waypoints"], dtype=np.float64)
        config = TaskConfig()
        mean_cost = float(self._costs(signed_hole_clearance(self.layout, route)).mean())
        budget = config.progress_reward_scale + config.success_bonus
        charged = 0.02 * mean_cost * 750
        self.assertLess(charged, 0.05 * budget)


class SafePathAndWallCostTests(unittest.TestCase):
    def test_new_path_and_wall_penalties_default_to_zero(self):
        config = TaskConfig()
        self.assertEqual(config.path_tracking_penalty, 0.0)
        self.assertEqual(config.wall_riding_penalty, 0.0)

    def test_path_tracking_cost_ignores_error_inside_tolerance(self):
        config = TaskConfig(path_tracking_tolerance_m=0.004)
        self.assertEqual(path_tracking_cost(config, 0.003), 0.0)
        self.assertAlmostEqual(path_tracking_cost(config, 0.006), 0.5)

    def test_wall_riding_cost_ramps_near_walls(self):
        config = TaskConfig(wall_warning_m=0.003)
        self.assertEqual(wall_riding_cost(config, 0.010), 0.0)
        self.assertAlmostEqual(wall_riding_cost(config, 0.0015), 0.5)
        self.assertEqual(wall_riding_cost(config, -0.001), 1.0)

    def test_wall_clearance_excludes_holes(self):
        layout = {
            "board_width": 0.20,
            "board_height": 0.20,
            "ball_radius": 0.006,
            "wall_thickness": 0.002,
            "walls_h": [],
            "walls_v": [],
            "walls_angled": [],
            "holes": [[0.10, 0.10]],
            "hole_radii": [0.0075],
        }
        point = np.asarray([[0.10, 0.10]], dtype=np.float64)
        self.assertLess(signed_hole_clearance(layout, point)[0], 0.0)
        self.assertGreater(signed_wall_clearance(layout, point)[0], 0.08)


if __name__ == "__main__":
    unittest.main()
