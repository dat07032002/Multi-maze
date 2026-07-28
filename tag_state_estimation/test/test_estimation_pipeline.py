import numpy as np

from tag_state_estimation.core.estimation_pipeline import EstimationPipeline


def test_invalid_plate_pose_holds_last_finite_estimator_input():
    pipeline = EstimationPipeline.__new__(EstimationPipeline)
    pipeline._last_finite_inputs = np.zeros(2, dtype=float)

    finite = pipeline._safe_estimator_inputs([0.1, -0.2])
    held = pipeline._safe_estimator_inputs([np.nan, np.nan])

    np.testing.assert_allclose(finite, [0.1, -0.2])
    np.testing.assert_allclose(held, finite)


def test_invalid_initial_plate_pose_uses_neutral_estimator_input():
    pipeline = EstimationPipeline.__new__(EstimationPipeline)
    pipeline._last_finite_inputs = np.zeros(2, dtype=float)

    held = pipeline._safe_estimator_inputs([np.nan, np.nan])

    np.testing.assert_allclose(held, [0.0, 0.0])
