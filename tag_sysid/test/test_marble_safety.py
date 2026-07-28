import ast
from pathlib import Path
import unittest


MARBLE = Path(__file__).parents[1] / "tag_sysid" / "marble.py"


class MarbleSafetyTest(unittest.TestCase):
    def test_runner_contains_separate_approval_and_motion_interlocks(self):
        source = MARBLE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        names = {
            node.id for node in ast.walk(tree) if isinstance(node, ast.Name)
        }
        attributes = {
            node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
        }
        self.assertIn("STANDARD_ARM_TOKEN", names)
        self.assertIn("HIGH_ARM_TOKEN", names)
        self.assertIn("--marble-installed", source)
        self.assertIn("--start-clear", source)
        self.assertIn("--operator-present", source)
        self.assertIn("--execute", source)
        self.assertIn("marble_failure", attributes)
        self.assertIn("return_home", attributes)
        self.assertIn("max_speed_mps", attributes)
        self.assertIn("max_missing_frames", attributes)


if __name__ == "__main__":
    unittest.main()
