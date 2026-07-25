import numpy as np

from tag_state_estimation.core.hybrid_ball import HybridBallTracker


def _point(row, column):
    return np.array([row, column], dtype=np.float32)


def _initialize(tracker, point=None):
    point = _point(100, 200) if point is None else point
    results = [tracker.update(point, point) for _ in range(3)]
    assert results[-1].source == "fused_reacquired_confirmed"
    return results[-1]


def test_startup_requires_three_consistent_frames():
    tracker = HybridBallTracker(far_reacquire_confirm_frames=3)
    results = [tracker.update(_point(100, 200), _point(101, 201)) for _ in range(3)]
    assert [result.source for result in results] == [
        "lost",
        "lost",
        "fused_reacquired_confirmed",
    ]
    np.testing.assert_allclose(results[-1].measurement, _point(100.5, 200.5))


def test_hsv_only_candidate_cannot_reset_loss_timer():
    tracker = HybridBallTracker(occlusion_grace_frames=2)
    _initialize(tracker)
    results = [tracker.update(_point(100, 200), None) for _ in range(3)]
    assert [result.source for result in results] == [
        "kalman_occlusion",
        "kalman_occlusion",
        "lost",
    ]
    assert results[-1].missing_frames == 3


def test_ai_is_authoritative_when_detectors_disagree():
    tracker = HybridBallTracker()
    _initialize(tracker)
    result = tracker.update(_point(20, 20), _point(102, 201))
    assert result.source == "ai_disagreement"
    np.testing.assert_allclose(result.measurement, _point(102, 201))
    assert result.disagreement_px > 12.0


def test_any_reacquisition_after_a_missing_frame_requires_confirmation():
    tracker = HybridBallTracker(far_reacquire_confirm_frames=3)
    _initialize(tracker)
    assert tracker.update(None, None).source == "kalman_occlusion"
    results = [tracker.update(_point(101, 201), _point(101, 201)) for _ in range(3)]
    assert [result.source for result in results] == [
        "kalman_occlusion",
        "kalman_occlusion",
        "fused_reacquired_confirmed",
    ]


def test_reset_forgets_position_and_pending_reacquisition():
    tracker = HybridBallTracker()
    _initialize(tracker)
    tracker.reset()
    result = tracker.update(None, _point(100, 200))
    assert result.source == "lost"
    assert np.all(np.isnan(result.measurement))
    assert result.missing_frames == 1
