from __future__ import annotations

import logging
from typing import Union

from PySide6.QtWidgets import QMessageBox, QWidget


logger = logging.getLogger(__name__)


def describe_exception(error: BaseException) -> str:
    """Translate common technical exceptions into useful user-facing text."""
    detail = str(error).strip()

    if isinstance(error, KeyError):
        missing = detail.strip("'\"") or "an expected column"
        return f"The selected file is missing the required column '{missing}'."
    if isinstance(error, PermissionError):
        return (
            "NeuroSyncApp could not access the file. Close it in Excel or another "
            "program, check that you have permission to use the folder, and try again."
        )
    if isinstance(error, FileNotFoundError):
        return "The selected file or folder no longer exists. Select it again and retry."
    if "could not convert string to float" in detail.lower():
        return (
            "A value that should be numeric contains text. Check the selected file and "
            "any time or baseline fields, then try again."
        )
    if error.__class__.__name__ in {"ParserError", "EmptyDataError"}:
        return (
            "The selected file could not be read as tabular data. Check that it is a "
            "valid CSV or Excel file and that its delimiter and headers are correct."
        )
    return detail or "An unexpected error occurred."


def format_action_error(
    summary: str,
    error: BaseException,
    recovery: str | None = None,
) -> str:
    """Build a consistent action/cause/recovery message for GUI dialogs."""
    parts = [summary.rstrip(". ") + ".", describe_exception(error)]
    if recovery:
        parts.append(recovery.strip())
    return "\n\n".join(part for part in parts if part)


def show_action_error(
    title: str,
    summary: str,
    error: BaseException,
    parent: QWidget | None = None,
    recovery: str | None = None,
) -> None:
    """Log the technical failure and show a concise, recoverable GUI error."""
    logger.error("%s: %s", summary, error, exc_info=error)
    QMessageBox.critical(
        parent,
        title,
        format_action_error(summary, error, recovery),
    )


def show_error(
    title: str,
    message: Union[str, Exception],
    parent: QWidget | None = None,
) -> None:
    """
    Display an error message in a messagebox.

    Parameters:
    - title (str): The title of the error messagebox.
    - message (str | Exception): The error message or exception details to display.

    Returns:
    - None
    """

    # Ensure the message is a string
    error_message = str(message)
    QMessageBox.critical(parent, title, error_message)
