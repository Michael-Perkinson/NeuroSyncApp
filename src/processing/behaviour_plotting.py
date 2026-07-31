"""Pure helpers for photometry-behaviour plotting workflows."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def build_treeview_rows(dataframe: pd.DataFrame) -> list[list]:
    """Return table rows ready for insertion into the treeview."""
    rows = [
        [
            Path(str(file_path)).name,
            selected_col,
            behaviour_name,
            behaviour_type,
            pre_time,
            post_time,
            bin_size,
            start_time,
            end_time,
        ]
        for file_path, selected_col, behaviour_name, behaviour_type, pre_time, post_time, bin_size, start_time, end_time in zip(
            dataframe["File Path"],
            dataframe["Selected Column"],
            dataframe["Behaviour Name"],
            dataframe["Behaviour Type"],
            dataframe["Pre Behaviour Time"],
            dataframe["Post Behaviour Time"],
            dataframe["Bin Size"],
            dataframe["Start Time"],
            dataframe["End Time"],
        )
    ]
    return rows


def extract_behaviour_occurrences(
    table_df: pd.DataFrame,
    graphed_behaviour: str,
    selected_column: str,
    checkbox_state: bool,
) -> tuple[list[tuple[float, float | None, float, float]], str, list[float], list[float]]:
    """Return aligned occurrence tuples for a single behaviour."""
    column_used = "baselined_z_score" if checkbox_state else selected_column
    behaviour_occurrences: list[tuple[float, float | None, float, float]] = []
    pre_behaviour_times: list[float] = []
    post_behaviour_times: list[float] = []

    filtered_df = table_df[table_df["Behaviour Name"] == graphed_behaviour]

    # Vectorized column extraction
    start_times = (filtered_df["Start Time"].astype(float) / 60).round(2).values
    pre_behaviour_times_vec = (filtered_df["Pre Behaviour Time"].astype(float) / 60).round(2).values
    post_behaviour_times_vec = (filtered_df["Post Behaviour Time"].astype(float) / 60).round(2).values
    end_time_vals = pd.to_numeric(filtered_df["End Time"], errors='coerce') / 60
    is_point = (filtered_df["Behaviour Type"] == "Point").values

    # Build occurrence tuples with conditional end_time
    behaviour_occurrences = [
        (st, None if is_pt else et, pre, post)
        for st, et, is_pt, pre, post in zip(
            start_times, end_time_vals, is_point, pre_behaviour_times_vec, post_behaviour_times_vec
        )
    ]
    pre_behaviour_times = pre_behaviour_times_vec.tolist()
    post_behaviour_times = post_behaviour_times_vec.tolist()

    return (
        behaviour_occurrences,
        column_used,
        pre_behaviour_times,
        post_behaviour_times,
    )


def select_single_row_window(
    dataframe: pd.DataFrame,
    start_time: float,
    pre_behaviour_time: float,
    post_behaviour_time: float,
) -> tuple[pd.DataFrame, float, float]:
    """Return the photometry slice surrounding the selected table row."""
    start_point = start_time - pre_behaviour_time
    end_point = start_time + post_behaviour_time
    selected_data = dataframe.loc[
        (dataframe.iloc[:, 0] >= start_point) & (dataframe.iloc[:, 0] <= end_point)
    ]
    return selected_data, start_point, end_point


def parse_optional_float(value: str | None) -> float | None:
    """Convert a string to float, returning None for empty/invalid values."""
    text = (value or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def build_adjusted_behaviour_df(
    behaviours: list[str],
    start_times_min: list[float],
    end_times_min: list,
    selected_behaviour: str,
    zero_axis_enabled: bool,
) -> pd.DataFrame | None:
    """Return adjusted start/end times when zeroing is enabled."""
    if (
        not zero_axis_enabled
        or not selected_behaviour
        or selected_behaviour not in behaviours
    ):
        return None

    onset_index = behaviours.index(selected_behaviour)
    onset_time = start_times_min[onset_index]
    adjusted_start = [t - onset_time for t in start_times_min]
    adjusted_end = [t - onset_time if t is not None else None for t in end_times_min]

    return pd.DataFrame(
        {
            "Behaviour Name": behaviours,
            "Adjusted Start Time": adjusted_start,
            "Adjusted End Time": adjusted_end,
        }
    )


def compute_zeroed_time_axis(
    converted_time_data,
    behaviours: list[str],
    original_start_times_min: list[float],
    selected_behaviour: str,
    time_factor: float,
    data_already_adjusted: bool,
    first_offset_time_min: float | None,
    baseline_start_time_min: float | None,
    checkbox_state: bool,
    figure_display: str,
):
    """Apply zeroing and optional baseline offsets to display time data."""
    adjusted_time = converted_time_data.copy()
    if selected_behaviour not in behaviours:
        return adjusted_time, first_offset_time_min

    selected_behaviour_index = behaviours.index(selected_behaviour)
    if selected_behaviour_index >= len(original_start_times_min):
        return adjusted_time, first_offset_time_min

    zero_time = original_start_times_min[selected_behaviour_index] * time_factor
    adjusted_time -= zero_time

    if baseline_start_time_min is None:
        return adjusted_time, first_offset_time_min

    if data_already_adjusted:
        if first_offset_time_min is None:
            first_offset_time_min = baseline_start_time_min
        offset_time = (baseline_start_time_min - first_offset_time_min) * time_factor
        adjusted_time += offset_time
    elif checkbox_state and figure_display == "Z-scored data":
        adjusted_time += baseline_start_time_min * time_factor

    return adjusted_time, first_offset_time_min
