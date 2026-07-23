"""Open the complete delayed Hiwonder system model in MuJoCo's viewer."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import mujoco
import mujoco.viewer
import numpy as np

from maze_layout import load_json_layout
from system_model import CyberRunnerSystemModel


HERE = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--layout",
        type=Path,
        default=HERE / "generated_mazes" / "maze_seed_970.json",
    )
    parser.add_argument("--randomize", action="store_true")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    system = CyberRunnerSystemModel(load_json_layout(args.layout))
    print(f"Layout: {system.layout.get('name', args.layout.stem)}")
    print("W/S and A/D change normalized policy actions; C centers; R resets.")
    while True:
        system.reset(seed=args.seed, randomize=args.randomize)
        action = np.zeros(2, dtype=np.float64)
        reset_requested = [False]

        def on_key(keycode: int) -> None:
            key = chr(keycode).upper() if 0 <= keycode < 256 else ""
            if key == "W":
                action[0] = np.clip(action[0] + 0.1, -1.0, 1.0)
            elif key == "S":
                action[0] = np.clip(action[0] - 0.1, -1.0, 1.0)
            elif key == "A":
                action[1] = np.clip(action[1] + 0.1, -1.0, 1.0)
            elif key == "D":
                action[1] = np.clip(action[1] - 0.1, -1.0, 1.0)
            elif key == "C":
                action[:] = 0.0
            elif key == "R":
                reset_requested[0] = True
            else:
                return
            print(f"Policy action: x={action[0]:+.2f}, y={action[1]:+.2f}")

        viewer_closed = False
        with mujoco.viewer.launch_passive(
            system.sim.model,
            system.sim.data,
            key_callback=on_key,
            show_left_ui=True,
            show_right_ui=True,
        ) as viewer:
            viewer.cam.type = mujoco.mjtCamera.mjCAMERA_FIXED
            viewer.cam.fixedcamid = mujoco.mj_name2id(
                system.sim.model, mujoco.mjtObj.mjOBJ_CAMERA, "top"
            )
            period = 1.0 / system.config.control_rate_hz
            stopped = False
            while viewer.is_running() and not reset_requested[0]:
                started = time.perf_counter()
                if not stopped:
                    result = system.step(action)
                    if result.terminated or result.truncated:
                        stopped = True
                        action[:] = 0.0
                        print(f"Episode stopped: {result.reason}. Press R to reset.")
                viewer.sync()
                remaining = period - (time.perf_counter() - started)
                if remaining > 0.0:
                    time.sleep(remaining)
            viewer_closed = not viewer.is_running()
        if viewer_closed:
            break


if __name__ == "__main__":
    main()
