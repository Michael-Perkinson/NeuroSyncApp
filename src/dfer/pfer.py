from __future__ import annotations

import logging
import time
from pathlib import Path

import numpy as np

from .df_common import (
    missing_columns,
    raise_missing_columns,
    read_analysis_output,
)
from .pfer_detection import (
    DEFAULT_ART_THRESHOLD,
    DEFAULT_PROMINENCE,
    PFerResult,
    analyze_signal,
    baseline_mask,
    signal_specs,
)
from .pfer_plots import build_bokeh_plots

logger = logging.getLogger(__name__)


def _stats_output_path(
    outdir: Path, stem: str, signal_name: str, is_dual: bool
) -> Path:
    if is_dual:
        return outdir / f"{stem}_{signal_name}_Peak_STATS.csv"
    return outdir / f"{stem}_Peak_STATS.csv"


def _waveform_output_path(
    outdir: Path, stem: str, signal_name: str, is_dual: bool
) -> Path:
    if is_dual:
        return outdir / f"{stem}_{signal_name}_Peak_WAVEFORM.csv"
    return outdir / f"{stem}_Peak_WAVEFORM.csv"


def _export_results(
    outdir: Path, stem: str, signal_name: str, result: PFerResult, is_dual: bool
) -> Path:
    out_path = _stats_output_path(outdir, stem, signal_name, is_dual)
    np.savetxt(
        out_path,
        np.c_[
            result["peak_min"],
            result["trough_min"],
            result["peak_amp"],
            result["trough_amp"],
            result["amplitudes"],
            result["rise_t"],
        ],
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

    df = read_analysis_output(csv_path)
    df.columns = [str(col).strip().lstrip("#").strip() for col in df.columns]

    missing = missing_columns(df, ["t_min"])
    if missing:
        raise_missing_columns(
            "PFer input",
            missing,
            "t_min plus DFer output columns such as dFoF_465/dFoF_405 or dFoF_470/dFoF_560",
        )

    if len(df.index) < 3:
        raise ValueError("PFer input CSV must contain at least 3 rows of data.")

    t_vec = df["t_min"].to_numpy(dtype=float)
    baseline = baseline_mask(t_vec, w_start, w_end)
    dataset_kind, specs = signal_specs(df)

    traces: dict[str, np.ndarray] = {}
    results: dict[str, PFerResult] = {}
    output_paths: list[Path] = []

    logger.info("Begin PFer analysis: %s", filename)
    logger.info("Detected %s PFer input", dataset_kind)

    for spec in specs:
        signal_name = spec["name"]
        signal_trace = df[spec["signal_col"]].to_numpy(dtype=float)
        signal_trace = signal_trace - np.percentile(signal_trace, 2)

        baseline_source = df[spec["baseline_col"]].to_numpy(dtype=float)
        baseline_source = baseline_source - np.percentile(baseline_source, 2)
        baseline_trace = baseline_source[baseline]

        logger.info("Cleaning up peaks for channel %s...", signal_name)
        result = analyze_signal(
            t_vec=t_vec,
            signal_trace=signal_trace,
            baseline_trace=baseline_trace,
            prominence=prominence,
            artifact_threshold=artifact_threshold,
        )

        traces[signal_name] = signal_trace
        results[signal_name] = result
        output_paths.append(
            _export_results(
                outdir, stem, signal_name, result, is_dual=(dataset_kind == "dual")
            )
        )

        logger.info("Final peak count (%s): %s", signal_name, result["peak_count"])
        amplitudes = result["amplitudes"]
        rise_t = result["rise_t"]
        if len(amplitudes) > 0:
            logger.info("Mean amplitude (%s): %.4f", signal_name, np.mean(amplitudes))
            logger.info("Mean rise time (%s): %.2f s", signal_name, np.mean(rise_t))

        baseline_peak_count = int(result["baseline_peak_count"])
        baseline_amp_mean = result["baseline_amp_mean"]
        if (
            dataset_kind == "single"
            and result["peak_count"] > 0
            and baseline_peak_count > 0
        ):
            if result["peak_count"] < baseline_peak_count:
                logger.warning(
                    "PFer warning 1: data may not be suitable for PFer analysis"
                )
            if (
                len(amplitudes) > 0
                and baseline_amp_mean is not None
                and (float(np.mean(amplitudes)) * 0.85) < baseline_amp_mean
            ):
                logger.warning(
                    "PFer warning 2: data may not be suitable for PFer analysis"
                )

    if make_plots:
        build_bokeh_plots(filename, t_vec, specs, traces, results)

    logger.info("%s PFer analysis complete", filename)
    time.sleep(1)
    logger.info("Ready for next file")

    if dataset_kind == "single":
        return str(output_paths[0])
    return "\n".join(str(path) for path in output_paths)
