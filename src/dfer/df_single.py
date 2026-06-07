from __future__ import annotations

import logging
import time
from pathlib import Path

import numpy as np
import pandas as pd

from .df_common import (
    BUTTER_CUTOFF,
    BUTTER_ORDER,
    SAVGOL_COARSE,
    SAVGOL_FINE,
    butter_lowpass_filter,
    compute_adjusted_baselines,
    expected_analysis_output_path,
    safe_savgol,
    validate_single_df,
    window_slice,
)
from .df_plots import (
    render_single_option_plots,
    render_single_preview,
    render_single_results,
)

logger = logging.getLogger(__name__)


def compute_single_options(
    selectedfile: str | Path,
    w_start: str,
    w_end: str,
) -> dict:
    """Compute the four DFer option traces for a single-channel file.

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
    t_min = np.asarray(t_vec[sl], dtype=float) / 60.0

    adj1, adj2, _, _ = compute_adjusted_baselines(y405, y465)
    filter_adj1 = butter_lowpass_filter(adj1, BUTTER_CUTOFF, fs, BUTTER_ORDER)
    filter_adj2 = butter_lowpass_filter(adj2, BUTTER_CUTOFF, fs, BUTTER_ORDER)
    filter_465 = butter_lowpass_filter(y465, BUTTER_CUTOFF, fs, BUTTER_ORDER)

    return {
        "file_type": "single",
        "filename": Path(selectedfile).name,
        "signal_label": y465_col,
        "t_min": t_min,
        "smooth_465": safe_savgol(filter_465, *SAVGOL_FINE),
        "smooth_adj_1": safe_savgol(filter_adj1, *SAVGOL_FINE),
        "smooth_adj_2": safe_savgol(filter_adj2, *SAVGOL_FINE),
        "smooth_adj_3": safe_savgol(filter_adj1, *SAVGOL_COARSE),
        "smooth_adj_4": safe_savgol(filter_adj2, *SAVGOL_COARSE),
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

    adj1, adj2, _, scaled_quad = compute_adjusted_baselines(y405, y465)
    filter_adj1 = butter_lowpass_filter(adj1, BUTTER_CUTOFF, fs, BUTTER_ORDER)
    filter_adj2 = butter_lowpass_filter(adj2, BUTTER_CUTOFF, fs, BUTTER_ORDER)
    filter_465 = butter_lowpass_filter(y465, BUTTER_CUTOFF, fs, BUTTER_ORDER)

    smooth_adj_1 = safe_savgol(filter_adj1, *SAVGOL_FINE)
    smooth_adj_2 = safe_savgol(filter_adj2, *SAVGOL_FINE)
    smooth_adj_3 = safe_savgol(filter_adj1, *SAVGOL_COARSE)
    smooth_adj_4 = safe_savgol(filter_adj2, *SAVGOL_COARSE)
    smooth_465 = safe_savgol(filter_465, *SAVGOL_FINE)

    if do_preview_plots:
        render_single_option_plots(
            filename, t_min, smooth_465, smooth_adj_1, smooth_adj_2, smooth_adj_3, smooth_adj_4)

    if mode == "options_only":
        return ""

    smooth_adj_map = {"1": smooth_adj_1, "2": smooth_adj_2,
                      "3": smooth_adj_3, "4": smooth_adj_4}
    dfof_adj_for_405 = {"1": smooth_adj_1, "2": smooth_adj_2,
                        "3": smooth_adj_1, "4": smooth_adj_2}

    if analysis_path not in smooth_adj_map:
        raise ValueError("analysis_path must be '1','2','3','4'")

    smooth_adjusted_405 = smooth_adj_map[analysis_path]
    dfof_465 = (smooth_465 - smooth_adjusted_405) / smooth_adjusted_405
    dfof_405 = (dfof_adj_for_405[analysis_path] - scaled_quad) / scaled_quad

    mu465, sigma465 = float(np.mean(dfof_465)), float(np.std(dfof_465))
    mu405, sigma405 = float(np.mean(dfof_405)), float(np.std(dfof_405))
    z_465 = (dfof_465 - mu465) / sigma465
    z_405 = (dfof_405 - mu405) / sigma405

    out_file_path = str(expected_analysis_output_path(selectedfile, file_type="single"))
    np.savetxt(
        out_file_path,
        np.c_[t_min, y405, y465, smooth_465, smooth_adjusted_405,
              dfof_405, z_405, dfof_465, z_465],
        delimiter=",",
        header="t_min,405,465,filtered_465,fitted_405,dFoF_405,Z_405,dFoF_465,Z_465",
        fmt="%f",
    )

    if do_final_plots:
        render_single_results(filename, t_min, dfof_405, dfof_465, z_405, z_465)

    logger.info("%s analysis complete", filename)
    time.sleep(1)
    logger.info("Ready for next file")
    return out_file_path
