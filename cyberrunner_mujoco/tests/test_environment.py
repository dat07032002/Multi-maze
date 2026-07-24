from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from cyberrunner_mujoco.cyberrunner_env import (
    CyberRunnerEnv,
    CyberRunnerTask,
    TaskConfig,
    reward_components,
)
from cyberrunner_mujoco.build_maze_dataset import _generation_kwargs
from cyberrunner_mujoco.expert_controller import RouteExpertController, collect_episode
from cyberrunner_mujoco.maze_dataset import (
    DEFAULT_MANIFEST,
    file_sha256,
    load_manifest,
    load_split,
)
from cyberrunner_mujoco.system_model import PolylineRoute
from cyberrunner_mujoco.system_config import ActuatorConfig, PhysicsConfig


class EnvironmentTest(unittest.TestCase):
    def test_maze_identity_ignores_only_platform_newlines(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "maze.json"
            path.write_bytes(b'{\r\n  "board_width": 0.259\r\n}\r\n')
            windows_hash = file_sha256(path)
            path.write_bytes(b'{\n  "board_width": 0.259\n}\n')
            self.assertEqual(file_sha256(path), windows_hash)
            path.write_bytes(b'{\n  "board_width": 0.260\n}\n')
            self.assertNotEqual(file_sha256(path), windows_hash)

    def test_manifest_has_disjoint_40_8_8_splits(self):
        manifest = load_manifest(DEFAULT_MANIFEST)
        self.assertEqual(len(manifest["train"]), 40)
        self.assertEqual(len(manifest["validation"]), 8)
        self.assertEqual(len(manifest["test"]), 8)
        self.assertFalse(set(manifest["train"]) & set(manifest["validation"]))
        self.assertFalse(set(manifest["train"]) & set(manifest["test"]))
        self.assertFalse(set(manifest["validation"]) & set(manifest["test"]))

    def test_v2_manifest_has_disjoint_512_64_64_splits(self):
        path = DEFAULT_MANIFEST.with_name("maze_splits_v2.json")
        manifest = load_manifest(path)
        self.assertEqual(len(manifest["train"]), 512)
        self.assertEqual(len(manifest["validation"]), 64)
        self.assertEqual(len(manifest["test"]), 64)
        self.assertFalse(set(manifest["train"]) & set(manifest["validation"]))
        self.assertFalse(set(manifest["train"]) & set(manifest["test"]))
        self.assertFalse(set(manifest["validation"]) & set(manifest["test"]))
        metadata = tuple(manifest["metadata"].values())
        self.assertEqual(len({item["sha256"] for item in metadata}), 640)
        self.assertEqual(
            {
                (
                    item["generation_parameters"]["columns"],
                    item["generation_parameters"]["rows"],
                )
                for item in metadata
            },
            {(9, 7), (10, 8), (11, 9), (12, 10)},
        )

    def test_curriculum_starts_easy_and_converges_to_uniform(self):
        task = CyberRunnerTask(
            task_config=TaskConfig(
                maze_manifest=str(DEFAULT_MANIFEST),
                maze_split="train",
                maze_sampling="curriculum",
                curriculum_episodes=100,
            )
        )
        difficulty = np.asarray(load_split("train").difficulty_scores)
        initial = task.sampling_probabilities()
        self.assertLess(float(np.dot(initial, difficulty)), float(np.mean(difficulty)))
        self.assertTrue(np.all(initial > 0.0))
        task.episodes_started = 100
        np.testing.assert_allclose(
            task.sampling_probabilities(),
            np.full(len(difficulty), 1.0 / len(difficulty)),
        )

    def test_plr_retains_uniform_coverage_and_prioritizes_unseen_mazes(self):
        task = CyberRunnerTask(
            task_config=TaskConfig(
                maze_manifest=str(DEFAULT_MANIFEST),
                maze_split="train",
                maze_sampling="plr",
                plr_uniform_mix=0.20,
                plr_staleness_mix=0.10,
            )
        )
        task._maze_visits[:] = 1
        task._maze_visits[3] = 0
        probabilities = task.sampling_probabilities()
        self.assertAlmostEqual(float(probabilities.sum()), 1.0)
        self.assertTrue(np.all(probabilities > 0.0))
        self.assertGreater(probabilities[3], float(np.median(probabilities)))

    def test_success_threshold_expands_start_and_randomization_curricula(self):
        task = CyberRunnerTask(
            task_config=TaskConfig(
                random_start=True,
                start_curriculum=True,
                start_curriculum_initial_min=0.8,
                start_curriculum_expand_step=0.1,
                start_curriculum_window=4,
                start_curriculum_success_threshold=0.75,
                randomize_plant=True,
                randomization_curriculum=True,
                randomization_initial_strength=0.0,
                randomization_expand_step=0.2,
                randomization_window=4,
                randomization_success_threshold=0.75,
            )
        )
        task.episodes_started = 4
        task._recent_successes.extend((1.0, 1.0, 1.0, 0.0))
        task._advance_curricula()
        self.assertAlmostEqual(task._start_frontier, 0.7)
        self.assertAlmostEqual(task._randomization_strength, 0.2)

    def test_randomization_strength_interpolates_from_nominal(self):
        nominal_actuator = ActuatorConfig()
        nominal_physics = PhysicsConfig()
        zero_actuator = nominal_actuator.randomized(np.random.default_rng(3), 0.0)
        zero_physics = nominal_physics.randomized(np.random.default_rng(3), 0.0)
        self.assertEqual(zero_actuator, nominal_actuator)
        self.assertEqual(zero_physics, nominal_physics)
        full_actuator = nominal_actuator.randomized(np.random.default_rng(3), 1.0)
        full_physics = nominal_physics.randomized(np.random.default_rng(3), 1.0)
        self.assertNotEqual(full_actuator, nominal_actuator)
        self.assertNotEqual(full_physics, nominal_physics)

    def test_diverse_generation_profile_is_deterministic_and_varied(self):
        first = _generation_kwargs(12345, "diverse_v2")
        self.assertEqual(first, _generation_kwargs(12345, "diverse_v2"))
        variants = {
            tuple(sorted(_generation_kwargs(seed, "diverse_v2").items()))
            for seed in range(12345, 12355)
        }
        self.assertGreater(len(variants), 1)

    def test_privileged_expert_emits_finite_contract_actions(self):
        task = CyberRunnerTask(seed=8)
        task.reset(seed=8)
        controller = RouteExpertController()
        action = controller.action(task)
        self.assertEqual(action.shape, (2,))
        self.assertTrue(np.all(np.isfinite(action)))
        self.assertTrue(np.all(np.abs(action) <= controller.config.action_limit))

    def test_privileged_expert_can_save_success_without_privileged_fields(self):
        manifest = DEFAULT_MANIFEST.with_name("maze_splits_v2.json")
        task = CyberRunnerTask(
            seed=10,
            task_config=TaskConfig(
                maze_manifest=str(manifest),
                maze_split="train",
                random_start=True,
                start_progress_min=0.85,
                start_progress_max=0.90,
            ),
        )
        episode, info = collect_episode(
            task,
            RouteExpertController(),
            layout_index=0,
            seed=10,
            max_steps=100,
        )
        self.assertEqual(info["termination_reason"], "goal_reached")
        self.assertTrue(bool(episode["is_last"][-1]))
        self.assertTrue(bool(episode["is_terminal"][-1]))
        self.assertNotIn("ball_visible", episode)
        self.assertNotIn("true_ball_position", episode)

    def test_scaled_progress_preserves_progress_direction_and_scale(self):
        legacy = CyberRunnerTask(task_config=TaskConfig(reward_mode="progress"))
        scaled = CyberRunnerTask(
            task_config=TaskConfig(
                reward_mode="scaled_progress",
                progress_reward_scale=10.0,
            )
        )
        legacy.reset(seed=17)
        scaled.reset(seed=17)
        action = np.asarray((0.2, -0.1), dtype=np.float32)
        legacy_step = legacy.step(action)
        scaled_step = scaled.step(action)
        self.assertEqual(legacy_step[2:4], scaled_step[2:4])
        self.assertAlmostEqual(scaled_step[1], 10.0 * legacy_step[1], places=6)

    def test_scaled_reward_has_explicit_success_and_failure_terms(self):
        config = TaskConfig(
            reward_mode="scaled_progress",
            progress_reward_scale=10.0,
            success_bonus=10.0,
            failure_penalty=5.0,
        )
        self.assertEqual(reward_components(config, 0.1, 0.4, "running"), (1.0, 0.0, 0.0))
        self.assertEqual(
            reward_components(config, 0.1, 1.0, "goal_reached"),
            (1.0, 10.0, 0.0),
        )
        self.assertEqual(
            reward_components(config, 0.1, 0.4, "ball_fell"),
            (1.0, 0.0, -5.0),
        )

    def test_stateful_projection_rejects_nearby_later_corridor(self):
        route = PolylineRoute(
            [
                (0.0, 0.0),
                (0.1, 0.0),
                (0.1, 0.01),
                (0.0, 0.01),
            ]
        )
        global_progress = route.project((0.001, 0.009))[0]
        local_progress = route.project(
            (0.001, 0.009),
            progress_hint=0.001,
            backward_window=0.01,
            forward_window=0.02,
        )[0]
        self.assertGreater(global_progress, 0.20)
        self.assertLess(local_progress, 0.03)

    def test_reset_and_step_are_deterministic(self):
        first = CyberRunnerTask(seed=4)
        second = CyberRunnerTask(seed=4)
        first_obs, _ = first.reset(seed=11)
        second_obs, _ = second.reset(seed=11)
        for key in first_obs:
            np.testing.assert_array_equal(first_obs[key], second_obs[key])
        first_step = first.step(np.zeros(2, dtype=np.float32))
        second_step = second.step(np.zeros(2, dtype=np.float32))
        self.assertEqual(first_step[1:4], second_step[1:4])
        for key in first_step[0]:
            np.testing.assert_array_equal(first_step[0][key], second_step[0][key])

    def test_gym_space_contains_observations_and_no_nan(self):
        env = CyberRunnerEnv()
        reset_result = env.reset(seed=5)
        observation = reset_result[0] if isinstance(reset_result, tuple) else reset_result
        self.assertTrue(env.observation_space.contains(observation))
        for _ in range(12):
            result = env.step(np.zeros(2, dtype=np.float32))
            observation = result[0]
            self.assertTrue(env.observation_space.contains(observation))
            for value in observation.values():
                self.assertTrue(np.all(np.isfinite(value)))
            if bool(result[2]) or (len(result) == 5 and bool(result[3])):
                break


if __name__ == "__main__":
    unittest.main()
