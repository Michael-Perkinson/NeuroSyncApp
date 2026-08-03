import re
from datetime import time

import pandas as pd

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


def convert_time(value: float, from_unit: str, to_unit: str = "minutes") -> float:
    """Convert a time value from from_unit to to_unit."""
    if from_unit not in CONVERSION_FACTORS or to_unit not in CONVERSION_FACTORS:
        raise ValueError(
            "Unsupported time unit. Supported units are: minutes, seconds, hours.")
    return value * CONVERSION_FACTORS[from_unit] / CONVERSION_FACTORS[to_unit]


def get_time_label(unit: str) -> str:
    """Return the display label for a given time unit."""
    return TIME_LABELS.get(unit, "Time (min)")


def time_to_seconds(time_input: str | time) -> int:
    """Convert a time input to seconds; raises ValueError for an unsupported input type."""
    if isinstance(time_input, str):
        h, m, s = map(int, time_input.split(':'))
        return h * 3600 + m * 60 + s
    elif isinstance(time_input, time):
        return time_input.hour * 3600 + time_input.minute * 60 + time_input.second
    else:
        # ValueError (not TypeError) is the documented/tested contract for this function.
        raise ValueError("Invalid input type for time_to_seconds function")  # noqa: TRY004


def check_and_convert_time_column(dataframe: pd.DataFrame, target_unit: str = "minutes") -> pd.DataFrame:
    """Convert the DataFrame's first column to target_unit if it names a recognised time unit."""
    first_column_title: str = dataframe.columns[0].lower()

    for unit, unit_factor in CONVERSION_FACTORS.items():
        # Match unit in column name
        pattern = re.compile(r'\b' + re.escape(unit) + r's?\b', re.IGNORECASE)
        if pattern.search(first_column_title):
            factor: float = unit_factor / CONVERSION_FACTORS[target_unit]
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
        mode_result = diffs.mode()
        if len(mode_result) == 0:
            return False
        mode_diff = mode_result[0]
        tolerance = mode_diff * 0.05
        consistent_diffs_count = sum(abs(diffs - mode_diff) < tolerance)
        return consistent_diffs_count / min(subset_size, len(diffs)) >= tolerance_ratio
    return False
