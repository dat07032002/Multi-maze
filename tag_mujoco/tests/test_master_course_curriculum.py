from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from tag_mujoco.master_course_gate import (
    evaluate_master_course_gate,
    stage_training_trend,
)
from tag_mujoco.master_course_generator import (
    COURSE_STAGES,
    build_master_course_dataset,
    build_master_course_layout,
)
from tag_mujoco.maze_dataset import load_manifest
from tag_mujoco.route_planner import PlannerConfig, validate_route
from tag_mujoco.tag_env import TagMazeTask, TaskConfig


def _canonical(trigger_step, *, completion, progress, falls=0.0):
    """Build one canonical validation result, as the monitor writes them."""
    return {
        "trigger_step": trigger_step,
        "checkpoint": f"step_{trigger_step:09d}/checkpoint.ckpt",
        "summary": {
            "completion_rate": completion,
            "fall_rate": falls,
            "mean_max_route_completion": progress,
        },
    }


class MasterCourseCurriculumTests(unittest.TestCase):
    def test_every_stage_is_deterministic_safe_and_skill_labeled(self):
        for stage in COURSE_STAGES:
            first, metadata = build_master_course_layout(stage.name, 7)
            second, _ = build_master_course_layout(stage.name, 7)
            self.assertEqual(first, second)
            self.assertEqual(first["master_course"]["skills"], list(stage.skills))
            self.assertFalse(metadata["policy_observation_contains_labels"])
            validation = validate_route(first, first["waypoints"], PlannerConfig())
            self.assertTrue(validation.passed, stage.name)
            self.assertGreater(validation.route_length_m, 0.04)
            for zone in first["master_course"]["zones"]:
                self.assertGreaterEqual(zone["start_progress_fraction"], 0.0)
                self.assertLessEqual(zone["end_progress_fraction"], 1.0)
                self.assertLess(
                    zone["start_progress_fraction"], zone["end_progress_fraction"]
                )
            if stage.hazards:
                self.assertGreaterEqual(len(first["holes"]), 2)
                self.assertLess(metadata["minimum_clearance_m"], 0.010)
            if stage.narrow_corridor:
                self.assertEqual(len(first["walls_angled"]), 2)
                first_wall, second_wall = first["walls_angled"]
                first_midpoint = 0.5 * (
                    np.asarray(first_wall[:2]) + np.asarray(first_wall[2:])
                )
                second_midpoint = 0.5 * (
                    np.asarray(second_wall[:2]) + np.asarray(second_wall[2:])
                )
                self.assertAlmostEqual(
                    float(np.linalg.norm(first_midpoint - second_midpoint)),
                    0.030,
                    places=6,
                )

    def test_variants_change_geometry_without_changing_skill_order(self):
        first, _ = build_master_course_layout("compound", 0)
        second, _ = build_master_course_layout("compound", 1)
        self.assertNotEqual(first["waypoints"], second["waypoints"])
        self.assertEqual(
            [zone["skill"] for zone in first["master_course"]["zones"]],
            [zone["skill"] for zone in second["master_course"]["zones"]],
        )

    def test_manifests_are_cumulative_disjoint_and_hash_verified(self):
        with tempfile.TemporaryDirectory() as temporary:
            outputs = build_master_course_dataset(
                Path(temporary),
                train_per_stage=2,
                validation_per_stage=1,
                test_per_stage=1,
            )
            self.assertEqual(set(outputs), {stage.name for stage in COURSE_STAGES})
            for stage in COURSE_STAGES:
                manifest = load_manifest(outputs[stage.name])
                self.assertEqual(len(manifest["train"]), 2 * stage.index)
                self.assertEqual(len(manifest["validation"]), stage.index)
                self.assertEqual(len(manifest["test"]), stage.index)
                self.assertFalse(set(manifest["train"]) & set(manifest["validation"]))
                self.assertFalse(set(manifest["train"]) & set(manifest["test"]))
                stages = {
                    manifest["metadata"][relative]["course_stage"]
                    for relative in manifest["train"]
                }
                self.assertEqual(
                    stages, {item.name for item in COURSE_STAGES[: stage.index]}
                )
                dev_stages = {
                    manifest["metadata"][relative]["course_stage"]
                    for relative in manifest["dev"]
                }
                self.assertEqual(dev_stages, stages)

    def test_recovery_metadata_changes_reset_without_policy_labels(self):
        with tempfile.TemporaryDirectory() as temporary:
            outputs = build_master_course_dataset(
                Path(temporary),
                train_per_stage=1,
                validation_per_stage=1,
                test_per_stage=1,
            )
            manifest = load_manifest(outputs["recovery"])
            recovery = next(
                relative
                for relative in manifest["train"]
                if manifest["metadata"][relative]["course_stage"] == "recovery"
            )
            task = TagMazeTask(
                layout_paths=[str(outputs["recovery"].parent / recovery)],
                layout_metadata=[manifest["metadata"][recovery]],
                task_config=TaskConfig(conditioned_resets=True),
            )
            observation, info = task.reset(options={"layout_index": 0})
            self.assertGreater(info["start_progress_fraction"], 0.0)
            self.assertNotIn("course_stage", observation)
            self.assertNotIn("skills", observation)
            self.assertEqual(
                set(task.policy_contract.observation_keys), {"image", "states", "goal"}
            )

    def test_each_stage_resets_and_steps_in_the_simulator(self):
        with tempfile.TemporaryDirectory() as temporary:
            outputs = build_master_course_dataset(
                Path(temporary),
                train_per_stage=1,
                validation_per_stage=1,
                test_per_stage=1,
            )
            for stage in COURSE_STAGES:
                manifest = load_manifest(outputs[stage.name])
                relative = next(
                    item
                    for item in manifest["train"]
                    if manifest["metadata"][item]["course_stage"] == stage.name
                )
                task = TagMazeTask(
                    layout_paths=[str(outputs[stage.name].parent / relative)],
                    layout_metadata=[manifest["metadata"][relative]],
                    task_config=TaskConfig(conditioned_resets=True),
                )
                observation, _ = task.reset(options={"layout_index": 0})
                task.policy_contract.validate_observation(observation)
                observation, reward, _, _, info = task.step(np.zeros(2))
                task.policy_contract.validate_observation(observation)
                self.assertTrue(np.isfinite(reward), stage.name)
                self.assertTrue(np.isfinite(info["route_completion"]), stage.name)

    def test_gate_requires_current_mastery_and_previous_retention(self):
        with tempfile.TemporaryDirectory() as temporary:
            outputs = build_master_course_dataset(
                Path(temporary),
                train_per_stage=1,
                validation_per_stage=4,
                test_per_stage=1,
            )
            manifest = load_manifest(outputs["turns"])
            episodes = []
            for relative in manifest["validation"]:
                for _ in range(1):
                    episodes.append(
                        {
                            "layout": Path(relative).name,
                            "success": True,
                            "fall": False,
                            "max_route_completion": 0.97,
                        }
                    )
            result = evaluate_master_course_gate(
                {"episodes": episodes}, manifest, "turns"
            )
            self.assertTrue(result["passed"])
            episodes[-1]["fall"] = True
            episodes[-1]["success"] = False
            result = evaluate_master_course_gate(
                {"episodes": episodes}, manifest, "turns"
            )
            self.assertFalse(result["passed"])

    def test_progress_earned_far_off_route_cannot_pass_the_gate(self):
        """The 50k smoke result, replayed against the gate.

        Four validation layouts reported max_route_completion of exactly 1.0
        while averaging 174 mm of cross-track error on a 259 mm board. Route
        completion projects the ball onto the route without checking how far
        away it is, so a ball crossing the board sweeps the projection to the
        end and scores a perfect route. Those episodes must not satisfy the
        progress floor.
        """
        with tempfile.TemporaryDirectory() as temporary:
            outputs = build_master_course_dataset(
                Path(temporary),
                train_per_stage=1,
                validation_per_stage=4,
                test_per_stage=1,
            )
            manifest = load_manifest(outputs["turns"])
            episodes = [
                {
                    "layout": Path(relative).name,
                    "success": True,
                    "fall": False,
                    "max_route_completion": 1.0,
                    "mean_cross_track_error_m": 0.174,
                }
                for relative in manifest["validation"]
            ]
            result = evaluate_master_course_gate(
                {"episodes": episodes}, manifest, "turns"
            )
            self.assertFalse(result["passed"])
            stage = result["stages"]["foundation"]
            self.assertEqual(stage["untrusted_progress_episodes"], stage["episodes"])
            self.assertTrue(any("route corridor" in r for r in stage["reasons"]))

    def test_genuinely_tracked_progress_still_passes(self):
        """The guard must not punish a policy that really follows the route."""
        with tempfile.TemporaryDirectory() as temporary:
            outputs = build_master_course_dataset(
                Path(temporary),
                train_per_stage=1,
                validation_per_stage=4,
                test_per_stage=1,
            )
            manifest = load_manifest(outputs["turns"])
            episodes = [
                {
                    "layout": Path(relative).name,
                    "success": True,
                    "fall": False,
                    "max_route_completion": 0.97,
                    "mean_cross_track_error_m": 0.004,
                }
                for relative in manifest["validation"]
            ]
            result = evaluate_master_course_gate(
                {"episodes": episodes}, manifest, "turns"
            )
            self.assertTrue(result["passed"])
            self.assertEqual(
                result["stages"]["foundation"]["untrusted_progress_episodes"], 0
            )

    def test_difficulty_rises_monotonically_across_stages(self):
        """A cumulative curriculum has to actually get harder.

        The score is what the gate's difficulty bands and the weakness report
        are keyed on, so a stage ordering that does not increase difficulty
        would make every later floor meaningless without failing anything.
        """
        scores = []
        for stage in COURSE_STAGES:
            _, metadata = build_master_course_layout(stage.name, 0)
            scores.append(metadata["difficulty_score"])
            self.assertGreaterEqual(metadata["difficulty_score"], 0.0)
            self.assertLessEqual(metadata["difficulty_score"], 1.0)
        self.assertEqual(scores, sorted(scores))
        self.assertGreater(scores[-1], scores[0])
        # Variant jitter must not reorder the stages it sits between.
        for stage in COURSE_STAGES:
            variants = [
                build_master_course_layout(stage.name, variant)[1]["difficulty_score"]
                for variant in range(5)
            ]
            self.assertLess(max(variants) - min(variants), 0.17)

    def test_a_stage_that_ends_worse_than_it_started_is_not_promoted(self):
        """The 150k foundation run, replayed against the gate.

        Canonical mean route completion started at 0.729 on the untrained
        checkpoint, then sat at 0.501 for three milestones. Every floor check
        in this gate reads a single snapshot, so without the trend the run
        could be promoted on a lucky evaluation despite having unlearned the
        skill it started with.
        """
        history = [
            _canonical(0, completion=0.0, progress=0.7289),
            _canonical(50_000, completion=0.0, progress=0.5012),
            _canonical(100_000, completion=0.0, progress=0.5012),
            _canonical(150_000, completion=0.0, progress=0.5011),
        ]
        trend = stage_training_trend(history)
        self.assertTrue(trend["regressed"])
        self.assertTrue(trend["plateaued"])
        self.assertEqual(trend["best_trigger_step"], 0)
        self.assertAlmostEqual(trend["progress_drop"], 0.2278, places=4)
        self.assertTrue(any("route progress fell" in r for r in trend["reasons"]))

    def test_a_stage_that_improves_is_not_flagged_as_a_regression(self):
        history = [
            _canonical(0, completion=0.10, progress=0.60),
            _canonical(50_000, completion=0.55, progress=0.82),
            _canonical(100_000, completion=0.88, progress=0.95),
        ]
        trend = stage_training_trend(history)
        self.assertFalse(trend["regressed"])
        self.assertFalse(trend["plateaued"])
        self.assertEqual(trend["best_trigger_step"], 100_000)
        self.assertEqual(trend["reasons"], [])

    def test_a_high_scoring_plateau_is_reported_but_still_promotable(self):
        """Plateauing at mastery means finished, not failed.

        Only a regression blocks promotion. A stage that reaches its floors and
        then stops improving has learned the skill and should move on.
        """
        history = [
            _canonical(0, completion=0.91, progress=0.96),
            _canonical(50_000, completion=0.91, progress=0.96),
            _canonical(100_000, completion=0.91, progress=0.96),
            _canonical(150_000, completion=0.91, progress=0.96),
        ]
        trend = stage_training_trend(history)
        self.assertTrue(trend["plateaued"])
        self.assertFalse(trend["regressed"])

    def test_an_empty_history_is_reported_as_unevaluated(self):
        trend = stage_training_trend([])
        self.assertFalse(trend["evaluated"])
        self.assertFalse(trend["regressed"])
        self.assertEqual(trend["history_length"], 0)

    def test_regression_overrides_passing_floor_checks(self):
        with tempfile.TemporaryDirectory() as temporary:
            outputs = build_master_course_dataset(
                Path(temporary),
                train_per_stage=1,
                validation_per_stage=4,
                test_per_stage=1,
            )
            manifest = load_manifest(outputs["turns"])
            episodes = [
                {
                    "layout": Path(relative).name,
                    "success": True,
                    "fall": False,
                    "max_route_completion": 0.97,
                }
                for relative in manifest["validation"]
            ]
            history = [
                _canonical(0, completion=0.0, progress=0.7289),
                _canonical(50_000, completion=0.0, progress=0.5012),
                _canonical(100_000, completion=0.0, progress=0.5012),
            ]
            result = evaluate_master_course_gate(
                {"episodes": episodes},
                manifest,
                "turns",
                canonical_results=history,
            )
            self.assertFalse(result["passed"])
            self.assertTrue(result["trend"]["regressed"])
            # Without the history the same snapshot still passes, so the trend
            # is doing the work rather than an unrelated floor tightening.
            self.assertTrue(
                evaluate_master_course_gate(
                    {"episodes": episodes}, manifest, "turns"
                )["passed"]
            )


if __name__ == "__main__":
    unittest.main()
