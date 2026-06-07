"""Compatibility wrapper around the canonical time conversion helpers."""

from __future__ import annotations

import pandas as pd

from src.math_ops.time_converters import check_and_convert_time_column as _convert


def check_and_convert_time_column(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Convert the first time column to minutes using the shared converter."""
    return _convert(dataframe, target_unit="minutes")




