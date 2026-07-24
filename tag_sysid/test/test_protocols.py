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
