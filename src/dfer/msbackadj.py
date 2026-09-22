"""A bounded Python implementation of the ``msbackadj`` baseline estimator.

The DFer option uses the documented quantile-window model with a pchip fit,
10% quantile, and equal window/step sizes.  MATLAB is not available in the
application test environment, so this module is intentionally described as a
compatible estimator rather than an exact MATLAB implementation.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.interpolate import CubicSpline, PchipInterpolator

MSBACKADJ_WINDOW_FRACTION = 0.10
MSBACKADJ_QUANTILE = 0.10
MSBACKADJ_REGRESSION = "pchip"


@dataclass(frozen=True)
class MsBackAdjResult:
    """Baseline and corrected trace returned by :func:`msbackadj`."""

    corrected: np.ndarray
    baseline: np.ndarray
    centers: np.ndarray
    estimates: np.ndarray
    counts: np.ndarray


def _as_finite_vector(name: str, values: object) -> np.ndarray:
    array = np.asarray(values, dtype=float).reshape(-1)
    if array.size == 0:
        raise ValueError(f"{name} must not be empty")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must not contain NaN or Inf")
    return array


def _validate_time(values: object) -> np.ndarray:
    time_values = _as_finite_vector("X", values)
    if time_values.size < 2:
        raise ValueError("X must contain at least two points")
    if not np.all(np.diff(time_values) > 0):
        raise ValueError("X must be strictly increasing")
    return time_values


def msbackadj_window_size(
    time_values: object,
    fraction: float = MSBACKADJ_WINDOW_FRACTION,
) -> float:
    """Return a recording-relative window in the same units as ``time_values``."""
    time_array = _validate_time(time_values)
    fraction_value = float(fraction)
    if not np.isfinite(fraction_value) or fraction_value <= 0:
        raise ValueError("window fraction must be a positive finite number")
    duration = float(time_array[-1] - time_array[0])
    if duration <= 0:
        raise ValueError("X must span a positive duration")
    return duration * fraction_value


def _window_centers(time_values: np.ndarray, step_size: float) -> np.ndarray:
    first = float(time_values[0])
    last = float(time_values[-1])
    span = last - first
    count = int(np.floor(span / step_size))
    centers = first + step_size * np.arange(count + 1, dtype=float)
    if centers[-1] < last - 1e-9 * max(1.0, abs(last)):
        centers = np.append(centers, last)
    return centers


def _regress(
    centers: np.ndarray,
    estimates: np.ndarray,
    time_values: np.ndarray,
    method: str,
) -> np.ndarray:
    if centers.size == 1:
        return np.full(time_values.shape, float(estimates[0]))
    if method == "pchip":
        return np.asarray(
            PchipInterpolator(centers, estimates)(time_values), dtype=float
        )
    if method == "linear":
        return np.asarray(np.interp(time_values, centers, estimates), dtype=float)
    if method == "spline":
        return np.asarray(
            CubicSpline(centers, estimates, bc_type="not-a-knot")(time_values),
            dtype=float,
        )
    raise ValueError(f"Unsupported RegressionMethod: {method!r}")


def msbackadj(
    time_values: object,
    intensities: object,
    window_size: float,
    step_size: float | None = None,
    *,
    regression_method: str = MSBACKADJ_REGRESSION,
    quantile_value: float = MSBACKADJ_QUANTILE,
) -> MsBackAdjResult:
    """Estimate and subtract a slowly varying quantile baseline.

    This implements the subset used by DFer option 5: quantile windows,
    pchip/linear/spline interpolation, and no peak-height preservation.
    """
    x = _validate_time(time_values)
    y = _as_finite_vector("Intensities", intensities)
    if y.size != x.size:
        raise ValueError("X and Intensities must have the same number of elements")

    window = float(window_size)
    step = window if step_size is None else float(step_size)
    quantile = float(quantile_value)
    if not np.isfinite(window) or window <= 0:
        raise ValueError("WindowSize must be a positive finite number")
    if not np.isfinite(step) or step <= 0:
        raise ValueError("StepSize must be a positive finite number")
    if not 0.0 < quantile < 1.0:
        raise ValueError("QuantileValue must be between 0 and 1")

    centers = _window_centers(x, step)
    estimates = np.empty(centers.size, dtype=float)
    counts = np.empty(centers.size, dtype=int)
    half_width = window / 2.0
    for index, center in enumerate(centers):
        mask = (x >= center - half_width) & (x <= center + half_width)
        counts[index] = int(np.count_nonzero(mask))
        estimates[index] = (
            float(np.quantile(y[mask], quantile, method="linear"))
            if counts[index]
            else np.nan
        )

    valid = np.isfinite(estimates)
    if not np.any(valid):
        raise ValueError("No window contained any sample")
    valid_centers = centers[valid]
    valid_estimates = estimates[valid]
    valid_counts = counts[valid]
    if valid_centers.size >= 2:
        keep = np.concatenate(([True], np.diff(valid_centers) > 0))
        valid_centers = valid_centers[keep]
        valid_estimates = valid_estimates[keep]
        valid_counts = valid_counts[keep]

    baseline = _regress(valid_centers, valid_estimates, x, regression_method)
    return MsBackAdjResult(
        corrected=y - baseline,
        baseline=baseline,
        centers=valid_centers,
        estimates=valid_estimates,
        counts=valid_counts,
    )
