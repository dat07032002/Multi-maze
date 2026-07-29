"""Validation helpers for keeping non-finite values out of training."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np


class NonFiniteDataError(ValueError):
    """Raised when a numeric training value contains NaN or infinity."""


def nonfinite_fields(values: Mapping[str, object]) -> dict[str, dict[str, object]]:
    """Return counts and first indices for non-finite numeric mapping values."""

    failures: dict[str, dict[str, object]] = {}
    for key, value in values.items():
        array = np.asarray(value)
        if not (
            np.issubdtype(array.dtype, np.floating)
            or np.issubdtype(array.dtype, np.complexfloating)
        ):
            continue
        mask = ~np.isfinite(array)
        if not np.any(mask):
            continue
        first = tuple(int(index) for index in np.argwhere(mask)[0])
        failures[str(key)] = {
            "count": int(mask.sum()),
            "first_index": first,
            "shape": tuple(int(size) for size in array.shape),
            "dtype": str(array.dtype),
        }
    return failures


def assert_finite(values: Mapping[str, object], context: str) -> None:
    """Fail with field-level diagnostics if numeric values are not finite."""

    failures = nonfinite_fields(values)
    if failures:
        details = ", ".join(
            f"{key}: count={info['count']} first_index={info['first_index']}"
            for key, info in sorted(failures.items())
        )
        raise NonFiniteDataError(f"{context} contains non-finite values ({details})")
