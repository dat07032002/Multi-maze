# Local cleanup candidates

This is an approval manifest only. Nothing listed here was deleted during the
local TAG/AI update.

## Safe cache candidates

- `cyberrunner_dreamer/`: three Python bytecode files, 14,931 bytes
- `cyberrunner_dynamixel/`: two Python bytecode files, 17,437 bytes
- generated `__pycache__/` directories created by local verification

The first two directories contain no source code. Their working source has
already been retained under `tag_dreamer/` and `tag_hiwonder/`.

## Hardware recordings requiring a retention decision

| Path | Size | SHA-256 or contents |
| --- | ---: | --- |
| `cyberrunner_hardware_recorder-20260724T184830Z-1-001/` | 241,539 bytes | 42 extracted files |
| `cyberrunner_hardware_recorder-20260724T184830Z-1-001.zip` | 83,326 bytes | `AFD918119EC26AD05AA7F70109AE3E788872E082349D2870326AC97945357B3A` |
| `cyberrunner_hardware_recorder-20260724T191749Z-1-001.zip` | 83,326 bytes | `AB232D297FD45FDDF21401BBDE5866589EF6D3AD4027A4CD0822B5D1B4F43C94` |
| `hardware_recordings-20260724T192033Z-1-001.zip` | 7,324,337 bytes | `241905EE2D17DF8D2C66B7539C6BC6752A0CDE79EC60ADE29ECABF18ED2BAC65` |

The two 83 KB archives have different hashes and must not be treated as
duplicates without comparing their sessions. Raw recordings remain useful for
system identification, so they should be moved to a canonical external archive
or retained until their derived results are reproducible.

## Explicitly protected

- `tag_mujoco/.venv/`: the local working simulation environment
- `tag_mujoco/outputs/`: review before removing generated demonstrations
- all manifest-referenced 40/8/8 and 512/64/64 maze files
- route pickle files, calibration, markers, ONNX model, and system-ID results
- server checkpoints, replay chunks, metrics, and historic server log paths
- `dreamerv3/dreamerv3/embodied/scripts/`: review as upstream source, even if
  an ignore rule currently hides it

Do not run `git clean -fdX` for this repository: the ignored set includes the
working virtual environment and locally valuable artifacts.

## Approval options

1. Remove only the bytecode-only legacy directories and generated caches.
2. Keep every recording but move them into one external archive with a checksum
   index.
3. Compare recording contents first, then request approval for exact redundant
   files only.
