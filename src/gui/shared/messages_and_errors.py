from tkinter import messagebox
from typing import Union


def show_error(title: str, message: Union[str, Exception]) -> None:
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
    messagebox.showerror(title, error_message)
