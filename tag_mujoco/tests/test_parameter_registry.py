from __future__ import annotations

import unittest

from cyberrunner_mujoco.parameter_registry import (
    load_parameter_registry,
    unresolved_parameters,
)


class ParameterRegistryTest(unittest.TestCase):
    def test_registry_is_valid_and_preserves_uncertainty(self):
        registry = load_parameter_registry()
        unresolved = unresolved_parameters(registry)
        self.assertIn("actuator.total_delay", unresolved)
        self.assertEqual(
            registry["parameters"]["board.width"]["status"], "design"
        )


if __name__ == "__main__":
    unittest.main()

