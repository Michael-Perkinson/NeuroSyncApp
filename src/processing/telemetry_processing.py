"""
Pure data-processing helpers for telemetry/photometry/opto alignment.

No UI framework dependencies — all inputs and outputs are plain Python
types, NumPy arrays, or pandas DataFrames.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from src.processing import telemetry_recording_io as _recording_io

AmbiguousTelemetryAlignmentError = _recording_io.AmbiguousTelemetryAlignmentError
parse_recording_date = _recording_io.parse_recording_date
_parse_clock_time = _recording_io._parse_clock_time
calculate_nighttime_periods = _recording_io.calculate_nighttime_periods
find_offset_for_previous_time = _recording_io.find_offset_for_previous_time
_find_alignment_anchor = _recording_io._find_alignment_anchor
_candidate_target_datetimes = _recording_io._candidate_target_datetimes
_build_alignment_candidates = _recording_io._build_alignment_candidates
_alignment_timestamp = _recording_io._alignment_timestamp
_select_alignment_candidate = _recording_io._select_alignment_candidate
_rows_matching_alignment_time = _recording_io._rows_matching_alignment_time
_resolve_sheet_name = _recording_io._resolve_sheet_name
_extract_sheet_table = _recording_io._extract_sheet_table
extract_and_trim_data = _recording_io.extract_and_trim_data
extract_data_with_buffer = _recording_io.extract_data_with_buffer
upsample_telemetry_data = _recording_io.upsample_telemetry_data


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _float_range(start: float, stop: float, step: float):
    """Yield floating-point values from *start* up to (not including) *stop*."""
    while start < stop:
        yield start
        start += step


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------

def get_universal_times(
    peak_time: float,
    longest_pre_peak: float,
    longest_post_peak: float,
) -> tuple[float, float]:
    """Return ``(universal_start_time, universal_end_time)`` around *peak_time*."""
    return peak_time - longest_pre_peak, peak_time + longest_post_peak


# ---------------------------------------------------------------------------
# Alignment
# ---------------------------------------------------------------------------

def align_and_concatenate_data(
    all_data: list[pd.DataFrame],
    universal_time_axis: np.ndarray,
) -> pd.DataFrame:
    """Align and concatenate multiple DataFrames onto a universal time axis.

    Parameters
    ----------
    all_data:
        List of DataFrames, each with a ``'Time (min)'``, ``'Data'``, and
        ``'Cluster Name'`` column.
    universal_time_axis:
        1-D array of time values (seconds) to align against.

    Returns
    -------
    pd.DataFrame
        Concatenated DataFrame with ``'Time (s)'`` as the first column
        followed by one column per input DataFrame (named after its cluster).
    """
    aligned_data = []
    min_length_after_alignment = float("inf")

    for df in all_data:
        if "Time (min)" in df.columns and not df.empty:
            aligned_df = pd.DataFrame({"Time (s)": universal_time_axis})

            start_idx = int(np.argmin(np.abs(df["Time (min)"] - universal_time_axis[0])))

            num_points_to_insert = min(len(df) - start_idx, len(aligned_df))

            source_data = df.iloc[
                start_idx : start_idx + num_points_to_insert,
                df.columns.get_loc("Data"),
            ].values

            num_points_to_insert = min(num_points_to_insert, len(aligned_df))
            num_points_to_insert = min(num_points_to_insert, len(source_data))

            aligned_df.loc[: num_points_to_insert - 1, "Data"] = source_data[:num_points_to_insert]
            aligned_df = aligned_df.rename(columns={"Data": df["Cluster Name"].iloc[0]})

            num_points_after_start = len(df) - start_idx
            min_length_after_alignment = min(min_length_after_alignment, num_points_after_start)

            aligned_data.append(aligned_df)
            continue

    if not aligned_data:
        return pd.DataFrame(columns=["Time (s)"])

    min_length = min(min_length_after_alignment, len(universal_time_axis))
    trimmed_time_axis = universal_time_axis[:min_length]

    time_column = pd.DataFrame(trimmed_time_axis, columns=["Time (s)"])
    data_columns = pd.concat(
        [df.loc[: min_length - 1, df.columns[1]] for df in aligned_data], axis=1
    )
    return pd.concat([time_column, data_columns], axis=1)


# ---------------------------------------------------------------------------
# Mean / SEM aggregation
# ---------------------------------------------------------------------------

def compute_photometry_mean(photometry_data_list: list[pd.DataFrame]) -> pd.DataFrame:
    """Merge a list of photometry DataFrames and compute per-row Mean and SEM.

    Parameters
    ----------
    photometry_data_list:
        Each DataFrame has a time column (first) and a signal column (second).

    Returns
    -------
    pd.DataFrame
        Merged DataFrame with additional ``'Mean'`` and ``'SEM'`` columns.
    """
    all_photometry_data = photometry_data_list[0].copy()
    time_col = all_photometry_data.columns[0]
    all_photometry_data = all_photometry_data.sort_values(by=time_col)
    all_photometry_data.rename(
        columns={all_photometry_data.columns[1]: "dFoF_465_0"}, inplace=True
    )

    for i, df in enumerate(photometry_data_list[1:], start=1):
        df = df.sort_values(by=time_col)
        all_photometry_data = pd.merge_asof(
            all_photometry_data,
            df.rename(columns={df.columns[1]: f"dFoF_465_{i}"}),
            on=time_col,
            tolerance=0.002,
            direction="nearest",
        )

    data_columns = all_photometry_data.columns[1:]
    all_photometry_data["Mean"] = all_photometry_data[data_columns].mean(axis=1, skipna=True)

    if len(data_columns) == 1:
        all_photometry_data["SEM"] = 0
    else:
        all_photometry_data["SEM"] = all_photometry_data[data_columns].sem(axis=1, skipna=True)

    return all_photometry_data


def calculate_mean_and_sem(concatenated_data: pd.DataFrame) -> pd.DataFrame:
    """Return *concatenated_data* with per-row `Mean` and `SEM` columns added."""
    working = concatenated_data.copy()
    data_for_calculation = working.iloc[:, 1:].apply(pd.to_numeric, errors="coerce")
    working["Mean"] = data_for_calculation.mean(axis=1)
    working["SEM"] = data_for_calculation.sem(axis=1).fillna(0)
    return working


def trim_data_to_minimum_length(all_data: list[pd.DataFrame]) -> list[pd.DataFrame]:
    """Trim each DataFrame in *all_data* to the minimum available length."""
    min_length = min(len(dataframe) for dataframe in all_data)
    return [dataframe.iloc[:min_length].copy() for dataframe in all_data]


def create_universal_time_axis(
    axis_time_start: float,
    axis_time_end: float,
    sample_rate: float,
) -> np.ndarray:
    """Return a universal time axis spanning the requested range at *sample_rate*."""
    return np.arange(axis_time_start, axis_time_end + sample_rate, sample_rate)


def create_linear_time_index(start: float, end: float, step: float) -> np.ndarray:
    """Return a linear time index from *start* to *end* inclusive."""
    return np.arange(start, end + step, step)


def process_photometry_data(
    truncated_data: pd.DataFrame,
    step: float = 0.00167,
    tolerance: float = 0.002,
) -> pd.DataFrame:
    """Reindex and interpolate a photometry segment onto a regular time base."""
    if truncated_data.empty:
        return truncated_data.copy()

    time_column_name = truncated_data.columns[0]
    reference_time_index = pd.Index(
        create_linear_time_index(
            truncated_data.iloc[0, 0], truncated_data.iloc[-1, 0], step
        ),
        name=time_column_name,
    )

    working = truncated_data.copy()
    working.set_index(time_column_name, inplace=True)
    processed_data = working.reindex(
        reference_time_index, method="nearest", tolerance=tolerance
    ).reset_index()
    processed_data.interpolate(method="linear", inplace=True)
    return processed_data


# ---------------------------------------------------------------------------
# Binning
# ---------------------------------------------------------------------------

def bin_data_dynamic(data: pd.DataFrame, bin_size_sec: int) -> pd.DataFrame:
    """Bin *data* into fixed-width bins of *bin_size_sec* seconds.

    Parameters
    ----------
    data:
        DataFrame whose first column is time and which has ``'Mean'`` and
        ``'SEM'`` columns.
    bin_size_sec:
        Bin width in seconds.

    Returns
    -------
    pd.DataFrame
        Columns: ``'Bin Range'``, ``'Mean'``, ``'SEM'``.
    """
    time_col = data.columns[0]

    bin_edges = list(
        _float_range(data[time_col].iloc[0], data[time_col].iloc[-1] + bin_size_sec, bin_size_sec)
    )

    if (bin_edges[-1] - bin_edges[-2]) < bin_size_sec:
        bin_edges.pop(-1)

    bins = pd.cut(data[time_col], bins=bin_edges, right=False, include_lowest=True, labels=False)

    binned_data = data.groupby(bins)[["Mean", "SEM"]].mean()
    binned_data.reset_index(inplace=True)

    bin_ranges = [
        f"{int(bin_edges[i])} - {int(bin_edges[i + 1])}" for i in range(len(bin_edges) - 1)
    ]
    binned_data["Bin Range"] = bin_ranges
    return binned_data[["Bin Range", "Mean", "SEM"]]


def build_aligned_photometry_cluster_data(
    dataframe: pd.DataFrame,
    data_column: str,
    clusters_by_period: dict[str, list[dict]],
    longest_pre_peak: float,
    longest_post_peak: float,
    extra_buffer: float = 0.5,
    step_size: float = 1 / 600,
) -> dict[str, dict[str, pd.DataFrame | None]]:
    """Build aligned photometry cluster tables for each period bucket."""
    photometry_data = {
        period: {"Clusters": None} for period in clusters_by_period
    }
    common_time_axis = pd.Index(
        np.arange(-longest_pre_peak, longest_post_peak + step_size, step_size),
        name="Time (min)",
    )
    dataframe_copy = dataframe.copy()

    for period, clusters in clusters_by_period.items():
        if not clusters:
            continue

        cluster_data_frames = []
        for cluster_data in clusters:
            peak_time = cluster_data["peaks"][cluster_data["alignment_index"]]
            universal_start_time, universal_end_time = get_universal_times(
                peak_time, longest_pre_peak, longest_post_peak
            )
            extended_truncated_data = dataframe_copy[
                (dataframe_copy.iloc[:, 0] >= universal_start_time - extra_buffer)
                & (dataframe_copy.iloc[:, 0] <= universal_end_time + extra_buffer)
            ][[dataframe_copy.columns[0], data_column]].copy()

            processed_data = process_photometry_data(extended_truncated_data)
            if processed_data.empty:
                continue

            time_column_name = processed_data.columns[0]
            processed_data[time_column_name] -= peak_time
            processed_data.set_index(time_column_name, inplace=True)

            aligned_data = processed_data.reindex(
                common_time_axis, method="nearest", tolerance=0.002
            ).interpolate()
            aligned_data.columns = [cluster_data["name"]]
            cluster_data_frames.append(aligned_data)

        if cluster_data_frames:
            combined_data = pd.concat(cluster_data_frames, axis=1).reset_index()
            combined_data.columns = ["Time (min)"] + [
                frame.columns[0] for frame in cluster_data_frames
            ]
            photometry_data[period]["Clusters"] = combined_data

    return photometry_data


def apply_cluster_binning(mean_cluster_data: dict, file_data: dict) -> dict:
    """Attach binned temp/activity summaries to *mean_cluster_data* in place."""
    peak_to_bin_size: dict[int, int] = {}

    for cluster_key, cluster_info in file_data.items():
        match = re.match(r"(\d+) Peaks?", cluster_key)
        if not match:
            match = re.match(r"(\d+)_stim", cluster_key)
        if match and cluster_info.get("bin_size"):
            peak_to_bin_size[int(match.group(1))] = int(cluster_info["bin_size"])

    for cluster_number, cluster_periods in mean_cluster_data.items():
        bin_size_sec = peak_to_bin_size.get(cluster_number)
        if not bin_size_sec:
            continue

        for period in ("full", "day", "night"):
            period_data = cluster_periods.get(period, {})
            mean_temp_data = period_data.get("mean_temp_data")
            mean_act_data = period_data.get("mean_act_data")
            if mean_temp_data is None or mean_act_data is None:
                continue

            period_data["binned_mean_temp_data"] = bin_data_dynamic(
                mean_temp_data, bin_size_sec
            )
            period_data["binned_mean_act_data"] = bin_data_dynamic(
                mean_act_data, bin_size_sec
            )

    return mean_cluster_data


def extract_data_for_date_and_offset(
    file_path: str | Path,
    sheet_name: str,
    target_date: str,
    target_time: str,
    duration: float | None = None,
    selected_alignment_datetime=None,
) -> tuple[pd.DataFrame, float | None, str | pd.Timestamp | None]:
    """Compatibility wrapper that preserves patching of the legacy sheet loader."""
    return _recording_io.extract_data_for_date_and_offset(
        file_path,
        sheet_name,
        target_date,
        target_time,
        duration,
        selected_alignment_datetime,
        _sheet_loader=_extract_sheet_table,
    )


def calculate_stim_timings(
    stim_data_df: pd.DataFrame,
    start_time_str: str,
) -> list[tuple[int, list[tuple[float, float]]]]:
    """Build per-cluster stimulation windows in minutes relative to recording start."""
    stim_timings = []
    start_time = (
        datetime.strptime(start_time_str, "%H:%M:%S") - datetime(1900, 1, 1)
    ).total_seconds() / 60

    for cluster_size, stim_duration, interstim_interval, stim_onset in zip(
        stim_data_df["Cluster size (num)"].astype(int),
        stim_data_df["Stim duration (sec)"],
        stim_data_df["Interstim interval (sec)"],
        stim_data_df["Stim onset (hh:mm:ss)"].dt.total_seconds() / 60,
    ):
        stim_onset_relative = stim_onset - start_time

        stim_periods = []
        for stim_number in range(cluster_size):
            stim_start = stim_onset_relative + stim_number * (
                stim_duration + interstim_interval
            ) / 60
            stim_end = stim_start + stim_duration / 60
            stim_periods.append((stim_start, stim_end))

        stim_timings.append((cluster_size, stim_periods))

    return stim_timings


def calculate_sample_rate(timestamps) -> float:
    """Calculate the mean sample interval from a list of timestamps or floats."""
    if isinstance(timestamps[0], (datetime, pd.Timestamp, np.datetime64)):
        parsed_timestamps = pd.to_datetime(pd.Series(timestamps), errors="coerce")
        time_diffs = (
            parsed_timestamps.diff().dt.total_seconds().dropna().tolist()
        )
    else:
        time_diffs = [
            timestamps[i + 1] - timestamps[i]
            for i in range(len(timestamps) - 1)
        ]

    time_diffs = [diff for diff in time_diffs if diff > 0]
    if not time_diffs:
        raise ValueError("Could not calculate a positive telemetry sample interval.")
    return sum(time_diffs) / len(time_diffs)


def data_dict_to_df(data_dict: dict) -> pd.DataFrame:
    """Flatten a {period: {cluster_name: row_dict}} mapping into a DataFrame."""
    rows = []
    for clusters in data_dict.values():
        for cluster_name, cluster_data in clusters.items():
            row = cluster_data.copy()
            row["Cluster Name"] = cluster_name
            rows.append(row)
    return pd.DataFrame(rows)
