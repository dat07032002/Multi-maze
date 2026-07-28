import cv2 as cv
import numpy as np

from tag_state_estimation.core.gaussian_robust import detect_gaussian


def test_corner_detection_prefers_prediction_over_larger_distractor():
    mask = np.zeros((51, 51), dtype=np.uint8)
    cv.circle(mask, (25, 25), 3, 255, -1)
    cv.circle(mask, (43, 6), 5, 255, -1)

    center, found = detect_gaussian(mask, 0, 5, 0.002, False)

    assert found
    assert np.allclose(center, [25.0, 25.0], atol=0.5)
