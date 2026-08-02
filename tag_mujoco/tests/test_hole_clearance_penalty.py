import json
import unittest
from pathlib import Path

import numpy as np

from tag_mujoco.route_planner import (
    signed_ball_clearance,
    signed_hole_clearance,
    signed_wall_clearance,
)
from tag_mujoco.system_model import PolylineRoute
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


class RouteProgressCorridorTests(unittest.TestCase):
    """Progress must measure route following, not proximity of a projection.

    PolylineRoute.project returns the nearest route point inside the along-route
    window and reports the cross-track distance, but never uses that distance to
    reject the match. Without a corridor gate a ball crossing the board sweeps
    the projection along the whole route, so route_completion reaches 1.0 and
    progress reward is paid for travel that never happened.
    """

    def setUp(self):
        self.layout = json.loads(LAYOUT.read_text(encoding="utf-8"))
        self.route = PolylineRoute(
            np.asarray(self.layout["waypoints"], dtype=np.float64)
        )

    def test_default_corridor_matches_the_measured_route_geometry(self):
        # On-route ball clearance over 40 foundation layouts: 39.1 mm median,
        # 23.5 mm at the 1st percentile. The corridor sits at the median, so a
        # ball beyond it is outside the route's own corridor for most geometry.
        self.assertAlmostEqual(TaskConfig().progress_corridor_m, 0.040)

    def test_projection_reports_a_far_ball_at_full_progress(self):
        """Pin the underlying behavior this guard exists to contain."""
        end = self.route.point_at(self.route.total_length)
        # A point well off the route but near its end, as a wandering ball is.
        far = np.asarray(end) + np.asarray([0.0, 0.12])
        progress, _, cross_track = self.route.project(far)
        self.assertGreater(cross_track, 0.10)
        # The projection still hands back a progress value despite the distance.
        self.assertGreaterEqual(progress, 0.0)

    def test_corridor_rejects_the_measured_failure_and_accepts_tracking(self):
        corridor = TaskConfig().progress_corridor_m
        # The 50k foundation validation averaged 174 mm of cross-track error
        # while reporting route completion of 1.0.
        self.assertGreater(0.174, corridor)
        self.assertGreater(0.116, corridor)
        # A policy that tracks the route sits an order of magnitude inside it.
        self.assertLess(0.004, corridor)
        self.assertLess(0.015, corridor)


class SafePathAndWallCostTests(unittest.TestCase):
    def test_new_path_and_wall_penalties_default_to_zero(self):
        config = TaskConfig()
        self.assertEqual(config.path_tracking_penalty, 0.0)
        self.assertEqual(config.wall_riding_penalty, 0.0)

    def test_path_tracking_cost_ignores_error_inside_tolerance(self):
        config = TaskConfig(path_tracking_tolerance_m=0.004)
        self.assertEqual(path_tracking_cost(config, 0.003), 0.0)
        self.assertAlmostEqual(path_tracking_cost(config, 0.006), 0.5)

    def test_path_tracking_cost_saturates_like_every_other_hazard_term(self):
        """A ball far off route must not be charged without limit.

        Cross-track error is unbounded, so an unclipped ramp let this term grow
        without limit while the positive reward stayed capped. Saturating one
        tolerance width outside the tube matches hole_proximity_cost and
        wall_riding_cost, both of which return a cost in [0, 1].
        """
        config = TaskConfig(path_tracking_tolerance_m=0.004)
        self.assertEqual(path_tracking_cost(config, 0.008), 1.0)
        # A stalled ball a third of the way across the board measured 27.5.
        self.assertEqual(path_tracking_cost(config, 0.115), 1.0)
        self.assertEqual(path_tracking_cost(config, 10.0), 1.0)

    def test_active_master_course_path_penalty_fits_the_reward_budget(self):
        """Guard the calibration of the arm that is actually being trained.

        tag_sim_v5_master_base charges 0.002 per unit cost over 3000 step
        episodes against progress_reward_scale 15 plus success_bonus 20. With
        the cost bounded at one, the worst case is 6 against a budget of 35,
        which leaves route progress the dominant term.
        """
        budget = 15.0 + 20.0
        worst_case = 0.002 * 1.0 * 3000
        self.assertLess(worst_case, 0.25 * budget)

    def test_the_unclipped_term_would_have_swamped_the_master_course_return(self):
        """Pin the regression this clip fixes so it cannot silently return.

        The 150k foundation run logged a mean path cost of 27.5 per step, which
        unclipped charged about -165 against a budget of 35. The recorded
        episode score was -156, i.e. this single term was the entire return.
        """
        budget = 15.0 + 20.0
        measured_unclipped_cost = 27.5
        self.assertGreater(0.002 * measured_unclipped_cost * 3000, 4 * budget)

    def test_legacy_safe_path_tracking_coefficient_is_known_out_of_budget(self):
        """Document, rather than hide, a superseded arm's calibration.

        tag_sim_v2_safe_path_tracking ships 0.20 and inherits 3000 step
        episodes, so even with the cost bounded at one it can charge 600
        against a budget of 20. Clipping bounds it but does not make it sane.
        That profile belongs to the retired staged-dodge curriculum; this test
        exists so the number is not mistaken for a calibrated default if the
        curriculum is ever revived.
        """
        config = TaskConfig()
        budget = config.progress_reward_scale + config.success_bonus
        self.assertGreater(0.20 * 1.0 * 3000, 10 * budget)

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
