from typing import Union

from PySide6.QtWidgets import QMessageBox, QWidget


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
