"""DFer/PFer raw photometry analysis.

This package ports the Argotech/Tussock Innovation DFer_v1.4 + PFer_2.4
analysis workflow (OCT-2024). That workflow is based on analysis methods from
GuPPy:

Sherathiya, V. N., Schaid, M. D., Seiler, J. L., Lopez, G. C., & Lerner, T. N.
GuPPy, a Python toolbox for the analysis of fiber photometry data.
Scientific Reports 11, 24212 (2021). https://doi.org/10.1038/s41598-021-03626-9
"""

from __future__ import annotations

from pathlib import Path


def compute_options(
    selectedfile: str | Path,
    w_start: str = "",
    w_end: str = "",
) -> dict:
    """Compute DFer option traces, importing the analysis stack on demand."""
    from .analysis import compute_options as _compute_options

    return _compute_options(selectedfile, w_start, w_end)


def run_analysis(
    selectedfile: str | Path,
    w_start: str = "",
    w_end: str = "",
    analysis_path: str = "1",
    make_plots: bool = False,
    mode: str = "full",
    plot_stage: str = "all",
) -> str:
    """Run DFer, importing the analysis stack on demand."""
    from .analysis import run_analysis as _run_analysis

    return _run_analysis(
        selectedfile,
        w_start,
        w_end,
        analysis_path,
        make_plots,
        mode,
        plot_stage,
    )


def run_pfer(
    csv_path: str | Path,
    w_start: str = "",
    w_end: str = "",
    prominence: float = 0.003,
    artifact_threshold: int = 10,
    make_plots: bool = False,
) -> str:
    """Run PFer, importing the peak-finding stack on demand."""
    from .pfer import run_pfer as _run_pfer

    return _run_pfer(
        csv_path,
        w_start,
        w_end,
        prominence,
        artifact_threshold,
        make_plots,
    )


__all__ = ["compute_options", "run_analysis", "run_pfer"]
