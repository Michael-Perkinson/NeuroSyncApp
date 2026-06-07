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
    validate_dual_df,
    window_slice,
)
from .df_plots import (
    render_dual_option_plots,
    render_dual_preview,
    render_dual_results,
)

logger = logging.getLogger(__name__)


def compute_dual_options(
    selectedfile: str | Path,
    skiprows: int,
    w_start: str,
    w_end: str,
) -> dict:
    """Compute the four DFer option traces for a dual-channel file.

    Returns a dict with numpy arrays for inline display (no file I/O, no plots).
    """
    selectedfile = str(Path(selectedfile).expanduser().resolve())
    df = pd.read_csv(selectedfile, skiprows=skiprows, index_col=False, low_memory=False)
    validate_dual_df(df)

    t_ms = df["TimeStamp"].astype(float).to_numpy()
    y410 = df["CH1-410"].astype(float).to_numpy()
    y470 = df["CH1-470"].astype(float).to_numpy()
    y560 = df["CH1-560"].astype(float).to_numpy()

    dt_ms = float(np.median(np.diff(t_ms)))
    dt_sec = dt_ms / 1000.0
    fs = 1.0 / dt_sec

    sl, _, _ = window_slice(len(t_ms), dt_sec, w_start, w_end)
    t_min = (t_ms[sl] / 1000.0) / 60.0
    y410 = y410[sl]
    y470 = y470[sl]
    y560 = y560[sl]

    def _process_pair(control: np.ndarray, target: np.ndarray) -> dict[str, np.ndarray]:
        adj1, adj2, _, _ = compute_adjusted_baselines(control, target)
        filt_adj1 = butter_lowpass_filter(adj1, BUTTER_CUTOFF, fs, BUTTER_ORDER)
        filt_adj2 = butter_lowpass_filter(adj2, BUTTER_CUTOFF, fs, BUTTER_ORDER)
        filt_target = butter_lowpass_filter(target, BUTTER_CUTOFF, fs, BUTTER_ORDER)
        return {
            "target_smooth": safe_savgol(filt_target, *SAVGOL_FINE),
            "adj1": safe_savgol(filt_adj1, *SAVGOL_FINE),
            "adj2": safe_savgol(filt_adj2, *SAVGOL_FINE),
            "adj3": safe_savgol(filt_adj1, *SAVGOL_COARSE),
            "adj4": safe_savgol(filt_adj2, *SAVGOL_COARSE),
        }

    return {
        "file_type": "dual",
        "filename": Path(selectedfile).name,
        "t_min": t_min,
        "p470": _process_pair(y410, y470),
        "p560": _process_pair(y410, y560),
    }


def run_dual_analysis(
    selectedfile: str | Path,
    filename: str,
    skiprows: int,
    w_start: str,
    w_end: str,
    analysis_path: str,
    do_preview_plots: bool,
    do_final_plots: bool,
    mode: str,
) -> str:
    """Run the dual-photometry DFer workflow."""
    df = pd.read_csv(selectedfile, skiprows=skiprows,
                     index_col=False, low_memory=False)
    validate_dual_df(df)
    logger.info("Begin analysing (DUAL) %s", filename)

    t_ms = df["TimeStamp"].astype(float).to_numpy()
    y410 = df["CH1-410"].astype(float).to_numpy()
    y470 = df["CH1-470"].astype(float).to_numpy()
    y560 = df["CH1-560"].astype(float).to_numpy()

    dt_ms = float(np.median(np.diff(t_ms)))
    dt_sec = dt_ms / 1000.0
    fs = 1.0 / dt_sec

    if do_preview_plots:
        render_dual_preview(filename, t_ms, y410, y470, y560)

    sl, _, _ = window_slice(len(t_ms), dt_sec, w_start, w_end)
    t_ms = t_ms[sl]
    y410 = y410[sl]
    y470 = y470[sl]
    y560 = y560[sl]
    t_min = (t_ms / 1000.0) / 60.0

    def _process_pair(control: np.ndarray, target: np.ndarray) -> dict[str, np.ndarray]:
        adj1, adj2, _, _ = compute_adjusted_baselines(control, target)
        filt_adj1 = butter_lowpass_filter(adj1, BUTTER_CUTOFF, fs, BUTTER_ORDER)
        filt_adj2 = butter_lowpass_filter(adj2, BUTTER_CUTOFF, fs, BUTTER_ORDER)
        filt_target = butter_lowpass_filter(target, BUTTER_CUTOFF, fs, BUTTER_ORDER)
        return {
            "target_smooth": safe_savgol(filt_target, *SAVGOL_FINE),
            "adj1": safe_savgol(filt_adj1, *SAVGOL_FINE),
            "adj2": safe_savgol(filt_adj2, *SAVGOL_FINE),
            "adj3": safe_savgol(filt_adj1, *SAVGOL_COARSE),
            "adj4": safe_savgol(filt_adj2, *SAVGOL_COARSE),
        }

    p470 = _process_pair(y410, y470)
    p560 = _process_pair(y410, y560)

    if do_preview_plots:
        render_dual_option_plots(filename, t_min, p470, p560)

    if mode == "options_only":
        return ""

    adj_key = {"1": "adj1", "2": "adj2", "3": "adj3", "4": "adj4"}
    if analysis_path not in adj_key:
        raise ValueError("analysis_path must be '1','2','3','4'")

    fit470 = p470[adj_key[analysis_path]]
    fit560 = p560[adj_key[analysis_path]]
    dfof_470 = (p470["target_smooth"] - fit470) / fit470
    dfof_560 = (p560["target_smooth"] - fit560) / fit560

    mu470, sig470 = float(np.mean(dfof_470)), float(np.std(dfof_470))
    mu560, sig560 = float(np.mean(dfof_560)), float(np.std(dfof_560))
    z_470 = (dfof_470 - mu470) / sig470
    z_560 = (dfof_560 - mu560) / sig560

    out_file_path = str(expected_analysis_output_path(selectedfile, file_type="dual"))
    np.savetxt(
        out_file_path,
        np.c_[t_min, y410, y470, y560, p470["target_smooth"], fit470,
              dfof_470, z_470, p560["target_smooth"], fit560, dfof_560, z_560],
        delimiter=",",
        header="t_min,410,470,560,filtered_470,fitted_410_to_470,dFoF_470,Z_470,filtered_560,fitted_410_to_560,dFoF_560,Z_560",
        fmt="%f",
    )

    if do_final_plots:
        render_dual_results(filename, t_min, dfof_470, dfof_560, z_470, z_560)

    logger.info("%s (DUAL) analysis complete", filename)
    time.sleep(1)
    logger.info("Ready for next file")
    return out_file_path
