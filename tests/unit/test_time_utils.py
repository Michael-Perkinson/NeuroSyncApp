"""
Unit tests for src/processing/time_utils.py.

Note: This module duplicates some logic from src/math_ops/time_converters.py.
These tests cover the simpler version in time_utils. During refactoring,
this module should be removed and callers migrated to math_ops/time_converters.py.
"""
import pytest
import pandas as pd

from src.processing.time_utils import check_and_convert_time_column


class TestCheckAndConvertTimeColumn:
    def test_seconds_column_converted(self):
        df = pd.DataFrame({"Time (seconds)": [0, 60, 120], "val": [1, 2, 3]})
        result = check_and_convert_time_column(df.copy())
        assert result.iloc[1, 0] == pytest.approx(1.0)

    def test_column_renamed_to_time_min(self):
        df = pd.DataFrame({"Time (seconds)": [0, 60], "val": [1, 2]})
        result = check_and_convert_time_column(df.copy())
        assert result.columns[0] == "Time (min)"

    def test_minutes_column_stays_unchanged(self):
        df = pd.DataFrame({"Time (minutes)": [0.0, 1.0], "val": [1, 2]})
        result = check_and_convert_time_column(df.copy())
        assert result.iloc[1, 0] == pytest.approx(1.0)

    def test_min_abbreviation_detected(self):
        df = pd.DataFrame({"t_min": [0.0, 1.0], "val": [1, 2]})
        result = check_and_convert_time_column(df.copy())
        # 'min' matched — stays at same scale (factor=1)
        assert result.iloc[1, 0] == pytest.approx(1.0)

    def test_no_unit_returns_unchanged(self):
        df = pd.DataFrame({"column_a": [0.0, 1.0], "val": [1, 2]})
        result = check_and_convert_time_column(df.copy())
        assert result.iloc[1, 0] == pytest.approx(1.0)
