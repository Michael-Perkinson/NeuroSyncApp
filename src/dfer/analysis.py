from __future__ import annotations

from pathlib import Path

from .df_common import detect_photometry_file_type, expected_analysis_output_path
from .df_dual import compute_dual_options, run_dual_analysis
from .df_single import compute_single_options, run_single_analysis


def run_analysis(
    selectedfile: str | Path,
    w_start: str = "",
    w_end: str = "",
    analysis_path: str = "1",
    make_plots: bool = False,
    mode: str = "full",
    plot_stage: str = "all",
) -> str:
    """Run DFer on a single or dual photometry CSV.

    Set ``make_plots=True`` only when the optional ``html-plots`` extra is
    installed; the Qt app renders matplotlib figures inline instead.
    """
    if mode not in {"full", "options_only"}:
        raise ValueError("mode must be 'full' or 'options_only'")
    if plot_stage not in {"preview", "final", "all", "none"}:
        raise ValueError("plot_stage must be 'preview' | 'final' | 'all' | 'none'")

    do_preview_plots = make_plots and (plot_stage in {"preview", "all"})
    do_final_plots = make_plots and (plot_stage in {"final", "all"})

    selectedfile = str(Path(selectedfile).expanduser().resolve())
    filename = Path(selectedfile).name

    file_type, skiprows = detect_photometry_file_type(selectedfile)

    if file_type == "single":
        return run_single_analysis(
            selectedfile=selectedfile,
            filename=filename,
            w_start=w_start,
            w_end=w_end,
            analysis_path=analysis_path,
            do_preview_plots=do_preview_plots,
            do_final_plots=do_final_plots,
            mode=mode,
        )

    return run_dual_analysis(
        selectedfile=selectedfile,
        filename=filename,
        skiprows=skiprows,
        w_start=w_start,
        w_end=w_end,
        analysis_path=analysis_path,
        do_preview_plots=do_preview_plots,
        do_final_plots=do_final_plots,
        mode=mode,
    )


def compute_options(
    selectedfile: str | Path,
    w_start: str = "",
    w_end: str = "",
) -> dict:
    """Compute DFer option traces without plotting or saving files.

    Returns a dict of numpy arrays suitable for inline matplotlib display.
    Works for both single-channel and dual-channel photometry files.
    """
    selectedfile = str(Path(selectedfile).expanduser().resolve())
    file_type, skiprows = detect_photometry_file_type(selectedfile)

    if file_type == "single":
        return compute_single_options(selectedfile, w_start, w_end)

    return compute_dual_options(selectedfile, skiprows, w_start, w_end)


__all__ = [
    "detect_photometry_file_type",
    "expected_analysis_output_path",
    "run_analysis",
    "compute_options",
]
