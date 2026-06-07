"""
Pure Excel/CSV export helpers for telemetry/photometry/opto alignment.

No UI framework dependencies.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Cluster heading generation
# ---------------------------------------------------------------------------

def generate_cluster_headings(
    file_data: dict,
    cluster_number: int,
    data_type: str,
) -> list[str]:
    """Build column headings for a cluster export sheet.

    Parameters
    ----------
    file_data:
        Dict whose keys are cluster names (e.g. ``'2 Peaks in Cluster_1'``).
    cluster_number:
        Number of peaks (photometry) or stimuli (stim) to match against.
    data_type:
        ``'photometry'`` or ``'stim'``.

    Returns
    -------
    list[str]
        Starting with ``'Cluster ID'`` then one entry per matching cluster key.
    """
    cluster_headings = ["Cluster ID"]

    if data_type == "photometry":
        pattern = re.compile(rf"^{cluster_number} Peaks? in Cluster_\d+$")
        def format_key(key: str) -> str:
            return key
    else:
        pattern = re.compile(rf"^{cluster_number}_stim_cluster_\d+$")
        def format_key(key: str) -> str:
            return f"{cluster_number} cluster in {key.split('_', 1)[1]}"

    for cluster_key in file_data:
        if pattern.match(cluster_key):
            cluster_headings.append(format_key(cluster_key))

    return cluster_headings


def build_ordered_cluster_records(
    cluster_dict: dict,
    file_data: dict,
    data_type: str,
) -> list[dict]:
    """Return cluster metadata sorted chronologically, regardless of cluster size."""
    records: list[dict] = []

    if data_type == "photometry":
        for (start_idx, end_idx, cluster_size), details in cluster_dict.items():
            file_entry = file_data.get(details["name"], {}) if file_data else {}
            alignment_time = float(details["peaks"][details["alignment_index"]])
            first_peak_time = float(details["peaks"][0])
            pre_cluster_minutes = float(
                file_entry.get("pre_cluster_time", details.get("pre_cluster_time", 0)) or 0
            ) / 60
            post_cluster_minutes = float(
                file_entry.get("post_cluster_time", details.get("post_cluster_time", 0)) or 0
            ) / 60
            cluster_start_relative = float(details["peaks"][0]) - alignment_time
            cluster_end_relative = float(details["end_time"]) - alignment_time
            records.append(
                {
                    "cluster_order_key": (float(details["start_time"]), float(details["end_time"]), cluster_size),
                    "cluster_name": details["name"],
                    "cluster_size": cluster_size,
                    "time_period": details.get("time_period", ""),
                    "start_time": float(details["start_time"]),
                    "end_time": float(details["end_time"]),
                    "duration": float(details["cluster_duration"]),
                    "alignment_time": alignment_time,
                    "first_peak_time": first_peak_time,
                    "alignment_offset_from_first_peak": alignment_time - first_peak_time,
                    "actual_window_start_time": first_peak_time - pre_cluster_minutes,
                    "actual_window_end_time": float(details["end_time"]) + post_cluster_minutes,
                    "full_window_start_relative": cluster_start_relative - pre_cluster_minutes,
                    "full_window_end_relative": cluster_end_relative + post_cluster_minutes,
                    "fixed_window_start_relative": -pre_cluster_minutes,
                    "fixed_window_end_relative": post_cluster_minutes,
                    "standardized_window_end_relative": (
                        float(details["end_time"]) - first_peak_time
                    )
                    + post_cluster_minutes,
                }
            )
    else:
        for cluster_name, details in file_data.items():
            if "stim" not in cluster_name:
                continue
            pre_stim_minutes = float(details.get("pre_stim_time", 0)) / 60
            post_stim_minutes = float(details.get("post_stim_time", 0)) / 60
            stim_duration = float(details["stim_end"] - details["stim_start"])
            records.append(
                {
                    "cluster_order_key": (
                        float(details["stim_start"]),
                        float(details["stim_end"]),
                        int(details["cluster_size"]),
                    ),
                    "cluster_name": details.get("name", cluster_name),
                    "cluster_size": int(details["cluster_size"]),
                    "time_period": details.get("time_period", ""),
                    "start_time": float(details["stim_start"]),
                    "end_time": float(details["stim_end"]),
                    "duration": stim_duration,
                    "alignment_time": float(details["stim_start"]),
                    "first_peak_time": float(details["stim_start"]),
                    "alignment_offset_from_first_peak": 0.0,
                    "actual_window_start_time": float(details["stim_start"]) - pre_stim_minutes,
                    "actual_window_end_time": float(details["stim_end"]) + post_stim_minutes,
                    "full_window_start_relative": -pre_stim_minutes,
                    "full_window_end_relative": stim_duration + post_stim_minutes,
                    "fixed_window_start_relative": -pre_stim_minutes,
                    "fixed_window_end_relative": post_stim_minutes,
                    "standardized_window_end_relative": stim_duration + post_stim_minutes,
                }
            )

    records.sort(key=lambda row: row["cluster_order_key"])
    for index, record in enumerate(records, start=1):
        record["cluster_order"] = index
    return records


def build_intercluster_interval_frame(
    cluster_dict: dict,
    file_data: dict,
    data_type: str,
) -> pd.DataFrame:
    """Build a chronological per-cluster interval summary."""
    records = build_ordered_cluster_records(cluster_dict, file_data, data_type)
    rows = []
    previous_record = None

    for record in records:
        row = {
            "Cluster Order": record["cluster_order"],
            "Cluster Name": record["cluster_name"],
            "Cluster Size": record["cluster_size"],
            "Time Period": record["time_period"],
            "Start Time (min)": record["start_time"],
            "End Time (min)": record["end_time"],
            "Duration (min)": record["duration"],
            "Alignment Time (min)": record["alignment_time"],
            "Previous Cluster": "",
            "Interval From Previous End (min)": "",
            "Interval Start-to-Start (min)": "",
        }

        if previous_record is not None:
            row["Previous Cluster"] = previous_record["cluster_name"]
            row["Interval From Previous End (min)"] = (
                record["start_time"] - previous_record["end_time"]
            )
            row["Interval Start-to-Start (min)"] = (
                record["start_time"] - previous_record["start_time"]
            )

        rows.append(row)
        previous_record = record

    return pd.DataFrame(rows)


def build_native_signal_frame(
    mean_cluster_data: dict,
    cluster_dict: dict,
    file_data: dict,
    data_type: str,
    signal_type: str,
    window_mode: str = "full_cluster",
) -> pd.DataFrame:
    """Build a long-format frame of native-rate aligned samples for one signal type."""
    records = build_ordered_cluster_records(cluster_dict, file_data, data_type)
    cluster_lookup = {record["cluster_name"]: record for record in records}
    native_rows: list[dict] = []

    if window_mode not in {"full_cluster", "fixed_window"}:
        raise ValueError(f"Unknown window mode: {window_mode}")

    global_fixed_start = min(
        (record["fixed_window_start_relative"] for record in records), default=0.0
    )
    global_fixed_end = max(
        (record["standardized_window_end_relative"] for record in records), default=0.0
    )

    segment_key = f"native_{signal_type}_segments"
    for cluster_number in sorted(mean_cluster_data):
        period_data = mean_cluster_data[cluster_number].get("full", {})
        for segment in period_data.get(segment_key, []):
            if segment is None or segment.empty:
                continue

            cluster_name = str(segment["Cluster Name"].iloc[0])
            cluster_record = cluster_lookup.get(cluster_name)
            if cluster_record is None:
                continue

            time_column = "Time (min)" if "Time (min)" in segment.columns else segment.columns[0]
            date_time_column = next(
                (column for column in ("Date Time", "DateTime") if column in segment.columns),
                "",
            )
            if window_mode == "full_cluster":
                window_start = cluster_record["full_window_start_relative"]
                window_end = cluster_record["full_window_end_relative"]
                segment_for_export = segment[
                    (segment[time_column] >= window_start) & (segment[time_column] <= window_end)
                ].reset_index(drop=True)
            else:
                window_start = global_fixed_start
                window_end = global_fixed_end

                segment_for_export = _build_padded_fixed_window_segment(
                    segment,
                    time_column,
                    date_time_column,
                    cluster_record,
                    window_start,
                    window_end,
                )

            if segment_for_export.empty:
                continue

            for sample_index, (_, sample) in enumerate(segment_for_export.iterrows(), start=1):
                row = {
                    "Cluster Order": cluster_record["cluster_order"],
                    "Cluster Name": cluster_name,
                    "Cluster Size": cluster_record["cluster_size"],
                    "Time Period": cluster_record["time_period"],
                    "First Peak Time (min)": cluster_record["first_peak_time"],
                    "Cluster Start Time (min)": cluster_record["start_time"],
                    "Cluster End Time (min)": cluster_record["end_time"],
                    "Window Start (min)": cluster_record["actual_window_start_time"],
                    "Window End (min)": cluster_record["actual_window_end_time"],
                    "Sample Index": sample_index,
                    "Relative Time (min)": sample.get(time_column, ""),
                    "Absolute Time": sample.get(date_time_column, ""),
                    "Value": sample.get("Data", ""),
                }
                native_rows.append(row)

    frame = pd.DataFrame(native_rows)
    if not frame.empty:
        frame = frame.sort_values(
            ["Cluster Order", "Sample Index"], kind="stable"
        ).reset_index(drop=True)
    return frame


def get_standardized_native_window_bounds(
    cluster_dict: dict,
    file_data: dict,
    data_type: str,
    window_mode: str,
) -> tuple[float, float]:
    """Return the export window bounds used for native-rate sheet generation."""
    records = build_ordered_cluster_records(cluster_dict, file_data, data_type)
    if not records:
        return 0.0, 0.0

    if window_mode == "full_cluster":
        return (
            min(record["full_window_start_relative"] for record in records),
            max(record["full_window_end_relative"] for record in records),
        )
    if window_mode == "fixed_window":
        return (
            min(record["fixed_window_start_relative"] for record in records),
            max(record["standardized_window_end_relative"] for record in records),
        )
    raise ValueError(f"Unknown window mode: {window_mode}")


def _build_padded_fixed_window_segment(
    segment: pd.DataFrame,
    time_column: str,
    date_time_column: str,
    cluster_record: dict,
    window_start: float,
    window_end: float,
) -> pd.DataFrame:
    """Return a first-peak-aligned, end-padded fixed window segment."""
    segment = segment.copy()
    time_offset = cluster_record["alignment_offset_from_first_peak"]
    segment[time_column] = pd.to_numeric(segment[time_column], errors="coerce")
    segment = segment.dropna(subset=[time_column]).sort_values(time_column).reset_index(drop=True)
    if segment.empty:
        columns = [time_column, "Data"]
        if date_time_column:
            columns.append(date_time_column)
        return pd.DataFrame(columns=columns)

    segment[time_column] = segment[time_column] + time_offset
    full_segment = segment.copy()
    segment = segment[
        (segment[time_column] >= window_start) & (segment[time_column] <= window_end)
    ].reset_index(drop=True)

    if len(full_segment) > 1:
        diffs = pd.Series(full_segment[time_column]).diff().dropna()
        positive_diffs = diffs[diffs > 0]
        if not positive_diffs.empty:
            time_step = float(positive_diffs.min())
        else:
            time_step = 1 / 60
    else:
        time_step = 1 / 60

    full_axis = np.round(np.arange(window_start, window_end + (time_step / 2), time_step), 10)
    axis_frame = pd.DataFrame(
        {
            "_sample_position": np.arange(len(full_axis), dtype=int),
            time_column: full_axis,
        }
    )

    if not segment.empty:
        segment["_sample_position"] = np.rint(
            (segment[time_column] - window_start) / time_step
        ).astype(int)
        segment = segment[
            (segment["_sample_position"] >= 0)
            & (segment["_sample_position"] < len(full_axis))
        ].copy()

        if not segment.empty:
            keep_columns = ["_sample_position", "Data"]
            if date_time_column:
                keep_columns.append(date_time_column)
            segment = segment[keep_columns].drop_duplicates(
                subset=["_sample_position"], keep="first"
            )

    empty_merge_frame = pd.DataFrame(
        columns=["_sample_position", "Data"] + ([date_time_column] if date_time_column else [])
    )
    merged = axis_frame.merge(
        segment if not segment.empty else empty_merge_frame,
        on="_sample_position",
        how="left",
    )
    if date_time_column and date_time_column not in merged.columns:
        merged[date_time_column] = pd.NaT
    merged.drop(columns=["_sample_position"], inplace=True)
    return merged
