"""
Unit tests for src/processing/data_utils.py.
"""
import pytest
import pandas as pd

from src.processing.data_utils import extract_mouse_name, get_column_titles


class TestExtractMouseName:
    """Tests against filenames drawn from actual example data."""

    def test_extracts_from_example_photometry_path(self):
        path = "example_data/photometry_behaviour/example_Data ST5435.csv"
        assert extract_mouse_name(path) == "ST5435"

    def test_extracts_from_menopause_path(self):
        path = "example_data/menopause_photometry/23-9-20 MP5 OVXd69_Data.csv"
        assert extract_mouse_name(path) == "MP5"

    def test_extracts_from_mp2_path(self):
        path = "23-12-4 MP2 OVXd144 ON_Data.csv"
        assert extract_mouse_name(path) == "MP2"

    def test_simple_mouse_id(self):
        assert extract_mouse_name("/data/Mouse42_recording.csv") == "Mouse42"

    def test_no_match_returns_none(self):
        assert extract_mouse_name("/data/12345_recording.csv") is None

    def test_works_with_just_filename(self):
        result = extract_mouse_name("MP5_data.csv")
        assert result == "MP5"


class TestGetColumnTitles:
    def test_returns_list_of_columns(self):
        df = pd.DataFrame({"time": [1, 2], "signal": [3, 4]})
        assert get_column_titles(df) == ["time", "signal"]

    def test_empty_dataframe_returns_empty_list(self):
        df = pd.DataFrame()
        assert get_column_titles(df) == []

    def test_preserves_column_order(self):
        df = pd.DataFrame(columns=["z", "a", "m"])
        assert get_column_titles(df) == ["z", "a", "m"]

    def test_returns_list_not_index(self):
        df = pd.DataFrame({"a": [1]})
        result = get_column_titles(df)
        assert isinstance(result, list)
