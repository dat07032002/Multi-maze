from __future__ import annotations

import math
import unittest

import numpy as np

from tag_mujoco.policy_contract import TagPolicyContract
from tag_mujoco.actuator_model import HiwonderActuatorModel
from tag_mujoco.system_config import ActuatorConfig


class TagPolicyContractTest(unittest.TestCase):
    def setUp(self):
        self.contract = TagPolicyContract()

    def test_centered_hardware_state_matches_lower_left_sim_state(self):
        lower_left = self.contract.hardware_centered_to_lower_left((0.0, 0.0))
        state = self.contract.normalize_states(
            (math.radians(5.0), math.radians(-2.5)),
            lower_left,
        )
        np.testing.assert_allclose(state, (0.5, -0.25, 0.5, 0.5), atol=1e-6)

    def test_each_route_point_uses_its_own_horizon(self):
        points = np.asarray(
            [(0.012 * index, 0.0) for index in range(1, 6)], dtype=np.float32
        )
        goal = self.contract.normalize_relative_goal(points).reshape(5, 2)
        np.testing.assert_allclose(goal[:, 0], np.ones(5), atol=1e-6)
        np.testing.assert_allclose(goal[:, 1], np.zeros(5), atol=1e-6)

    def test_effective_bridge_limit_and_servo_targets(self):
        command = self.contract.action_to_hiwonder_command((1.0, -1.0))
        np.testing.assert_array_equal(command, (-180.0, 180.0))
        target = self.contract.hiwonder_command_to_servo_target(command)
        np.testing.assert_array_equal(target, (230.0, 770.0))

    def test_sim_action_path_matches_policy_contract(self):
        config = ActuatorConfig(
            command_timeout_seconds=100.0,
            total_delay_seconds=0.0,
            response_time_constant_seconds=0.001,
        )
        for action in ((0.0, 0.0), (0.5, -0.5), (0.75, -0.75), (1.0, -1.0)):
            with self.subTest(action=action):
                actuator = HiwonderActuatorModel(config)
                actuator.submit_action(action)
                for _ in range(40):
                    actuator.step(1.0 / config.update_rate_hz)
                command = self.contract.action_to_hiwonder_command(action)
                expected = self.contract.hiwonder_command_to_servo_target(command)
                np.testing.assert_allclose(
                    actuator.commanded_servo_positions,
                    expected,
                    atol=1e-6,
                )

    def test_nonfinite_action_is_rejected_by_contract_and_sim(self):
        with self.assertRaises(ValueError):
            self.contract.action_to_hiwonder_command((np.nan, 0.0))
        with self.assertRaises(ValueError):
            HiwonderActuatorModel(ActuatorConfig()).submit_action((0.0, np.inf))

    def test_grayscale_is_arithmetic_channel_mean(self):
        color = np.zeros((64, 64, 3), dtype=np.uint8)
        color[..., 0] = 3
        color[..., 1] = 9
        color[..., 2] = 18
        gray = self.contract.grayscale_patch(color)
        self.assertEqual(int(gray[0, 0, 0]), 10)

    def test_ball_visible_is_rejected_as_policy_input(self):
        observation = self.contract.make_observation(
            np.zeros((64, 64, 1), dtype=np.uint8),
            (0.0, 0.0),
            (0.1, 0.1),
            np.zeros((5, 2), dtype=np.float32),
        )
        observation["ball_visible"] = np.ones(1, dtype=np.uint8)
        with self.assertRaises(ValueError):
            self.contract.validate_observation(observation)

    def test_hiwonder_timeout_returns_target_home(self):
        actuator = HiwonderActuatorModel(
            ActuatorConfig(total_delay_seconds=0.0, response_time_constant_seconds=0.01)
        )
        actuator.submit_action((1.0, 1.0))
        for _ in range(50):
            actuator.step(0.01)
        self.assertFalse(actuator.timed_out)
        for _ in range(120):
            actuator.step(0.01)
        self.assertTrue(actuator.timed_out)
        for _ in range(60):
            actuator.step(0.01)
        np.testing.assert_allclose(actuator.commanded_servo_positions, (500.0, 500.0))

    def test_hardware_reset_profile_matches_tag_driver(self):
        profile = HiwonderActuatorModel(ActuatorConfig()).hardware_reset_profile()
        self.assertEqual(profile["prehome_positions"], (700.0, 700.0))
        self.assertEqual(profile["prehome_wait_seconds"], 0.5)
        self.assertEqual(profile["home_positions"], (500.0, 500.0))

    def test_measured_actuator_map_is_direction_dependent_and_coupled(self):
        config = ActuatorConfig(
            total_delay_seconds=0.0,
            response_time_constant_seconds=0.001,
        )

        def settle(action):
            actuator = HiwonderActuatorModel(config)
            for _ in range(100):
                actuator.submit_action(action)
                actuator.step(0.01)
            return actuator.board_target_angles

        axis2_positive = settle((0.0, -0.15))
        axis2_negative = settle((0.0, 0.15))
        self.assertLess(abs(axis2_positive[0]), math.radians(0.1))
        # The command-80 fit predicts about +0.19/+0.14 degrees at command
        # -36. Preserve the measured sign and coupling without retaining the
        # substantially larger gain from the superseded command-26.67 fit.
        self.assertGreater(axis2_negative[0], math.radians(0.1))
        self.assertGreater(axis2_negative[1], math.radians(0.1))

    def test_axis2_positive_stiction_rejects_local_small_command(self):
        actuator = HiwonderActuatorModel(
            ActuatorConfig(
                total_delay_seconds=0.0,
                response_time_constant_seconds=0.001,
            )
        )
        # action -0.1 becomes command +18, below the measured +40 threshold.
        for _ in range(100):
            actuator.submit_action((0.0, -0.1))
            actuator.step(0.01)
        np.testing.assert_allclose(actuator.board_target_angles, (0.0, 0.0))

    def test_privileged_inverse_respects_directional_map(self):
        config = ActuatorConfig()
        actuator = HiwonderActuatorModel(config)
        target = np.radians((0.4, -0.2))
        action = actuator.action_for_board_target(target)
        self.assertTrue(np.all(np.isfinite(action)))
        self.assertTrue(np.all(np.abs(action) <= 1.0))


if __name__ == "__main__":
    unittest.main()
