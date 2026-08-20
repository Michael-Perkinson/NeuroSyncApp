"""Compatibility facade for behaviour parsing and signal extraction.

New code may import the focused input-parsing and window-extraction modules
directly.  Existing imports from this historical module remain supported.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from src.processing.behaviour_input_parser import (
    DEFAULT_BEHAVIOUR_COLUMN_CANDIDATES,
    _normalise_column_mapping,
    build_params_from_df,
    check_total_time_divisible,
    find_out_of_range_behaviour_times,
    get_behaviour_name,
    get_behaviour_settings,
    get_behaviour_type,
    get_start_end_times,
    process_behaviour_rows,
    read_behaviour_csv,
    retrieve_static_params,
    update_behaviour_durations,
)
from src.processing.behaviour_window_extractor import (
    BOUNDARY_TOLERANCE_MIN,
    TIME_AXIS_DECIMALS,
    _find_window_positions,
    _prepare_signal_and_time_columns,
    extract_behaviour_results,
    extract_data_slice,
    extract_data_slice_with_time,
)


def create_extraction_folder(file_path: str) -> str:
    """Create the ``<stem>_NeuroBehaviorSync`` output folder."""
    path = Path(file_path)
    folder = path.parent / (path.stem + "_NeuroBehaviorSync")
    folder.mkdir(parents=True, exist_ok=True)
    return str(folder)


def truncate_sheet_title(title: str, max_length: int = 31) -> str:
    """Truncate *title* to *max_length* characters for an Excel sheet name."""
    words = title.split()
    if len(title) > max_length:
        longest = max(words, key=len)
        if len(longest) > 3:
            words[words.index(longest)] = longest[:3] + "..."

    result = re.sub(r"\s+", " ", " ".join(words).strip())
    if len(result) > max_length:
        result = result[:max_length].strip()
    return result


__all__ = [
    "BOUNDARY_TOLERANCE_MIN",
    "DEFAULT_BEHAVIOUR_COLUMN_CANDIDATES",
    "TIME_AXIS_DECIMALS",
    "Path",
    "_find_window_positions",
    "_normalise_column_mapping",
    "_prepare_signal_and_time_columns",
    "build_params_from_df",
    "check_total_time_divisible",
    "create_extraction_folder",
    "extract_behaviour_results",
    "extract_data_slice",
    "extract_data_slice_with_time",
    "find_out_of_range_behaviour_times",
    "get_behaviour_name",
    "get_behaviour_settings",
    "get_behaviour_type",
    "get_start_end_times",
    "np",
    "pd",
    "process_behaviour_rows",
    "re",
    "read_behaviour_csv",
    "retrieve_static_params",
    "truncate_sheet_title",
    "update_behaviour_durations",
]
