"""
Unit tests for src/math_ops/time_converters.py.

NOTE — known bug in current code:
  CONVERSION_FACTORS = {"minutes": 1, "seconds": 60, "hours": 1/60}
  with formula: value * CF[from_unit] / CF[to_unit]

  This gives the wrong direction for convert_time, e.g.:
    convert_time(60, "seconds", "minutes") → 3600  (should be 1.0)
  The tests below document the CORRECT expected behavior.
  They will fail until the refactor fixes the conversion logic.
  The equivalent function in processing/time_utils.py is correct.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import time

from src.math_ops.time_converters import (
    convert_time,
    get_time_label,
    time_to_seconds,
    check_and_convert_time_column,
    is_time_data,
)


class TestConvertTime:
    def test_minutes_to_seconds(self):
        assert convert_time(1.0, "minutes", "seconds") == pytest.approx(60.0)

    def test_seconds_to_minutes(self):
        assert convert_time(60.0, "seconds", "minutes") == pytest.approx(1.0)

    def test_hours_to_minutes(self):
        assert convert_time(1.0, "hours", "minutes") == pytest.approx(60.0)

    def test_minutes_to_hours(self):
        assert convert_time(60.0, "minutes", "hours") == pytest.approx(1.0)

    def test_same_unit_returns_same_value(self):
        assert convert_time(5.0, "minutes", "minutes") == pytest.approx(5.0)

    def test_unsupported_from_unit_raises(self):
        with pytest.raises(ValueError, match="Unsupported"):
            convert_time(1.0, "milliseconds", "minutes")

    def test_unsupported_to_unit_raises(self):
        with pytest.raises(ValueError, match="Unsupported"):
            convert_time(1.0, "minutes", "days")

    def test_zero_value(self):
        assert convert_time(0, "seconds", "minutes") == pytest.approx(0.0)


class TestGetTimeLabel:
    def test_minutes_label(self):
        assert get_time_label("minutes") == "Time (min)"

    def test_seconds_label(self):
        assert get_time_label("seconds") == "Time (s)"

    def test_hours_label(self):
        assert get_time_label("hours") == "Time (h)"

    def test_unknown_unit_defaults_to_minutes(self):
        assert get_time_label("furlongs") == "Time (min)"


class TestTimeToSeconds:
    def test_string_hms(self):
        assert time_to_seconds("0:20:01") == 1201

    def test_string_all_zeros(self):
        assert time_to_seconds("0:00:00") == 0

    def test_string_with_hours(self):
        assert time_to_seconds("1:30:00") == 5400

    def test_datetime_time_object(self):
        t = time(0, 20, 1)
        assert time_to_seconds(t) == 1201

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError, match="Invalid input type"):
            time_to_seconds(1201)


class TestCheckAndConvertTimeColumn:
    def test_seconds_column_converted_to_minutes(self):
        df = pd.DataFrame({"Time (seconds)": [0, 60, 120], "val": [1, 2, 3]})
        result = check_and_convert_time_column(df.copy(), target_unit="minutes")
        assert result.iloc[1, 0] == pytest.approx(1.0)

    def test_column_renamed_after_conversion(self):
        df = pd.DataFrame({"Time (seconds)": [0, 60], "val": [1, 2]})
        result = check_and_convert_time_column(df.copy(), target_unit="minutes")
        assert result.columns[0] == "Time (min)"

    def test_minutes_column_unchanged(self):
        df = pd.DataFrame({"Time (minutes)": [0.0, 1.0, 2.0], "val": [1, 2, 3]})
        result = check_and_convert_time_column(df.copy(), target_unit="minutes")
        assert result.iloc[1, 0] == pytest.approx(1.0)

    def test_no_time_unit_returns_unchanged_values(self):
        df = pd.DataFrame({"column_a": [0.0, 1.0], "val": [1, 2]})
        original_val = df.iloc[0, 0]
        result = check_and_convert_time_column(df.copy(), target_unit="minutes")
        assert result.iloc[0, 0] == original_val


class TestIsTimeData:
    def test_regular_time_series_detected(self):
        df = pd.DataFrame({"time": np.arange(0, 100, 0.1), "val": 1})
        assert is_time_data(df) is True

    def test_irregular_data_not_detected(self):
        rng = np.random.default_rng(42)
        df = pd.DataFrame({"col": rng.uniform(0, 1000, 100), "val": 1})
        assert is_time_data(df) is False

    def test_non_numeric_column_returns_false(self):
        df = pd.DataFrame({"col": ["a", "b", "c"], "val": [1, 2, 3]})
        assert is_time_data(df) is False
