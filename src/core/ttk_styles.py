"""Legacy compatibility wrapper for Tk ttk styles."""

from __future__ import annotations


def define_custom_ttk_styles(*_args, **_kwargs):
    """Raise a clear error directing callers to the GUI-specific style module."""
    raise RuntimeError(
        "Tk style helpers moved to src.gui.shared.tk_styles. "
        "Import define_custom_ttk_styles from there instead."
    )
