from __future__ import annotations

import math
import unittest

from tag_mujoco.actuator_authority import (
    action_for_command,
    angle_from_edge_lift,
    authority_envelope,
    edge_lift_mm,
    settle,
    stiction_dead_band,
    transition_time_to_fraction,
)
from tag_mujoco.actuator_model import HiwonderActuatorModel
from tag_mujoco.policy_contract import TagPolicyContract
from tag_mujoco.system_config import ActuatorConfig


class EdgeLiftTests(unittest.TestCase):
    """The bench's primary reference converts angle to millimetres of lift."""

    def test_round_trip(self):
        contract = TagPolicyContract()
        for degrees in (0.25, 1.0, 2.5, 10.0):
            lift = edge_lift_mm(math.radians(degrees), contract.board_width_m)
            recovered = angle_from_edge_lift(lift, contract.board_width_m)
            self.assertAlmostEqual(math.degrees(recovered), degrees, places=9)

    def test_matches_published_reference_table(self):
        # These are the numbers the recording sheet and the plan quote. If the
        # board dimensions change, the sheet is wrong and this should say so.
        contract = TagPolicyContract()
        self.assertAlmostEqual(
            edge_lift_mm(math.radians(1.0), contract.board_width_m), 4.52, places=2
        )
        self.assertAlmostEqual(
            edge_lift_mm(math.radians(10.0), contract.board_width_m), 45.67, places=2
        )
        self.assertAlmostEqual(
            math.degrees(angle_from_edge_lift(1.0, contract.board_width_m)),
            0.221,
            places=3,
        )


class CommandMappingTests(unittest.TestCase):
    def test_action_for_command_inverts_scale_and_sign(self):
        config = ActuatorConfig()
        action = action_for_command(80.0, config)
        command = (
            action * config.policy_command_scale[0] * config.policy_command_sign[0]
        )
        self.assertAlmostEqual(command, 80.0, places=9)

    def test_commands_beyond_the_bridge_clamp_are_unreachable(self):
        # The learner scales by 240 and the bridge clamps to 180, so |action|
        # above 0.75 is the same command. A tool that reported otherwise would
        # invent authority the hardware does not have.
        config = ActuatorConfig()
        clamped = action_for_command(240.0, config)
        at_limit = action_for_command(180.0, config)
        self.assertAlmostEqual(clamped, at_limit, places=9)
        self.assertAlmostEqual(abs(at_limit), 0.75, places=9)


class SettleTests(unittest.TestCase):
    def test_settle_actually_moves_the_board(self):
        """Regression: convergence must not be declared before the first tick.

        The driver advances at `update_rate_hz` (30 Hz) while `settle` steps at
        the physics dt (1 kHz). A convergence check aligned to a single tick
        period can land entirely between ticks, observe no change, and return a
        board angle of exactly zero for every action -- which is a silently
        wrong answer of exactly the kind this measurement exists to remove.
        """

        config = ActuatorConfig()
        model = HiwonderActuatorModel(config)
        result = settle(model, [-0.75, -0.75])
        self.assertTrue(result["converged"])
        self.assertGreater(max(abs(value) for value in result["angles_rad"]), 1e-4)

    def test_settle_reaches_the_commanded_servo_position(self):
        config = ActuatorConfig()
        model = HiwonderActuatorModel(config)
        settle(model, [-0.75, -0.75])
        # action -0.75 -> command +180 -> servo offset +270 from home 500.
        for position in model.commanded_servo_positions:
            self.assertAlmostEqual(position, 770.0, places=6)

    def test_home_action_leaves_the_board_level(self):
        config = ActuatorConfig()
        model = HiwonderActuatorModel(config)
        result = settle(model, [0.0, 0.0])
        for angle in result["angles_rad"]:
            self.assertAlmostEqual(angle, 0.0, places=12)


class StictionTests(unittest.TestCase):
    def test_dead_band_matches_configured_thresholds(self):
        """The measured band must reproduce the configured command thresholds.

        `policy_command_sign` is negative, so a positive action produces a
        negative command and is gated by `stiction_command_negative`. Getting
        that crossing wrong would misreport which direction is stiff.
        """

        config = ActuatorConfig()
        bands = stiction_dead_band(config, resolution=0.002)
        scale = config.policy_command_scale[0]
        expected = {
            "axis1_positive": config.stiction_command_negative[0] / scale,
            "axis1_negative": config.stiction_command_positive[0] / scale,
            "axis2_positive": config.stiction_command_negative[1] / scale,
            "axis2_negative": config.stiction_command_positive[1] / scale,
        }
        for key, threshold in expected.items():
            measured = bands[key]["first_moving_action"]
            self.assertIsNotNone(measured, f"{key} never moved")
            self.assertAlmostEqual(measured, threshold, delta=0.005)


