from __future__ import annotations

import unittest

import numpy as np

from cyberrunner_mujoco.observation_filter import TagObservationFilter


class TagObservationFilterTest(unittest.TestCase):
    @staticmethod
    def goal(position):
        return np.tile(np.asarray(position, dtype=np.float32), 5)

    @staticmethod
    def project(position):
        projected = np.asarray(position, dtype=np.float32).copy()
        projected[1] = 0.1
        return projected

    def update(self, filter_, detected, position=(0.1, 0.1), dt=0.1):
        return filter_.update(
            image=np.full((64, 64, 1), 17, dtype=np.uint8),
            board_angles_rad=(0.01, -0.02),
            measured_xy_m=position if detected else None,
            relative_goal_m=np.zeros((5, 2), dtype=np.float32),
            detected=detected,
            dt_seconds=dt,
            goal_for_position=self.goal,
            project_to_route=self.project,
        )

    def test_hysteresis_then_grace_then_confirmed_loss(self):
        filter_ = TagObservationFilter(miss_threshold=3, grace_seconds=0.25)
        self.update(filter_, True)
        for _ in range(2):
            observation, reported, mode = self.update(filter_, False)
            self.assertTrue(reported)
            self.assertEqual(mode, "detector_hysteresis")
            self.assertEqual(int(observation["image"][0, 0, 0]), 17)
        _, reported, mode = self.update(filter_, False)
        self.assertTrue(reported)
        self.assertEqual(mode, "occlusion_grace")
        _, reported, mode = self.update(filter_, False)
        self.assertTrue(reported)
        self.assertEqual(mode, "occlusion_grace")
        _, reported, mode = self.update(filter_, False)
        self.assertFalse(reported)
        self.assertEqual(mode, "lost")

    def test_prediction_speed_is_capped_and_projected_to_route(self):
        filter_ = TagObservationFilter(miss_threshold=1, grace_seconds=1.0)
        self.update(filter_, True, position=(0.0, 0.1), dt=0.1)
        self.update(filter_, True, position=(0.1, 0.1), dt=0.1)
        observation, reported, mode = self.update(filter_, False, dt=0.1)
        self.assertTrue(reported)
        self.assertEqual(mode, "occlusion_grace")
        self.assertAlmostEqual(float(observation["states"][3]), 0.1, places=6)
        self.assertLessEqual(float(observation["states"][2]), 0.1151)


if __name__ == "__main__":
    unittest.main()
