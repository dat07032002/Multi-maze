"""Open the custom maze in MuJoCo's interactive desktop viewer."""

from __future__ import annotations

import argparse
import math
import time
from pathlib import Path

import mujoco
import mujoco.viewer

from maze_layout import load_json_layout
from simulator import CyberRunnerSim


TILT_STEP = math.radians(1.0)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--layout",
        type=Path,
        help="Generated maze JSON to open (default: original custom maze)",
    )
    args = parser.parse_args()
    layout = load_json_layout(args.layout) if args.layout else None
    sim = CyberRunnerSim(layout)
    tilt = [0.0, 0.0]

    def on_key(keycode: int) -> None:
        key = chr(keycode).upper() if 0 <= keycode < 256 else ""
        if key == "W":
            tilt[0] += TILT_STEP
        elif key == "S":
            tilt[0] -= TILT_STEP
        elif key == "A":
            tilt[1] += TILT_STEP
        elif key == "D":
            tilt[1] -= TILT_STEP
        elif key == "C":
            tilt[:] = [0.0, 0.0]
        elif key == "R":
            tilt[:] = [0.0, 0.0]
            sim.reset()
        else:
            return
        sim.set_tilt(*tilt)
        print(
            f"Tilt command: x={math.degrees(tilt[0]):.1f} deg, "
            f"y={math.degrees(tilt[1]):.1f} deg"
        )

    print("CyberRunner MuJoCo viewer controls")
    print(f"  Layout: {sim.layout.get('name', 'custom maze')}")
    print("  W/S: tilt X axis by 1 degree")
    print("  A/D: tilt Y axis by 1 degree")
    print("  C: center the board")
    print("  R: reset the board and ball")
    print("  Mouse: MuJoCo camera controls")

    with mujoco.viewer.launch_passive(
        sim.model, sim.data, key_callback=on_key, show_left_ui=True, show_right_ui=True
    ) as viewer:
        viewer.cam.type = mujoco.mjtCamera.mjCAMERA_FIXED
        viewer.cam.fixedcamid = mujoco.mj_name2id(
            sim.model, mujoco.mjtObj.mjOBJ_CAMERA, "top"
        )
        timestep = float(sim.model.opt.timestep)
        while viewer.is_running():
            frame_start = time.perf_counter()
            mujoco.mj_step(sim.model, sim.data)
            viewer.sync()
            remaining = timestep - (time.perf_counter() - frame_start)
            if remaining > 0:
                time.sleep(remaining)


if __name__ == "__main__":
    main()
