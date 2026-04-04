"""GUI file-dialog helpers."""

from __future__ import annotations

from tkinter import filedialog


def select_csv_file() -> str:
    """Open a file dialog and return the selected CSV file path."""
    return filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])


def select_file() -> str:
    """Backward-compatible alias for CSV file selection."""
    return select_csv_file()
