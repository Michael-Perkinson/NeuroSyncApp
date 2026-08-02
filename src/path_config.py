from __future__ import annotations

import sys
from pathlib import Path

"""
Central path configuration shared by the embedded dfer package.

Output files are written relative to the project root by default.
Call configure_paths() to redirect them anywhere (e.g. user Documents).
"""


def _resolve_default_root() -> Path:
    if getattr(sys, "frozen", False):
        # Frozen bundle: write outputs to a persistent user-visible location
        return Path.home() / "Documents" / "NeuroSyncApp"
    return Path(__file__).resolve().parent.parent


_DEFAULT_ROOT = _resolve_default_root()

module: str
data: str
results: str
peakF_results: str
processor: str


def configure_paths(root: str | Path) -> None:
    root_path = Path(root).expanduser().resolve()
    global module, data, results, peakF_results, processor
    module = str(root_path)
    data = str(root_path / "Raw_data")
    results = str(root_path / "DF_Results")
    peakF_results = str(root_path / "PeakF_Results")
    processor = str(root_path / "Processor")


configure_paths(_DEFAULT_ROOT)
