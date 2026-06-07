"""
Pure parsing and filesystem helpers for photometry-behaviour alignment.

No UI framework dependencies — all inputs and outputs are plain Python
types, NumPy arrays, or pandas DataFrames. The UI layer (Tkinter /
PySide6) reads widget values *before* calling these functions.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Filesystem
# ---------------------------------------------------------------------------

def create_extraction_folder(file_path: str) -> str:
    """Create the output folder next to *file_path* and return its path.

    The folder is named ``<stem>_NeuroBehaviorSync``.
    """
    p = Path(file_path)
    folder = p.parent / (p.stem + "_NeuroBehaviorSync")
    folder.mkdir(parents=True, exist_ok=True)
    return str(folder)


# ---------------------------------------------------------------------------
# CSV reading
# ---------------------------------------------------------------------------

def read_behaviour_csv(
    file_path: str,
    column_names: dict,
    time_unit: str,
) -> tuple[pd.DataFrame, dict]:
    """Read and normalise a behaviour CSV file.

    Parameters
    ----------
    file_path:
        Path to the CSV file.
    column_names:
        Mapping of logical name → actual header (e.g.
        ``{"Behaviours/events": "behaviour", "Start Time": "start", ...}``).
        Values are lowercased inside this function.
    time_unit:
        ``"minutes"`` or ``"seconds"``.  If ``"minutes"``, start/end columns
        are multiplied by 60 to convert to seconds.

    Returns
    -------
    df : pd.DataFrame
        Cleaned DataFrame with NaN behaviour rows dropped.
    column_names : dict
        Lowercased column-name mapping (same keys, lower-case values).

    Raises
    ------
    ValueError
        If a required column is missing from the CSV.
    """
    df = pd.read_csv(file_path)
    df.columns = [c.lower() for c in df.columns]
    column_names = {k: v.lower() for k, v in column_names.items()}

    if time_unit == "minutes":
        df[column_names["Start Time"]] = df[column_names["Start Time"]] * 60
        df[column_names["End Time"]] = df[column_names["End Time"]] * 60

    required = [
        column_names["Behaviours/events"],
        column_names["Start Time"],
        column_names["End Time"],
    ]
    for col in required:
        if col not in df.columns:
            available = [c for c in df.columns if not c.startswith("unnamed")]
            raise ValueError(
                f"Required column '{col}' is not present in the CSV file.\n\n"
                f"Available columns:\n  - " + "\n  - ".join(available)
            )

    df = df.dropna(subset=[column_names["Behaviours/events"]])
    return df, column_names


# ---------------------------------------------------------------------------
# Row-level helpers
# ---------------------------------------------------------------------------

def get_behaviour_name(row: pd.Series, column_names: dict) -> str:
    """Extract and clean the behaviour name from a DataFrame row."""
    raw = row[column_names["Behaviours/events"]]
    if isinstance(raw, float) and raw.is_integer():
        return str(int(raw)).strip()
    return str(raw).strip()


def get_start_end_times(
    row: pd.Series,
    column_names: dict,
    synchronize_start_time: float,
) -> tuple[float, float]:
    """Return (start_time, end_time) with synchronisation offset applied."""
    start = row[column_names["Start Time"]] + synchronize_start_time
    end = row[column_names["End Time"]] + synchronize_start_time
    return float(start), float(end)


def get_behaviour_type(end_time) -> str:
    """Return ``"Point"`` if *end_time* is NaN/None, else ``"Continuous"``."""
    if pd.isnull(end_time):
        return "Point"
    return "Continuous"


def update_behavior_durations(
    behavior_durations: dict,
    behaviour_name: str,
    start_time: float,
    end_time: float,
) -> dict:
    """Append start/end times to the per-behaviour duration dict and return it."""
    if behaviour_name not in behavior_durations:
        behavior_durations[behaviour_name] = {"start_times": [], "end_times": []}
    behavior_durations[behaviour_name]["start_times"].append(start_time)
    behavior_durations[behaviour_name]["end_times"].append(end_time)
    return behavior_durations


def get_behaviour_settings(
    behaviour_name: str,
    behaviour_settings: dict,
    default_pre: str,
    default_post: str,
    default_bin: str,
) -> tuple[str, str, str]:
    """Look up per-behaviour pre/post/bin settings with defaults.

    Returns
    -------
    pre_behaviour_time, post_behaviour_time, bin_size
    """
    if behaviour_name in behaviour_settings:
        s = behaviour_settings[behaviour_name]
        pre = s.get("pre_behaviour_time", "")
        post = s.get("post_behaviour_time", "")
        bin_ = s.get("bin_size", "")
        if all(str(v) != "" for v in [pre, post, bin_]):
            return str(pre), str(post), str(bin_)
    return default_pre, default_post, default_bin


# ---------------------------------------------------------------------------
# Process rows
# ---------------------------------------------------------------------------

def process_behaviour_rows(
    df: pd.DataFrame,
    column_names: dict,
    behaviour_settings: dict,
    synchronize_start_time: float,
    file_path: str,
    selected_column: str,
    default_pre: str = "10",
    default_post: str = "10",
    default_bin: str = "1",
) -> tuple[list[tuple], set[str], dict]:
    """Process every row of a behaviour DataFrame into table rows.

    Parameters
    ----------
    df:
        Cleaned behaviour DataFrame (NaN rows already dropped).
    column_names:
        Lowercased column-name mapping.
    behaviour_settings:
        Per-behaviour settings loaded from JSON (may be empty dict).
    synchronize_start_time:
        Offset added to all start/end times.
    file_path:
        Photometry file path — stored in each table row.
    selected_column:
        Signal column name — stored in each table row.
    default_pre, default_post, default_bin:
        Fallback timing strings when no saved settings exist.

    Returns
    -------
    table_data : list[tuple]
        One 9-tuple per row: ``(file_path, selected_column, behaviour_name,
        behaviour_type, pre, post, bin, start_time, end_time)``.
    behaviour_names : set[str]
        All unique behaviour names encountered.
    behavior_durations : dict
        ``{behaviour_name: {"start_times": [...], "end_times": [...]}}``
    """
    behaviour_names: set[str] = set()
    table_data: list[tuple] = []
    behavior_durations: dict = {}

    for _, row in df.iterrows():
        behaviour_name = get_behaviour_name(row, column_names).capitalize()
        start_time, end_time = get_start_end_times(row, column_names, synchronize_start_time)
        behavior_durations = update_behavior_durations(
            behavior_durations, behaviour_name, start_time, end_time
        )
        pre, post, bin_ = get_behaviour_settings(
            behaviour_name, behaviour_settings, default_pre, default_post, default_bin
        )
        table_data.append((
            file_path,
            selected_column,
            behaviour_name,
            get_behaviour_type(end_time),
            pre,
            post,
            bin_,
            start_time,
            end_time,
        ))
        behaviour_names.add(behaviour_name)

    return table_data, behaviour_names, behavior_durations


# ---------------------------------------------------------------------------
# Parameter building / validation
# ---------------------------------------------------------------------------

def check_total_time_divisible(
    pre_behaviour_time: float,
    post_behaviour_time: float,
    bin_size,
) -> bool:
    """Return True if ``(pre + post)`` is exactly divisible by *bin_size*."""
    total_time = int(pre_behaviour_time + post_behaviour_time)
    return total_time % int(bin_size) == 0


def build_params_from_df(
    df: pd.DataFrame,
    behaviour_display_status: dict,
) -> tuple[dict, set[str], set[str], set[str]]:
    """Build the extraction params dict from a table DataFrame.

    This is the pure core of ``check_and_prepare_parameters``.  It does
    *not* call any UI code; the caller is responsible for showing errors.

    Parameters
    ----------
    df:
        Table DataFrame with columns ``Behaviour Name``, ``Pre Behaviour
        Time``, ``Post Behaviour Time``, ``Bin Size``, ``Start Time``.
    behaviour_display_status:
        ``{behaviour_name: int}`` — 1 = enabled, 0/missing = skip.
        The caller resolves any GUI-bound state before passing this in.

    Returns
    -------
    params : dict
        Keyed by behaviour name; each value is a list of instance dicts.
        Also contains ``"behaviours_to_export"`` (set) and
        ``"params_to_extract"`` (empty list).
    behaviours_to_export : set[str]
    missing_pre : set[str]
        Behaviour names with empty pre-behaviour time.
    missing_post : set[str]
        Behaviour names with empty post-behaviour time.
    not_divisible : set[str]
        Behaviour names whose total time is not divisible by bin size.
    """
    df = df.copy()
    df["Start Time"] = df["Start Time"].astype(float)
    df = df[df["Start Time"] >= 0]

    params: dict = {}
    behaviours_to_export: set[str] = set()
    params_to_extract: list = []
    missing_pre: set[str] = set()
    missing_post: set[str] = set()
    not_divisible: set[str] = set()

    for _, row in df.iterrows():
        behaviour_name = row["Behaviour Name"]
        status = behaviour_display_status.get(behaviour_name, 0)
        if status != 1:
            continue

        pre = row["Pre Behaviour Time"]
        post = row["Post Behaviour Time"]
        bin_ = row["Bin Size"]

        instance = {
            "pre_behaviour_time": pre,
            "post_behaviour_time": post,
            "bin_size": bin_,
            "behaviour_start_time": float(row["Start Time"]),
        }
        params.setdefault(behaviour_name, []).append(instance)

        if pre == "":
            missing_pre.add(behaviour_name)
        elif post == "":
            missing_post.add(behaviour_name)
        elif not check_total_time_divisible(float(pre), float(post), bin_):
            not_divisible.add(behaviour_name)
        else:
            behaviours_to_export.add(behaviour_name)

    params["behaviours_to_export"] = behaviours_to_export
    params["params_to_extract"] = params_to_extract
    return params, behaviours_to_export, missing_pre, missing_post, not_divisible


# ---------------------------------------------------------------------------
# Signal extraction
# ---------------------------------------------------------------------------

def extract_data_slice(
    df: pd.DataFrame,
    start_time_min: float,
    behaviour_time_min: float,
    end_time_min: float,
    column: str,
    z_scored_data=None,
) -> tuple[pd.Series, pd.Series]:
    """Slice signal data around a behaviour event.

    Parameters
    ----------
    df:
        Full recording DataFrame; first column is the time axis (minutes),
        unless *column* is ``"baselined_z_score"`` in which case
        ``df["z_scored_time"]`` is used.
    start_time_min, behaviour_time_min, end_time_min:
        Window boundaries in minutes.
    column:
        Column to slice from *df*.
    z_scored_data:
        If *column* is ``"baselined_z_score"``, pass the z-scored series so
        the function can write it into the temporary column before slicing.

    Returns
    -------
    start_data : pd.Series
        Signal from *start_time_min* up to (but not including) *behaviour_time_min*.
    end_data : pd.Series
        Signal from *behaviour_time_min* to *end_time_min* (inclusive).
    """
    if column == "baselined_z_score" and z_scored_data is not None:
        df = df.copy()
        df["baselined_z_score"] = z_scored_data
        time_col = df["z_scored_time"]
    else:
        time_col = df.iloc[:, 0]

    start_idx = (time_col - start_time_min).abs().idxmin()
    beh_idx = (time_col - behaviour_time_min).abs().idxmin()
    end_idx = (time_col - end_time_min).abs().idxmin()

    start_data = df.loc[start_idx : beh_idx - 1, column].reset_index(drop=True)
    end_data = df.loc[beh_idx:end_idx, column].reset_index(drop=True)
    return start_data, end_data


# ---------------------------------------------------------------------------
# Bulk behaviour extraction
# ---------------------------------------------------------------------------

def extract_behaviour_results(
    behaviours_to_export: set,
    params: dict,
    df: pd.DataFrame,
    checkbox_state: bool,
    selected_column: str,
    z_scored_data=None,
) -> tuple[dict, dict]:
    """Extract signal slices for every instance of every exported behaviour.

    Parameters
    ----------
    behaviours_to_export:
        Set of behaviour names to process.
    params:
        Extraction-params dict built by :func:`build_params_from_df`.
    df:
        Full recording DataFrame.
    checkbox_state:
        If ``True``, slices the z-scored column.
    selected_column:
        Signal column used when *checkbox_state* is ``False``.
    z_scored_data:
        Pre-computed z-scored Series; required when *checkbox_state* is
        ``True``.

    Returns
    -------
    behaviours_results : dict
        ``{behaviour_name: [(start_data, end_data), ...]}``.
    time_ranges : dict
        ``{behaviour_name: pd.Series}`` — relative time axis for each
        behaviour window.
    """
    behaviours_results: dict = {}
    time_ranges: dict = {}

    for behaviour_name in behaviours_to_export:
        behaviour_instances = params[behaviour_name]
        for behaviour_instance in behaviour_instances:
            pre_behaviour_time  = float(behaviour_instance["pre_behaviour_time"])
            post_behaviour_time = float(behaviour_instance["post_behaviour_time"])
            behaviour_start_time = float(behaviour_instance["behaviour_start_time"])

            behaviours_results.setdefault(behaviour_name, [])

            if not pre_behaviour_time:
                continue

            start_time = behaviour_start_time - pre_behaviour_time
            end_time   = behaviour_start_time + post_behaviour_time

            start_time_min           = start_time           / 60
            end_time_min             = end_time             / 60
            behaviour_start_time_min = behaviour_start_time / 60

            num_samples = int((pre_behaviour_time + post_behaviour_time) * 10)
            step = (pre_behaviour_time + post_behaviour_time) / num_samples
            time_range = pd.Series(
                np.arange(-pre_behaviour_time, post_behaviour_time, step)
            )
            time_range[np.isclose(time_range, 0)] = 0
            time_ranges[behaviour_name] = time_range

            use_zscore = checkbox_state and z_scored_data is not None
            column = "baselined_z_score" if use_zscore else selected_column
            start_data, end_data = extract_data_slice(
                df,
                start_time_min,
                behaviour_start_time_min,
                end_time_min,
                column,
                z_scored_data if use_zscore else None,
            )
            behaviours_results[behaviour_name].append((start_data, end_data))

    return behaviours_results, time_ranges


# ---------------------------------------------------------------------------
# Static param retrieval
# ---------------------------------------------------------------------------

def retrieve_static_params(
    params: dict, behaviour_name: str
) -> tuple[int, int, int]:
    """Return (pre_behaviour_time, post_behaviour_time, bin_size) as ints.

    Uses the last instance in the list (matches original God class behaviour).
    """
    pre = post = bin_ = None
    for instance in params[behaviour_name]:
        pre = int(instance.get("pre_behaviour_time"))
        post = int(instance.get("post_behaviour_time"))
        bin_ = int(instance.get("bin_size"))
    return pre, post, bin_


# ---------------------------------------------------------------------------
# String helpers
# ---------------------------------------------------------------------------

def truncate_sheet_title(title: str, max_length: int = 31) -> str:
    """Truncate *title* to *max_length* characters for an Excel sheet name.

    Shortens the longest word to a 3-character prefix + ``"..."`` first;
    then hard-truncates if still too long.
    """
    words = title.split()
    if len(title) > max_length:
        longest = max(words, key=len)
        if len(longest) > 3:
            words[words.index(longest)] = longest[:3] + "..."

    result = re.sub(r"\s+", " ", " ".join(words).strip())
    if len(result) > max_length:
        result = result[:max_length].strip()
    return result
