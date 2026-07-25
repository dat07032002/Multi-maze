"""Run deterministic smoke checks of level, tilt, walls, and physical holes."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from simulator import CyberRunnerSim


HERE = Path(__file__).resolve().parent
OUTPUTS = HERE / "outputs"


def _distance_xy(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a[:2] - b[:2]))


def verify() -> dict:
    sim = CyberRunnerSim()
    results = {}

    # A quiet open location away from the listed holes and most interior walls.
    level_start = np.array([0.105, 0.125])
    sim.reset(level_start)
    initial = sim.ball_board_position()
    sim.step(1500)
    final = sim.ball_board_position()
    level_drift = _distance_xy(initial, final)
    results["level_board"] = {
        "passed": level_drift < 0.006,
        "drift_m": level_drift,
        "start_xy": initial[:2].tolist(),
        "end_xy": final[:2].tolist(),
    }

    # Tilt inside the large central enclosure and require meaningful rolling
    # without letting this test turn into another hole/fall check.
    tilt_start = np.array([0.105, 0.125])
    sim.reset(tilt_start)
    initial = sim.ball_board_position()
    sim.set_tilt(math.radians(-5.0), math.radians(5.0))
    sim.step(1800)
    final = sim.ball_board_position()
    tilt_displacement = _distance_xy(initial, final)
    stayed_on_board = final[2] > 0.0
    results["tilted_board"] = {
        "passed": tilt_displacement > 0.008 and bool(stayed_on_board),
        "displacement_m": tilt_displacement,
        "start_xy": initial[:2].tolist(),
        "end_xyz": final.tolist(),
        "command_deg": [-5.0, 5.0],
    }

    # Push the ball toward the solid left rim and make sure the rim contains it.
    wall_start = np.array([0.012, 0.150])
    sim.reset(wall_start)
    sim.set_tilt(0.0, math.radians(-7.0))
    sim.step(2200)
    wall_final = sim.ball_board_position()
    contained = wall_final[0] >= sim.ball_radius * 0.65
    results["outer_wall_collision"] = {
        "passed": bool(contained),
        "end_xyz": wall_final.tolist(),
        "minimum_expected_x_m": sim.ball_radius * 0.65,
    }

    # Centering the ball over a modeled opening must make it fall below the board.
    hole_xy = np.asarray(sim.layout["holes"][0], dtype=np.float64)
    sim.reset(hole_xy, settle_steps=0)
    initial_z = float(sim.ball_board_position()[2])
    sim.step(1000)
    hole_final = sim.ball_board_position()
    fell = hole_final[2] < -0.02
    results["physical_hole"] = {
        "passed": bool(fell),
        "hole_xy": hole_xy.tolist(),
        "start_z_m": initial_z,
        "end_xyz": hole_final.tolist(),
    }

    results["all_passed"] = all(
        item.get("passed", True)
        for item in results.values()
        if isinstance(item, dict)
    )
    return results


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    sim = CyberRunnerSim()
    sim.save_xml(OUTPUTS / "cyberrunner_custom_maze.xml")
    results = verify()
    (OUTPUTS / "verification.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    print(json.dumps(results, indent=2))
    if not results["all_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
