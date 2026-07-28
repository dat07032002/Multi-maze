"""Pure state-selection logic for guarded HSV and AI marble tracking."""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class HybridBallResult:
    """Selected measurement and diagnostic state for one camera frame."""

    measurement: np.ndarray
    source: str
    disagreement_px: float
    missing_frames: int


def _valid(position):
    return position is not None and np.all(np.isfinite(position))


class HybridBallTracker:
    """Fuse detections, gate reacquisition, and identify prediction-only gaps."""

    def __init__(
        self,
        agreement_radius_px=12.0,
        max_reacquire_jump_px=25.0,
        occlusion_grace_frames=90,
        far_reacquire_confirm_frames=3,
        ai_fusion_weight=0.5,
    ):
        self.agreement_radius_px = float(agreement_radius_px)
        self.max_reacquire_jump_px = float(max_reacquire_jump_px)
        self.occlusion_grace_frames = int(occlusion_grace_frames)
        self.far_reacquire_confirm_frames = int(far_reacquire_confirm_frames)
        self.ai_fusion_weight = float(ai_fusion_weight)
        self.last_position = None
        self.missing_frames = 0
        self.pending_ai_position = None
        self.pending_ai_frames = 0
        self.cross_validated_track = False

    @staticmethod
    def _distance(first, second):
        return float(np.linalg.norm(np.asarray(first) - np.asarray(second)))

    def reset(self):
        self.last_position = None
        self.missing_frames = 0
        self.pending_ai_position = None
        self.pending_ai_frames = 0
        self.cross_validated_track = False

    def _clear_pending(self):
        self.pending_ai_position = None
        self.pending_ai_frames = 0

    def _accept(self, position, source, disagreement=np.nan):
        self.last_position = np.asarray(position, dtype=np.float32).copy()
        self.missing_frames = 0
        self.pending_ai_position = None
        self.pending_ai_frames = 0
        if source.startswith("fused"):
            self.cross_validated_track = True
        return HybridBallResult(
            self.last_position.copy(), source, float(disagreement), 0
        )

    def _missing(self):
        self.missing_frames += 1
        measurement = np.array([np.nan, np.nan], dtype=np.float32)
        if (
            self.last_position is not None
            and self.missing_frames <= self.occlusion_grace_frames
        ):
            source = "kalman_occlusion"
        else:
            source = "lost"
        return HybridBallResult(
            measurement, source, np.nan, self.missing_frames
        )

    def _confirm_reacquisition(self, position, source):
        if (
            self.pending_ai_position is not None
            and self._distance(position, self.pending_ai_position)
            <= self.agreement_radius_px
        ):
            self.pending_ai_frames += 1
            self.pending_ai_position = 0.5 * (
                self.pending_ai_position + position
            )
        else:
            self.pending_ai_position = position.copy()
            self.pending_ai_frames = 1
        if self.pending_ai_frames >= self.far_reacquire_confirm_frames:
            return self._accept(self.pending_ai_position, source)
        return None

    def update(self, hsv_position=None, ai_position=None):
        hsv_valid = _valid(hsv_position)
        ai_valid = _valid(ai_position)
        disagreement = np.nan

        if hsv_valid and ai_valid:
            hsv_position = np.asarray(hsv_position, dtype=np.float32)
            ai_position = np.asarray(ai_position, dtype=np.float32)
            disagreement = self._distance(hsv_position, ai_position)
            if disagreement <= self.agreement_radius_px:
                ai_weight = self.ai_fusion_weight
                fused = (1.0 - ai_weight) * hsv_position + ai_weight * ai_position
                if self.last_position is None or self.missing_frames > 0:
                    confirmed = self._confirm_reacquisition(
                        fused, "fused_reacquired_confirmed"
                    )
                    return confirmed if confirmed is not None else self._missing()
                return self._accept(fused, "fused", disagreement)

            # Static blue maze features can fool either detector. Disagreement
            # must never establish a track or move one to a distant candidate.
            # AI may only bridge a disagreement close to an actively tracked
            # position; reacquisition requires both detectors to agree.
            if self.last_position is not None and self.missing_frames == 0:
                ai_jump = self._distance(ai_position, self.last_position)
                if ai_jump <= self.max_reacquire_jump_px:
                    return self._accept(ai_position, "ai_disagreement", disagreement)
            self._clear_pending()
            return self._missing()

        if hsv_valid:
            # Blue board markers can satisfy the HSV filter. Never let an
            # HSV-only candidate become a measurement or reset the loss timer.
            return self._missing()

        if ai_valid:
            ai_position = np.asarray(ai_position, dtype=np.float32)
            # The heatmap detector always has a strongest cell, including on
            # an empty board.  AI-only detections therefore must not create or
            # reacquire a track.  They may bridge a short HSV miss only after
            # a track has already been cross-validated by both detectors.
            if self.last_position is None:
                self._clear_pending()
                return self._missing()
            jump = self._distance(ai_position, self.last_position)
            if self.cross_validated_track and jump <= self.max_reacquire_jump_px:
                return self._accept(ai_position, "ai_reacquired")
            self._clear_pending()

        return self._missing()
