from __future__ import annotations

import logging


class QtTextHandler(logging.Handler):
    def __init__(self, text_widget) -> None:
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record: logging.LogRecord) -> None:
        if self.text_widget is None:
            return
        message = self.format(record)
        try:
            self.text_widget.appendPlainText(message)
        except RuntimeError:
            # The underlying Qt widget's C++ object has been deleted (its
            # owning panel/tab was destroyed) but this handler is still
            # registered on the logger. Drop the dangling reference and
            # detach so subsequent log calls don't crash the app.
            self.text_widget = None
            logging.getLogger().removeHandler(self)
