import tkinter as tk
from tkinter import ttk
from typing import Callable

# Constants (can be adjusted or overridden as needed)
DEFAULT_FONT = ("Helvetica", 10)
DEFAULT_BG = "snow"
DEFAULT_BUTTON_COLOR = "lightblue"


def create_label(parent: ttk.Frame, text: str, font: tuple = DEFAULT_FONT, bg: str = DEFAULT_BG, fg: str = "black") -> tk.Label:
    """
    Create a label widget.

    Parameters:
    - parent (ttk.Frame): The parent frame for the label.
    - text (str): The label text.
    - font (tuple): The font configuration (default: DEFAULT_FONT).
    - bg (str): Background color (default: DEFAULT_BG).
    - fg (str): Foreground (text) color (default: "black").

    Returns:
    - tk.Label: The created label widget.
    """
    return tk.Label(parent, text=text, font=font, bg=bg, fg=fg)


def create_entry(parent: ttk.Frame, variable: tk.StringVar, width: int = 20, font: tuple = DEFAULT_FONT, bg: str = DEFAULT_BG, fg: str = "black") -> tk.Entry:
    """
    Create an entry widget.

    Parameters:
    - parent (ttk.Frame): The parent frame for the entry.
    - variable (tk.StringVar): The StringVar to bind to the entry.
    - width (int): The width of the entry (default: 20).
    - font (tuple): The font configuration (default: DEFAULT_FONT).
    - bg (str): Background color (default: DEFAULT_BG).
    - fg (str): Foreground (text) color (default: "black").

    Returns:
    - tk.Entry: The created entry widget.
    """
    return tk.Entry(parent, textvariable=variable, width=width, font=font, bg=bg, fg=fg)


def create_button(parent: ttk.Frame, text: str, command: Callable[[], None], font: tuple = DEFAULT_FONT, bg: str = DEFAULT_BUTTON_COLOR, fg: str = "black") -> tk.Button:
    """
    Create a button widget.

    Parameters:
    - parent (ttk.Frame): The parent frame for the button.
    - text (str): The button text.
    - command (Callable[[], None]): The function to execute when the button is clicked.
    - font (tuple): The font configuration (default: DEFAULT_FONT).
    - bg (str): Background color (default: DEFAULT_BUTTON_COLOR).
    - fg (str): Foreground (text) color (default: "black").

    Returns:
    - tk.Button: The created button widget.
    """
    return tk.Button(parent, text=text, font=font, bg=bg, fg=fg, command=command)
