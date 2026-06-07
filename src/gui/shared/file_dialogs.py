"""GUI file-dialog helpers."""

from __future__ import annotations

from PySide6.QtWidgets import QFileDialog, QWidget


def select_csv_file(parent: QWidget | None = None) -> str:
    """Open a file dialog and return the selected CSV file path."""
    file_path, _ = QFileDialog.getOpenFileName(
        parent,
        "Select CSV File",
        "",
        "CSV Files (*.csv)",
    )
    return file_path


def select_file(parent: QWidget | None = None) -> str:
    """Backward-compatible alias for CSV file selection."""
    return select_csv_file(parent)
