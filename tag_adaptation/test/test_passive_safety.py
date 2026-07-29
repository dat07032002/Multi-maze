import ast
from pathlib import Path
import unittest


class PassiveSafetyTests(unittest.TestCase):
    def test_package_imports_no_ros_and_creates_no_control_endpoints(self):
        package = Path(__file__).parents[1] / "tag_adaptation"
        forbidden_calls = {
            "create_publisher",
            "create_service",
            "create_client",
            "publish",
        }
        for path in package.glob("*.py"):
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("import rclpy", source)
            tree = ast.parse(source)
            called = {
                node.func.attr
                for node in ast.walk(tree)
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
            }
            self.assertFalse(
                called & forbidden_calls,
                f"{path.name} contains a control endpoint",
            )


if __name__ == "__main__":
    unittest.main()
