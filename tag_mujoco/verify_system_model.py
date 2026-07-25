"""Validate the complete actuator, camera, timing, and MuJoCo system model."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

from actuator_model import HiwonderActuatorModel
from maze_layout import load_json_layout
from system_config import ActuatorConfig, SystemConfig
from system_model import TagSystemModel


HERE = Path(__file__).resolve().parent
OUTPUTS = HERE / "outputs"
DEFAULT_LAYOUT = HERE / "generated_mazes" / "maze_seed_970.json"


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


def _camera_montage(model: TagSystemModel) -> Image.Image:
    points = [
        model.route.point_at(0.0),
        model.route.point_at(model.route.total_length * 0.5),
        model.route.point_at(model.route.total_length),
    ]
    labels = ("START PATCH", "MIDDLE PATCH", "GOAL PATCH")
    panels = []
    for point, label in zip(points, labels):
        patch, detected = model.camera.capture(point, model.sim.ball_radius, True)
        if not detected:
            raise RuntimeError("Nominal camera unexpectedly dropped a diagnostic frame")
        panel = Image.fromarray(patch[..., 0]).convert("RGB").resize(
            (256, 256), Image.Resampling.NEAREST
        )
        titled = Image.new("RGB", (256, 286), "white")
        titled.paste(panel, (0, 30))
        ImageDraw.Draw(titled).text((8, 9), label, fill="black")
        panels.append(titled)
    montage = Image.new("RGB", (sum(panel.width for panel in panels), 286), "white")
    cursor = 0
    for panel in panels:
        montage.paste(panel, (cursor, 0))
        cursor += panel.width
    return montage


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    layout = load_json_layout(DEFAULT_LAYOUT)
    config = SystemConfig()
    results = {}

    actuator = HiwonderActuatorModel(ActuatorConfig())
    actuator.submit_action((1.0, -1.0))
    for _ in range(20):
        actuator.step(0.001)
    before_delay = actuator.board_target_angles
    policy_period_steps = round(1.0 / (config.control_rate_hz * 0.001))
    for index in range(1180):
        if index % policy_period_steps == 0:
            actuator.submit_action((1.0, -1.0))
        actuator.step(0.001)
    after_settle = actuator.board_target_angles
    results["actuator"] = {
        "no_instantaneous_response": bool(np.max(np.abs(before_delay)) < 1e-8),
        "positive_x_negative_y_mapping": bool(
            after_settle[0] > math.radians(9.0)
            and after_settle[1] < -math.radians(9.0)
        ),
        "settled_angles_deg": np.degrees(after_settle),
        "servo_positions": actuator.commanded_servo_positions,
    }
    results["actuator"]["passed"] = bool(
        results["actuator"]["no_instantaneous_response"]
        and results["actuator"]["positive_x_negative_y_mapping"]
    )

    model = TagSystemModel(layout, config)
    observation = model.reset(seed=1234, randomize=False)
    camera_metadata = model.camera.metadata()
    results["camera"] = {
        "calibration_scales_to_published_frame": bool(
            camera_metadata["scaled_resolution"]
            == camera_metadata["published_resolution"]
            == [640, 400]
        ),
        "image_shape": list(observation["image"].shape),
        "image_dtype": str(observation["image"].dtype),
        "image_has_structure": bool(np.std(observation["image"]) > 5.0),
        "calibration": camera_metadata,
    }
    results["camera"]["passed"] = bool(
        results["camera"]["calibration_scales_to_published_frame"]
        and observation["image"].shape == (64, 64, 1)
        and observation["image"].dtype == np.uint8
        and results["camera"]["image_has_structure"]
    )

    expected_shapes = {
        "image": (64, 64, 1),
        "states": (4,),
        "goal": (10,),
    }
    shapes_match = all(observation[key].shape == shape for key, shape in expected_shapes.items())
    step = model.step((0.0, 0.0))
    results["interface"] = {
        "shapes_match_real_policy_interface": shapes_match,
        "initial_step_reason": step.reason,
        "control_rate_hz": config.control_rate_hz,
        "observation_delay_steps": config.camera.observation_delay_steps,
        "passed": bool(shapes_match and step.reason == "running"),
    }

    nominal = model.parameter_snapshot()
    model.reset(seed=99, randomize=True)
    randomized = model.parameter_snapshot()
    model.reset(seed=99, randomize=True)
    randomized_repeat = model.parameter_snapshot()
    results["domain_randomization"] = {
        "actuator_changed": nominal["actuator"] != randomized["actuator"],
        "physics_changed": nominal["physics"] != randomized["physics"],
        "same_seed_reproduces_parameters": randomized == randomized_repeat,
    }
    results["domain_randomization"]["passed"] = bool(
        results["domain_randomization"]["actuator_changed"]
        and results["domain_randomization"]["physics_changed"]
        and results["domain_randomization"]["same_seed_reproduces_parameters"]
    )

    model.reset(seed=5, randomize=False, ball_xy=layout["holes"][0])
    fall_reason = "running"
    for _ in range(80):
        result = model.step((0.0, 0.0))
        fall_reason = result.reason
        if result.terminated:
            break
    results["physical_hole"] = {
        "termination_reason": fall_reason,
        "passed": fall_reason == "ball_fell",
    }

    model.reset(seed=1234, randomize=False)
    _camera_montage(model).save(OUTPUTS / "system_model_camera_patches.png")
    results["all_passed"] = all(
        section.get("passed", True)
        for key, section in results.items()
        if key != "all_passed"
    )
    output_path = OUTPUTS / "system_model_validation.json"
    output_path.write_text(
        json.dumps(_jsonable(results), indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(_jsonable(results), indent=2))
    if not results["all_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
