"""Timestamp-aware marble velocity estimation from observed positions."""

from __future__ import annotations

from collections import deque
import math

import numpy as np


class PositionVelocityEstimator:
    """Estimate velocity with a sliding local-linear position fit."""

    def __init__(
        self,
        window_seconds: float = 0.25,
        min_samples: int = 6,
        stationary_deadband_mps: float = 0.002,
    ) -> None:
        if not 0.05 <= window_seconds <= 1.0:
            raise ValueError("window_seconds must be in [0.05, 1.0]")
        if not 3 <= min_samples <= 60:
            raise ValueError("min_samples must be in [3, 60]")
        if not 0.0 <= stationary_deadband_mps <= 0.02:
            raise ValueError("stationary_deadband_mps must be in [0, 0.02]")
        self.window_seconds = float(window_seconds)
        self.min_samples = int(min_samples)
        self.stationary_deadband_mps = float(stationary_deadband_mps)
        self.samples: deque[tuple[float, float, float]] = deque()

    def reset(self) -> None:
        """Forget position history after loss or a timestamp discontinuity."""
        self.samples.clear()

    def update(self, position, timestamp_seconds: float) -> tuple[float, float]:
        """Return x/y velocity in m/s, or NaN until a valid fit is ready."""
        timestamp = float(timestamp_seconds)
        point = (float(position[0]), float(position[1]))
        if not math.isfinite(timestamp) or not all(map(math.isfinite, point)):
            self.reset()
            return math.nan, math.nan
        if self.samples and timestamp <= self.samples[-1][0]:
            self.reset()
        self.samples.append((timestamp, point[0], point[1]))
        cutoff = timestamp - self.window_seconds
        while self.samples and self.samples[0][0] < cutoff:
            self.samples.popleft()
        if len(self.samples) < self.min_samples:
            return math.nan, math.nan

        data = np.asarray(self.samples, dtype=float)
        relative_time = data[:, 0] - data[-1, 0]
        design = np.column_stack((relative_time, np.ones(len(data))))
        velocities = np.linalg.lstsq(design, data[:, 1:], rcond=None)[0][0]
        velocities[np.abs(velocities) < self.stationary_deadband_mps] = 0.0
        return float(velocities[0]), float(velocities[1])
