import hashlib
from pathlib import Path

import cv2
import numpy as np

from tag_state_estimation.ai_marble_common import decode_heatmap, sigmoid


def test_sigmoid_is_stable_for_large_values():
    values = sigmoid(np.array([-1000.0, 0.0, 1000.0], dtype=np.float32))
    assert values[0] == 0.0
    assert values[1] == 0.5
    assert values[2] == 1.0


def test_decode_heatmap_maps_cell_center_to_source_pixels():
    logits = np.full((1, 1, 25, 40), -10.0, dtype=np.float32)
    logits[0, 0, 9, 14] = 10.0
    detection = decode_heatmap(logits, image_width=640, image_height=400)
    assert detection.visible
    assert abs(detection.x_px - 224.0) < 0.01
    assert abs(detection.y_px - 144.0) < 0.01
    assert detection.confidence > 0.99


def test_decode_heatmap_can_report_not_visible():
    logits = np.full((1, 1, 25, 40), -10.0, dtype=np.float32)
    detection = decode_heatmap(logits, 640, 400, threshold=0.55)
    assert not detection.visible


def test_decode_heatmap_rejects_stronger_peak_outside_roi():
    logits = np.full((1, 1, 50, 80), -10.0, dtype=np.float32)
    logits[0, 0, 47, 40] = 12.0
    logits[0, 0, 20, 30] = 10.0
    detection = decode_heatmap(
        logits,
        image_width=640,
        image_height=400,
        threshold=0.90,
        valid_roi=(0.25, 0.15, 0.72, 0.80),
    )
    assert detection.visible
    assert abs(detection.x_px - 240.0) < 0.01
    assert abs(detection.y_px - 160.0) < 0.01


def test_deployed_model_has_expected_hash_and_output_shape():
    model_path = Path(__file__).parents[1] / "models" / "marble_detector.onnx"
    digest = hashlib.sha256(model_path.read_bytes()).hexdigest()
    assert digest == "0a09032fb6a62c680dcc16f1411973aebe7e1d77771e094cfbd828adbdeb154b"

    network = cv2.dnn.readNetFromONNX(str(model_path))
    network.setInput(np.zeros((1, 3, 200, 320), dtype=np.float32))
    assert network.forward().shape == (1, 1, 50, 80)