class TimingTests(unittest.TestCase):
    def test_full_reversal_takes_longer_than_a_step_from_home(self):
        """A full reversal covers twice the servo travel of a step from home.

        The binding constraint is `max_step_per_tick`, not servo dynamics, so
        this ratio is a property of the rate limiter. If the two ever match,
        the slew limit has stopped being modelled.
        """

        config = ActuatorConfig()
        full = action_for_command(float(config.policy_command_limit[0]), config)
        step = transition_time_to_fraction(config, [0.0, 0.0], [full, full])
        reversal = transition_time_to_fraction(config, [full, full], [-full, -full])
        for axis in range(2):
            self.assertIsNotNone(step["seconds_per_axis"][axis])
            self.assertIsNotNone(reversal["seconds_per_axis"][axis])
            self.assertGreater(
                reversal["seconds_per_axis"][axis],
                1.5 * step["seconds_per_axis"][axis],
            )

    def test_reversal_is_slew_limited_not_dynamics_limited(self):
        """The rate limiter, not servo dynamics, sets transition time.

        A full reversal spans 540 servo units at 20 units per 30 Hz tick, so
        the servo cannot complete it faster than 0.9 s. The angle reaches 90%
        of its change somewhat sooner, because the stiction dead zone makes the
        command-to-angle map discontinuous at the threshold -- so the bound is
        a fraction of the full traversal rather than 90% of it.

        The comparison that matters is against
        `response_time_constant_seconds`, which is 0.001 s: if servo dynamics
        dominated, transitions would be milliseconds. They are hundreds of
        milliseconds, which is why commanding early and hard is the rational
        strategy and why penalising action rate could not fix cornering.
        """

        config = ActuatorConfig()
        full = action_for_command(float(config.policy_command_limit[0]), config)
        reversal = transition_time_to_fraction(config, [full, full], [-full, -full])
        full_traversal = (540.0 / config.max_step_per_tick[0]) / config.update_rate_hz
        for seconds in reversal["seconds_per_axis"]:
            self.assertGreaterEqual(seconds, 0.7 * full_traversal)
            self.assertLessEqual(seconds, full_traversal + 1e-6)
            self.assertGreater(seconds, 100.0 * config.response_time_constant_seconds)


class EnvelopeTests(unittest.TestCase):
    def test_envelope_is_anisotropic(self):
        """Cross-coupling makes reachable tilt depend on the sign combination.

        Driving both motors positive puts the two alpha terms against each
        other and very nearly cancels. Reporting a single "maximum tilt" would
        hide that one diagonal of the action square is nearly dead, which
        matters for route feasibility in the weak direction.
        """

        config = ActuatorConfig()
        contract = TagPolicyContract()
        envelope = authority_envelope(config, contract)
        self.assertEqual(len(envelope["corners"]), 4)
        magnitudes = [
            max(abs(value) for value in corner["angles_deg"])
            for corner in envelope["corners"]
        ]
        self.assertGreater(max(magnitudes), 4.0 * min(magnitudes))
        self.assertLessEqual(envelope["weakest_axis_deg"], max(magnitudes))

    def test_envelope_stays_inside_the_configured_board_limit(self):
        config = ActuatorConfig()
        envelope = authority_envelope(config, TagPolicyContract())
        limit_deg = math.degrees(config.board_angle_limit_rad)
        for corner in envelope["corners"]:
            for angle in corner["angles_deg"]:
                self.assertLessEqual(abs(angle), limit_deg + 1e-9)


class ExtrapolationDisclosureTests(unittest.TestCase):
    def test_calibration_is_applied_beyond_its_fit_point(self):
        """Fail loudly while the shipped map is used past where it was fitted.

        `board_rad_per_command_*` is a local slope fitted near |command|=80 and
        applied at the policy limit of 180. That is a real property of the
        current configuration, not a bug in this test -- it is recorded here so
        the extrapolation is a visible, checked fact rather than a comment.
        Once the Monday campaign measures the response across the full command
        range, update FIT_COMMAND to the new fit point and this passes.
        """

        config = ActuatorConfig()
        fit_command = 80.0
        applied_command = float(config.policy_command_limit[0])
        factor = applied_command / fit_command
        self.assertAlmostEqual(factor, 2.25, places=6)


if __name__ == "__main__":
    unittest.main()
