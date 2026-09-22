from __future__ import annotations

from collections.abc import Mapping
from typing import TypedDict, cast

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from scipy.signal import find_peaks

from .df_common import analysis_option_from_frame

# ---------------------------------------------------------------------------
# Peak-finding parameters
# ---------------------------------------------------------------------------
DEFAULT_PROMINENCE = 0.003
DEFAULT_ART_THRESHOLD = 10  # minimum samples between trough and peak
DEFAULT_AMP_THRESHOLD = 0.01  # minimum trough-to-peak amplitude (dF/F)
DEFAULT_Z_THRESHOLD = 0.3  # minimum Z-score for a peak to be kept
END_GUARD_SEC = 10  # ignore peaks in the last N seconds
WAVEFORM_HALF = 50
WAVEFORM_TAIL = 100


class PFerResult(TypedDict):
    peak_count: int
    peak_min: NDArray[np.float64]
    trough_min: NDArray[np.float64]
    peak_amp: NDArray[np.float64]
    trough_amp: NDArray[np.float64]
    amplitudes: NDArray[np.float64]
    rise_t: NDArray[np.float64]
    sigs: list[NDArray[np.float64]]
    waveform_time: NDArray[np.float64] | None
    mean_wave: NDArray[np.float64] | None
    baseline_peak_count: int
    baseline_amp_mean: float | None


def baseline_mask(t_vec: np.ndarray, w_start: str, w_end: str) -> np.ndarray:
    if not w_start:
        return np.ones_like(t_vec, dtype=bool)

    win_start_min = float(w_start) / 60.0
    win_end_min = float(w_end) / 60.0 if w_end else float(t_vec.max())

    if win_end_min - win_start_min < 5.0:
        raise ValueError(
            "Baseline period must be at least 5 minutes. "
            "Use a longer window or leave blank to use the full trace."
        )

    mask = (t_vec >= win_start_min) & (t_vec <= win_end_min)
    if not np.any(mask):
        raise ValueError("Baseline window does not overlap the recording.")
    return mask


def signal_specs(df: pd.DataFrame) -> tuple[str, list[dict[str, str]]]:
    if "dFoF_465" in df.columns and "dFoF_405" in df.columns:
        baseline_col = "dFoF_405"
        if analysis_option_from_frame(df) == 5:
            baseline_col = "dFoF_465"
        return "single", [
            {
                "name": "465",
                "signal_col": "dFoF_465",
                "baseline_col": baseline_col,
                "color": "green",
            }
        ]

    dual_specs: list[dict[str, str]] = []
    if "dFoF_470" in df.columns:
        dual_specs.append(
            {
                "name": "470",
                "signal_col": "dFoF_470",
                "baseline_col": "dFoF_470",
                "color": "green",
            }
        )
    if "dFoF_560" in df.columns:
        dual_specs.append(
            {
                "name": "560",
                "signal_col": "dFoF_560",
                "baseline_col": "dFoF_560",
                "color": "red",
            }
        )
    if dual_specs:
        return "dual", dual_specs

    raise ValueError(
        "Could not find supported dF/F columns in PFer input CSV.\n\n"
        "Expected either:\n"
        "- single-output columns: dFoF_465 and dFoF_405\n"
        "- dual-output columns: dFoF_470 and/or dFoF_560"
    )


