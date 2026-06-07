from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from .plotting import render_html


# ---------------------------------------------------------------------------
# Matplotlib inline figures (used by the Qt UI for in-app display)
# ---------------------------------------------------------------------------

_OPTION_TITLES_SINGLE = [
    "Option 1: Good noise correction and bleach correction",
    "Option 2: Assumes shifts in 465 baseline are independent of activity",
    "Option 3: No noise correction",
    "Option 4: No noise correction, no activity-dependent baseline correction",
]


def mpl_options_figure(data: dict) -> Figure:
    """Return a matplotlib Figure showing the four DFer option traces.

    Works for both single-channel and dual-channel data dicts produced by
    compute_single_options() / compute_dual_options().
    """
    file_type = data.get("file_type", "single")
    t = data["t_min"]

    if file_type == "single":
        smooth_465 = data["smooth_465"]
        adjs = [data["smooth_adj_1"], data["smooth_adj_2"],
                data["smooth_adj_3"], data["smooth_adj_4"]]

        fig = Figure(figsize=(12, 12), tight_layout=True)
        for i, (title, adj) in enumerate(zip(_OPTION_TITLES_SINGLE, adjs)):
            ax = fig.add_subplot(4, 1, i + 1)
            ax.plot(t, smooth_465, color="green", linewidth=0.6, label="465nm")
            ax.plot(t, adj, color="red", linewidth=0.6, alpha=0.7, label="fitted control")
            ax.set_title(title, fontsize=9)
            ax.set_ylabel("RFU")
            if i == 3:
                ax.set_xlabel("Time (min)")
            ax.legend(fontsize=8, loc="upper right")
        return fig

    # dual
    p470 = data["p470"]
    p560 = data["p560"]
    adj_keys = ["adj1", "adj2", "adj3", "adj4"]
    titles = [f"Option {i + 1}" for i in range(4)]

    fig = Figure(figsize=(12, 12), tight_layout=True)
    for i, (title, key) in enumerate(zip(titles, adj_keys)):
        ax = fig.add_subplot(4, 1, i + 1)
        ax.plot(t, p470["target_smooth"], color="green", linewidth=0.6,
                alpha=0.8, label="470nm")
        ax.plot(t, p470[key], color="green", linewidth=0.6, alpha=0.3,
                linestyle="--", label="470 fitted")
        ax.plot(t, p560["target_smooth"], color="red", linewidth=0.6,
                alpha=0.8, label="560nm")
        ax.plot(t, p560[key], color="red", linewidth=0.6, alpha=0.3,
                linestyle="--", label="560 fitted")
        ax.set_title(title, fontsize=9)
        ax.set_ylabel("RFU")
        if i == 3:
            ax.set_xlabel("Time (min)")
        ax.legend(fontsize=8, loc="upper right")
    return fig


def mpl_results_figure(csv_path: str) -> Figure:
    """Read a DFer output CSV and return a matplotlib Figure with dF/F and Z-score.

    Handles both single-channel and dual-channel output files.
    """
    df = pd.read_csv(csv_path, index_col=False)
    df.columns = [str(c).strip().lstrip("#").strip() for c in df.columns]
    t_min = df["t_min"].to_numpy(dtype=float)

    is_dual = "dFoF_470" in df.columns

    fig = Figure(figsize=(12, 6), tight_layout=True)

    if is_dual:
        dfof_470 = df["dFoF_470"].to_numpy(dtype=float)
        dfof_560 = df["dFoF_560"].to_numpy(dtype=float)
        z_470 = df["Z_470"].to_numpy(dtype=float)
        z_560 = df["Z_560"].to_numpy(dtype=float)

        ax1 = fig.add_subplot(2, 1, 1)
        ax1.plot(t_min, dfof_470, color="green", linewidth=0.6, label="470nm dF/F")
        ax1.plot(t_min, dfof_560, color="red", linewidth=0.6, label="560nm dF/F")
        ax1.set_ylabel("dF/F")
        ax1.set_title("dF/F")
        ax1.legend(fontsize=8, loc="upper right")

        ax2 = fig.add_subplot(2, 1, 2)
        ax2.plot(t_min, z_470, color="green", linewidth=0.6, label="470nm Z")
        ax2.plot(t_min, z_560, color="red", linewidth=0.6, label="560nm Z")
        ax2.set_xlabel("Time (min)")
        ax2.set_ylabel("Z-score")
        ax2.set_title("Z-score")
        ax2.legend(fontsize=8, loc="upper right")
    else:
        dfof_405 = df["dFoF_405"].to_numpy(dtype=float)
        dfof_465 = df["dFoF_465"].to_numpy(dtype=float)
        z_405 = df["Z_405"].to_numpy(dtype=float)
        z_465 = df["Z_465"].to_numpy(dtype=float)

        ax1 = fig.add_subplot(2, 1, 1)
        ax1.plot(t_min, dfof_405, color="purple", linewidth=0.6, label="405nm dF/F")
        ax1.plot(t_min, dfof_465, color="green", linewidth=0.6, label="465nm dF/F")
        ax1.set_ylabel("dF/F")
        ax1.set_title("dF/F")
        ax1.legend(fontsize=8, loc="upper right")

        ax2 = fig.add_subplot(2, 1, 2)
        ax2.plot(t_min, z_405, color="purple", linewidth=0.6, label="405nm Z")
        ax2.plot(t_min, z_465, color="green", linewidth=0.6, label="465nm Z")
        ax2.set_xlabel("Time (min)")
        ax2.set_ylabel("Z-score")
        ax2.set_title("Z-score")
        ax2.legend(fontsize=8, loc="upper right")

    return fig


