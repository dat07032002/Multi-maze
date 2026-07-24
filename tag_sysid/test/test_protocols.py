import unittest

from tag_sysid.protocols import (
    HARD_COMMAND_LIMIT,
    Phase,
    build_protocol,
    validate_protocol,
)


class ProtocolTest(unittest.TestCase):
    def test_every_protocol_is_bounded_single_axis_and_returns_home(self):
        for test in ("home", "axis", "sweep", "step"):
            phases = build_protocol(test)
            validate_protocol(phases)
            self.assertTrue(phases)
            self.assertEqual(phases[-1].command_1, 0.0)
            self.assertEqual(phases[-1].command_2, 0.0)
            for phase in phases:
                self.assertLessEqual(abs(phase.command_1), HARD_COMMAND_LIMIT)
                self.assertLessEqual(abs(phase.command_2), HARD_COMMAND_LIMIT)
                self.assertFalse(phase.command_1 and phase.command_2)

    def test_axis_protocol_uses_only_small_commands(self):
        phases = build_protocol("axis")
        maximum = max(
            max(abs(phase.command_1), abs(phase.command_2)) for phase in phases
        )
        self.assertEqual(maximum, 40.0)

    def test_protocol_command_scale_reduces_every_excitation(self):
        phases = build_protocol("axis", command_scale=0.5)
        nonzero = [
            abs(value)
            for phase in phases
            for value in (phase.command_1, phase.command_2)
            if value
        ]
        self.assertTrue(nonzero)
        self.assertEqual(max(nonzero), 20.0)
        validate_protocol(phases)

    def test_protocol_command_scale_cannot_increase_commands(self):
        with self.assertRaises(ValueError):
            build_protocol("axis", command_scale=1.01)

    def test_axis_only_protocol_never_commands_other_axis(self):
        phases = build_protocol("axis", repetitions=2, axes=(2,))
        self.assertTrue(phases)
        self.assertTrue(any(phase.command_2 for phase in phases))
        self.assertTrue(all(phase.command_1 == 0.0 for phase in phases))
        self.assertTrue(all(phase.axis in (0, 2) for phase in phases))
        validate_protocol(phases)

    def test_invalid_dual_axis_protocol_is_rejected(self):
        phases = [Phase("unsafe", 1, 0, 40.0, 40.0, 1.0)]
        with self.assertRaises(ValueError):
            validate_protocol(phases)

    def test_protocol_exceeding_hard_limit_is_rejected(self):
        phases = [Phase("unsafe", 1, 1, HARD_COMMAND_LIMIT + 1, 0.0, 1.0)]
        with self.assertRaises(ValueError):
            validate_protocol(phases)


if __name__ == "__main__":
    unittest.main()
