import os
import re

import pandas as pd


def extract_mouse_name(file_path: str) -> str | None:
    """Extract the mouse name (letters followed by numbers) from a file path, or None if not found."""
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    pattern = r"[A-Za-z]+\d+"
    matches = re.findall(pattern, base_name)

    if matches:
        return matches[0]

    return None


def get_column_titles(dataframe: pd.DataFrame) -> list[str]:
    """Returns a list of column titles from a DataFrame."""
    return dataframe.columns.tolist()
