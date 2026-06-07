from __future__ import annotations

import logging
from typing import cast
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import signal
from scipy.signal import butter, savgol_filter

logger = logging.getLogger(__name__)

# Shared signal-processing defaults for DFer smoothing and filtering.
BUTTER_CUTOFF = 0.4       # Hz  - lowpass cutoff for both single and dual
BUTTER_ORDER = 1
SAVGOL_FINE = (21, 6)     # (window, poly) - gentle smoothing
SAVGOL_COARSE = (501, 0)  # (window, poly) - strong smoothing / moving average


def missing_columns(df: pd.DataFrame, required: list[str]) -> list[str]:
    return [column for column in required if column not in df.columns]


def raise_missing_columns(file_kind: str, missing: list[str], required_help: str) -> None:
    missing_str = ", ".join(f"'{column}'" for column in missing)
    raise ValueError(
        f"{file_kind} CSV is missing required column(s): {missing_str}\n\n"
        f"Expected columns: {required_help}"
    )


def validate_single_df(df: pd.DataFrame) -> None:
    missing = missing_columns(df, ["#time(seconds)", "405nm"])
    signal_present = ("465nm" in df.columns) or ("490nm" in df.columns)
    if not signal_present:
        missing.append("465nm or 490nm")
    if missing:
        raise_missing_columns(
            "Single photometry",
            missing,
            "#time(seconds), 405nm, and either 465nm or 490nm",
        )
    if len(df.index) < 3:
        raise ValueError("Single photometry CSV must contain at least 3 rows of data.")


def validate_dual_df(df: pd.DataFrame) -> None:
    required = ["TimeStamp", "CH1-410", "CH1-470", "CH1-560"]
    missing = missing_columns(df, required)
    if missing:
        raise_missing_columns(
            "Dual photometry",
            missing,
            "TimeStamp, CH1-410, CH1-470, CH1-560",
        )
    if len(df.index) < 3:
        raise ValueError("Dual photometry CSV must contain at least 3 rows of data.")


def butter_lowpass_filter(data: np.ndarray, cutoff: float, fs: float, order: int = 5) -> np.ndarray:
    if len(data) < 4:
        return np.asarray(data, dtype=float).copy()
    b, a = cast(tuple[np.ndarray, np.ndarray], butter(
        order, cutoff, fs=fs, btype="low", analog=False))
    return np.asarray(signal.filtfilt(b, a, data, padtype=None), dtype=float)


def safe_savgol(data: np.ndarray, window: int, poly: int) -> np.ndarray:
    arr = np.asarray(data, dtype=float)
    n = len(arr)
    if n == 0:
        return arr.copy()
    max_window = n if (n % 2 == 1) else (n - 1)
    if max_window <= poly:
        return arr.copy()
    safe_window = min(window, max_window)
    if safe_window % 2 == 0:
        safe_window -= 1
    min_valid_window = poly + 1 if ((poly + 1) % 2 == 1) else (poly + 2)
    if safe_window < min_valid_window:
        safe_window = min_valid_window
    if safe_window > max_window:
        return arr.copy()
    return np.asarray(savgol_filter(arr, safe_window, poly), dtype=float)


def polyeval(coeffs: np.ndarray, n: int) -> np.ndarray:
    return np.polyval(coeffs, np.arange(n))


def compute_adjusted_baselines(
    control: np.ndarray,
    target: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    n = len(target)
    idx = np.arange(n)
    scale_factor = np.mean(target) / np.mean(control)
    scaled_control = control * scale_factor
    qfit_control = np.polyfit(idx, control, 2)
    qfit_target = np.polyfit(idx, target, 2)
    qfit_scaled = np.polyfit(idx, scaled_control, 2)
    control_quad = polyeval(qfit_control, n)
    raw_target_quad = polyeval(qfit_target, n)
    scaled_quad = polyeval(qfit_scaled, n)
    raw_df = (control - control_quad) / control_quad
    adjusted_1 = scaled_quad * raw_df + scaled_quad
    adjusted_2 = raw_target_quad * raw_df + raw_target_quad
    return adjusted_1, adjusted_2, raw_target_quad, scaled_quad


def detect_photometry_file_type(selectedfile: str | Path) -> tuple[str, int]:
    selectedfile = str(Path(selectedfile).expanduser().resolve())
    cols0 = pd.read_csv(selectedfile, nrows=0, low_memory=False).columns.astype(str).tolist()
    first0 = cols0[0] if cols0 else ""
    if first0 == "#time(seconds)":
        return "single", 0
    if first0 == "TimeStamp":
        return "dual", 0
    cols1 = pd.read_csv(selectedfile, nrows=0, skiprows=1, low_memory=False).columns.astype(str).tolist()
    first1 = cols1[0] if cols1 else ""
    if first1 == "TimeStamp":
        return "dual", 1
    raise ValueError(
        "Could not detect file type.\n\n"
        "Expected first column '#time(seconds)' (single) or 'TimeStamp' (dual).\n"
        "Dual files may have metadata in row 1 (we try skiprows=1)."
    )


def expected_analysis_output_path(
    selectedfile: str | Path,
    file_type: str | None = None,
) -> Path:
    selected_path = Path(selectedfile).expanduser().resolve()
    if file_type is None:
        file_type, _ = detect_photometry_file_type(selected_path)
    if file_type == "single":
        outdir = selected_path.parent / "dfof_results"
        outdir.mkdir(parents=True, exist_ok=True)
        return outdir / f"{selected_path.stem}_Data.csv"
    if file_type == "dual":
        outdir = selected_path.parent.parent / "dfof_results"
        outdir.mkdir(parents=True, exist_ok=True)
        safe_stem = "".join(
            c if c not in '<>:"/\\|?*' else "_"
            for c in (selected_path.parent.name or selected_path.stem)
        ).strip()
        return outdir / f"{safe_stem}_Dual_Data.csv"
    raise ValueError("file_type must be 'single' or 'dual'")


def window_slice(length: int, dt_sec: float, w_start: str, w_end: str) -> tuple[slice, int, int]:
    if w_start:
        win_start = (float(w_start) / dt_sec) + 1
        if win_start < 0:
            win_start = 1
            logger.warning("Start of window cannot precede the first data point.")
    else:
        win_start = 1

    if w_end:
        win_end = (float(w_end) / dt_sec) + 1
        if win_end > length:
            win_end = length
            logger.warning("End of window cannot exceed the last data point.")
    else:
        win_end = length

    min_samples = int(np.ceil(120.0 / dt_sec))
    if (win_end < win_start) or ((win_end - win_start) < (min_samples - 1)):
        raise ValueError(
            "End time cannot precede Start time, and analysis window must be at least 120 seconds.")

    return slice(int(win_start) - 1, int(win_end)), int(win_start), int(win_end)
