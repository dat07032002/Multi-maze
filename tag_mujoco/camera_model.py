"""Board-rectified policy observation produced by the calibrated camera stack."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

try:
    from .system_config import CameraConfig, OcamCalibration
except ImportError:
    from system_config import CameraConfig, OcamCalibration


class PolicyCameraModel:
    """Render the 64 mm square, ball-centered patch used by the real policy.

    The real state estimator uses OCamCalib and marker poses to remap a physical
    square around the ball. Rendering directly in board coordinates reproduces
    that post-remap observation without approximating the fisheye image first.
    """

    def __init__(self, layout: Dict[str, Any], config: CameraConfig):
        self.layout = layout
        self.config = config
        self.calibration = OcamCalibration.load(config.calibration_path)
        self.width = float(layout["board_width"])
        self.height = float(layout["board_height"])
        self.ppm = int(config.raster_pixels_per_meter)
        self._background = self._draw_background()
        self._rng = np.random.default_rng(0)
        self._randomize = False
        self._brightness = 1.0
        self._contrast = 1.0
        self._blur = 0.0
        self._noise_std = 0.0
        self._crop_shift = np.zeros(2, dtype=np.float64)
        self._dropout_remaining = 0
        self._randomization_strength = 0.0

    def reset(
        self,
        seed: int | None = None,
        randomize: bool = False,
        randomization_strength: float = 1.0,
    ) -> None:
        self._rng = np.random.default_rng(seed)
        strength = float(np.clip(randomization_strength, 0.0, 1.0))
        self._randomize = bool(randomize and strength > 0.0)
        self._randomization_strength = strength if randomize else 0.0
        if randomize:
            def around_one(bounds: Tuple[float, float]) -> float:
                sampled = float(self._rng.uniform(*bounds))
                return 1.0 + strength * (sampled - 1.0)

            self._brightness = around_one(self.config.brightness_range)
            self._contrast = around_one(self.config.contrast_range)
            self._blur = strength * float(
                self._rng.uniform(*self.config.blur_radius_range)
            )
            self._noise_std = strength * float(
                self._rng.uniform(*self.config.pixel_noise_std_range)
            )
            limit = self.config.crop_shift_range_m
            self._crop_shift = strength * self._rng.uniform(-limit, limit, size=2)
        else:
            self._brightness = 1.0
            self._contrast = 1.0
            self._blur = 0.0
            self._noise_std = 0.0
            self._crop_shift[:] = 0.0
        self._dropout_remaining = 0

    def _point(self, xy: Iterable[float]) -> Tuple[float, float]:
        x, y = xy
        return float(x) * self.ppm, (self.height - float(y)) * self.ppm

    def _draw_background(self) -> Image.Image:
        size = (
            max(1, round(self.width * self.ppm)),
            max(1, round(self.height * self.ppm)),
        )
        image = Image.new("L", size, 205)
        draw = ImageDraw.Draw(image)
        wall_thickness = float(self.layout.get("wall_thickness", 0.0022))
        wall_pixels = max(2, round(wall_thickness * self.ppm))
        for x0, x1, y in self.layout["walls_h"]:
            draw.line(
                [self._point((x0, y)), self._point((x1, y))],
                fill=92,
                width=wall_pixels,
            )
        for y0, y1, x in self.layout["walls_v"]:
            draw.line(
                [self._point((x, y0)), self._point((x, y1))],
                fill=92,
                width=wall_pixels,
            )
        for x0, y0, x1, y1 in self.layout["walls_angled"]:
            draw.line(
                [self._point((x0, y0)), self._point((x1, y1))],
                fill=92,
                width=wall_pixels,
            )
        for (x, y), radius in zip(
            self.layout["holes"], self.layout["hole_radii"]
        ):
            cx, cy = self._point((x, y))
            r = float(radius) * self.ppm
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=12)
        rim = max(3, round(0.003 * self.ppm))
        draw.rectangle((0, 0, size[0] - 1, size[1] - 1), outline=55, width=rim)
        return image

    def capture(
        self,
        ball_xy: Iterable[float],
        ball_radius: float,
        ball_visible: bool = True,
    ) -> Tuple[np.ndarray, bool]:
        ball_xy = np.asarray(tuple(ball_xy), dtype=np.float64)
        detected = bool(ball_visible)
        if self._randomize and detected:
            if self._dropout_remaining > 0:
                self._dropout_remaining -= 1
                detected = False
            elif self._rng.random() < (
                self._randomization_strength
                * self.config.dropout_burst_start_probability
            ):
                low, high = self.config.dropout_burst_frames
                burst = int(self._rng.integers(max(1, low), max(1, high) + 1))
                self._dropout_remaining = max(0, burst - 1)
                detected = False
            elif self._rng.random() < (
                self._randomization_strength * self.config.dropout_probability
            ):
                detected = False
        if not detected:
            return (
                np.zeros(
                    (self.config.output_pixels, self.config.output_pixels, 1),
                    dtype=np.uint8,
                ),
                False,
            )

        source_size = max(4, round(self.config.patch_extent_m * self.ppm))
        half = source_size / 2.0
        crop_center = ball_xy + self._crop_shift
        center_x, center_y = self._point(crop_center)
        patch = self._background.crop(
            (
                round(center_x - half),
                round(center_y - half),
                round(center_x + half),
                round(center_y + half),
            )
        )

        # The crop follows the estimated ball. A small crop calibration error
        # makes the rendered ball move away from the exact image center.
        draw = ImageDraw.Draw(patch)
        ball_x = half - self._crop_shift[0] * self.ppm
        ball_y = half + self._crop_shift[1] * self.ppm
        radius_px = float(ball_radius) * self.ppm
        shadow = 0.18 * radius_px
        draw.ellipse(
            (
                ball_x - radius_px + shadow,
                ball_y - radius_px + shadow,
                ball_x + radius_px + shadow,
                ball_y + radius_px + shadow,
            ),
            fill=45,
        )
        draw.ellipse(
            (
                ball_x - radius_px,
                ball_y - radius_px,
                ball_x + radius_px,
                ball_y + radius_px,
            ),
            fill=72,
        )
        highlight = 0.35 * radius_px
        draw.ellipse(
            (
                ball_x - 0.45 * radius_px - highlight,
                ball_y - 0.45 * radius_px - highlight,
                ball_x - 0.45 * radius_px + highlight,
                ball_y - 0.45 * radius_px + highlight,
            ),
            fill=150,
        )
        patch = patch.resize(
            (self.config.output_pixels, self.config.output_pixels),
            Image.Resampling.LANCZOS,
        )
        if self._contrast != 1.0:
            patch = ImageEnhance.Contrast(patch).enhance(self._contrast)
        if self._brightness != 1.0:
            patch = ImageEnhance.Brightness(patch).enhance(self._brightness)
        if self._blur > 1e-6:
            patch = patch.filter(ImageFilter.GaussianBlur(self._blur))
        pixels = np.asarray(patch, dtype=np.float32)
        if self._noise_std > 0.0:
            pixels += self._rng.normal(0.0, self._noise_std, size=pixels.shape)
        pixels = np.clip(pixels, 0, 255).astype(np.uint8)
        return pixels[..., None], True

    def metadata(self) -> Dict[str, Any]:
        return {
            **self.calibration.summary(),
            "capture_resolution": [
                self.config.capture_width,
                self.config.capture_height,
            ],
            "effective_capture_rate_hz": self.config.effective_capture_rate_hz,
            "detector_miss_threshold": self.config.detector_miss_threshold,
            "ball_loss_grace_seconds": self.config.ball_loss_grace_seconds,
            "published_resolution": [
                self.config.resized_width,
                self.config.resized_height
                + 2 * self.config.vertical_border_pixels,
            ],
            "policy_patch_extent_m": self.config.patch_extent_m,
            "policy_patch_shape": [
                self.config.output_pixels,
                self.config.output_pixels,
                1,
            ],
            "grayscale_method": "mean_of_available_channels",
            "model_level": "post_calibration_board_rectified",
            "sampled_brightness": self._brightness,
            "sampled_contrast": self._contrast,
            "sampled_blur_radius": self._blur,
            "sampled_pixel_noise_std": self._noise_std,
            "sampled_crop_shift_m": self._crop_shift.tolist(),
            "effective_dropout_probability": (
                self._randomization_strength * self.config.dropout_probability
            ),
            "effective_dropout_burst_start_probability": (
                self._randomization_strength
                * self.config.dropout_burst_start_probability
            ),
        }
