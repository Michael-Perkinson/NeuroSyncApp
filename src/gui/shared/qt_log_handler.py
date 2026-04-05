from __future__ import annotations

import logging


class QtTextHandler(logging.Handler):
    def __init__(self, text_widget) -> None:
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record: logging.LogRecord) -> None:
        message = self.format(record)
        self.text_widget.appendPlainText(message)
