import unittest

import numpy as np

from tag_mujoco.tag_env import TaskConfig, action_rate_cost


class ActionRateCostTests(unittest.TestCase):
    def test_default_configuration_charges_nothing(self):
        # The historical reward must be unchanged unless an arm opts in.
        self.assertEqual(TaskConfig().action_rate_penalty, 0.0)

    def test_first_step_of_an_episode_is_not_charged(self):
        cost = action_rate_cost(np.array([1.0, -1.0]), None)
        self.assertEqual(cost, 0.0)

    def test_holding_a_command_costs_nothing(self):
        previous = np.array([0.4, -0.7])
        self.assertEqual(action_rate_cost(previous.copy(), previous), 0.0)

    def test_cost_is_the_mean_absolute_change_per_axis(self):
        cost = action_rate_cost(np.array([1.0, 0.0]), np.array([-1.0, 0.5]))
        self.assertAlmostEqual(cost, (2.0 + 0.5) / 2)

    def test_full_range_reversal_on_both_axes_is_the_maximum(self):
        cost = action_rate_cost(np.array([1.0, 1.0]), np.array([-1.0, -1.0]))
        self.assertAlmostEqual(cost, 2.0)

    def test_smooth_driving_costs_far_less_than_measured_chatter(self):
        # The 500k nominal policy averaged step-to-step changes of 0.5-1.2.
        chatter = action_rate_cost(np.array([0.9, -0.9]), np.array([-0.9, 0.9]))
        smooth = action_rate_cost(np.array([0.35, 0.20]), np.array([0.30, 0.18]))
        self.assertGreater(chatter, 10 * smooth)

    def test_cost_is_symmetric_in_direction(self):
        a, b = np.array([0.8, -0.2]), np.array([-0.1, 0.6])
        self.assertAlmostEqual(action_rate_cost(a, b), action_rate_cost(b, a))

    def test_shipped_penalty_stays_a_minority_of_the_episode_return(self):
        """Guard the calibration, not just the mechanism.

        A full route earns progress_reward_scale plus success_bonus. If the
        smoothness term can rival that, the best policy is to stop moving, so
        the shipped penalty must stay well inside the reward budget at the
        chatter the 500k policy actually produced.
        """
        config = TaskConfig()
        budget = config.progress_reward_scale + config.success_bonus
        measured_chatter = 0.57
        typical_steps = 750
        for penalty in (0.003, 0.005):
            cost = penalty * measured_chatter * typical_steps
            self.assertLess(cost, 0.25 * budget, f"penalty {penalty} is too large")
        # A penalty two orders of magnitude higher would swamp the return.
        self.assertGreater(0.5 * measured_chatter * typical_steps, budget)


if __name__ == "__main__":
    unittest.main()
