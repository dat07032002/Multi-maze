"""Verify the clean environment without starting Dreamer or touching a GPU."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

try:
    from .cyberrunner_env import CyberRunnerTask
    from .maze_layout import load_json_layout
    from .maze_dataset import DEFAULT_MANIFEST, load_manifest, load_split
    from .parameter_registry import load_parameter_registry, unresolved_parameters
    from .route_planner import PlannerConfig, validate_route
except ImportError:
    from cyberrunner_env import CyberRunnerTask
    from maze_layout import load_json_layout
    from maze_dataset import DEFAULT_MANIFEST, load_manifest, load_split
    from parameter_registry import load_parameter_registry, unresolved_parameters
    from route_planner import PlannerConfig, validate_route


HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "outputs" / "training_readiness.json"


def _jsonable(value: Any):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer, np.bool_)):
        return value.item()
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def main() -> None:
    registry = load_parameter_registry()
    manifest = load_manifest(DEFAULT_MANIFEST)
    train = load_split("train", DEFAULT_MANIFEST)
    validation_split = load_split("validation", DEFAULT_MANIFEST)
    test = load_split("test", DEFAULT_MANIFEST)
    layouts = list(train.paths + validation_split.paths + test.paths)
    config = PlannerConfig()
    layout_results = {}
    for path in layouts:
        layout = load_json_layout(path)
        route_check = validate_route(layout, layout["waypoints"], config)
        layout_results[path.name] = {
            "passed": route_check.passed,
            "minimum_clearance_m": route_check.minimum_clearance_m,
            "required_margin_m": route_check.required_margin_m,
            "route_length_m": route_check.route_length_m,
        }

    task = CyberRunnerTask(layout_paths=[str(path) for path in layouts], seed=123)
    rollout_results = []
    finite = True
    for layout_index in range(len(layouts)):
        observation, info = task.reset(
            seed=1000 + layout_index, options={"layout_index": layout_index}
        )
        for _ in range(10):
            observation, reward, terminated, truncated, info = task.step(
                np.zeros(2, dtype=np.float32)
            )
            finite = finite and np.isfinite(reward) and all(
                np.all(np.isfinite(value)) for value in observation.values()
            )
            if terminated or truncated:
                break
        rollout_results.append(
            {
                "layout": layouts[layout_index].name,
                "steps": info["episode_steps"],
                "termination_reason": info["termination_reason"],
                "finite": finite,
            }
        )

    all_routes_pass = bool(layout_results) and all(
        result["passed"] for result in layout_results.values()
    )
    result = {
        "training_started": False,
        "approval_required": True,
        "physical_gpu_0_excluded": True,
        "planned_smoke_test_physical_gpu": 2,
        "parameter_registry_valid": True,
        "unresolved_hardware_parameter_count": len(unresolved_parameters(registry)),
        "maze_dataset_id": manifest["dataset_id"],
        "maze_split_counts": {
            "train": len(train.paths),
            "validation": len(validation_split.paths),
            "test": len(test.paths),
        },
        "held_out_splits_disjoint": not bool(
            set(train.paths) & (set(validation_split.paths) | set(test.paths))
            or set(validation_split.paths) & set(test.paths)
        ),
        "continuous_routes": layout_results,
        "zero_action_rollouts": rollout_results,
        "observations_and_rewards_finite": bool(finite),
        "ready_for_multimaze_training_approval": bool(
            all_routes_pass
            and finite
            and len(train.paths) == 40
            and len(validation_split.paths) == 8
            and len(test.paths) == 8
        ),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(_jsonable(result), indent=2) + "\n", encoding="utf-8")
    print(json.dumps(_jsonable(result), indent=2))
    if not result["ready_for_multimaze_training_approval"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
