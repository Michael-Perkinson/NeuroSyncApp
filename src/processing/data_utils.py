import re
import os
import pandas as pd
from typing import Optional, List

def extract_mouse_name(file_path: str) -> Optional[str]:
    """
    Extracts the mouse name from the given file path, looking for patterns of letters followed by numbers.

    Parameters:
    - file_path (str): The file path to extract the mouse name from.

    Returns:
    - Optional[str]: The extracted mouse name, or None if not found.
    """
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    pattern = r"[A-Za-z]+\d+"
    matches = re.findall(pattern, base_name)

    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        num1 = int(re.search(r"\d+", matches[0]).group())
        num2 = int(re.search(r"\d+", matches[1]).group())
        return matches[0] if num1 <= num2 else matches[1]

    return None  # Return None if no match is found


def get_column_titles(dataframe: pd.DataFrame) -> List[str]:
    """Returns a list of column titles from a DataFrame."""
    return dataframe.columns.tolist()
