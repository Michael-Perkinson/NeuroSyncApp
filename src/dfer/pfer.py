from __future__ import annotations

import logging
import time
from collections.abc import Mapping
from pathlib import Path
from typing import TypedDict, cast

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from scipy.signal import find_peaks

from src import default_dirs

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Peak-finding parameters
# ---------------------------------------------------------------------------
DEFAULT_PROMINENCE = 0.003
DEFAULT_ART_THRESHOLD = 10     # minimum samples between trough and peak
DEFAULT_AMP_THRESHOLD = 0.01   # minimum trough-to-peak amplitude (dF/F)
DEFAULT_Z_THRESHOLD = 0.3      # minimum Z-score for a peak to be kept
END_GUARD_SEC = 10             # ignore peaks in the last N seconds
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


def _set_axis_labels(plot, x_label: str, y_label: str) -> None:
    plot.xaxis.axis_label = x_label
    plot.yaxis.axis_label = y_label


def _missing_columns(df: pd.DataFrame, required: list[str]) -> list[str]:
    return [column for column in required if column not in df.columns]


def _raise_missing_columns(missing: list[str], expected_help: str) -> None:
    missing_str = ", ".join(f"'{column}'" for column in missing)
    raise ValueError(
        f"PFer input CSV is missing required column(s): {missing_str}\n\n"
        f"Expected columns: {expected_help}"
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

    peak_id = np.column_stack([peaks_arr, np.ones(len(peaks_arr))])
    trough_id = np.column_stack([troughs_arr, np.full(len(troughs_arr), 2)])
    combined = np.vstack([peak_id, trough_id])
    order = np.argsort(combined[:, 0])
    types = combined[order, 1].astype(int)
    jitter = np.where(np.diff(types) == 0)[0]

    for idx in reversed(jitter):
        del_pos = idx // 2
        if types[idx] == 2:
            troughs_arr = np.delete(troughs_arr, del_pos)
        else:
            peaks_arr = np.delete(peaks_arr, del_pos)
            if prom_arr is not None:
                prom_arr = np.delete(prom_arr, del_pos)
            if width_arr is not None:
                width_arr = np.delete(width_arr, del_pos)

    return peaks_arr, troughs_arr, prom_arr, width_arr


def _baseline_mask(t_vec: np.ndarray, w_start: str, w_end: str) -> np.ndarray:
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


def _waveforms_for_peaks(
    signal_trace: np.ndarray,
    t_vec: np.ndarray,
    peak_times_min: np.ndarray,
) -> tuple[list[NDArray[np.float64]], NDArray[np.float64] | None, NDArray[np.float64] | None]:
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
    peaks, raw_peak_props = find_peaks(trace, prominence=prominence, width=0, rel_height=0.5)
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
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    return (
        peaks[mask], troughs[mask], peak_amp[mask], trough_amp[mask],
        peak_min[mask], trough_min[mask], amplitudes[mask], rise_t[mask],
    )


def _baseline_amplitude_mean(
    baseline_trace: np.ndarray,
    baseline_peaks: np.ndarray,
    baseline_troughs: np.ndarray,
) -> float | None:
    if len(baseline_peaks) == 0 or len(baseline_troughs) == 0:
        return None
    n_base = min(len(baseline_peaks), len(baseline_troughs))
    baseline_amps = baseline_trace[baseline_peaks[:n_base]] - baseline_trace[baseline_troughs[:n_base]]
    if len(baseline_amps) == 0:
        return None
    return float(np.mean(baseline_amps))


def _analyze_signal(
    t_vec: np.ndarray,
    signal_trace: np.ndarray,
    baseline_trace: np.ndarray,
    prominence: float,
    artifact_threshold: int,
) -> PFerResult:
    end_t = float(t_vec.max())

    peaks, troughs, peak_prom, peak_width = _find_peak_features(signal_trace, prominence)
    baseline_peaks, baseline_troughs, _, _ = _find_peak_features(baseline_trace, prominence)

    peaks, troughs, peak_prom_opt, peak_width_opt = _fix_jitter(peaks, troughs, peak_prom, peak_width)
    baseline_peaks, baseline_troughs, _, _ = _fix_jitter(baseline_peaks, baseline_troughs)

    if peak_prom_opt is None or peak_width_opt is None:
        raise ValueError("Peak properties were unavailable for the detected signal peaks.")
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
    peaks, troughs, peak_amp, trough_amp, peak_min, trough_min, amplitudes, rise_t = _apply_peak_mask(
        amp_ok, peaks, troughs, peak_amp, trough_amp, peak_min, trough_min, amplitudes, rise_t)

    sigma = float(np.std(baseline_trace))
    if sigma == 0:
        sigma = np.finfo(float).eps

    z_value = amplitudes / sigma
    z_ok = z_value > DEFAULT_Z_THRESHOLD
    peaks, troughs, peak_amp, trough_amp, peak_min, trough_min, amplitudes, rise_t = _apply_peak_mask(
        z_ok, peaks, troughs, peak_amp, trough_amp, peak_min, trough_min, amplitudes, rise_t)

    end_thresh = end_t - (END_GUARD_SEC / 60.0)
    end_ok = (peak_min < end_thresh) & (trough_min < end_thresh)
    peaks, troughs, peak_amp, trough_amp, peak_min, trough_min, amplitudes, rise_t = _apply_peak_mask(
        end_ok, peaks, troughs, peak_amp, trough_amp, peak_min, trough_min, amplitudes, rise_t)

    sigs, waveform_time, mean_wave = _waveforms_for_peaks(signal_trace, t_vec, peak_min)
    baseline_amp_mean = _baseline_amplitude_mean(baseline_trace, baseline_peaks, baseline_troughs)

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


def _signal_specs(df: pd.DataFrame) -> tuple[str, list[dict[str, str]]]:
    if "dFoF_465" in df.columns and "dFoF_405" in df.columns:
        return "single", [
            {"name": "465", "signal_col": "dFoF_465", "baseline_col": "dFoF_405", "color": "green"}
        ]

    dual_specs: list[dict[str, str]] = []
    if "dFoF_470" in df.columns:
        dual_specs.append({"name": "470", "signal_col": "dFoF_470",
                          "baseline_col": "dFoF_470", "color": "green"})
    if "dFoF_560" in df.columns:
        dual_specs.append({"name": "560", "signal_col": "dFoF_560",
                          "baseline_col": "dFoF_560", "color": "red"})
    if dual_specs:
        return "dual", dual_specs

    raise ValueError(
        "Could not find supported dF/F columns in PFer input CSV.\n\n"
        "Expected either:\n"
        "- single-output columns: dFoF_465 and dFoF_405\n"
        "- dual-output columns: dFoF_470 and/or dFoF_560"
    )


def _stats_output_path(outdir: Path, stem: str, signal_name: str, is_dual: bool) -> Path:
    if is_dual:
        return outdir / f"{stem}_{signal_name}_Peak_STATS.csv"
    return outdir / f"{stem}_Peak_STATS.csv"


def _waveform_output_path(outdir: Path, stem: str, signal_name: str, is_dual: bool) -> Path:
    if is_dual:
        return outdir / f"{stem}_{signal_name}_Peak_WAVEFORM.csv"
    return outdir / f"{stem}_Peak_WAVEFORM.csv"


def _export_results(outdir: Path, stem: str, signal_name: str, result: PFerResult, is_dual: bool) -> Path:
    out_path = _stats_output_path(outdir, stem, signal_name, is_dual)
    np.savetxt(
        out_path,
        np.c_[result["peak_min"], result["trough_min"], result["peak_amp"],
              result["trough_amp"], result["amplitudes"], result["rise_t"]],
        delimiter=",",
        header="peak_time_min,trough_time_min,peak_amplitude,trough_amplitude,relative_amplitude,rise_time_s",
        fmt="%f",
    )

    waveform_time = result["waveform_time"]
    mean_wave = result["mean_wave"]
    if waveform_time is not None and mean_wave is not None:
        wave_path = _waveform_output_path(outdir, stem, signal_name, is_dual)
        np.savetxt(
            wave_path,
            np.c_[waveform_time, mean_wave],
            delimiter=",",
            header="time_s,mean_peak_waveform_dFoF",
            fmt="%f",
        )

    return out_path


def _build_bokeh_plots(
    filename: str,
    t_vec: np.ndarray,
    signal_specs: list[dict[str, str]],
    traces: dict[str, np.ndarray],
    results: dict[str, PFerResult],
) -> None:
    from bokeh.layouts import column  # lazy
    from bokeh.plotting import figure, output_file, save  # lazy

    figures = []
    for spec in signal_specs:
        signal_name = spec["name"]
        color = spec["color"]
        trace = traces[signal_name]
        result = results[signal_name]

        peak_min = result["peak_min"]
        trough_min = result["trough_min"]
        peak_amp = result["peak_amp"]
        trough_amp = result["trough_amp"]
        sigs = result["sigs"]
        waveform_time = result["waveform_time"]
        mean_wave = result["mean_wave"]

        p1 = figure(width=1000, height=360,
                    title=f"{filename}   Detected peaks ({signal_name})")
        _set_axis_labels(p1, "Time (min)", "dF/F")
        p1.line(t_vec, trace, line_color=color, line_width=0.6)
        if len(peak_min) > 0:
            p1.inverted_triangle(peak_min, peak_amp, color="red", size=7)
            p1.triangle(trough_min, trough_amp, color="black", size=7)
        figures.append(p1)

        p2 = figure(width=1000, height=320,
                    title=f"{filename}   Individual peak waveforms ({signal_name})")
        _set_axis_labels(p2, "Time (sec)", "dF/F")
        if sigs and waveform_time is not None:
            wave_xs = [waveform_time.tolist() for _ in sigs]
            wave_ys = [sig.tolist() for sig in sigs]
            p2.multi_line(wave_xs, wave_ys, line_color=color, line_width=0.6)
        figures.append(p2)

        p3 = figure(width=1000, height=320,
                    title=f"{filename}   Average waveform ({signal_name})")
        _set_axis_labels(p3, "Time (sec)", "dF/F")
        if waveform_time is not None and mean_wave is not None:
            p3.line(waveform_time, mean_wave, line_color=color, line_width=0.6)
        figures.append(p3)

    out_html = Path(default_dirs.processor) / "PFer_results.html"
    out_html.parent.mkdir(parents=True, exist_ok=True)
    output_file(str(out_html), title=filename)
    save(column(*figures))


def run_pfer(
    csv_path: str | Path,
    w_start: str = "",
    w_end: str = "",
    prominence: float = DEFAULT_PROMINENCE,
    artifact_threshold: int = DEFAULT_ART_THRESHOLD,
    make_plots: bool = False,
) -> str:
    """Run peak-finding (PFer) on a DFer output CSV.

    Single-channel DFer outputs keep the legacy single stats filename.
    Dual-channel DFer outputs write one stats/waveform pair per signal.
    Set ``make_plots=True`` only when the optional ``html-plots`` extra is
    installed; the Qt app renders matplotlib figures inline instead.
    """
    csv_path = str(Path(csv_path).expanduser().resolve())
    filename = Path(csv_path).name
    stem = Path(csv_path).stem

    outdir = Path(csv_path).parent
    outdir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(csv_path, index_col=False)
    df.columns = [str(col).strip().lstrip("#").strip() for col in df.columns]

    if "t_min" not in df.columns:
        _raise_missing_columns(
            ["t_min"], "t_min plus DFer output columns such as dFoF_465/dFoF_405 or dFoF_470/dFoF_560")

    if len(df.index) < 3:
        raise ValueError("PFer input CSV must contain at least 3 rows of data.")

    t_vec = df["t_min"].to_numpy(dtype=float)
    baseline_mask = _baseline_mask(t_vec, w_start, w_end)
    dataset_kind, signal_specs = _signal_specs(df)

    traces: dict[str, np.ndarray] = {}
    results: dict[str, PFerResult] = {}
    output_paths: list[Path] = []

    logger.info("Begin PFer analysis: %s", filename)
    logger.info("Detected %s PFer input", dataset_kind)

    for spec in signal_specs:
        signal_name = spec["name"]
        signal_trace = df[spec["signal_col"]].to_numpy(dtype=float)
        signal_trace = signal_trace - np.percentile(signal_trace, 2)

        baseline_source = df[spec["baseline_col"]].to_numpy(dtype=float)
        baseline_source = baseline_source - np.percentile(baseline_source, 2)
        baseline_trace = baseline_source[baseline_mask]

        logger.info("Cleaning up peaks for channel %s...", signal_name)
        result = _analyze_signal(
            t_vec=t_vec,
            signal_trace=signal_trace,
            baseline_trace=baseline_trace,
            prominence=prominence,
            artifact_threshold=artifact_threshold,
        )

        traces[signal_name] = signal_trace
        results[signal_name] = result
        output_paths.append(_export_results(outdir, stem, signal_name, result, is_dual=(dataset_kind == "dual")))

        logger.info("Final peak count (%s): %s", signal_name, result["peak_count"])
        amplitudes = result["amplitudes"]
        rise_t = result["rise_t"]
        if len(amplitudes) > 0:
            logger.info("Mean amplitude (%s): %.4f", signal_name, np.mean(amplitudes))
            logger.info("Mean rise time (%s): %.2f s", signal_name, np.mean(rise_t))

        baseline_peak_count = int(result["baseline_peak_count"])
        baseline_amp_mean = result["baseline_amp_mean"]
        if dataset_kind == "single" and result["peak_count"] > 0 and baseline_peak_count > 0:
            if result["peak_count"] < baseline_peak_count:
                logger.warning("PFer warning 1: data may not be suitable for PFer analysis")
            if len(amplitudes) > 0 and baseline_amp_mean is not None:
                if (float(np.mean(amplitudes)) * 0.85) < baseline_amp_mean:
                    logger.warning("PFer warning 2: data may not be suitable for PFer analysis")

    if make_plots:
        _build_bokeh_plots(filename, t_vec, signal_specs, traces, results)

    logger.info("%s PFer analysis complete", filename)
    time.sleep(1)
    logger.info("Ready for next file")

    if dataset_kind == "single":
        return str(output_paths[0])
    return "\n".join(str(path) for path in output_paths)
