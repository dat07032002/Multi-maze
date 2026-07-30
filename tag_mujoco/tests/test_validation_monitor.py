import argparse
import tempfile
import unittest
from pathlib import Path

from tag_mujoco.validation_monitor import (
    barrier_paths,
    evaluator_command,
    latest_metric_step,
    milestones,
    regressed_from_baseline,
    retention_gate_failed,
    requires_new_checkpoint,
)


def _args(**overrides):
    values = dict(
        python=Path("/python"),
        repo_root=Path("/repo"),
        run_dir=Path("/run"),
        manifest=Path("/manifest.json"),
        split="validation",
        policy_mode="sample",
        canonical_episodes_per_maze=1,
        robust_episodes_per_maze=3,
        retention_manifest=None,
        retention_episodes_per_maze=3,
        robust_randomization_strength=None,
        max_steps=3000,
        seed=20260723,
    )
    values.update(overrides)
    return argparse.Namespace(**values)


def _flag(command, name):
    return command[command.index(name) + 1]


class ValidationMonitorTests(unittest.TestCase):
    def test_barrier_paths_are_stable_and_milestone_specific(self):
        request, release = barrier_paths(Path("/validation"), 25_000)
        self.assertEqual(
            request, Path("/validation/barriers/step_000025000.request.json")
        )
        self.assertEqual(
            release, Path("/validation/barriers/step_000025000.release.json")
        )

    def test_latest_metric_step_skips_partial_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "metrics.jsonl"
            path.write_text(
                '{"step": 100}\nnot-json\n{"step": 250}\n{"other": 1}\n',
                encoding="utf-8",
            )
            self.assertEqual(latest_metric_step(path), 250)

    def test_milestones_include_baseline_once(self):
        self.assertEqual(
            milestones(500_000, 500_000, 1_500_000, True),
            [0, 500_000, 1_000_000, 1_500_000],
        )

    def test_only_intermediate_milestones_require_a_new_checkpoint(self):
        self.assertFalse(requires_new_checkpoint(0, 1_500_000))
        self.assertTrue(requires_new_checkpoint(500_000, 1_500_000))
        self.assertFalse(requires_new_checkpoint(1_500_000, 1_500_000))

    def test_default_canonical_command_keeps_the_historical_protocol(self):
        command = evaluator_command(
            _args(), Path("/snap.ckpt"), Path("/milestone"), 500_000, "canonical"
        )
        self.assertEqual(_flag(command, "--split"), "validation")
        self.assertEqual(_flag(command, "--policy-mode"), "sample")
        self.assertEqual(_flag(command, "--episodes-per-maze"), "1")

    def test_dev_split_and_mode_policy_reach_the_evaluator(self):
        command = evaluator_command(
            _args(split="dev", policy_mode="mode", canonical_episodes_per_maze=3),
            Path("/snap.ckpt"),
            Path("/milestone"),
            500_000,
            "canonical",
        )
        self.assertEqual(_flag(command, "--split"), "dev")
        self.assertEqual(_flag(command, "--policy-mode"), "mode")
        self.assertEqual(_flag(command, "--episodes-per-maze"), "3")

    def test_robust_mode_uses_its_own_episode_count(self):
        command = evaluator_command(
            _args(canonical_episodes_per_maze=1, robust_episodes_per_maze=3),
            Path("/snap.ckpt"),
            Path("/milestone"),
            500_000,
            "robust",
        )
        self.assertEqual(_flag(command, "--episodes-per-maze"), "3")

    def test_fixed_robust_strength_reaches_the_evaluator(self):
        command = evaluator_command(
            _args(robust_randomization_strength=0.10),
            Path("/snap.ckpt"),
            Path("/milestone"),
            250_000,
            "robust",
        )
        self.assertEqual(_flag(command, "--randomization-strength"), "0.1")

    def test_retention_uses_frozen_skill_manifest_and_canonical_conditions(self):
        command = evaluator_command(
            _args(retention_manifest=Path("/stabilize.json")),
            Path("/snap.ckpt"),
            Path("/milestone"),
            25_000,
            "retention",
        )
        self.assertEqual(_flag(command, "--manifest"), "/stabilize.json")
        self.assertEqual(_flag(command, "--mode"), "canonical")
        self.assertEqual(_flag(command, "--episodes-per-maze"), "3")
        self.assertEqual(_flag(command, "--output"), "/milestone/retention.json")

    def test_retention_can_select_the_stabilization_actor_head(self):
        command = evaluator_command(
            _args(
                retention_manifest=Path("/stabilize.json"),
                retention_actor_head="stabilize",
            ),
            Path("/snap.ckpt"),
            Path("/milestone"),
            25_000,
            "retention",
        )
        self.assertEqual(_flag(command, "--actor-head"), "stabilize")

    def test_retention_gate_checks_completion_or_falls_independently(self):
        self.assertTrue(retention_gate_failed(
            {"completion_rate": 0.74, "fall_rate": 0.0}, 0.75, 0.05
        ))
        self.assertTrue(retention_gate_failed(
            {"completion_rate": 0.90, "fall_rate": 0.06}, 0.75, 0.05
        ))
        self.assertFalse(retention_gate_failed(
            {"completion_rate": 0.75, "fall_rate": 0.05}, 0.75, 0.05
        ))

    def test_regression_requires_both_worse_completion_and_more_falls(self):
        baseline = {"completion_rate": 0.90, "fall_rate": 0.08}
        self.assertTrue(
            regressed_from_baseline(
                baseline, {"completion_rate": 0.85, "fall_rate": 0.12}
            )
        )
        self.assertFalse(
            regressed_from_baseline(
                baseline, {"completion_rate": 0.85, "fall_rate": 0.07}
            )
        )
        self.assertFalse(
            regressed_from_baseline(
                baseline, {"completion_rate": 0.91, "fall_rate": 0.12}
            )
        )


if __name__ == "__main__":
    unittest.main()
