"""Legacy compatibility wrapper for moved GUI file selection helpers."""

from __future__ import annotations


def select_file() -> str:
    raise RuntimeError(
        "File dialog helpers moved to src.gui.shared.file_dialogs.select_file."
    )
