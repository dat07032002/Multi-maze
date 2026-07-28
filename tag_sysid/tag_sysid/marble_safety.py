"""Pure temporal safety filters for guarded marble system identification."""

from __future__ import annotations

from collections import deque
import math
import statistics


class ConfirmedDisplacementGuard:
    """Confirm displacement using a rolling median over consecutive frames."""

    def __init__(self, threshold_m: float, window_size: int, confirm_frames: int):
        if threshold_m <= 0.0:
            raise ValueError("threshold_m must be positive")
        if window_size < 3 or window_size % 2 == 0:
            raise ValueError("window_size must be an odd integer of at least 3")
        if confirm_frames < 1:
            raise ValueError("confirm_frames must be positive")
        self.threshold_m = float(threshold_m)
        self.window_size = int(window_size)
        self.confirm_frames = int(confirm_frames)
        self.positions = deque(maxlen=self.window_size)
        self.start = None
        self.consecutive = 0
        self.filtered_distance_m = 0.0

    def reset(self, start_x_m: float, start_y_m: float) -> None:
        self.start = (float(start_x_m), float(start_y_m))
        self.positions.clear()
        self.positions.append(self.start)
        self.consecutive = 0
        self.filtered_distance_m = 0.0

    def update(self, x_m: float, y_m: float) -> bool:
        if self.start is None:
            return False
        self.positions.append((float(x_m), float(y_m)))
        if len(self.positions) < self.window_size:
            return False
        median_x = statistics.median(position[0] for position in self.positions)
        median_y = statistics.median(position[1] for position in self.positions)
        self.filtered_distance_m = math.hypot(
            median_x - self.start[0], median_y - self.start[1]
        )
        if self.filtered_distance_m > self.threshold_m:
            self.consecutive += 1
        else:
            self.consecutive = 0
        return self.consecutive >= self.confirm_frames
