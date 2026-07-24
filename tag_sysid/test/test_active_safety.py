import ast
from pathlib import Path
import unittest


ACTIVE = Path(__file__).parents[1] / "tag_sysid" / "active.py"


class ActiveSafetyTest(unittest.TestCase):
    def test_active_runner_contains_required_interlocks(self):
        source = ACTIVE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        names = {
            node.id for node in ast.walk(tree) if isinstance(node, ast.Name)
        }
        attributes = {
            node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
        }
        self.assertIn("ARM_TOKEN", names)
        self.assertIn("_external_publishers", attributes)
        self.assertIn("return_home", attributes)
        self.assertIn("publish", attributes)
        self.assertIn("--operator-present", source)
        self.assertIn("--ball-removed", source)
        self.assertIn("--max-command", source)
        self.assertIn("--command-scale", source)
        self.assertIn("--max-board-angle-deg", source)
        self.assertIn("--runtime-state-timeout", source)
        self.assertIn("--max-angle-excursion-deg", source)
        self.assertIn("--baseline-seconds", source)
        self.assertIn("angle_limit_exceeded", attributes)
        self.assertIn("latest_state_ns", attributes)
        self.assertIn("baseline_alpha_rad", attributes)
        self.assertIn("baseline_beta_rad", attributes)


if __name__ == "__main__":
    unittest.main()