def _fix_jitter(
    peaks_arr: np.ndarray,
    troughs_arr: np.ndarray,
    prom_arr: np.ndarray | None = None,
    width_arr: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None, np.ndarray | None]:
    if len(peaks_arr) == 0 or len(troughs_arr) == 0:
        return peaks_arr, troughs_arr, prom_arr, width_arr

    if peaks_arr[0] < troughs_arr[0]:
        peaks_arr = peaks_arr[1:]
        if prom_arr is not None:
            prom_arr = prom_arr[1:]
        if width_arr is not None:
            width_arr = width_arr[1:]

    if len(peaks_arr) == 0 or len(troughs_arr) == 0:
        return peaks_arr, troughs_arr, prom_arr, width_arr

    if peaks_arr[-1] < troughs_arr[-1]:
        troughs_arr = troughs_arr[:-1]

    if len(peaks_arr) == 0 or len(troughs_arr) == 0:
        return peaks_arr, troughs_arr, prom_arr, width_arr

    peak_id = np.column_stack(
        [peaks_arr, np.ones(len(peaks_arr)), np.arange(len(peaks_arr))]
    )
    trough_id = np.column_stack(
        [troughs_arr, np.full(len(troughs_arr), 2), np.arange(len(troughs_arr))]
    )
    combined = np.vstack([peak_id, trough_id])
    order = np.argsort(combined[:, 0])
    sorted_combined = combined[order]
    types = sorted_combined[:, 1].astype(int)
    jitter = np.where(np.diff(types) == 0)[0]

    peaks_to_delete = []
    troughs_to_delete = []
    for idx in jitter:
        if types[idx] == 2:
            orig_idx = int(sorted_combined[idx, 2])
            troughs_to_delete.append(orig_idx)
        else:
            orig_idx = int(sorted_combined[idx, 2])
            peaks_to_delete.append(orig_idx)

    peaks_arr = np.delete(peaks_arr, peaks_to_delete)
    troughs_arr = np.delete(troughs_arr, troughs_to_delete)
    if prom_arr is not None:
        prom_arr = np.delete(prom_arr, peaks_to_delete)
    if width_arr is not None:
        width_arr = np.delete(width_arr, peaks_to_delete)

    return peaks_arr, troughs_arr, prom_arr, width_arr


def _waveforms_for_peaks(
    signal_trace: np.ndarray,
    t_vec: np.ndarray,
    peak_times_min: np.ndarray,
) -> tuple[
    list[NDArray[np.float64]], NDArray[np.float64] | None, NDArray[np.float64] | None
]:
    peak_indices = np.searchsorted(t_vec, peak_times_min)
    waveform_len = WAVEFORM_HALF + WAVEFORM_TAIL

    sigs: list[np.ndarray] = []
    for idx in peak_indices:
        start = int(idx) - WAVEFORM_HALF
        end = int(idx) + WAVEFORM_TAIL
        if start < 0 or end > len(signal_trace):
            continue
        waveform = signal_trace[start:end]
        sigs.append(waveform - waveform.min())

    if not sigs:
        return sigs, None, None

    waveform_time = np.linspace(-0.085, 0.165, num=waveform_len) * 60
    mean_wave = np.asarray(np.mean(sigs, axis=0), dtype=float)
    return sigs, waveform_time, mean_wave


def _find_peak_features(
    trace: np.ndarray,
    prominence: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    peaks, raw_peak_props = find_peaks(
        trace, prominence=prominence, width=0, rel_height=0.5
    )
    troughs, _ = find_peaks(-trace, prominence=prominence, width=0, rel_height=0.5)
    peak_props = cast(Mapping[str, np.ndarray], raw_peak_props)
    peak_prom = np.asarray(peak_props["prominences"], dtype=float)
    peak_width = np.asarray(peak_props["widths"], dtype=float)
    return (
        np.asarray(peaks, dtype=int),
        np.asarray(troughs, dtype=int),
        peak_prom,
        peak_width,
    )


def _apply_peak_mask(
    mask: np.ndarray,
    peaks: np.ndarray,
    troughs: np.ndarray,
    peak_amp: np.ndarray,
    trough_amp: np.ndarray,
    peak_min: np.ndarray,
    trough_min: np.ndarray,
    amplitudes: np.ndarray,
    rise_t: np.ndarray,
) -> tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
]:
    return (
        peaks[mask],
        troughs[mask],
        peak_amp[mask],
        trough_amp[mask],
        peak_min[mask],
        trough_min[mask],
        amplitudes[mask],
        rise_t[mask],
    )


