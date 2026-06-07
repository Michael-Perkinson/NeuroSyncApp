"""
Pure data-processing helpers for telemetry/photometry/opto alignment.

No UI framework dependencies — all inputs and outputs are plain Python
types, NumPy arrays, or pandas DataFrames.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import re

import numpy as np
import pandas as pd


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


def parse_recording_date(date_str: str) -> datetime:
    """Parse a ``yy-mm-dd`` recording date into a datetime."""
    year, month, day = date_str.split("-")
    year = "20" + year
    return datetime.strptime(f"{day}-{month}-{year}", "%d-%m-%Y")


def _parse_clock_time(value: str | None):
    """Return a ``time`` parsed from ``HH:MM:SS`` or ``None`` when blank/invalid."""
    normalized_value = str(value or "").strip()
    if not normalized_value:
        return None
    try:
        return datetime.strptime(normalized_value, "%H:%M:%S").time()
    except ValueError:
        return None


def calculate_nighttime_periods(
    recording_date,
    start_time_str: str,
    lights_off_time_str: str,
    duration_minutes: float,
) -> list[tuple]:
    """Return nighttime periods bounded by the recording duration."""
    start_time = _parse_clock_time(start_time_str)
    lights_off_time = _parse_clock_time(lights_off_time_str)
    if start_time is None or lights_off_time is None:
        return []

    start_datetime = datetime.combine(recording_date, start_time)
    lights_off_datetime = datetime.combine(recording_date, lights_off_time)

    if lights_off_datetime < start_datetime:
        night_start = start_datetime
        night_end = datetime.combine(recording_date, lights_off_time) + timedelta(hours=12)
    else:
        night_start = lights_off_datetime
        night_end = lights_off_datetime + timedelta(hours=12)

    if night_end.time() < night_start.time():
        night_end = datetime.combine(
            night_start.date() + timedelta(days=1), night_end.time()
        )

    end_datetime = start_datetime + timedelta(minutes=duration_minutes)
    if night_end > end_datetime:
        night_end = end_datetime

    return [(night_start.time(), night_end.time())]


def find_offset_for_previous_time(
    dataframe: pd.DataFrame,
    target_time_str: str,
) -> tuple[float | None, str | None]:
    """Return the offset in minutes to the last timestamp before *target_time_str*."""
    working_df = dataframe.copy()
    working_df["DateTime"] = pd.to_datetime(working_df["Date Time"])
    target_time = pd.to_datetime(target_time_str).time()

    working_df["Offset"] = working_df["DateTime"].apply(
        lambda value: (datetime.combine(value.date(), target_time) - value)
        if value.time() < target_time
        else pd.Timedelta(days=1)
    )

    before_target = working_df[working_df["Offset"] < pd.Timedelta(days=1)]
    if before_target.empty:
        return None, None

    last_row_before_target = before_target.iloc[-1]
    offset_minutes = last_row_before_target["Offset"].total_seconds() / 60
    prev_time_from_data = last_row_before_target["DateTime"].strftime("%H:%M:%S")
    return offset_minutes, prev_time_from_data


def _resolve_sheet_name(sheet_names: list[str], target_name: str) -> str:
    """Return the matching sheet name, falling back to a case-insensitive match."""
    if target_name in sheet_names:
        return target_name

    target_name_upper = target_name.upper()
    sheet_names_upper = [name.upper() for name in sheet_names]
    if target_name_upper in sheet_names_upper:
        return sheet_names[sheet_names_upper.index(target_name_upper)]

    raise ValueError(f"Sheet name '{target_name}' not found in the Excel file.")


def _extract_sheet_table(file_path: str | Path, sheet_name: str) -> pd.DataFrame:
    """Load a telemetry worksheet and return the tabular portion below the header label."""
    excel_file = pd.ExcelFile(file_path)
    correct_sheet_name = _resolve_sheet_name(excel_file.sheet_names, sheet_name)
    data = pd.read_excel(file_path, sheet_name=correct_sheet_name)

    if "Time" not in data.columns:
        time_label_row = data[data.eq("Time").any(axis=1)]
        if time_label_row.empty:
            raise ValueError("Couldn't locate the 'Time' label in the data.")
        start_data_index = time_label_row.index[0] + 1
    else:
        start_data_index = data[data["Time"] == "Time"].index[0] + 1

    data = data.iloc[start_data_index:]
    data.columns = [str(col).upper() for col in data.columns]

    sheet_name_upper = sheet_name.upper()
    if sheet_name_upper in data.columns:
        data = data.rename(columns={"NAME": "Date Time", sheet_name_upper: "Data"})

    data["Date Time"] = pd.to_datetime(data["Date Time"], errors="coerce")
    return data


def extract_data_for_date_and_offset(
    file_path: str | Path,
    sheet_name: str,
    target_date: str,
    target_time: str,
) -> tuple[pd.DataFrame, float | None, str | None]:
    """Load telemetry data for *target_date* and locate its alignment offset."""
    data = _extract_sheet_table(file_path, sheet_name)
    target_date_parsed = pd.to_datetime(target_date).date()
    date_data = data[data["Date Time"].dt.date >= target_date_parsed]
    target_day_data = data[data["Date Time"].dt.date == target_date_parsed]
    offset, previous_time = find_offset_for_previous_time(target_day_data, target_time)
    return date_data, offset, previous_time


def extract_and_trim_data(
    dataframe: pd.DataFrame,
    previous_time: str,
    offset: float,
    duration: float,
    sample_rate: float,
) -> pd.DataFrame:
    """Trim a telemetry dataframe to the requested duration and build a relative time axis."""
    if previous_time in (None, "") or offset is None:
        raise ValueError(
            "The selected alignment time is earlier than the first telemetry sample "
            "available for that date."
        )

    previous_time_str = str(previous_time)
    date_time_series = pd.to_datetime(dataframe["Date Time"], errors="coerce")
    matching_rows = dataframe[
        date_time_series.dt.strftime("%H:%M:%S") == previous_time_str
    ]
    if matching_rows.empty:
        raise ValueError(
            f"Could not locate telemetry samples matching the alignment time {previous_time_str}."
        )

    start_index = matching_rows.index[0]
    num_data_points = int(((duration + offset) * 60) / sample_rate)
    extracted_data = dataframe.loc[start_index : start_index + num_data_points - 1]

    rows_to_trim = int(np.ceil((offset * 60) / sample_rate))
    trimmed_df = extracted_data.iloc[rows_to_trim:].copy()
    trimmed_df["Time (min)"] = [(i * (sample_rate / 60)) for i in range(len(trimmed_df))]
    return trimmed_df


def extract_data_with_buffer(
    dataframe: pd.DataFrame,
    offset: float,
    sample_rate: float,
    previous_time: str | None = None,
    duration: float | None = None,
) -> pd.DataFrame:
    """Return a copy of *dataframe* with a relative time axis that includes the leading buffer."""
    if dataframe.empty:
        return dataframe.copy()

    extracted_extended_data = dataframe.copy()

    if "Offset" in extracted_extended_data.columns:
        start_offset = extracted_extended_data.iloc[0]["Offset"].total_seconds() / 60
    else:
        start_offset = float(offset)

        if previous_time:
            previous_time_str = str(previous_time)
            date_time_series = pd.to_datetime(dataframe["Date Time"], errors="coerce")
            matching_rows = dataframe[
                date_time_series.dt.strftime("%H:%M:%S") == previous_time_str
            ]
            if not matching_rows.empty:
                start_index = matching_rows.index[0]
                if duration is not None:
                    num_data_points = int(((duration + offset) * 60) / sample_rate)
                    extracted_extended_data = dataframe.loc[
                        start_index : start_index + num_data_points - 1
                    ].copy()
                else:
                    extracted_extended_data = dataframe.loc[start_index:].copy()

    extracted_extended_data = extracted_extended_data.reset_index(drop=True)
    extracted_extended_data["Time (min)"] = [
        (i * (sample_rate / 60) - start_offset) for i in range(len(extracted_extended_data))
    ]
    return extracted_extended_data


def upsample_telemetry_data(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Upsample telemetry data to 100 ms resolution using linear interpolation."""
    working_df = dataframe.copy()
    if "DateTime" not in working_df.columns:
        if "Date Time" not in working_df.columns:
            raise ValueError("Telemetry data must contain 'Date Time' or 'DateTime'.")
        working_df["DateTime"] = pd.to_datetime(working_df["Date Time"], errors="coerce")
    else:
        working_df["DateTime"] = pd.to_datetime(working_df["DateTime"], errors="coerce")

    working_df = working_df.set_index("DateTime")
    working_df["Data"] = pd.to_numeric(working_df["Data"], errors="coerce")

    upsampled_df = working_df[["Data"]].resample("100ms").interpolate().reset_index()
    upsampled_df["Date Time"] = (
        upsampled_df["DateTime"].dt.strftime("%Y-%m-%d %H:%M:%S.%f").str[:-3]
    )
    upsampled_df["Offset"] = pd.NaT
    return upsampled_df[["Date Time", "Data", "DateTime", "Offset"]]


def calculate_stim_timings(
    stim_data_df: pd.DataFrame,
    start_time_str: str,
) -> list[tuple[int, list[tuple[float, float]]]]:
    """Build per-cluster stimulation windows in minutes relative to recording start."""
    stim_timings = []
    start_time = (
        datetime.strptime(start_time_str, "%H:%M:%S") - datetime(1900, 1, 1)
    ).total_seconds() / 60

    for _, row in stim_data_df.iterrows():
        cluster_size = int(row["Cluster size (num)"])
        stim_duration = row["Stim duration (sec)"]
        interstim_interval = row["Interstim interval (sec)"]
        stim_onset = row["Stim onset (hh:mm:ss)"].total_seconds() / 60
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
