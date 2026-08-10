"""Parse behaviour CSV schemas and build extraction parameters.

All functions in this module operate on plain Python values or pandas
objects.  They intentionally contain no UI-framework dependencies.
"""

from __future__ import annotations

import pandas as pd

DEFAULT_BEHAVIOUR_COLUMN_CANDIDATES = {
    "Behaviours/events": (
        "behaviour",
        "behavior",
        "behaviours",
        "behaviors",
        "event",
        "events",
    ),
    "Start Time": ("start", "start time", "onset", "onset time"),
    "End Time": ("end", "end time", "offset", "offset time"),
}


def _normalise_column_mapping(column_names: dict, available_columns: list[str]) -> dict:
    """Fill blank behaviour-column mappings from common CSV headers."""
    normalised = {
        key: str(value or "").strip().lower()
        for key, value in column_names.items()
    }
    available = set(available_columns)

    for logical_name, candidates in DEFAULT_BEHAVIOUR_COLUMN_CANDIDATES.items():
        mapped_name = normalised.get(logical_name, "")
        if mapped_name in available:
            continue
        for candidate in candidates:
            if candidate in available:
                normalised[logical_name] = candidate
                break

    return normalised


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
        Mapping of logical name -> actual header (e.g.
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
    df.columns = [str(c).strip().lower() for c in df.columns]
    column_names = _normalise_column_mapping(column_names, list(df.columns))

    required = [
        column_names["Behaviours/events"],
        column_names["Start Time"],
        column_names["End Time"],
    ]
    for col in required:
        if not col or col not in df.columns:
            available = [c for c in df.columns if not c.startswith("unnamed")]
            raise ValueError(
                "Required column mapping "
                f"'{col or '<blank>'}' is not present in the CSV file.\n\n"
                f"Available columns:\n  - " + "\n  - ".join(available)
            )

    if time_unit == "minutes":
        df[column_names["Start Time"]] = df[column_names["Start Time"]] * 60
        df[column_names["End Time"]] = df[column_names["End Time"]] * 60

    df = df.dropna(subset=[column_names["Behaviours/events"]])
    return df, column_names


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


def update_behaviour_durations(
    behaviour_durations: dict,
    behaviour_name: str,
    start_time: float,
    end_time: float,
) -> dict:
    """Append start/end times to the per-behaviour duration dict and return it."""
    if behaviour_name not in behaviour_durations:
        behaviour_durations[behaviour_name] = {"start_times": [], "end_times": []}
    behaviour_durations[behaviour_name]["start_times"].append(start_time)
    behaviour_durations[behaviour_name]["end_times"].append(end_time)
    return behaviour_durations


def get_behaviour_settings(
    behaviour_name: str,
    behaviour_settings: dict,
    default_pre: str,
    default_post: str,
    default_bin: str,
) -> tuple[str, str, str]:
    """Look up per-behaviour pre/post/bin settings with defaults."""
    if behaviour_name in behaviour_settings:
        settings = behaviour_settings[behaviour_name]
        pre = settings.get("pre_behaviour_time", "")
        post = settings.get("post_behaviour_time", "")
        bin_ = settings.get("bin_size", "")
        if all(str(value) != "" for value in [pre, post, bin_]):
            return str(pre), str(post), str(bin_)
    return default_pre, default_post, default_bin


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
    """Process every row of a behaviour DataFrame into table rows."""
    behaviour_names: set[str] = set()
    table_data: list[tuple] = []
    behaviour_durations: dict = {}

    for row_tuple in df.itertuples(index=False):
        row = pd.Series(dict(zip(df.columns, row_tuple)))
        behaviour_name = get_behaviour_name(row, column_names).capitalize()
        start_time, end_time = get_start_end_times(
            row, column_names, synchronize_start_time
        )
        behaviour_durations = update_behaviour_durations(
            behaviour_durations, behaviour_name, start_time, end_time
        )
        pre, post, bin_ = get_behaviour_settings(
            behaviour_name,
            behaviour_settings,
            default_pre,
            default_post,
            default_bin,
        )
        table_data.append(
            (
                file_path,
                selected_column,
                behaviour_name,
                get_behaviour_type(end_time),
                pre,
                post,
                bin_,
                start_time,
                end_time,
            )
        )
        behaviour_names.add(behaviour_name)

    return table_data, behaviour_names, behaviour_durations


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
) -> tuple[dict, set[str], set[str], set[str], set[str]]:
    """Build the extraction params dict from a table DataFrame."""
    df = df.copy()
    df["Start Time"] = df["Start Time"].astype(float)
    df = df[df["Start Time"] >= 0]

    params: dict = {}
    behaviours_to_export: set[str] = set()
    params_to_extract: list = []
    missing_pre: set[str] = set()
    missing_post: set[str] = set()
    not_divisible: set[str] = set()

    for row_tuple in df.itertuples(index=False):
        row = pd.Series(dict(zip(df.columns, row_tuple)))
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


def retrieve_static_params(
    params: dict, behaviour_name: str
) -> tuple[int, int, int]:
    """Return (pre_behaviour_time, post_behaviour_time, bin_size) as ints."""
    instances = params[behaviour_name]
    if not instances:
        raise ValueError(f"No instances recorded for behaviour {behaviour_name!r}")
    last_instance = instances[-1]
    pre = int(last_instance.get("pre_behaviour_time"))
    post = int(last_instance.get("post_behaviour_time"))
    bin_ = int(last_instance.get("bin_size"))
    return pre, post, bin_
