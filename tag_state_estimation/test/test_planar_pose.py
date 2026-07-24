import unittest

import cv2
import numpy as np

from tag_state_estimation.core.plate_pose import PlatePoseEstimator


class PlanarPoseTest(unittest.TestCase):
    def setUp(self):
        self.estimator = PlatePoseEstimator.__new__(PlatePoseEstimator)
        self.estimator.K = np.array(
            [[300.0, 0.0, 320.0], [0.0, 300.0, 240.0], [0.0, 0.0, 1.0]]
        )
        self.estimator._previous_pnp_poses = {}
        self.points = np.array(
            [
                [-0.13, -0.11, 0.0],
                [0.13, -0.11, 0.0],
                [0.13, 0.11, 0.0],
                [-0.13, 0.11, 0.0],
            ],
            dtype=np.float32,
        )

    def project(self, rotation_vec, translation_vec):
        points, _ = cv2.projectPoints(
            self.points,
            np.asarray(rotation_vec, dtype=float),
            np.asarray(translation_vec, dtype=float),
            self.estimator.K,
            None,
        )
        return points.reshape(-1, 2)

    def test_recovers_positive_depth_pose(self):
        expected_rvec = np.array([0.12, -0.08, 0.03])
        expected_tvec = np.array([0.01, -0.02, 0.55])
        image_points = self.project(expected_rvec, expected_tvec)

        _, translation, rotation = self.estimator._select_planar_pose(
            self.points, image_points, "maze"
        )
        expected_rotation, _ = cv2.Rodrigues(expected_rvec)

        self.assertLess(
            self.estimator._rotation_distance(expected_rotation, rotation), 1e-3
        )
        np.testing.assert_allclose(translation.ravel(), expected_tvec, atol=1e-3)

    def test_continuous_frames_stay_on_same_pose_branch(self):
        poses = []
        for tilt in np.linspace(0.08, 0.12, 10):
            image_points = self.project(
                np.array([tilt, -0.05, 0.02]), np.array([0.01, -0.02, 0.55])
            )
            _, _, rotation = self.estimator._select_planar_pose(
                self.points, image_points, "maze"
            )
            poses.append(rotation)

        jumps = [
            self.estimator._rotation_distance(first, second)
            for first, second in zip(poses, poses[1:])
        ]
        self.assertLess(max(jumps), 0.01)


if __name__ == "__main__":
    unittest.main()
