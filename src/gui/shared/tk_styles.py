"""Shared ttk style configuration for the Tk GUI."""

from __future__ import annotations

import tkinter.ttk as ttk


def define_custom_ttk_styles(style: ttk.Style | None = None) -> ttk.Style:
    """Configure and return the shared ttk styles used by the Tk app."""
    style = style or ttk.Style()
    style.configure("Custom.TFrame", background="snow")
    style.configure(
        "Bordered.TFrame",
        background="snow",
        borderwidth=2,
        relief="solid",
        bordercolor="black",
    )
    style.configure(
        "Custom.TCheckbutton",
        background="snow",
        foreground="black",
        font=("Helvetica", 10),
        compound="left",
        padding=(20, 0, 0, 0),
        wraplength=150,
    )
    style.configure(
        "CustomScale.TScale",
        background="snow",
        troughcolor="lightgray",
        gripcount=0,
    )
    style.configure("NoBorder.TFrame", background="snow", borderwidth=0, padding=0)
    style.configure("CustomNotebook.TNotebook", background="snow")
    style.configure("CustomNotebook.TFrame", background="snow")
    style.configure(
        "Custom.TMenubutton",
        background="snow",
        width=10,
        font=("Helvetica", 10),
        bd=1,
        relief="solid",
        indicatoron=True,
    )
    return style
