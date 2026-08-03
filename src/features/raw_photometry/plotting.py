"""Matplotlib figure builders for raw-photometry analysis results."""

from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib.figure import Figure


def _graph_time_values(axis) -> np.ndarray | None:
    values: list[float] = []
    for line in axis.lines:
        x_data = np.asarray(line.get_xdata(), dtype=float)
        if x_data.size:
            values.extend([float(np.nanmin(x_data)), float(np.nanmax(x_data))])
    if not values:
        return None
    return np.asarray(values, dtype=float)


def _tighten_time_axes(figure: Figure) -> None:
    for axis in figure.axes:
        values = _graph_time_values(axis)
        if values is None:
            continue
        finite = values[np.isfinite(values)]
        if finite.size == 0:
            continue
        x_min = float(np.min(finite))
        x_max = float(np.max(finite))
        if x_min == x_max:
            axis.set_xlim(x_min - 0.5, x_max + 0.5)
        else:
            pad = (x_max - x_min) * 0.005
            axis.set_xlim(x_min - pad, x_max + pad)
        axis.margins(x=0)


OPTION_TITLES = [
    "Option 1: Good noise correction and bleach correction",
    "Option 2: Assumes shifts in 465 baseline are independent of activity",
    "Option 3: No noise correction",
    "Option 4: No noise correction, no activity-dependent baseline correction",
]


def normalise_dfer_result_frame(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(column).strip().lstrip("#").strip() for column in df.columns]
    return df


def mpl_dfer_results_figure_from_frame(
    df: pd.DataFrame,
    graph: str = "dfof",
    show_405: bool = True,
) -> Figure:
    """Return a single-panel DFer result figure from a normalised result frame."""
    df = normalise_dfer_result_frame(df)
    t_min = df["t_min"].to_numpy(dtype=float)
    is_dual = "dFoF_470" in df.columns

    figure = Figure(figsize=(12, 4), tight_layout=True)
    axis = figure.add_subplot(1, 1, 1)
    if is_dual:
        if graph == "dfof":
            axis.plot(t_min, df["dFoF_470"].to_numpy(dtype=float), color="green", linewidth=0.6, alpha=0.55, label="470nm dF/F")
            axis.plot(t_min, df["dFoF_560"].to_numpy(dtype=float), color="red", linewidth=0.6, alpha=0.4, label="560nm dF/F")
            axis.set_ylabel("dF/F")
        else:
            axis.plot(t_min, df["Z_470"].to_numpy(dtype=float), color="green", linewidth=0.6, alpha=0.55, label="470nm Z-score")
            axis.plot(t_min, df["Z_560"].to_numpy(dtype=float), color="red", linewidth=0.6, alpha=0.4, label="560nm Z-score")
            axis.set_ylabel("Z-score")
    elif graph == "dfof":
        if show_405:
            axis.plot(t_min, df["dFoF_405"].to_numpy(dtype=float), color="purple", linewidth=0.6, label="405nm dF/F")
        axis.plot(t_min, df["dFoF_465"].to_numpy(dtype=float), color="green", linewidth=0.6, label="465nm dF/F")
        axis.set_ylabel("dF/F")
    else:
        if show_405:
            axis.plot(t_min, df["Z_405"].to_numpy(dtype=float), color="purple", linewidth=0.6, label="405nm Z-score")
        axis.plot(t_min, df["Z_465"].to_numpy(dtype=float), color="green", linewidth=0.6, label="465nm Z-score")
        axis.set_ylabel("Z-score")

    axis.set_xlabel("Time (min)")
    axis.legend(fontsize=8, loc="upper right")
    _tighten_time_axes(figure)
    return figure


def mpl_dfer_results_figure(
    csv_path: str,
    graph: str = "dfof",
    show_405: bool = True,
) -> Figure:
    """Read a DFer output CSV and build its result figure."""
    return mpl_dfer_results_figure_from_frame(
        pd.read_csv(csv_path, index_col=False), graph, show_405
    )


def mpl_single_option_figure(
    data: dict,
    idx: int,
    dual_display: str = "both",
) -> Figure:
    """Render one DFer option as a full-canvas figure."""
    time_values = data["t_min"]
    file_type = data.get("file_type", "single")
    figure = Figure(figsize=(12, 4), tight_layout=True)
    axis = figure.add_subplot(1, 1, 1)

    if file_type == "single":
        adjustment_key = ["smooth_adj_1", "smooth_adj_2", "smooth_adj_3", "smooth_adj_4"][idx]
        axis.plot(time_values, data["smooth_465"], color="green", linewidth=0.6, label="465nm")
        axis.plot(time_values, data[adjustment_key], color="red", linewidth=0.6, alpha=0.7, label="fitted control")
    else:
        adjustment_key = ["adj1", "adj2", "adj3", "adj4"][idx]
        if dual_display in {"both", "470"}:
            axis.plot(time_values, data["p470"]["target_smooth"], color="green", linewidth=0.6, alpha=0.8, label="470nm")
            axis.plot(time_values, data["p470"][adjustment_key], color="green", linewidth=0.6, alpha=0.3, linestyle="--", label="470 fitted")
        if dual_display in {"both", "560"}:
            axis.plot(time_values, data["p560"]["target_smooth"], color="red", linewidth=0.6, alpha=0.8, label="560nm")
            axis.plot(time_values, data["p560"][adjustment_key], color="red", linewidth=0.6, alpha=0.3, linestyle="--", label="560 fitted")

    axis.set_title(OPTION_TITLES[idx], fontsize=10)
    axis.set_ylabel("RFU")
    axis.set_xlabel("Time (min)")
    axis.legend(fontsize=8, loc="upper right")
    _tighten_time_axes(figure)
    return figure