def _baseline_amplitude_mean(
    baseline_trace: np.ndarray,
    baseline_peaks: np.ndarray,
    baseline_troughs: np.ndarray,
) -> float | None:
    if len(baseline_peaks) == 0 or len(baseline_troughs) == 0:
        return None
    n_base = min(len(baseline_peaks), len(baseline_troughs))
    baseline_amps = (
        baseline_trace[baseline_peaks[:n_base]]
        - baseline_trace[baseline_troughs[:n_base]]
    )
    if len(baseline_amps) == 0:
        return None
    return float(np.mean(baseline_amps))


def analyze_signal(
    t_vec: np.ndarray,
    signal_trace: np.ndarray,
    baseline_trace: np.ndarray,
    prominence: float,
    artifact_threshold: int,
) -> PFerResult:
    end_t = float(t_vec.max())

    peaks, troughs, peak_prom, peak_width = _find_peak_features(
        signal_trace, prominence
    )
    baseline_peaks, baseline_troughs, _, _ = _find_peak_features(
        baseline_trace, prominence
    )

    peaks, troughs, peak_prom_opt, peak_width_opt = _fix_jitter(
        peaks, troughs, peak_prom, peak_width
    )
    baseline_peaks, baseline_troughs, _, _ = _fix_jitter(
        baseline_peaks, baseline_troughs
    )

    if peak_prom_opt is None or peak_width_opt is None:
        raise ValueError(
            "Peak properties were unavailable for the detected signal peaks."
        )
    peak_prom = peak_prom_opt
    peak_width = peak_width_opt

    if len(peaks) > 0 and len(troughs) > 0:
        n = min(len(peaks), len(troughs))
        legit = (peaks[:n] - troughs[:n]) > artifact_threshold
        peaks = peaks[:n][legit]
        troughs = troughs[:n][legit]
        peak_prom = peak_prom[:n][legit]
        peak_width = peak_width[:n][legit]

    peak_amp = signal_trace[peaks]
    trough_amp = signal_trace[troughs]
    peak_min = t_vec[peaks]
    trough_min = t_vec[troughs]
    amplitudes = peak_amp - trough_amp

    amp_ok = amplitudes > DEFAULT_AMP_THRESHOLD
    rise_t = (peak_min - trough_min) * 60
    peaks, troughs, peak_amp, trough_amp, peak_min, trough_min, amplitudes, rise_t = (
        _apply_peak_mask(
            amp_ok,
            peaks,
            troughs,
            peak_amp,
            trough_amp,
            peak_min,
            trough_min,
            amplitudes,
            rise_t,
        )
    )

    sigma = float(np.std(baseline_trace))
    if sigma == 0:
        sigma = float(np.finfo(float).eps)

    z_value = amplitudes / sigma
    z_ok = z_value > DEFAULT_Z_THRESHOLD
    peaks, troughs, peak_amp, trough_amp, peak_min, trough_min, amplitudes, rise_t = (
        _apply_peak_mask(
            z_ok,
            peaks,
            troughs,
            peak_amp,
            trough_amp,
            peak_min,
            trough_min,
            amplitudes,
            rise_t,
        )
    )

    end_thresh = end_t - (END_GUARD_SEC / 60.0)
    end_ok = (peak_min < end_thresh) & (trough_min < end_thresh)
    peaks, troughs, peak_amp, trough_amp, peak_min, trough_min, amplitudes, rise_t = (
        _apply_peak_mask(
            end_ok,
            peaks,
            troughs,
            peak_amp,
            trough_amp,
            peak_min,
            trough_min,
            amplitudes,
            rise_t,
        )
    )

    sigs, waveform_time, mean_wave = _waveforms_for_peaks(signal_trace, t_vec, peak_min)
    baseline_amp_mean = _baseline_amplitude_mean(
        baseline_trace, baseline_peaks, baseline_troughs
    )

    return {
        "peak_count": len(peaks),
        "peak_min": peak_min,
        "trough_min": trough_min,
        "peak_amp": peak_amp,
        "trough_amp": trough_amp,
        "amplitudes": amplitudes,
        "rise_t": rise_t,
        "sigs": sigs,
        "waveform_time": waveform_time,
        "mean_wave": mean_wave,
        "baseline_peak_count": len(baseline_peaks),
        "baseline_amp_mean": baseline_amp_mean,
    }
