from __future__ import annotations

import inspect
import subprocess
import sys
from pathlib import Path

import src.features.raw_photometry.photometry_processing_widget as raw_widget
from src import dfer

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_import_probe(module: str) -> set[str]:
    code = f"""
import sys
import {module}
print("\\n".join(name for name in sys.modules if name in {{
    "src.dfer.analysis",
    "src.dfer.pfer",
    "src.dfer.df_common",
    "src.features.raw_photometry.plotting",
}}))
"""
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return {line for line in completed.stdout.splitlines() if line}


def test_dfer_public_import_defers_analysis_and_pfer_modules():
    imported = _run_import_probe("src.dfer")

    assert imported == set()


def test_raw_widget_import_defers_analysis_and_result_plot_modules():
    imported = _run_import_probe(
        "src.features.raw_photometry.photometry_processing_widget"
    )

    assert imported == set()


def test_dfer_lazy_wrappers_preserve_public_signatures():
    compute_options = inspect.signature(dfer.compute_options)
    assert tuple(compute_options.parameters) == ("selectedfile", "w_start", "w_end")
    assert compute_options.parameters["w_start"].default == ""
    assert compute_options.parameters["w_end"].default == ""

    run_analysis = inspect.signature(dfer.run_analysis)
    assert tuple(run_analysis.parameters) == (
        "selectedfile",
        "w_start",
        "w_end",
        "analysis_path",
        "make_plots",
        "mode",
        "plot_stage",
    )
    assert run_analysis.parameters["analysis_path"].default == "1"
    assert run_analysis.parameters["make_plots"].default is False
    assert run_analysis.parameters["mode"].default == "full"
    assert run_analysis.parameters["plot_stage"].default == "all"

    run_pfer = inspect.signature(dfer.run_pfer)
    assert tuple(run_pfer.parameters) == (
        "csv_path",
        "w_start",
        "w_end",
        "prominence",
        "artifact_threshold",
        "make_plots",
    )
    assert run_pfer.parameters["prominence"].default == 0.003
    assert run_pfer.parameters["artifact_threshold"].default == 10
    assert run_pfer.parameters["make_plots"].default is False


def test_raw_widget_lazy_wrappers_preserve_helper_signatures():
    assert tuple(
        inspect.signature(raw_widget.detect_photometry_file_type).parameters
    ) == ("selectedfile",)
    assert tuple(inspect.signature(raw_widget.load_dual_photometry).parameters) == (
        "selectedfile",
        "skiprows",
    )
    assert (
        inspect.signature(raw_widget.load_dual_photometry)
        .parameters["skiprows"]
        .default
        == 0
    )
    assert tuple(
        inspect.signature(raw_widget._mpl_dfer_results_figure_from_frame).parameters
    ) == ("df", "graph", "show_405")
