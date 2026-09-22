from __future__ import annotations

import logging
import time
from pathlib import Path

import numpy as np
import pandas as pd

from src.processing.behaviour_metrics import compute_full_trace_zscore

from .df_common import (
    BUTTER_CUTOFF,
    BUTTER_ORDER,
    SAVGOL_COARSE,
    SAVGOL_FINE,
    butter_lowpass_filter,
    compute_adjusted_baselines,
    expected_analysis_output_path,
    safe_savgol,
    save_analysis_output,
    validate_single_df,
    window_slice,
)
from .df_plots import (
    render_single_option_plots,
    render_single_preview,
    render_single_results,
)
from .msbackadj import msbackadj, msbackadj_window_size

logger = logging.getLogger(__name__)


def _compute_single_msbackadj_target(
    y465: np.ndarray,
    t_sec: np.ndarray,
    fs: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    filter_465 = butter_lowpass_filter(y465, BUTTER_CUTOFF, fs, BUTTER_ORDER)
    smooth_465 = safe_savgol(filter_465, *SAVGOL_FINE)
    window_size = msbackadj_window_size(t_sec)
    result = msbackadj(t_sec, smooth_465, window_size, window_size)
    return smooth_465, result.baseline, result.corrected


def _compute_single_option_traces(
    y405: np.ndarray,
    y465: np.ndarray,
    t_sec: np.ndarray,
    fs: float,
) -> dict[str, np.ndarray]:
    adj1, adj2, _, scaled_quad = compute_adjusted_baselines(y405, y465)
    filter_adj1 = butter_lowpass_filter(adj1, BUTTER_CUTOFF, fs, BUTTER_ORDER)
    filter_adj2 = butter_lowpass_filter(adj2, BUTTER_CUTOFF, fs, BUTTER_ORDER)
    smooth_465, ms_baseline_465, ms_corrected_465 = _compute_single_msbackadj_target(
        y465, t_sec, fs
    )

    return {
        "smooth_465": smooth_465,
        "smooth_adj_1": safe_savgol(filter_adj1, *SAVGOL_FINE),
        "smooth_adj_2": safe_savgol(filter_adj2, *SAVGOL_FINE),
        "smooth_adj_3": safe_savgol(filter_adj1, *SAVGOL_COARSE),
        "smooth_adj_4": safe_savgol(filter_adj2, *SAVGOL_COARSE),
        "smooth_adj_5": ms_baseline_465,
        "ms_baseline_465": ms_baseline_465,
        "ms_corrected_465": ms_corrected_465,
        "scaled_quad": scaled_quad,
    }


def compute_single_options(
    selectedfile: str | Path,
    w_start: str,
    w_end: str,
) -> dict:
    """Compute the five DFer option traces for a single-channel file.

    Returns a dict with numpy arrays for inline display (no file I/O, no plots).
    """
    selectedfile = str(Path(selectedfile).expanduser().resolve())
    df = pd.read_csv(selectedfile, index_col=False, low_memory=False)
    validate_single_df(df)

    y405 = df["405nm"][1:].to_numpy(dtype=float)
    y465_col = "465nm" if "465nm" in df.columns else "490nm"
    y465 = df[y465_col][1:].to_numpy(dtype=float)
    t_vec = df["#time(seconds)"][1:].to_numpy(dtype=float)

    dt_sec = float(np.median(np.diff(t_vec)))
    fs = 1.0 / dt_sec
    sl, _, _ = window_slice(len(t_vec), dt_sec, w_start, w_end)

    y405 = np.asarray(y405[sl], dtype=float)
    y465 = np.asarray(y465[sl], dtype=float)
    t_sec = np.asarray(t_vec[sl], dtype=float)
    t_min = t_sec / 60.0
    traces = _compute_single_option_traces(y405, y465, t_sec, fs)

    return {
        "file_type": "single",
        "filename": Path(selectedfile).name,
        "signal_label": y465_col,
        "t_min": t_min,
        "smooth_465": traces["smooth_465"],
        "smooth_adj_1": traces["smooth_adj_1"],
        "smooth_adj_2": traces["smooth_adj_2"],
        "smooth_adj_3": traces["smooth_adj_3"],
        "smooth_adj_4": traces["smooth_adj_4"],
        "smooth_adj_5": traces["smooth_adj_5"],
    }


def run_single_analysis(
    selectedfile: str | Path,
    filename: str,
    w_start: str,
    w_end: str,
    analysis_path: str,
    do_preview_plots: bool,
    do_final_plots: bool,
    mode: str,
) -> str:
    """Run the single-photometry DFer workflow."""
    df = pd.read_csv(selectedfile, index_col=False, low_memory=False)
    validate_single_df(df)
    logger.info("Begin analysing %s", filename)

    y405 = df["405nm"][1:].to_numpy(dtype=float)
    y465_col = "465nm" if "465nm" in df.columns else "490nm"
    y465 = df[y465_col][1:].to_numpy(dtype=float)
    t_vec = df["#time(seconds)"][1:].to_numpy(dtype=float)

    if do_preview_plots:
        render_single_preview(filename, t_vec, y405, y465)

    dt_sec = float(np.median(np.diff(t_vec)))
    fs = 1.0 / dt_sec
    sl, win_start, win_end = window_slice(len(t_vec), dt_sec, w_start, w_end)

    y405 = np.asarray(y405[sl], dtype=float)
    y465 = np.asarray(y465[sl], dtype=float)
    t_sec = np.asarray(t_vec[sl], dtype=float)
    t_min = t_sec / 60.0

    logger.info("Samples %s to %s processed", win_start, win_end)

    if analysis_path not in {"1", "2", "3", "4", "5"}:
        raise ValueError("analysis_path must be '1','2','3','4','5'")

    if analysis_path == "5":
        if do_preview_plots:
            preview_traces = _compute_single_option_traces(y405, y465, t_sec, fs)
            option_plot_args: tuple[
                str,
                np.ndarray,
                np.ndarray,
                np.ndarray,
                np.ndarray,
                np.ndarray,
                np.ndarray,
                np.ndarray,
            ] = (
                filename,
                t_min,
                preview_traces["smooth_465"],
                preview_traces["smooth_adj_1"],
                preview_traces["smooth_adj_2"],
                preview_traces["smooth_adj_3"],
                preview_traces["smooth_adj_4"],
                preview_traces["smooth_adj_5"],
            )
            render_single_option_plots(*option_plot_args)

        smooth_465, ms_baseline_465, ms_corrected_465 = (
            _compute_single_msbackadj_target(y465, t_sec, fs)
        )
        smooth_adjusted_405 = np.full_like(smooth_465, np.nan)
        dfof_465 = ms_corrected_465 / ms_baseline_465
        dfof_405 = np.full_like(dfof_465, np.nan)
    else:
        traces = _compute_single_option_traces(y405, y465, t_sec, fs)
        smooth_465 = traces["smooth_465"]
        smooth_adj_map = {
            "1": traces["smooth_adj_1"],
            "2": traces["smooth_adj_2"],
            "3": traces["smooth_adj_3"],
            "4": traces["smooth_adj_4"],
        }
        dfof_adj_for_405 = {
            "1": traces["smooth_adj_1"],
            "2": traces["smooth_adj_2"],
            "3": traces["smooth_adj_1"],
            "4": traces["smooth_adj_2"],
        }
        smooth_adjusted_405 = smooth_adj_map[analysis_path]
        if do_preview_plots:
            option_plot_args = (
                filename,
                t_min,
                smooth_465,
                traces["smooth_adj_1"],
                traces["smooth_adj_2"],
                traces["smooth_adj_3"],
                traces["smooth_adj_4"],
                traces["smooth_adj_5"],
            )
            render_single_option_plots(*option_plot_args)
        dfof_465 = (smooth_465 - smooth_adjusted_405) / smooth_adjusted_405
        dfof_405 = (dfof_adj_for_405[analysis_path] - traces["scaled_quad"]) / traces[
            "scaled_quad"
        ]

    if mode == "options_only":
        return ""

    z_465, _, _ = compute_full_trace_zscore(dfof_465)
    if analysis_path == "5":
        z_405 = np.full_like(dfof_405, np.nan)
    else:
        z_405, _, _ = compute_full_trace_zscore(dfof_405)

    out_file_path = str(expected_analysis_output_path(selectedfile, file_type="single"))
    save_analysis_output(
        out_file_path,
        np.c_[
            t_min,
            y405,
            y465,
            smooth_465,
            smooth_adjusted_405,
            dfof_405,
            z_405,
            dfof_465,
            z_465,
        ],
        "t_min,405,465,filtered_465,fitted_405,dFoF_405,Z_405,dFoF_465,Z_465",
        analysis_path,
    )

    if do_final_plots:
        render_single_results(
            filename,
            t_min,
            dfof_405,
            dfof_465,
            z_405,
            z_465,
            show_405=analysis_path != "5",
        )

    logger.info("%s analysis complete", filename)
    time.sleep(1)
    logger.info("Ready for next file")
    return out_file_path
