from src.math_ops.time_converters import check_and_convert_time_column, is_time_data
from src.processing.data_utils import get_column_titles
from typing import Optional
import pandas as pd
import re
import os

PREFERRED_SIGNAL_COLUMNS = ("dfof_465", "dfof_470", "490df/f")


def _normalise_column_name(column) -> str:
    return str(column).strip().lower()


def select_preferred_signal_column(dataframe: pd.DataFrame):
    """Return the best default signal column for plotting."""
    if len(dataframe.columns) < 2:
        raise ValueError("Loaded data must contain at least two columns.")

    normalised_columns = {
        _normalise_column_name(column): column for column in dataframe.columns
    }
    for preferred_column in PREFERRED_SIGNAL_COLUMNS:
        if preferred_column in normalised_columns:
            return normalised_columns[preferred_column]

    return dataframe.columns[1]


def load_data_file(file_path: str) -> pd.DataFrame:
    """
    Loads a CSV or Excel file into a DataFrame.

    Parameters:
    - file_path (str): The path to the file.

    Returns:
    - pd.DataFrame: The loaded data.
    """
    if file_path.endswith('.csv'):
        return _load_csv(file_path)
    elif file_path.endswith('.xlsx'):
        return _load_excel(file_path)
    else:
        raise ValueError(
            "Unsupported file type. Only CSV and Excel are supported.")


def _load_csv(file_path: str) -> pd.DataFrame:
    """
    Loads a CSV file while handling cases where the first row might contain column headers.

    Parameters:
    - file_path (str): The path to the CSV file.

    Returns:
    - pd.DataFrame: The loaded data.
    """
    with open(file_path, 'r') as file:
        column_titles = next(file).strip().split(',')
        for i, line in enumerate(file, start=1):
            first_value = line.split(',')[0]
            if first_value.replace('.', '', 1).isdigit():
                return pd.read_csv(file_path, skiprows=i, header=None, names=column_titles)

    return pd.read_csv(file_path)  # If no numeric row found, read normally


def _load_excel(file_path: str) -> pd.DataFrame:
    """
    Loads an Excel file while handling cases where the first row might contain column headers.

    Parameters:
    - file_path (str): The path to the Excel file.

    Returns:
    - pd.DataFrame: The loaded data.
    """
    column_titles = pd.read_excel(file_path, nrows=1).columns.tolist()

    for i in range(5):  # Check the first 5 rows
        try:
            temp_df = pd.read_excel(file_path, nrows=1, skiprows=i)
            if str(temp_df.columns[0]).replace('.', '', 1).isdigit():
                return pd.read_excel(file_path, skiprows=i, header=None, names=column_titles)
        except Exception:
            continue

    return pd.read_excel(file_path)  # Default load


def process_loaded_data(dataframe):
    """
    Handles column selection and checks if data is time-based.
    """
    dataframe = check_and_convert_time_column(dataframe, target_unit="minutes")
    column_titles = get_column_titles(dataframe)

    selected_column = select_preferred_signal_column(dataframe)

    is_time_based = is_time_data(dataframe)

    return {
        "dataframe": dataframe,
        "column_titles": column_titles,
        "selected_column": selected_column,
        "is_time_based": is_time_based
    }
