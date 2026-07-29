import json
from pathlib import Path
import tempfile
import unittest

from tag_adaptation.promotion import (
    PromotionGate,
    evaluation_summary,
    policy_identity,
    promote_candidate,
)
from tag_adaptation.weakness import analyze_weaknesses


class WeaknessAndPromotionTests(unittest.TestCase):
    def test_weakness_report_ranks_failing_hairpins(self):
        episodes = [
            {
                "maximum_turn_angle_deg": 90,
                "maximum_entry_speed_mps": 0.09,
                "minimum_hole_clearance_m": 0.002,
                "minimum_camera_confidence": 0.9,
                "actuator_direction_reversal": True,
                "difficulty_band": "hard",
                "success": False,
                "fall": True,
                "intervention_count": 2,
                "max_route_completion": 0.5,
            },
            {
                "maximum_turn_angle_deg": 5,
                "maximum_entry_speed_mps": 0.02,
                "minimum_hole_clearance_m": 0.02,
                "minimum_camera_confidence": 0.9,
                "actuator_direction_reversal": False,
                "difficulty_band": "easy",
                "success": True,
                "fall": False,
                "intervention_count": 0,
                "max_route_completion": 1.0,
            },
        ]
        report = analyze_weaknesses(episodes)
        worst = report["slices_worst_first"][0]
        self.assertIn(
            worst["value"],
            {"hairpin", "critical", "reversal", "hard"},
        )
        self.assertEqual(worst["fall_rate"], 1.0)

    def test_gate_requires_improvement_without_regression(self):
        champion = {
            "episodes": 192,
            "completion_rate": 0.85,
            "fall_rate": 0.10,
            "hard_completion_rate": 0.75,
        }
        improved = {
            "episodes": 192,
            "completion_rate": 0.87,
            "fall_rate": 0.08,
            "hard_completion_rate": 0.76,
        }
        regressed = {
            "episodes": 192,
            "completion_rate": 0.80,
            "fall_rate": 0.12,
            "hard_completion_rate": 0.70,
        }
        self.assertTrue(PromotionGate().evaluate(champion, improved)["passed"])
        self.assertFalse(
            PromotionGate().evaluate(champion, regressed)["passed"]
        )

    def test_dreamer_evaluation_result_is_normalized(self):
        summary = evaluation_summary(
            {
                "summary": {
                    "episodes": 192,
                    "completion_rate": 0.9,
                    "fall_rate": 0.05,
                },
                "by_difficulty": {"hard": {"completion_rate": 0.8}},
            }
        )
        self.assertEqual(summary["hard_completion_rate"], 0.8)

    def test_registry_promotion_is_hash_guarded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            champion_path = root / "champion.ckpt"
            candidate_path = root / "candidate.ckpt"
            champion_path.write_bytes(b"champion")
            candidate_path.write_bytes(b"candidate")
            champion = policy_identity(champion_path, role="champion")
            candidate = policy_identity(
                candidate_path,
                role="candidate",
                parent_sha256=champion["checkpoint_sha256"],
            )
            registry_path = root / "registry.json"
            registry_path.write_text(
                json.dumps({"schema_version": 1, "champion": champion})
            )
            with self.assertRaises(RuntimeError):
                promote_candidate(
                    registry_path,
                    candidate,
                    {"passed": True},
                    expected_champion_sha256="wrong",
                )
            promote_candidate(
                registry_path,
                candidate,
                {"passed": True},
                expected_champion_sha256=champion["checkpoint_sha256"],
            )
            registry = json.loads(registry_path.read_text())
            self.assertEqual(
                registry["champion"]["checkpoint_sha256"],
                candidate["checkpoint_sha256"],
            )
            self.assertEqual(len(registry["history"]), 1)


if __name__ == "__main__":
    unittest.main()
