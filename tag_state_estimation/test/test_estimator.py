import numpy as np

from tag_state_estimation.core.estimator import KF, KFBias


def test_kf_ignores_nonfinite_position_measurement():
    estimator = KF(fps=60)

    state, covariance = estimator.estimate(
        inputs=np.zeros(2), measurement=np.array([np.inf, -np.inf])
    )

    assert np.all(np.isfinite(state))
    assert np.all(np.isfinite(covariance))


def test_kf_bias_ignores_nonfinite_position_measurement():
    estimator = KFBias(fps=60)

    state, covariance = estimator.estimate(
        inputs=np.zeros(2), measurement=np.array([np.inf, -np.inf])
    )

    assert np.all(np.isfinite(state))
    assert np.all(np.isfinite(covariance))


def test_kf_restores_last_finite_state_after_internal_corruption():
    estimator = KF(fps=60)
    expected_state, expected_covariance = estimator.estimate(
        inputs=np.zeros(2), measurement=np.array([0.04, -0.01])
    )
    expected_state = expected_state.copy()
    expected_covariance = expected_covariance.copy()
    estimator.xm[:] = np.nan
    estimator.Pm[:] = np.nan

    state, covariance = estimator.estimate(
        inputs=np.zeros(2), measurement=np.array([np.nan, np.nan])
    )

    np.testing.assert_allclose(state[:2], expected_state[:2], atol=1.0e-3)
    assert np.all(np.isfinite(state))
    assert np.all(np.isfinite(covariance))
    assert np.all(np.diag(covariance) >= np.diag(expected_covariance))
