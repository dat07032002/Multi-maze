# Maze tools

`build_maze.py` validates a versioned `maze.json` and produces:

- `layout_generated.py`: importable geometry for TAG code
- `maze_preview.svg`: reviewable wall, hole, and waypoint overlay
- `manifest.json`: normalized generated geometry
- optionally `path_custom.pkl`: a `LinearPath` compatible with the current environment

The tool never edits the protected current layout or path pickle. Generate into
the maze revision's own `generated/` directory, review the outputs, and promote
them explicitly only after physical calibration.
