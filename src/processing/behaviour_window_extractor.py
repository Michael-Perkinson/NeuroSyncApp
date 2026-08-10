"""Extract numerical signal windows around behaviour events."""

from __future__ import annotations

import numpy as np
import pandas as pd

TIME_AXIS_DECIMALS = 3
BOUNDARY_TOLERANCE_MIN = 0.001 / 60.0


def _prepare_signal_and_time_columns(
    df: pd.DataFrame,
    column: str,
    z_scored_data=None,
) -> tuple[pd.DataFrame, pd.Series]:
    """Return a positional working frame and the time column used for slicing."""
    working = df.copy().reset_index(drop=True)
    if z_scored_data is not None:
        working[column] = pd.Series(z_scored_data).reset_index(drop=True)
        time_col = working["z_scored_time"]
    else:
        time_col = working.iloc[:, 0]

    return working, pd.to_numeric(time_col, errors="coerce")


def _find_window_positions(
    time_col: pd.Series,
    start_time_min: float,
    behaviour_time_min: float,
    end_time_min: float,
) -> tuple[int, int, int] | None:
    """Return positional [start, behaviour, end) bounds for a time window."""
    valid_positions = np.flatnonzero(time_col.notna().to_numpy())
    if valid_positions.size == 0:
        return None

    valid_times = time_col.iloc[valid_positions].to_numpy(dtype=float)
    start_insert = int(
        np.searchsorted(
            valid_times, start_time_min - BOUNDARY_TOLERANCE_MIN, side="left"
        )
    )
    behaviour_insert = int(
        np.searchsorted(
            valid_times, behaviour_time_min - BOUNDARY_TOLERANCE_MIN, side="left"
        )
    )
    end_insert = int(
        np.searchsorted(valid_times, end_time_min - BOUNDARY_TOLERANCE_MIN, side="left")
    )

    if start_insert >= len(valid_positions) or end_insert <= start_insert:
        return None

    start_pos = int(valid_positions[start_insert])
    behaviour_insert = min(max(behaviour_insert, start_insert), end_insert)
    behaviour_pos = (
        int(valid_positions[behaviour_insert])
        if behaviour_insert < len(valid_positions)
        else int(valid_positions[end_insert - 1]) + 1
    )
    end_pos = (
        int(valid_positions[end_insert])
        if end_insert < len(valid_positions)
        else len(time_col)
    )
    return start_pos, behaviour_pos, end_pos


def extract_data_slice_with_time(
    df: pd.DataFrame,
    start_time_min: float,
    behaviour_time_min: float,
    end_time_min: float,
    column: str,
    z_scored_data=None,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Slice signal data and return actual relative timestamps."""
    working, time_col = _prepare_signal_and_time_columns(df, column, z_scored_data)
    positions = _find_window_positions(
        time_col, start_time_min, behaviour_time_min, end_time_min
    )
    if positions is None:
        empty = pd.Series(dtype=float)
        return empty, empty, empty

    start_pos, behaviour_pos, end_pos = positions

    start_data = working.iloc[start_pos:behaviour_pos][column].reset_index(drop=True)
    end_data = working.iloc[behaviour_pos:end_pos][column].reset_index(drop=True)
    time_slice = time_col.iloc[start_pos:end_pos].reset_index(drop=True)
    behaviour_anchor_min = (
        time_col.iloc[behaviour_pos]
        if behaviour_pos < len(time_col) and pd.notna(time_col.iloc[behaviour_pos])
        else behaviour_time_min
    )
    relative_time_seconds = ((time_slice - behaviour_anchor_min) * 60).round(
        TIME_AXIS_DECIMALS
    )
    relative_time_seconds[np.isclose(relative_time_seconds, 0)] = 0
    return start_data, end_data, relative_time_seconds.reset_index(drop=True)


def extract_data_slice(
    df: pd.DataFrame,
    start_time_min: float,
    behaviour_time_min: float,
    end_time_min: float,
    column: str,
    z_scored_data=None,
) -> tuple[pd.Series, pd.Series]:
    """Slice signal data around a behaviour event."""
    start_data, end_data, _ = extract_data_slice_with_time(
        df,
        start_time_min,
        behaviour_time_min,
        end_time_min,
        column,
        z_scored_data,
    )
    return start_data, end_data


def extract_behaviour_results(
    behaviours_to_export: set,
    params: dict,
    df: pd.DataFrame,
    checkbox_state: bool,
    selected_column: str,
    z_scored_data=None,
) -> tuple[dict, dict]:
    """Extract signal slices for every instance of every exported behaviour."""
    behaviours_results: dict = {}
    time_ranges: dict = {}

    for behaviour_name in behaviours_to_export:
        behaviour_instances = params[behaviour_name]
        for behaviour_instance in behaviour_instances:
            pre_behaviour_time = float(behaviour_instance["pre_behaviour_time"])
            post_behaviour_time = float(behaviour_instance["post_behaviour_time"])
            behaviour_start_time = float(behaviour_instance["behaviour_start_time"])

            behaviours_results.setdefault(behaviour_name, [])

            if not pre_behaviour_time:
                continue

            start_time = behaviour_start_time - pre_behaviour_time
            end_time = behaviour_start_time + post_behaviour_time

            baseline_start_time_min = (
                float(params.get("baseline_start_time_min", 0.0))
                if checkbox_state
                else 0.0
            )
            start_time_min = (start_time / 60) - baseline_start_time_min
            end_time_min = (end_time / 60) - baseline_start_time_min
            behaviour_start_time_min = (
                behaviour_start_time / 60
            ) - baseline_start_time_min

            use_zscore = checkbox_state and z_scored_data is not None
            start_data, end_data, time_range = extract_data_slice_with_time(
                df,
                start_time_min,
                behaviour_start_time_min,
                end_time_min,
                selected_column,
                z_scored_data if use_zscore else None,
            )
            behaviours_results[behaviour_name].append((start_data, end_data))
            time_ranges.setdefault(behaviour_name, []).append(time_range)

    return behaviours_results, time_ranges
