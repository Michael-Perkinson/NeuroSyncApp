"""Telemetry recording ingestion, time alignment, and window extraction helpers."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class AmbiguousTelemetryAlignmentError(ValueError):
    """Raised when more than one telemetry start date can cover the recording."""

    def __init__(self, candidates: list[dict], duration: float):
        self.candidates = candidates
        self.duration = duration
        super().__init__(
            "Multiple telemetry alignment dates can cover the photometry recording."
        )


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
    night_end = min(night_end, end_datetime)

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


def _find_alignment_anchor(
    dataframe: pd.DataFrame,
    target_datetime: pd.Timestamp,
) -> tuple[float | None, pd.Timestamp | None, int | None]:
    """Return the nearest sample at/before *target_datetime* and its row index."""
    if dataframe.empty:
        return None, None, None

    date_times = pd.to_datetime(dataframe["Date Time"], errors="coerce")
    before_target = date_times[date_times <= target_datetime]
    if before_target.empty:
        return None, None, None

    anchor_index = int(before_target.index[-1])
    previous_timestamp = pd.Timestamp(before_target.iloc[-1])
    offset_minutes = (target_datetime - previous_timestamp).total_seconds() / 60
    if offset_minutes < 0:
        return None, None, None
    return offset_minutes, previous_timestamp, anchor_index


def _candidate_target_datetimes(target_date, target_time: str) -> list[pd.Timestamp]:
    target_date_parsed = pd.to_datetime(target_date).date()
    target_clock = pd.to_datetime(target_time).time()
    candidate_dates = [
        target_date_parsed,
        target_date_parsed - timedelta(days=1),
        target_date_parsed + timedelta(days=1),
    ]
    return [
        pd.Timestamp(datetime.combine(candidate_date, target_clock))
        for candidate_date in candidate_dates
    ]


def _build_alignment_candidates(
    dataframe: pd.DataFrame,
    target_date,
    target_time: str,
) -> list[dict]:
    alignment_candidates = []
    if dataframe.empty:
        return alignment_candidates

    last_timestamp = pd.Timestamp(dataframe["Date Time"].iloc[-1])
    for target_datetime in _candidate_target_datetimes(target_date, target_time):
        offset, previous_timestamp, anchor_index = _find_alignment_anchor(
            dataframe, target_datetime
        )
        if previous_timestamp is None or anchor_index is None:
            continue

        available_minutes = (last_timestamp - target_datetime).total_seconds() / 60
        if available_minutes < 0:
            continue

        alignment_candidates.append(
            {
                "target_datetime": target_datetime,
                "offset": offset,
                "previous_timestamp": previous_timestamp,
                "anchor_index": anchor_index,
                "available_minutes": available_minutes,
            }
        )

    return alignment_candidates


def _alignment_timestamp(value) -> pd.Timestamp | None:
    if isinstance(value, (datetime, pd.Timestamp, np.datetime64)):
        parsed = pd.to_datetime(value, errors="coerce")
        return None if pd.isna(parsed) else pd.Timestamp(parsed)

    text = str(value or "").strip()
    if not text:
        return None
    if not re.search(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", text):
        return None

    parsed = pd.to_datetime(text, errors="coerce")
    return None if pd.isna(parsed) else pd.Timestamp(parsed)


def _select_alignment_candidate(
    candidates: list[dict],
    duration: float | None = None,
    selected_alignment_datetime=None,
) -> dict | None:
    if not candidates:
        return None

    selected_timestamp = _alignment_timestamp(selected_alignment_datetime)
    if selected_timestamp is not None:
        for candidate in candidates:
            if candidate["target_datetime"] == selected_timestamp:
                return candidate
        raise ValueError(
            f"The selected telemetry alignment date {selected_timestamp} is not "
            "available in this telemetry file."
        )

    if duration is None:
        return candidates[0]

    covering_candidates = [
        candidate for candidate in candidates if candidate["available_minutes"] >= duration
    ]
    if len(covering_candidates) > 1:
        raise AmbiguousTelemetryAlignmentError(covering_candidates, duration)
    if len(covering_candidates) == 1:
        return covering_candidates[0]

    return max(candidates, key=lambda candidate: candidate["available_minutes"])


def _rows_matching_alignment_time(dataframe: pd.DataFrame, previous_time):
    date_time_series = pd.to_datetime(dataframe["Date Time"], errors="coerce")
    absolute_timestamp = _alignment_timestamp(previous_time)
    if absolute_timestamp is not None:
        return dataframe[date_time_series == absolute_timestamp]

    previous_time_str = str(previous_time)
    return dataframe[date_time_series.dt.strftime("%H:%M:%S") == previous_time_str]


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
        time_label_row = data[data["Time"] == "Time"]
        if time_label_row.empty:
            raise ValueError("Couldn't locate the 'Time' label in the data.")
        start_data_index = time_label_row.index[0] + 1

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
    duration: float | None = None,
    selected_alignment_datetime=None,
    *,
    _sheet_loader: Callable[[str | Path, str], pd.DataFrame] | None = None,
) -> tuple[pd.DataFrame, float | None, str | pd.Timestamp | None]:
    """Load telemetry data for *target_date* and locate its alignment offset."""
    sheet_loader = _sheet_loader or _extract_sheet_table
    data = sheet_loader(file_path, sheet_name)
    data = data.dropna(subset=["Date Time"]).sort_values("Date Time")

    dup_count = data["Date Time"].duplicated().sum()
    if dup_count > 0:
        data = data[~data["Date Time"].duplicated(keep="first")]
        logger.info("Removed %s duplicate timestamps from telemetry.", dup_count)

    data = data.reset_index(drop=True)
    target_date_parsed = pd.to_datetime(target_date).date()
    date_data = data[data["Date Time"].dt.date >= target_date_parsed].copy()
    target_day_data = data[data["Date Time"].dt.date == target_date_parsed]

    total_points = len(date_data)
    missing_points = date_data["Data"].isna().sum() if "Data" in date_data else 0
    if total_points > 0:
        missing_pct = (missing_points / total_points) * 100
        if missing_pct > 10:
            logger.warning(
                "Telemetry data has %.1f%% missing Data values. These samples are preserved.",
                missing_pct,
            )

    alignment_candidates = _build_alignment_candidates(data, target_date, target_time)
    if alignment_candidates:
        selected_candidate = _select_alignment_candidate(
            alignment_candidates,
            duration=duration,
            selected_alignment_datetime=selected_alignment_datetime,
        )
        date_data = data.iloc[selected_candidate["anchor_index"] :].copy()
        return (
            date_data,
            selected_candidate["offset"],
            selected_candidate["previous_timestamp"],
        )

    offset, previous_time = find_offset_for_previous_time(target_day_data, target_time)
    return date_data, offset, previous_time


def extract_and_trim_data(
    dataframe: pd.DataFrame,
    previous_time,
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

    matching_rows = _rows_matching_alignment_time(dataframe, previous_time)
    if matching_rows.empty:
        raise ValueError(
            f"Could not locate telemetry samples matching the alignment time {previous_time}."
        )

    start_index = dataframe.index.get_loc(matching_rows.index[0])
    num_data_points = int(((duration + offset) * 60) / sample_rate)
    extracted_data = dataframe.iloc[start_index : start_index + num_data_points]

    rows_to_trim = int(np.ceil((offset * 60) / sample_rate))
    trimmed_df = extracted_data.iloc[rows_to_trim:].copy()
    trimmed_df["Time (min)"] = [(i * (sample_rate / 60)) for i in range(len(trimmed_df))]
    return trimmed_df


def extract_data_with_buffer(
    dataframe: pd.DataFrame,
    offset: float,
    sample_rate: float,
    previous_time=None,
    duration: float | None = None,
) -> pd.DataFrame:
    """Return a copy of *dataframe* with a relative time axis including its buffer."""
    if dataframe.empty:
        return dataframe.copy()

    extracted_extended_data = dataframe.copy()

    if "Offset" in extracted_extended_data.columns:
        start_offset = extracted_extended_data.iloc[0]["Offset"].total_seconds() / 60
    else:
        start_offset = float(offset)

        if previous_time:
            matching_rows = _rows_matching_alignment_time(dataframe, previous_time)
            if not matching_rows.empty:
                start_index = dataframe.index.get_loc(matching_rows.index[0])
                if duration is not None:
                    num_data_points = int(((duration + offset) * 60) / sample_rate)
                    extracted_extended_data = dataframe.iloc[
                        start_index : start_index + num_data_points
                    ].copy()
                else:
                    extracted_extended_data = dataframe.iloc[start_index:].copy()

    extracted_extended_data = extracted_extended_data.reset_index(drop=True)
    extracted_extended_data["Time (min)"] = [
        (i * (sample_rate / 60) - start_offset)
        for i in range(len(extracted_extended_data))
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
