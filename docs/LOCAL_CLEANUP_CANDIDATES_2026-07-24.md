# Local cleanup record

The approved cache cleanup and recording reorganization were completed locally
on 2026-07-24. No ZIP archive, source file, trained model, or result was deleted.

## Removed regenerable caches

- `cyberrunner_dreamer/`: three Python bytecode files, 14,931 bytes
- `cyberrunner_dynamixel/`: two Python bytecode files, 17,437 bytes
- generated `__pycache__/` directories created by local verification

These directories contained no source code. Their working source remains under
`tag_dreamer/` and `tag_hiwonder/`.

## Retained hardware recordings

| Path | Size | SHA-256 or contents |
| --- | ---: | --- |
| `hardware_recordings/archive/tag_hardware_recorder_20260724T184830Z/` | 241,539 bytes | 42 extracted files, moved intact |
| `cyberrunner_hardware_recorder-20260724T184830Z-1-001.zip` | 83,326 bytes | `AFD918119EC26AD05AA7F70109AE3E788872E082349D2870326AC97945357B3A` |
| `cyberrunner_hardware_recorder-20260724T191749Z-1-001.zip` | 83,326 bytes | `AB232D297FD45FDDF21401BBDE5866589EF6D3AD4027A4CD0822B5D1B4F43C94` |
| `hardware_recordings-20260724T192033Z-1-001.zip` | 7,324,337 bytes | `241905EE2D17DF8D2C66B7539C6BC6752A0CDE79EC60ADE29ECABF18ED2BAC65` |

The two 83 KB archives have different hashes and must not be treated as
duplicates without comparing their sessions. The extracted recording was moved
under the canonical `hardware_recordings/archive/` hierarchy for future system
identification work.

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

## Future cleanup boundary

Compare recording contents and request approval for exact redundant files before
deleting any recording or ZIP archive.
