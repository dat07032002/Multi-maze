import unittest

from tag_sysid.marble_protocols import (
    MARBLE_COMMAND_LIMIT,
    build_marble_breakaway,
    build_marble_gentle_high,
    build_marble_high_breakaway,
    build_marble_pulse,
)


class MarbleProtocolTest(unittest.TestCase):
    def test_pulse_is_gradual_bounded_single_axis_and_returns_home(self):
        expected = [0, 5, 10, 15, 20, 15, 10, 5, 0]
        for axis in (1, 2):
            for direction in (-1, 1):
                phases = build_marble_pulse(axis, direction)
                values = [
                    phase.command_1 if axis == 1 else phase.command_2
                    for phase in phases
                ]
                self.assertEqual(values, [direction * value for value in expected])
                self.assertLessEqual(max(map(abs, values)), MARBLE_COMMAND_LIMIT)
                self.assertTrue(all(phase.axis in (0, axis) for phase in phases))
                self.assertEqual(values[-1], 0.0)

    def test_invalid_axis_and_direction_are_rejected(self):
        with self.assertRaises(ValueError):
            build_marble_pulse(0, 1)
        with self.assertRaises(ValueError):
            build_marble_pulse(1, 0)

    def test_breakaway_staircase_reaches_fifty_and_returns_home(self):
        phases = build_marble_breakaway(1, -1)
        self.assertEqual(
            [phase.command_1 for phase in phases],
            [0, -20, -25, -30, -35, -40, -45, -50, 0],
        )
        self.assertTrue(all(phase.command_2 == 0.0 for phase in phases))
        self.assertEqual(sum(p.duration_seconds for p in phases), 5.1)

    def test_high_breakaway_staircase_reaches_one_hundred(self):
        phases = build_marble_high_breakaway(1, -1)
        self.assertEqual(
            [phase.command_1 for phase in phases],
            [0, -50, -60, -70, -80, -90, -100, 0],
        )
        self.assertTrue(all(phase.command_2 == 0.0 for phase in phases))
        self.assertEqual(sum(p.duration_seconds for p in phases), 4.5)

    def test_gentle_high_uses_ten_command_steps_and_returns_home(self):
        phases = build_marble_gentle_high(2, -1)
        values = [phase.command_2 for phase in phases]
        self.assertEqual(min(values), -100.0)
        self.assertEqual(values[-1], 0.0)
        outward = values[1:11]
        self.assertTrue(
            all(
                abs(second - first) == 10.0
                for first, second in zip(outward, outward[1:])
            )
        )


if __name__ == "__main__":
    unittest.main()
