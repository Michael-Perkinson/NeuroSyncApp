"""Qt background-analysis and logging bridges for raw photometry."""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal


class AnalysisWorker(QObject):
    finished = Signal(object)
    failed = Signal(object)

    def __init__(self, fn, kwargs: dict) -> None:
        super().__init__()
        self._fn = fn
        self._kwargs = kwargs

    def run(self) -> None:
        try:
            result = self._fn(**self._kwargs)
        except Exception as exc:
            logging.getLogger(__name__).exception("Background analysis failed")
            self.failed.emit(exc)
        else:
            self.finished.emit(result)


class QtSignalLogHandler(logging.Handler):
    """Forward formatted log records through a Qt signal."""

    def __init__(self, signal: Signal) -> None:
        super().__init__()
        self._signal = signal

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._signal.emit(self.format(record))
        except RuntimeError:
            pass
