"""Tkinter logging helpers for in-app log display."""

from __future__ import annotations

import logging


class TkTextHandler(logging.Handler):
    """Logging handler that appends formatted records into a Tk text widget."""

    def __init__(self, text_widget, max_lines: int = 250):
        super().__init__()
        self.text_widget = text_widget
        self.max_lines = max_lines

    def emit(self, record):
        try:
            message = self.format(record)
        except Exception:
            self.handleError(record)
            return

        def append():
            if not self.text_widget.winfo_exists():
                return

            self.text_widget.configure(state="normal")
            self.text_widget.insert("end", message + "\n")

            line_count = int(float(self.text_widget.index("end-1c").split(".")[0]))
            if line_count > self.max_lines:
                lines_to_trim = line_count - self.max_lines
                self.text_widget.delete("1.0", f"{lines_to_trim + 1}.0")

            self.text_widget.see("end")
            self.text_widget.configure(state="disabled")

        try:
            self.text_widget.after(0, append)
        except Exception:
            self.handleError(record)