def mpl_pfer_figure(dfer_csv: str, stats_csv: str) -> Figure:
    """Return a matplotlib Figure showing the dF/F trace with detected peaks."""
    dfer_df = pd.read_csv(dfer_csv, index_col=False)
    dfer_df.columns = [str(c).strip().lstrip("#").strip() for c in dfer_df.columns]
    t_min = dfer_df["t_min"].to_numpy(dtype=float)
    is_dual = "dFoF_470" in dfer_df.columns

    stats_df = pd.read_csv(stats_csv, index_col=False)
    stats_df.columns = [str(c).strip().lstrip("#").strip() for c in stats_df.columns]

    if is_dual:
        signal_col = "dFoF_470" if "dFoF_470" in dfer_df.columns else "dFoF_560"
        color = "green" if signal_col == "dFoF_470" else "red"
        label = "470nm dF/F" if signal_col == "dFoF_470" else "560nm dF/F"
    else:
        signal_col = "dFoF_465"
        color = "green"
        label = "465nm dF/F"

    trace = dfer_df[signal_col].to_numpy(dtype=float) if signal_col in dfer_df.columns else None

    fig = Figure(figsize=(12, 4), tight_layout=True)
    ax = fig.add_subplot(1, 1, 1)

    if trace is not None:
        ax.plot(t_min, trace, color=color, linewidth=0.6, label=label)

    if "peak_time_min" in stats_df.columns and "peak_amplitude" in stats_df.columns:
        peak_t = stats_df["peak_time_min"].to_numpy(dtype=float)
        peak_a = stats_df["peak_amplitude"].to_numpy(dtype=float)
        trough_t = stats_df["trough_time_min"].to_numpy(dtype=float)
        trough_a = stats_df["trough_amplitude"].to_numpy(dtype=float)
        ax.scatter(peak_t, peak_a, marker="v", color="red", s=40, zorder=5, label="peaks")
        ax.scatter(trough_t, trough_a, marker="^", color="black", s=30, zorder=5, label="troughs")

    ax.set_xlabel("Time (min)")
    ax.set_ylabel("dF/F")
    ax.set_title(f"Detected peaks — {Path(stats_csv).stem}")
    ax.legend(fontsize=8, loc="upper right")
    return fig


# ---------------------------------------------------------------------------
# Bokeh HTML figures (optional — kept for CLI / batch use)
# ---------------------------------------------------------------------------

def _set_axis_labels(plot, x_label: str, y_label: str) -> None:
    plot.xaxis.axis_label = x_label
    plot.yaxis.axis_label = y_label


def render_single_preview(filename: str, acquisition_sec: np.ndarray, y405: np.ndarray, y465: np.ndarray) -> None:
    from bokeh.plotting import figure  # lazy
    p_raw = figure(width=1000, height=400, title=filename + "   465 vs 405 raw data")
    _set_axis_labels(p_raw, "Acquisition time (seconds)", "RFU")
    p_raw.line(acquisition_sec, y405, line_color="red", line_width=0.6)
    p_raw.line(acquisition_sec, y465, line_color="green", line_width=0.6)
    render_html(p_raw, "DFer_raw.html", title=filename, open_in_browser=True)


def render_single_option_plots(
    filename: str,
    t_min: np.ndarray,
    smooth_465: np.ndarray,
    smooth_adj_1: np.ndarray,
    smooth_adj_2: np.ndarray,
    smooth_adj_3: np.ndarray,
    smooth_adj_4: np.ndarray,
) -> None:
    from bokeh.layouts import column  # lazy
    from bokeh.plotting import figure  # lazy

    p1 = figure(width=1100, height=400, title=filename +
                "     Option 1: Good noise correction and bleach correction")
    _set_axis_labels(p1, "Time(min)", "RFU")
    p1.line(t_min, smooth_465, line_color="green", line_width=0.6)
    p1.line(t_min, smooth_adj_1, line_color="red", line_width=0.6)

    p2 = figure(width=1100, height=400, title=filename +
                "     Option 2: Assumes that shifts in 465 baseline are independent of activity.")
    _set_axis_labels(p2, "Time(min)", "RFU")
    p2.line(t_min, smooth_465, line_color="green", line_width=0.6)
    p2.line(t_min, smooth_adj_2, line_color="red", line_width=0.6)

    p3 = figure(width=1100, height=400, title=filename + "     Option 3: No noise correction")
    _set_axis_labels(p3, "Time(min)", "RFU")
    p3.line(t_min, smooth_465, line_color="green", line_width=0.6)
    p3.line(t_min, smooth_adj_3, line_color="red", line_width=0.6)

    p4 = figure(width=1100, height=400, title=filename +
                "     Option 4: No noise correction. No activity-dependent baseline correction")
    _set_axis_labels(p4, "Time(min)", "RFU")
    p4.line(t_min, smooth_465, line_color="green", line_width=0.6)
    p4.line(t_min, smooth_adj_4, line_color="red", line_width=0.6)

    render_html(column(p1, p2, p3, p4), "DFer_options.html", title=filename, open_in_browser=True)


