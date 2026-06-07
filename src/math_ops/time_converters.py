import re
from datetime import time
import pandas as pd
from typing import Union


# Centralized Conversion Factors and Labels
# Each value = how many minutes equal 1 of that unit.
# e.g. 1 second = 1/60 minute, 1 hour = 60 minutes.
CONVERSION_FACTORS: dict[str, float] = {
    "minutes": 1,
    "seconds": 1 / 60,
    "hours": 60,
}

TIME_LABELS: dict[str, str] = {
    "minutes": "Time (min)",
    "seconds": "Time (s)",
    "hours": "Time (h)",
}


def convert_time(value: Union[float, int], from_unit: str, to_unit: str = "minutes") -> float:
    """
    Convert time between units.

    Parameters:
    - value (float | int): The time value to convert.
    - from_unit (str): The current unit of the time value.
    - to_unit (str): The target unit to convert to.

    Returns:
    - float: The converted time value.
    """
    if from_unit not in CONVERSION_FACTORS or to_unit not in CONVERSION_FACTORS:
        raise ValueError(
            "Unsupported time unit. Supported units are: minutes, seconds, hours.")
    return value * CONVERSION_FACTORS[from_unit] / CONVERSION_FACTORS[to_unit]


def get_time_label(unit: str) -> str:
    """
    Get the label for a given time unit.

    Parameters:
    - unit (str): The time unit.

    Returns:
    - str: The corresponding label.
    """
    return TIME_LABELS.get(unit, "Time (min)")


def time_to_seconds(time_input: Union[str, time]) -> int:
    """
    Convert a time input to seconds.

    Parameters:
    - time_input (str | datetime.time): The time input to convert.

    Returns:
    - int: The equivalent time in seconds.

    Raises:
    - ValueError: If the input type is invalid.
    """
    if isinstance(time_input, str):
        h, m, s = map(int, time_input.split(':'))
        return h * 3600 + m * 60 + s
    elif isinstance(time_input, time):
        return time_input.hour * 3600 + time_input.minute * 60 + time_input.second
    else:
        raise ValueError("Invalid input type for time_to_seconds function")


def check_and_convert_time_column(dataframe: pd.DataFrame, target_unit: str = "minutes") -> pd.DataFrame:
    """
    Checks the first column of the given DataFrame for time units and converts them to the target unit if found.

    Parameters:
    - dataframe (pd.DataFrame): The pandas DataFrame.
    - target_unit (str): The target unit for conversion (default is "minutes").

    Returns:
    - pd.DataFrame: The modified DataFrame with time converted.
    """
    first_column_title: str = dataframe.columns[0].lower()

    for unit in CONVERSION_FACTORS.keys():
        # Match unit in column name
        pattern = re.compile(r'\b' + re.escape(unit) + r's?\b', re.IGNORECASE)
        if pattern.search(first_column_title):
            factor: float = CONVERSION_FACTORS[unit] / \
                CONVERSION_FACTORS[target_unit]
            first_column_name = dataframe.columns[0]
            dataframe[first_column_name] = dataframe.iloc[:, 0].astype(float) * factor
            dataframe.columns = [get_time_label(
                target_unit)] + dataframe.columns.tolist()[1:]
            return dataframe

    return dataframe


def is_time_data(dataframe, subset_size=20, tolerance_ratio=0.9):
    """Checks if the first column represents consistent time data."""
    first_column = dataframe.iloc[:, 0]
    if pd.api.types.is_numeric_dtype(first_column):
        diffs = first_column.diff().dropna()
        mode_diff = diffs.mode()[0]
        tolerance = mode_diff * 0.05
        consistent_diffs_count = sum(abs(diffs - mode_diff) < tolerance)
        return consistent_diffs_count / min(subset_size, len(diffs)) >= tolerance_ratio
    return False
