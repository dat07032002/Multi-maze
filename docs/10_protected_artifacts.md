# Protected artifacts

These files encode the previously trained or calibrated CyberRunner behavior.
They must not be deleted, regenerated in place, or silently replaced during
organization.

| SHA-256 | Bytes | Path |
| --- | ---: | --- |
| `1e512b50270de227dc6d322d85bdc41f63c80c8d66c8ef6b2e709a497dc34aa9` | 12,929,471 | `cyberrunner_dreamer/data/path_0002_hard.pkl` |
| `a250b1dc8607d59f04b06fe713b55504c7556f08c0c1ad779b86cd353583245a` | 6,035,890 | `cyberrunner_dreamer/data/path_custom.pkl` |
| `dbb7c44b6efea2fca762ae467d703d49c3880db49a1e8981a1f1eb7ab244ab4d` | 15,766 | `cyberrunner_dreamer/cyberrunner_dreamer/cyberrunner_layout_custom.py` |
| `d5026c97f246486bf27503d8706ce79a8f4d6854d11a93f4c00e05f08271347b` | 692 | `cyberrunner_state_estimation/calib/calib_results_cyberrunner.txt` |
| `ae9847e5e575396100cc768a8539bcb5132069811bdba904c09fae1266481e3d` | 408 | `cyberrunner_state_estimation/markers.csv` |
| `5a7f74e2bbd1eab8e5597135482442be3520b2923ceb1cfcd826f5195cc04e80` | 243,665 | `latest` |

Also protected until a clean rebuild is validated:

- tracked `build/`, `install/`, and `log/` snapshots
- `run_logs/` and `cache/`
- `cyberrunner_dreamer_thomas/` and `cyberrunner_dynamixel_thomas/`
- all calibration, marker, CAD, replay-conversion, bridge, and training scripts

The exact repository state before organization is available from local Git tag
`pre-organization-20260723`.
