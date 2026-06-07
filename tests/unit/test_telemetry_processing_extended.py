"""Extended tests for src/processing/telemetry_processing.py — targeting uncovered branches."""
from __future__ import annotations

from datetime import datetime, time

import numpy as np
import pandas as pd
import pytest

from src.processing.telemetry_processing import (
    _parse_clock_time,
    _resolve_sheet_name,
    align_and_concatenate_data,
    calculate_nighttime_periods,
    compute_photometry_mean,
    create_linear_time_index,
    extract_and_trim_data,
    extract_data_with_buffer,
    find_offset_for_previous_time,
    get_universal_times,
    parse_recording_date,
    process_photometry_data,
    upsample_telemetry_data,
)


class TestGetUniversalTimes:
    def test_symmetric_window(self):
        start, end = get_universal_times(10.0, 2.0, 3.0)
        assert start == pytest.approx(8.0)
        assert end == pytest.approx(13.0)

    def test_zero_pre_post(self):
        start, end = get_universal_times(5.0, 0.0, 0.0)
        assert start == pytest.approx(5.0)
        assert end == pytest.approx(5.0)


class TestAlignAndConcatenateData:
    def _make_frame(self, times_min, data_values, cluster_name):
        return pd.DataFrame(
            {
                "Time (min)": times_min,
                "Data": data_values,
                "Cluster Name": cluster_name,
            }
        )

    def test_empty_list_returns_time_column_only(self):
        result = align_and_concatenate_data([], np.array([0.0, 1.0, 2.0]))
        assert list(result.columns) == ["Time (s)"]

    def test_frame_without_time_min_column_is_skipped(self):
        df = pd.DataFrame({"Other": [1.0, 2.0], "Data": [3.0, 4.0]})
        result = align_and_concatenate_data([df], np.array([0.0, 1.0]))
        assert list(result.columns) == ["Time (s)"]

    def test_single_frame_aligns_data(self):
        df = self._make_frame([0.0, 1.0, 2.0], [10.0, 20.0, 30.0], "C1")
        result = align_and_concatenate_data([df], np.array([0.0, 1.0, 2.0]))
        assert "Time (s)" in result.columns
        assert "C1" in result.columns

    def test_two_frames_produces_two_data_columns(self):
        df1 = self._make_frame([0.0, 1.0, 2.0], [1.0, 2.0, 3.0], "C1")
        df2 = self._make_frame([0.0, 1.0, 2.0], [4.0, 5.0, 6.0], "C2")
        result = align_and_concatenate_data([df1, df2], np.array([0.0, 1.0, 2.0]))
        assert "C1" in result.columns
        assert "C2" in result.columns


class TestComputePhotometryMean:
    def _make_photometry_df(self, times, values):
        return pd.DataFrame({"Time (min)": times, "dFoF": values})

    def test_single_frame_has_zero_sem(self):
        df = self._make_photometry_df([0.0, 1.0], [1.0, 2.0])
        result = compute_photometry_mean([df])
        assert (result["SEM"] == 0).all()

    def test_single_frame_mean_equals_data(self):
        df = self._make_photometry_df([0.0, 1.0], [3.0, 5.0])
        result = compute_photometry_mean([df])
        assert result["Mean"].tolist() == pytest.approx([3.0, 5.0])

    def test_two_frames_computes_mean(self):
        df1 = self._make_photometry_df([0.0, 1.0], [2.0, 4.0])
        df2 = self._make_photometry_df([0.0, 1.0], [4.0, 6.0])
        result = compute_photometry_mean([df1, df2])
        assert result["Mean"].tolist() == pytest.approx([3.0, 5.0])

    def test_two_frames_have_positive_sem(self):
        df1 = self._make_photometry_df([0.0], [1.0])
        df2 = self._make_photometry_df([0.0], [3.0])
        result = compute_photometry_mean([df1, df2])
        assert result["SEM"].iloc[0] > 0


class TestProcessPhotometryDataEmptyPath:
    def test_empty_dataframe_returns_empty_copy(self):
        df = pd.DataFrame(columns=["Time", "Signal"])
        result = process_photometry_data(df)
        assert result.empty
        assert list(result.columns) == ["Time", "Signal"]


