import numpy as np

from tag_sysid.fit_dynamics import detect_impacts, fit_free_roll


def test_free_roll_fit_recovers_synthetic_damping_and_resistance():
    dt = 1.0 / 60.0
    times = np.arange(0.0, 12.0, dt)
    angles = np.column_stack(
        (0.025 + 0.01 * np.sin(0.7 * times), -0.018 + 0.012 * np.cos(times))
    )
    tilt_map = np.asarray([[0.4, 6.2], [-6.0, 0.3]])
    damping = 0.7
    resistance = 0.035
    velocity = np.zeros((len(times), 2))
    velocity[0] = (0.03, -0.02)
    position = np.zeros_like(velocity)
    for index in range(1, len(times)):
        prior = velocity[index - 1]
        speed = max(np.linalg.norm(prior), 1.0e-9)
        acceleration = (
            tilt_map @ angles[index - 1]
            - damping * prior
            - resistance * prior / speed
        )
        velocity[index] = prior + acceleration * dt
        position[index] = position[index - 1] + velocity[index] * dt

    result, _ = fit_free_roll(times, position, angles)
    assert result["samples"] > 200
    assert result["r2"] > 0.7
    assert abs(result["linear_damping_per_second"] - damping) < 0.25
    assert abs(result["rolling_resistance_mps2"] - resistance) < 0.02


def test_impact_detector_estimates_normal_velocity_ratio():
    times = np.arange(9, dtype=float) / 60.0
    positions = np.zeros((9, 2))
    velocity = np.tile((0.10, 0.01), (9, 1)).astype(float)
    velocity[5:] = (-0.06, 0.01)
    result = detect_impacts(times, positions, velocity)
    assert result["count"] >= 1
    assert abs(result["median"] - 0.6) < 0.05
