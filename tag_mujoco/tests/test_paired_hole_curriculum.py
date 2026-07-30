import json
import tempfile
import unittest
from pathlib import Path

from tag_mujoco.curriculum_phase_gate import evaluate_phase_gate
from tag_mujoco.paired_hole_curriculum import (
    build_production_datasets,
    transform_layout,
)
from tag_mujoco.route_planner import PlannerConfig, validate_route


ROOT = Path(__file__).resolve().parents[2]


def _evaluation(completion, falls, progress, episodes=192, band=None):
    band = completion if band is None else band
    return {
        "completed": True,
        "summary": {
            "episodes": episodes,
            "completion_rate": completion,
            "fall_rate": falls,
            "mean_max_route_completion": progress,
        },
        "by_difficulty": {
            "easy": {"completion_rate": band},
            "medium": {"completion_rate": band},
            "hard": {"completion_rate": band},
        },
    }


class PairedHoleCurriculumTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / "tag_mujoco/generated_mazes_v2/maze_seed_10000.json"
        cls.source = json.loads(path.read_text(encoding="utf-8"))

    def test_variants_preserve_topology_and_change_only_hole_task(self):
        variants = {
            name: transform_layout(self.source, name, seed=10000)
            for name in (
                "no_holes",
                "branch_holes",
                "easy_dodge",
                "mixed_holes",
            )
        }
        topology_keys = (
            "walls_h",
            "walls_v",
            "walls_angled",
            "start_cell",
            "goal_cell",
            "grid_horizontal_walls",
            "grid_vertical_walls",
        )
        for layout in variants.values():
            for key in topology_keys:
                self.assertEqual(layout[key], self.source[key])
            self.assertTrue(
                validate_route(
                    layout, layout["waypoints"], PlannerConfig()
                ).passed
            )
        self.assertEqual(len(variants["no_holes"]["holes"]), 0)
        self.assertGreater(len(variants["branch_holes"]["holes"]), 0)
        self.assertTrue(
            set(map(tuple, variants["branch_holes"]["hole_cells"])).isdisjoint(
                set(map(tuple, variants["branch_holes"]["solution_cells"]))
            )
        )
        self.assertEqual(len(variants["easy_dodge"]["holes"]), 1)
        self.assertGreater(
            len(variants["mixed_holes"]["holes"]),
            len(variants["branch_holes"]["holes"]),
        )

    def test_small_production_build_keeps_split_membership_paired(self):
        with tempfile.TemporaryDirectory() as directory:
            outputs = build_production_datasets(
                Path(directory),
                seed_start=51000,
                train_count=4,
                validation_count=1,
                test_count=1,
                max_candidates=30,
            )
            manifests = {
                name: json.loads(path.read_text(encoding="utf-8"))
                for name, path in outputs.items()
            }
            reference = manifests["no_holes"]
            for manifest in manifests.values():
                self.assertEqual(len(manifest["train"]), 4)
                self.assertEqual(len(manifest["validation"]), 1)
                self.assertEqual(len(manifest["test"]), 1)
                for split in ("train", "validation", "test"):
                    self.assertEqual(manifest[split], reference[split])

    def test_phase_two_mastery_gate(self):
        result = evaluate_phase_gate(
            2, _evaluation(0.91, 0.04, 0.96, band=0.86)
        )
        self.assertTrue(result["passed"])

    def test_hole_phases_require_retention_evaluation(self):
        candidate = _evaluation(0.92, 0.08, 0.96, band=0.86)
        self.assertFalse(evaluate_phase_gate(3, candidate)["passed"])
        baseline = _evaluation(0.92, 0.02, 0.97, band=0.90)
        retained = _evaluation(0.91, 0.02, 0.965, band=0.89)
        result = evaluate_phase_gate(
            3,
            candidate,
            retention_baseline=baseline,
            retention_candidate=retained,
        )
        self.assertTrue(result["passed"])

    def test_retention_loss_blocks_promotion(self):
        result = evaluate_phase_gate(
            4,
            _evaluation(0.82, 0.12, 0.92, band=0.72),
            retention_baseline=_evaluation(0.92, 0.02, 0.97),
            retention_candidate=_evaluation(0.88, 0.02, 0.94),
        )
        self.assertFalse(result["passed"])
        self.assertFalse(result["retention"]["passed"])


if __name__ == "__main__":
    unittest.main()