class TestCreateLinearTimeIndex:
    def test_basic_range(self):
        result = create_linear_time_index(0.0, 2.0, 1.0)
        assert list(result) == pytest.approx([0.0, 1.0, 2.0])

    def test_step_determines_length(self):
        result = create_linear_time_index(0.0, 1.0, 0.5)
        assert len(result) == 3

    def test_fractional_step(self):
        # Use integer-representable fractions to avoid np.arange floating-point edge cases
        result = create_linear_time_index(0.0, 1.0, 0.25)
        assert result[0] == pytest.approx(0.0)
        assert result[-1] == pytest.approx(1.0)


class TestParseRecordingDate:
    def test_parses_yy_mm_dd(self):
        result = parse_recording_date("23-06-15")
        assert result.year == 2023
        assert result.month == 6
        assert result.day == 15

    def test_century_prefix_added(self):
        result = parse_recording_date("99-01-01")
        assert result.year == 2099


class TestParseClockTime:
    def test_none_returns_none(self):
        assert _parse_clock_time(None) is None

    def test_empty_string_returns_none(self):
        assert _parse_clock_time("") is None

    def test_whitespace_string_returns_none(self):
        assert _parse_clock_time("   ") is None

    def test_invalid_format_returns_none(self):
        assert _parse_clock_time("not-a-time") is None

    def test_valid_hhmmss_parses(self):
        result = _parse_clock_time("20:00:00")
        assert isinstance(result, time)
        assert result.hour == 20

    def test_midnight_parses(self):
        result = _parse_clock_time("00:00:00")
        assert result.hour == 0 and result.minute == 0


class TestCalculateNighttimePeriods:
    def _date(self):
        return datetime(2023, 6, 15).date()

    def test_none_start_time_returns_empty(self):
        result = calculate_nighttime_periods(self._date(), None, "20:00:00", 1440.0)
        assert result == []

    def test_empty_start_time_returns_empty(self):
        result = calculate_nighttime_periods(self._date(), "", "20:00:00", 1440.0)
        assert result == []

    def test_none_lights_off_returns_empty(self):
        result = calculate_nighttime_periods(self._date(), "08:00:00", None, 1440.0)
        assert result == []

    def test_invalid_lights_off_returns_empty(self):
        result = calculate_nighttime_periods(self._date(), "08:00:00", "bad", 1440.0)
        assert result == []

    def test_normal_case_returns_one_period(self):
        result = calculate_nighttime_periods(self._date(), "08:00:00", "20:00:00", 1440.0)
        assert len(result) == 1

    def test_lights_off_before_start_uses_start_as_night_start(self):
        # Lights off at 06:00 is before recording start at 08:00 → night started at 08:00
        result = calculate_nighttime_periods(self._date(), "08:00:00", "06:00:00", 1440.0)
        assert len(result) == 1
        night_start, _ = result[0]
        assert night_start == time(8, 0, 0)

    def test_duration_caps_night_end(self):
        # Short recording of 30 min starting 5 min before lights-off
        result = calculate_nighttime_periods(self._date(), "19:55:00", "20:00:00", 30.0)
        assert len(result) == 1
        _, night_end = result[0]
        # night_end must not exceed recording end (19:55 + 30 min = 20:25)
        assert night_end <= time(20, 25, 0)


class TestFindOffsetForPreviousTime:
    def _make_df(self, datetimes):
        return pd.DataFrame({"Date Time": datetimes})

    def test_all_times_at_or_after_target_returns_none(self):
        df = self._make_df(["2023-06-15 20:00:00", "2023-06-15 21:00:00"])
        offset, prev = find_offset_for_previous_time(df, "20:00:00")
        assert offset is None and prev is None

    def test_finds_last_row_before_target(self):
        df = self._make_df(["2023-06-15 18:00:00", "2023-06-15 19:00:00"])
        offset, prev = find_offset_for_previous_time(df, "20:00:00")
        assert offset is not None
        assert prev == "19:00:00"

    def test_offset_is_positive_minutes(self):
        df = self._make_df(["2023-06-15 19:00:00"])
        offset, _ = find_offset_for_previous_time(df, "20:00:00")
        assert offset == pytest.approx(60.0)


class TestResolveSheetName:
    def test_exact_match_returns_name(self):
        assert _resolve_sheet_name(["Sheet1", "Sheet2"], "Sheet1") == "Sheet1"

    def test_case_insensitive_match(self):
        assert _resolve_sheet_name(["TEMP", "ACT"], "temp") == "TEMP"

    def test_no_match_raises_value_error(self):
        with pytest.raises(ValueError, match="not found"):
            _resolve_sheet_name(["Sheet1"], "Missing")

    def test_case_insensitive_preserves_original_casing(self):
        result = _resolve_sheet_name(["MixedCase"], "mixedcase")
        assert result == "MixedCase"


