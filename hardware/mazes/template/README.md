# Maze template

Rename this directory and replace the example geometry before printing.

Record here:

- maze ID and revision
- CAD application and source-file version
- measured finished dimensions
- filament/material
- printer, nozzle, layer height, infill, and orientation
- exported print filename and checksum
- camera/marker orientation
- compatible Hiwonder calibration file

Place editable CAD/STEP/DXF files in `source/` and STL/3MF exports in `print/`.
Run `tools/maze/build_maze.py --print-package` to validate the route and create
the legacy review files plus the common simulation/preview/prototype-STL
package. The prototype is not a final-fit insert until the mount is measured.
