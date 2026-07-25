# Camera diagnostics

These tools subscribe to the TAG camera stream or help tune its locked V4L2
settings. They are not part of the motor-control path.

- `camera_tuner_live.py`: tune exposure, white balance, and color controls
- `marble_hsv_picker.py`: inspect HSV values and classical detector gates
- `grayscale_marble_detector.py`: retained baseline detector for comparison
- `safe_image_viewer.py`: subscribe-only camera viewer
- `overlay_map_view_simple.py`: camera, route, and tracked-marble overlay

The learned runtime detector lives in `tag_state_estimation/`; these scripts are
diagnostic tools, not alternate production estimators.
