from __future__ import annotations

import json
import unittest

from tag_mujoco.fit_actuator_response import DEFAULT_REPORT, DEFAULT_SYSID, fit
from tag_mujoco.system_config import ActuatorConfig


def _generate_report():
    sysid = json.loads(DEFAULT_SYSID.read_text(encoding="utf-8"))
    return fit(sysid)


class ActuatorResponseTimingTests(unittest.TestCase):
    def test_committed_residual_lag_matches_fit_report(self):
        report = _generate_report()
        config = ActuatorConfig()
        self.assertEqual(
            report["recommended"],
            {
                "total_delay_seconds": config.total_delay_seconds,
                "response_time_constant_seconds": config.response_time_constant_seconds,
            },
        )
        self.assertLess(
            report["committed"]["median_absolute_error_seconds"],
            report["superseded_double_counted"]["median_absolute_error_seconds"],
        )

    def test_checked_in_report_matches_generator(self):
        committed = json.loads(DEFAULT_REPORT.read_text(encoding="utf-8"))
        generated = _generate_report()
        self.assertEqual(committed["recommended"], generated["recommended"])
        self.assertEqual(committed["conditions_used"], generated["conditions_used"])


if __name__ == "__main__":
    unittest.main()
