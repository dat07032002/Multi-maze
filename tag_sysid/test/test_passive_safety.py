import ast
from pathlib import Path
import unittest


RECORDER = Path(__file__).parents[1] / "tag_sysid" / "recorder.py"


class PassiveSafetyTest(unittest.TestCase):
    def test_recorder_has_subscriptions_but_no_control_endpoints(self):
        tree = ast.parse(RECORDER.read_text(encoding="utf-8"))
        calls = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        forbidden = {
            "create_publisher",
            "create_client",
            "create_service",
            "publish",
            "call",
            "call_async",
            "send_goal",
            "send_goal_async",
        }
        self.assertIn("create_subscription", calls)
        self.assertFalse(calls & forbidden)


if __name__ == "__main__":
    unittest.main()