def render_single_results(
    filename: str,
    t_min: np.ndarray,
    dfof_405: np.ndarray,
    dfof_465: np.ndarray,
    z_405: np.ndarray,
    z_465: np.ndarray,
) -> None:
    from bokeh.layouts import column  # lazy
    from bokeh.plotting import figure  # lazy

    p_df = figure(width=1000, height=400, title=filename + "   DF/F")
    _set_axis_labels(p_df, "Time(min)", "DF/F")
    p_df.line(t_min, dfof_405, line_color="purple", line_width=0.6)
    p_df.line(t_min, dfof_465, line_color="green", line_width=0.6)

    p_z = figure(width=1000, height=400, title=filename + "   Z-score")
    _set_axis_labels(p_z, "Time(min)", "Z")
    p_z.line(t_min, z_405, line_color="purple", line_width=0.6)
    p_z.line(t_min, z_465, line_color="green", line_width=0.6)

    render_html(column(p_df, p_z), "DFer_results.html", title=filename, open_in_browser=True)


def render_dual_preview(filename: str, t_ms: np.ndarray, y410: np.ndarray, y470: np.ndarray, y560: np.ndarray) -> None:
    from bokeh.plotting import figure  # lazy
    t_sec = t_ms / 1000.0
    p_raw = figure(width=1100, height=420, title=filename + "   RAW (dual)")
    _set_axis_labels(p_raw, "Time (sec)", "RFU")
    p_raw.line(t_sec, y410, line_color="gray", line_width=0.6, line_alpha=0.55, legend_label="410 (control)")
    p_raw.line(t_sec, y470, line_color="green", line_width=0.6, line_alpha=0.75, legend_label="470")
    p_raw.line(t_sec, y560, line_color="red", line_width=0.6, line_alpha=0.75, legend_label="560")
    p_raw.legend.click_policy = "hide"
    render_html(p_raw, "Dual_raw.html", title=filename, open_in_browser=True)


def render_dual_option_plots(
    filename: str,
    t_min: np.ndarray,
    p470: dict[str, np.ndarray],
    p560: dict[str, np.ndarray],
) -> None:
    from bokeh.layouts import column  # lazy
    from bokeh.plotting import figure  # lazy

    def _build(option_number, key470, key560):
        p = figure(width=1200, height=420, title=filename + f"   Option {option_number} (dual)")
        _set_axis_labels(p, "Time(min)", "RFU")
        p.line(t_min, p470["target_smooth"], line_color="green", line_width=0.6, line_alpha=0.75, legend_label="470 (smooth)")
        p.line(t_min, p470[key470], line_color="green", line_width=0.6, line_alpha=0.30, legend_label="470 fitted-control")
        p.line(t_min, p560["target_smooth"], line_color="red", line_width=0.6, line_alpha=0.75, legend_label="560 (smooth)")
        p.line(t_min, p560[key560], line_color="red", line_width=0.6, line_alpha=0.30, legend_label="560 fitted-control")
        p.legend.click_policy = "hide"
        return p

    render_html(
        column(_build("1", "adj1", "adj1"), _build("2", "adj2", "adj2"),
               _build("3", "adj3", "adj3"), _build("4", "adj4", "adj4")),
        "Dual_options.html", title=filename, open_in_browser=True,
    )


def render_dual_results(
    filename: str,
    t_min: np.ndarray,
    dfof_470: np.ndarray,
    dfof_560: np.ndarray,
    z_470: np.ndarray,
    z_560: np.ndarray,
) -> None:
    from bokeh.layouts import column  # lazy
    from bokeh.plotting import figure  # lazy

    p_df = figure(width=1100, height=420, title=filename + "   DF/F (dual)")
    _set_axis_labels(p_df, "Time(min)", "DF/F")
    p_df.line(t_min, dfof_470, line_color="green", line_width=0.6, line_alpha=0.85, legend_label="470 dF/F")
    p_df.line(t_min, dfof_560, line_color="red", line_width=0.6, line_alpha=0.85, legend_label="560 dF/F")
    p_df.legend.click_policy = "hide"

    p_z = figure(width=1100, height=420, title=filename + "   Z-score (dual)")
    _set_axis_labels(p_z, "Time(min)", "Z")
    p_z.line(t_min, z_470, line_color="green", line_width=0.6, line_alpha=0.85, legend_label="470 Z")
    p_z.line(t_min, z_560, line_color="red", line_width=0.6, line_alpha=0.85, legend_label="560 Z")
    p_z.legend.click_policy = "hide"

    render_html(column(p_df, p_z), "Dual_results.html", title=filename, open_in_browser=True)
