"""
Integration tests for file_management/file_loader.py.

Verifies that loading example CSV and Excel files produces the expected
DataFrames — correct shape, column names, selected column, and time detection.
"""
import pytest
import pandas as pd
from pathlib import Path

from src.file_management.file_loader import load_data_file, process_loaded_data

DATA_DIR = Path(__file__).parent.parent.parent / "example_data"

PHOTOMETRY_CSV = DATA_DIR / "photometry_behaviour" / "example_Data ST5435.csv"
MENOPAUSE_CSV = DATA_DIR / "menopause_photometry" / "23-9-20 MP5 OVXd69_Data.csv"
TEMP_XLSX = DATA_DIR / "menopause_photometry" / "Temp 23-9-20.xlsx"
ACT_XLSX = DATA_DIR / "menopause_photometry" / "Act 23-9-20.xlsx"


class TestLoadDataFile:
    def test_load_photometry_csv_returns_dataframe(self):
        df = load_data_file(str(PHOTOMETRY_CSV))
        assert isinstance(df, pd.DataFrame)

    def test_load_photometry_csv_shape(self):
        df = load_data_file(str(PHOTOMETRY_CSV))
        assert df.shape[0] == 84091
        assert df.shape[1] == 9

    def test_load_photometry_csv_columns(self):
        df = load_data_file(str(PHOTOMETRY_CSV))
        assert "dFoF_465" in df.columns
        assert "405" in df.columns
        assert "465" in df.columns

    def test_load_menopause_csv_returns_dataframe(self):
        df = load_data_file(str(MENOPAUSE_CSV))
        assert isinstance(df, pd.DataFrame)
        assert df.shape[0] > 0

    def test_load_excel_returns_dataframe(self):
        df = load_data_file(str(TEMP_XLSX))
        assert isinstance(df, pd.DataFrame)
        assert df.shape[0] > 0

    def test_unsupported_extension_raises(self, tmp_path):
        bad_file = tmp_path / "data.txt"
        bad_file.write_text("a,b,c\n1,2,3")
        with pytest.raises(ValueError, match="Unsupported file type"):
            load_data_file(str(bad_file))


class TestProcessLoadedData:
    def test_returns_required_keys(self):
        df = load_data_file(str(PHOTOMETRY_CSV))
        result = process_loaded_data(df)
        assert "dataframe" in result
        assert "column_titles" in result
        assert "selected_column" in result
        assert "is_time_based" in result

    def test_photometry_csv_selects_dfof_465(self):
        df = load_data_file(str(PHOTOMETRY_CSV))
        result = process_loaded_data(df)
        assert result["selected_column"] == "dFoF_465"

    def test_photometry_csv_is_time_based(self):
        df = load_data_file(str(PHOTOMETRY_CSV))
        result = process_loaded_data(df)
        assert result["is_time_based"] is True

    def test_column_titles_is_list(self):
        df = load_data_file(str(PHOTOMETRY_CSV))
        result = process_loaded_data(df)
        assert isinstance(result["column_titles"], list)
        assert len(result["column_titles"]) == 9

    def test_dataframe_in_result_is_dataframe(self):
        df = load_data_file(str(PHOTOMETRY_CSV))
        result = process_loaded_data(df)
        assert isinstance(result["dataframe"], pd.DataFrame)
