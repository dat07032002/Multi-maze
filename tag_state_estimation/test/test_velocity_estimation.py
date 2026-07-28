import math

import numpy as np

from tag_state_estimation.core.velocity_estimation import (
    PositionVelocityEstimator,
)


def test_recovers_constant_velocity_from_timestamped_positions():
    estimator = PositionVelocityEstimator(
        window_seconds=0.25,
        min_samples=6,
        stationary_deadband_mps=0.0,
    )
    velocity = (math.nan, math.nan)
    for index in range(30):
        timestamp = index / 60.0
        velocity = estimator.update(
            (0.03 * timestamp + 0.1, -0.02 * timestamp - 0.05),
            timestamp,
        )
    np.testing.assert_allclose(velocity, (0.03, -0.02), atol=1.0e-10)


def test_stationary_noise_is_zeroed_by_deadband():
    estimator = PositionVelocityEstimator(stationary_deadband_mps=0.002)
    rng = np.random.default_rng(7)
    velocity = (math.nan, math.nan)
    for index in range(60):
        velocity = estimator.update(
            np.array((0.05, -0.03))
            + rng.normal(0.0, 2.0e-5, size=2),
            index / 60.0,
        )
    assert velocity == (0.0, 0.0)


def test_loss_resets_history_and_requires_reinitialization():
    estimator = PositionVelocityEstimator(min_samples=3)
    for index in range(3):
        estimator.update((index * 0.001, 0.0), index / 60.0)
    lost = estimator.update((math.nan, math.nan), 3 / 60.0)
    recovered = estimator.update((0.004, 0.0), 4 / 60.0)
    assert all(math.isnan(value) for value in lost)
    assert all(math.isnan(value) for value in recovered)
