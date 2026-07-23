# Versioned maze hardware

Each subdirectory represents one immutable physical maze revision. Keep the CAD
source, exact printable export, geometry manifest, generated preview, measured
dimensions, and print settings together.

The existing trained maze remains in its current compatibility locations:

- `cyberrunner_dreamer/cyberrunner_dreamer/cyberrunner_layout_custom.py`
- `cyberrunner_dreamer/data/path_custom.pkl`

Do not move or overwrite those files until a new maze revision has been printed,
calibrated, and validated end to end.

Start a new design by copying `template/` to a new immutable identifier such as
`maze_v1/` or `maze_2026_01/`.
