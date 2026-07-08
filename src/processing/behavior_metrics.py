"""
Pure statistical and metric calculation functions for photometry behaviour analysis.

No UI framework dependencies — all inputs and outputs are plain Python types,
NumPy arrays, or pandas DataFrames. Safe to use from any UI layer (Tkinter,
PySide6, CLI, tests).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.integrate import simpson


# ---------------------------------------------------------------------------
# Per-event metrics
# ---------------------------------------------------------------------------

def calculate_auc(data: np.ndarray | list, dx: float = 0.1) -> float:
    """Area under curve using Simpson's rule.

    Parameters
    ----------
    data:
        Signal values (1-D array-like).
    dx:
        Sample spacing in seconds (default 0.1 s = 10 Hz).
    """
    arr = np.asarray(data, dtype=float).ravel()
    if arr.size == 0:
        return float("nan")
    return float(simpson(arr, dx=dx))


def calculate_max_amp(data: np.ndarray | list) -> float:
    """Maximum amplitude of a signal. Returns NaN when *data* is empty."""
    arr = np.asarray(data, dtype=float).ravel()
    if arr.size == 0:
        return float("nan")
    return float(np.nanmax(arr))


def calculate_mean_dff(data: np.ndarray | list) -> float:
    """Mean ΔF/F across all samples."""
    arr = np.asarray(data, dtype=float).ravel()
    if arr.size == 0:
        return float("nan")
    return float(np.nanmean(arr))


# ---------------------------------------------------------------------------
# Duration metrics
# ---------------------------------------------------------------------------

def calculate_duration_metrics(
    start_times: list[float],
    end_times: list[float],
) -> tuple[float, float]:
    """Mean and SEM of event durations (in minutes).

    Parameters
    ----------
    start_times:
        Event start times in seconds.
    end_times:
        Event end times in seconds. ``None`` values are skipped.

    Returns
    -------
    mean_duration, sem_duration
        Both in minutes. Returns ``(nan, nan)`` when no valid durations exist.
    """
    durations = []
    for start, end in zip(start_times, end_times):
        if start is None or end is None:
            continue
        try:
            start_value = float(start)
            end_value = float(end)
        except (TypeError, ValueError):
            continue
        if not np.isfinite(start_value) or not np.isfinite(end_value):
            continue
        durations.append((end_value - start_value) / 60.0)
    if not durations:
        return float("nan"), float("nan")

    arr = np.array(durations, dtype=float)
    n_valid = int(np.sum(~np.isnan(arr)))
    mean_dur = float(np.nanmean(arr))
    sem_dur = float(np.nanstd(arr) / np.sqrt(n_valid)) if n_valid > 1 else 0.0
    return mean_dur, sem_dur


# ---------------------------------------------------------------------------
# Mean / SEM across instances
# ---------------------------------------------------------------------------

def calculate_mean_sem(dataframe: pd.DataFrame, ignore_col: str) -> pd.DataFrame:
    """Row-wise mean and SEM across all columns except *ignore_col*.

    Parameters
    ----------
    dataframe:
        Wide-format DataFrame where each column (other than *ignore_col*)
        is one instance of a behaviour.
    ignore_col:
        Column to exclude (typically ``"Time"``).

    Returns
    -------
    pd.DataFrame
        Columns: ``Time``, ``Mean``, ``SEM``.
    """
    data = dataframe.drop(columns=[ignore_col])

    if data.shape[1] == 1:
        single = data.iloc[:, 0]
        return pd.DataFrame(
            {
                "Time": dataframe[ignore_col],
                "Mean": single.values,
                "SEM": np.zeros(len(single)),
            }
        )

    return pd.DataFrame(
        {
            "Time": dataframe[ignore_col],
            "Mean": data.mean(axis=1).values,
            "SEM": data.sem(axis=1).values,
        }
    )


def generate_mean_sem_df(
    behaviour_data_by_instance: dict,
    time_points: list | np.ndarray,
    start_time_adjusted: float,
    end_time_adjusted: float,
) -> pd.DataFrame:
    """Build a mean/SEM DataFrame from per-instance behaviour arrays.

    Parameters
    ----------
    behaviour_data_by_instance:
        Mapping of instance label → 1-D array of signal values.
    time_points:
        Time axis (only its length is used; axis is regenerated linearly).
    start_time_adjusted:
        First time value in the display unit (e.g. minutes).
    end_time_adjusted:
        Last time value in the display unit.

    Returns
    -------
    pd.DataFrame
        Columns: ``Time``, ``Mean``, ``SEM``.
    """
    df = pd.DataFrame(behaviour_data_by_instance)
    df.insert(
        0,
        "Time",
        np.linspace(start_time_adjusted, end_time_adjusted, len(time_points)),
    )
    return calculate_mean_sem(df, "Time")


# ---------------------------------------------------------------------------
# Binned metrics
# ---------------------------------------------------------------------------

def calculate_metrics_for_bins(
    instances_data: list[list],
    expected_num_bins: int,
    metric_name: str,
    metric_func: callable,
) -> list[float]:
    """Average a metric across all instances for each time bin.

    Parameters
    ----------
    instances_data:
        Outer list = instances; inner list = bins; each element is a
        1-D array of signal values for that bin.
    expected_num_bins:
        Number of bins expected per instance.
    metric_name:
        Used to detect AUC (``"auc"``) and unwrap scalar results.
    metric_func:
        Callable ``(array) -> float``.

    Returns
    -------
    list[float]
        One averaged metric value per bin.
    """
    metric_values_per_bin: list[float] = []

    for bin_idx in range(expected_num_bins):
        bin_data = [instance[bin_idx] for instance in instances_data]
        values = [metric_func(d) for d in bin_data]

        if metric_name == "auc" and values and isinstance(
            values[0], (list, np.ndarray)
        ):
            values = [v[0] for v in values]

        avg = sum(values) / len(values) if values else 0.0
        metric_values_per_bin.append(float(avg))

    return metric_values_per_bin


# ---------------------------------------------------------------------------
# Z-score
# ---------------------------------------------------------------------------

PRIMARY_ZSCORE_COLUMN = "baselined_z_score"


def zscore_column_key(column: str) -> str:
    """Dataframe key under which a column's baselined z-score series is stored.

    Each selected signal column gets its own z-scored series (computed over
    the same baseline window) so dual-column recordings can be baselined
    independently rather than only the primary column.
    """
    return f"{PRIMARY_ZSCORE_COLUMN}::{column}"


def compute_z_score(
    dataframe: pd.DataFrame,
    selected_column: str,
    baseline_start_min: float,
    baseline_end_min: float,
) -> tuple[pd.Series, pd.Series, float, float]:
    """Baseline-normalised z-score for a photometry trace.

    Time values are expected in **minutes** (first column of *dataframe*).

    Parameters
    ----------
    dataframe:
        Full recording DataFrame; first column is time in minutes.
    selected_column:
        Column name of the signal to z-score.
    baseline_start_min:
        Baseline window start in minutes.
    baseline_end_min:
        Baseline window end in minutes.

    Returns
    -------
    z_scored_data : pd.Series
    z_scored_time : pd.Series
        Re-zeroed to *baseline_start_min*.
    baseline_mean : float
    baseline_std : float
    """
    time_col = dataframe.iloc[:, 0]
    baseline_mask = (time_col >= baseline_start_min) & (time_col < baseline_end_min)
    post_mask = time_col >= baseline_start_min

    baseline_data = dataframe.loc[baseline_mask, selected_column].reset_index(drop=True)
    raw_data = dataframe.loc[post_mask, selected_column].reset_index(drop=True)

    baseline_mean = float(np.mean(baseline_data))
    baseline_std = float(np.std(baseline_data))

    z_scored_data = (raw_data - baseline_mean) / baseline_std
    z_scored_time = (
        dataframe.loc[post_mask].iloc[:, 0].reset_index(drop=True) - baseline_start_min
    )

    min_len = min(len(z_scored_data), len(z_scored_time))
    return (
        z_scored_data.iloc[:min_len],
        z_scored_time.iloc[:min_len],
        baseline_mean,
        baseline_std,
    )


# ---------------------------------------------------------------------------
# Time conversion
# ---------------------------------------------------------------------------

def convert_time(unit: str, time_in_seconds: float) -> float:
    """Convert a time value from seconds to *unit*.

    Parameters
    ----------
    unit:
        One of ``"hours"``, ``"minutes"``, ``"seconds"``.
    """
    if unit == "hours":
        return time_in_seconds / 3600.0
    if unit == "minutes":
        return time_in_seconds / 60.0
    return float(time_in_seconds)


def get_time_scale(time_unit: str) -> float:
    """Multiplier from minutes to *time_unit*.

    Used to scale pre-computed minute-based values to the display unit.
    """
    scales = {"hours": 1.0 / 60.0, "minutes": 1.0, "seconds": 60.0}
    return scales.get(time_unit, 1.0)
