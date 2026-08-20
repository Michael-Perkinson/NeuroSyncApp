"""
Pure matplotlib plotting functions for photometry-behaviour graphs.

No UI framework dependencies â€” callers resolve all widget values before
passing them in.  Every function takes an ``ax`` (matplotlib Axes) or
``fig`` (Figure) plus explicit data/style parameters and returns only
plain Python / NumPy / pandas objects.

When migrating between GUI frameworks the only change needed in the UI
layer is the canvas/toolbar embedding; none of the functions in this
module change.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle
from matplotlib.ticker import AutoLocator, MultipleLocator

from src.gui.framework import figure_export as _figure_export
from src.processing.behaviour_metrics import get_time_scale

apply_figure_size_and_fonts = _figure_export.apply_figure_size_and_fonts
build_save_path = _figure_export.build_save_path
save_figure = _figure_export.save_figure

# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------
_TIME_LABELS = {
    "minutes": "Time (min)",
    "seconds": "Time (s)",
    "hours":   "Time (h)",
}

_TIME_FACTORS = {
    "minutes": 1.0,
    "seconds": 60.0,
    "hours":   1.0 / 60.0,
}


def convert_time_data(
    time_data: pd.Series,
    time_unit: str,
) -> tuple[pd.Series, str]:
    """Scale *time_data* (in minutes) to *time_unit* and return the axis label.

    Parameters
    ----------
    time_data:
        Time values in **minutes**.
    time_unit:
        One of ``"minutes"``, ``"seconds"``, ``"hours"``.

    Returns
    -------
    converted : pd.Series
    x_label   : str
    """
    factor = _TIME_FACTORS.get(time_unit, 1.0)
    label  = _TIME_LABELS.get(time_unit, "Time (min)")
    return time_data * factor, label


# ---------------------------------------------------------------------------
# Axis helpers
# ---------------------------------------------------------------------------

def set_ax_tick_spacing(ax, x_ticks_str: str, y_ticks_str: str) -> None:
    """Apply tick spacing to *ax* from user-entered strings.

    Empty or zero strings fall back to matplotlib's AutoLocator.
    """
    if x_ticks_str and x_ticks_str.strip():
        x_ticks = float(x_ticks_str)
        if x_ticks > 0:
            ax.xaxis.set_major_locator(MultipleLocator(x_ticks))
        else:
            ax.xaxis.set_major_locator(AutoLocator())
    else:
        ax.xaxis.set_major_locator(AutoLocator())

    if y_ticks_str and y_ticks_str.strip():
        y_ticks = float(y_ticks_str)
        if y_ticks > 0:
            ax.yaxis.set_major_locator(MultipleLocator(y_ticks))
        else:
            ax.yaxis.set_major_locator(AutoLocator())
    else:
        ax.yaxis.set_major_locator(AutoLocator())


# ---------------------------------------------------------------------------
# Data extraction from table DataFrame (pure)
# ---------------------------------------------------------------------------

def retrieve_behaviour_records(
    table_df: pd.DataFrame,
) -> tuple[list, list, list, list[float], list]:
    """Extract behaviour timing lists from the table DataFrame.

    Returns
    -------
    behaviours       : list[str]
    start_times      : list[float]  â€” seconds
    end_times        : list          â€” seconds or NaN
    start_times_min  : list[float]  â€” minutes
    end_times_min    : list          â€” minutes or None
    """
    records = table_df.to_dict("records")
    behaviours      = [r["Behaviour Name"] for r in records]
    start_times     = [r["Start Time"]     for r in records]
    end_times       = [r["End Time"]       for r in records]
    start_times_min = [float(t) / 60.0     for t in start_times]

    end_times_min: list = []
    for t in end_times:
        try:
            end_times_min.append(float(t) / 60.0)
        except (ValueError, TypeError):
            end_times_min.append(None)

    return behaviours, start_times, end_times, start_times_min, end_times_min


# ---------------------------------------------------------------------------
# Behaviour data processing (pure)
# ---------------------------------------------------------------------------

def process_behaviour_data(
    df: pd.DataFrame,
    behaviour_occurrences: list[tuple],
    column_used: str,
    time_unit: str,
    checkbox_state: bool,
) -> tuple[dict, np.ndarray, float, float]:
    """Slice the photometry trace around each behaviour occurrence.

    Parameters
    ----------
    df:
        Full recording DataFrame.  First column is time in minutes; if
        *checkbox_state* is True, ``df["z_scored_time"]`` is used instead.
    behaviour_occurrences:
        List of ``(start_time, end_time, pre_behaviour_time,
        post_behaviour_time)`` tuples â€” all in **minutes**.
    column_used:
        Column to extract signal data from.
    time_unit:
        Display unit for the time axis.
    checkbox_state:
        If ``True``, uses z-scored time column.

    Returns
    -------
    behaviour_data_by_instance : dict  â€” ``{"Instance 1": [...], ...}``
    time_points                : np.ndarray
    start_time_adjusted        : float  â€” in display units
    end_time_adjusted          : float  â€” in display units
    """
    time_factor = get_time_scale(time_unit)
    behaviour_data_by_instance: dict = {}
    time_points = np.array([])
    start_time_adjusted = 0.0
    end_time_adjusted = 0.0
    reference_length = None

    for i, (start_time, end_time, pre_time, post_time) in enumerate(behaviour_occurrences):
        instance_id = f"Instance {i + 1}"
        start_point = start_time - pre_time
        end_point   = start_time + post_time
        start_point_adj = start_point - 0.001

        if checkbox_state:
            mask = (df["z_scored_time"] >= start_point_adj) & (df["z_scored_time"] <= end_point)
        else:
            mask = (df.iloc[:, 0] >= start_point_adj) & (df.iloc[:, 0] <= end_point)

        behaviour_data = df.loc[mask, column_used].tolist()

        if reference_length is None:
            reference_length = len(behaviour_data)
        else:
            if len(behaviour_data) > reference_length:
                behaviour_data = behaviour_data[:reference_length]
            else:
                behaviour_data = behaviour_data + [np.nan] * (reference_length - len(behaviour_data))

        behaviour_data_by_instance[instance_id] = behaviour_data

        start_time_adjusted = -pre_time  * time_factor
        end_time_adjusted   =  post_time * time_factor

    # Intentionally uses the last occurrence's bounds as the shared time axis for all instances.
    if reference_length is not None and behaviour_occurrences:
        start_point = behaviour_occurrences[-1][0] - behaviour_occurrences[-1][2]
        end_point = behaviour_occurrences[-1][0] + behaviour_occurrences[-1][3]
        time_points = np.linspace(
            start_point * time_factor, end_point * time_factor, reference_length
        )

    return behaviour_data_by_instance, time_points, start_time_adjusted, end_time_adjusted


def adjust_behavior_times(
    behaviours: list[str],
    start_times_min: list[float],
    end_times_min: list,
    selected_behaviour: str,
) -> pd.DataFrame | None:
    """Re-zero behaviour times relative to the onset of *selected_behaviour*.

    Returns
    -------
    pd.DataFrame with columns ``Behaviour Name``, ``Adjusted Start Time``,
    ``Adjusted End Time``, or ``None`` if *selected_behaviour* is not found.
    """
    if selected_behaviour not in behaviours:
        return None

    onset_index = behaviours.index(selected_behaviour)
    onset_time  = start_times_min[onset_index]

    adjusted_start = [t - onset_time for t in start_times_min]
    adjusted_end   = [
        t - onset_time if t is not None else None for t in end_times_min
    ]

    return pd.DataFrame({
        "Behaviour Name":    behaviours,
        "Adjusted Start Time": adjusted_start,
        "Adjusted End Time":   adjusted_end,
    })


# ---------------------------------------------------------------------------
# Drawing primitives (pure matplotlib)
# ---------------------------------------------------------------------------

def draw_trace(
    ax,
    time: pd.Series | np.ndarray,
    data: pd.Series | np.ndarray,
    trace_color: str,
    line_width: float,
    x_label: str,
    y_label: str,
    label: str | None = None,
) -> None:
    """Plot a single trace on *ax*."""
    ax.plot(time, data, color=trace_color, linewidth=line_width, label=label)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)


def draw_sem_band(
    ax,
    time: pd.Series | np.ndarray,
    mean: pd.Series | np.ndarray,
    sem: pd.Series | np.ndarray,
    sem_color: str,
    label: str | None = "SEM",
) -> None:
    """Fill Â±SEM band around *mean* if any SEM values are non-zero.

    Pass ``label=None`` to keep the band out of the legend â€” used when
    overlaying multiple columns, where each column's trace already carries
    its own legend entry and a per-column "SEM" entry would just be noise.
    """
    if not pd.Series(sem).eq(0).all():
        ax.fill_between(
            time, mean - sem, mean + sem, color=sem_color, alpha=0.5,
            label=label if label is not None else "_nolegend_",
        )


def draw_onset_line(
    ax,
    line_color: str,
    line_style: str,
    line_width: float,
) -> None:
    """Draw a vertical onset line at x=0."""
    ax.axvline(x=0, color=line_color, linestyle=line_style, linewidth=line_width)


def draw_behaviour_boxes(
    ax,
    data: pd.Series,
    time_data: pd.Series,
    behaviours: list[str],
    start_times_min: list,
    end_times_min: list,
    behaviour_colors: dict[str, str],
    behaviour_display: dict[str, bool],
    time_factor: float,
    box_height_factor: float,
    alpha: float,
    start_point: float | None = None,
    end_point: float | None = None,
) -> dict[str, list]:
    """Draw coloured transparent behaviour rectangles on *ax*.

    Parameters
    ----------
    behaviour_display:
        ``{behaviour_name: True/False}`` â€” pre-resolved from IntVar.get().
    time_factor:
        Already applied to *time_data* and *start/end_times_min*.
    box_height_factor:
        Fraction of the data range used as box height.
        The box starts at the minimum plotted signal value.
    alpha:
        Box transparency (0â€“1).
    start_point, end_point:
        If provided (Single Row display), restrict xlim and y-range to
        this window (already in display units).

    Returns
    -------
    behaviour_boxes : dict[str, list[Rectangle]]
    """
    if start_point is not None and end_point is not None:
        filtered = data[(time_data >= start_point) & (time_data <= end_point)]
        min_y, max_y = float(filtered.min()), float(filtered.max())
        ax.set_xlim(start_point, end_point)
    else:
        min_y, max_y = float(data.min()), float(data.max())
        clean = time_data.dropna().reset_index(drop=True)
        if not clean.empty:
            ax.set_xlim(float(clean.iloc[0]), float(clean.iloc[-1]))

    behaviour_boxes: dict[str, list] = {}
    min_box_width = 0.01

    for behaviour, start_min, end_min in zip(behaviours, start_times_min, end_times_min):
        if not behaviour_display.get(behaviour, False) or not behaviour:
            continue

        x_pos   = start_min if start_min is not None else start_point
        end_x   = end_min   if end_min   is not None else end_point
        width   = max((end_x - x_pos if end_x is not None else min_box_width), min_box_width)
        height  = box_height_factor * ((max_y - min_y) * 1.05)
        y_pos   = min_y
        color   = behaviour_colors.get(behaviour, "#888888")

        box = Rectangle(
            (x_pos * time_factor, y_pos),
            width * time_factor,
            height,
            facecolor=color,
            alpha=alpha,
        )
        behaviour_boxes.setdefault(behaviour, []).append(box)
        ax.add_patch(box)

    return behaviour_boxes


# ---------------------------------------------------------------------------
# Duration bar
# ---------------------------------------------------------------------------

def compute_bar_position(
    mean_sem_df: pd.DataFrame,
    height_modifier: float,
    size_factor: float,
) -> tuple[float, float]:
    """Return ``(bar_y, bar_height)`` for the duration bar.

    *height_modifier* is the raw spinbox value (can be negative).
    """
    max_mean  = float(mean_sem_df["Mean"].max())
    min_mean  = float(mean_sem_df["Mean"].min())
    mean_mean = float(mean_sem_df["Mean"].mean())

    if height_modifier >= 0:
        bar_y = mean_mean + height_modifier * (max_mean - mean_mean)
    else:
        bar_y = mean_mean - abs(height_modifier) * (mean_mean - min_mean)

    bar_height = size_factor * (max_mean - min_mean)
    return bar_y, bar_height


def draw_duration_bar(
    ax,
    mean_duration: float,
    sem_duration: float,
    bar_y: float,
    bar_height: float,
    fill_color: str,
    border_color: str,
    sem_color: str,
) -> list:
    """Draw a horizontal duration bar and return the artist items list."""
    bars = ax.barh(
        bar_y,
        mean_duration,
        xerr=sem_duration,
        height=bar_height,
        color=fill_color,
        edgecolor=border_color,
        alpha=0.5,
        error_kw={"ecolor": sem_color, "capsize": 5},
    )
    items = list(bars.patches)
    items.extend(bars.errorbar.get_children())
    return items


# ---------------------------------------------------------------------------
