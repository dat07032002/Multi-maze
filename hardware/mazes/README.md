# Versioned maze hardware

Each subdirectory represents one immutable physical maze revision. Keep the CAD
source, exact printable export, geometry manifest, generated preview, measured
dimensions, and print settings together.

The JSON layout is the single source of truth for simulation, route validation,
preview rendering, and the provisional STL. Export all of those together with:

```powershell
.\cyberrunner_mujoco\.venv\Scripts\python.exe -m cyberrunner_mujoco.maze_artifact `
  hardware\mazes\maze_v1\maze.json `
  --output-root hardware\mazes\packages
```

The generated STL is intentionally named `maze_prototype.stl`. Do not print it
as a final-fit insert until the TAG mounting interface has been measured and
recorded in `cyberrunner_mujoco/hardware_parameters.json`.

The existing trained maze remains in its current compatibility locations:

- `cyberrunner_dreamer/cyberrunner_dreamer/cyberrunner_layout_custom.py`
- `cyberrunner_dreamer/data/path_custom.pkl`

Do not move or overwrite those files until a new maze revision has been printed,
calibrated, and validated end to end.

Start a new design by copying `template/` to a new immutable identifier such as
`maze_v1/` or `maze_2026_01/`. `tools/maze/build_maze.py` remains a compatibility
front end for the older SVG/Python artifacts and can also invoke the same print
package exporter with `--print-package`.