class TestExtractAndTrimData:
    def _make_df(self):
        return pd.DataFrame(
            {
                "Date Time": pd.to_datetime(
                    ["2023-06-15 08:00:00", "2023-06-15 08:01:00", "2023-06-15 08:02:00"]
                ),
                "Data": [1.0, 2.0, 3.0],
            }
        )

    def test_none_previous_time_raises(self):
        with pytest.raises(ValueError):
            extract_and_trim_data(self._make_df(), None, 0.0, 5.0, 60.0)

    def test_empty_previous_time_raises(self):
        with pytest.raises(ValueError):
            extract_and_trim_data(self._make_df(), "", 0.0, 5.0, 60.0)

    def test_none_offset_raises(self):
        with pytest.raises(ValueError):
            extract_and_trim_data(self._make_df(), "08:00:00", None, 5.0, 60.0)

    def test_no_matching_rows_raises(self):
        df = self._make_df()
        with pytest.raises(ValueError, match="alignment time"):
            extract_and_trim_data(df, "09:00:00", 0.0, 5.0, 60.0)

    def test_valid_extraction_builds_time_column(self):
        df = self._make_df()
        result = extract_and_trim_data(df, "08:00:00", 0.0, 2.0, 60.0)
        assert "Time (min)" in result.columns


class TestExtractDataWithBuffer:
    def _make_df_with_datetime(self, datetimes, data):
        return pd.DataFrame(
            {"Date Time": pd.to_datetime(datetimes), "Data": data}
        )

    def test_empty_dataframe_returns_copy(self):
        df = pd.DataFrame(columns=["Date Time", "Data"])
        result = extract_data_with_buffer(df, 0.0, 60.0)
        assert result.empty

    def test_offset_column_used_when_present(self):
        df = pd.DataFrame(
            {
                "Date Time": pd.to_datetime(["2023-06-15 08:00:00", "2023-06-15 08:01:00"]),
                "Data": [1.0, 2.0],
                "Offset": pd.to_timedelta(["5min", "4min"]),
            }
        )
        result = extract_data_with_buffer(df, 99.0, 60.0)
        assert "Time (min)" in result.columns
        # start_offset = 5 minutes → first Time (min) = 0 - 5 = -5
        assert result["Time (min)"].iloc[0] == pytest.approx(-5.0)

    def test_no_offset_column_uses_argument(self):
        df = self._make_df_with_datetime(
            ["2023-06-15 08:00:00", "2023-06-15 08:01:00"], [10.0, 20.0]
        )
        result = extract_data_with_buffer(df, 0.0, 60.0)
        assert "Time (min)" in result.columns
        assert result["Time (min)"].iloc[0] == pytest.approx(0.0)

    def test_previous_time_with_no_duration_slices_from_match(self):
        df = self._make_df_with_datetime(
            ["2023-06-15 08:00:00", "2023-06-15 08:01:00", "2023-06-15 08:02:00"],
            [1.0, 2.0, 3.0],
        )
        result = extract_data_with_buffer(df, 0.0, 60.0, previous_time="08:01:00")
        assert "Time (min)" in result.columns


class TestUpsampleTelemetryData:
    def _make_df(self, col_name):
        times = pd.date_range("2023-06-15 08:00:00", periods=3, freq="1min")
        return pd.DataFrame({col_name: times, "Data": [1.0, 2.0, 3.0]})

    def test_date_time_column_accepted(self):
        df = self._make_df("Date Time")
        result = upsample_telemetry_data(df)
        assert "Date Time" in result.columns
        assert len(result) > 3  # upsampled to 100 ms

    def test_datetime_column_accepted_directly(self):
        # Has 'DateTime' not 'Date Time' — exercises the else branch at line 552
        df = self._make_df("DateTime")
        df["Data"] = [1.0, 2.0, 3.0]
        result = upsample_telemetry_data(df)
        assert len(result) > 3

    def test_missing_date_columns_raises(self):
        df = pd.DataFrame({"Other": [1, 2], "Data": [1.0, 2.0]})
        with pytest.raises(ValueError, match="Date Time"):
            upsample_telemetry_data(df)
