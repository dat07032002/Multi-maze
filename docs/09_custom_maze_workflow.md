# Custom 3D-printed maze workflow

The physical print and software geometry must be revisions of the same design.
Do not hand-edit a generated layout without updating its canonical maze source.

## Per-maze directory

Create a new directory under `hardware/mazes/`, for example `maze_v1/`:

```text
maze_v1/
├── README.md
├── source/       # native CAD, STEP, and 2D DXF export
├── print/        # STL or 3MF actually sent to the printer
├── maze.json     # board, walls, holes, and ordered waypoints
└── generated/    # validated software and preview artifacts
```

Copy `hardware/mazes/template/maze.json` as the starting manifest. Use meters in
the software manifest, even if the CAD program displays millimeters.

## Generation

Validate the manifest and generate a Python layout plus an SVG preview:

```bash
python3 tools/maze/build_maze.py \
  hardware/mazes/maze_v1/maze.json \
  --output-dir hardware/mazes/maze_v1/generated
```

Use `--path-pickle` only after the maze has no angled walls and the repository's
Python environment can import NumPy and `cyberrunner_dreamer`. The current path
collision precomputation supports horizontal and vertical walls; generation
fails safely for angled walls rather than producing a misleading path map.

## Before printing

1. Verify board width, height, wall thickness, ball radius, and hole radii.
2. Inspect the SVG preview for wall/waypoint mistakes.
3. Confirm the path never crosses a wall or hole and has enough clearance for the ball.
4. Export the exact print file and record material, scale, orientation, and slicer settings.
5. Assign an immutable `maze_id` and revision.

## After printing

1. Measure the print and compare it with the manifest.
2. Install the maze without changing the camera/marker coordinate orientation.
3. Re-level the board and recalibrate Hiwonder home and safe travel.
4. Re-run marker selection; redo camera calibration if the camera moved.
5. Overlay live state estimates on the generated maze preview.
6. Generate the new path pickle and select it explicitly for training.
7. Record the `maze_id` with every checkpoint and replay dataset.

The existing `cyberrunner_layout_custom.py` and `path_custom.pkl` remain protected
until the new printed maze completes this validation.
