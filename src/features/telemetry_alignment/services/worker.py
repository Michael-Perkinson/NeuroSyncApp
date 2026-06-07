"""Background worker for running heavy telemetry operations off the Qt main thread."""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, QThread, Signal

logger = logging.getLogger(__name__)


class Worker(QObject):
    """Runs a single callable on a background thread and emits signals when done."""

    finished = Signal()
    error = Signal(Exception)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            self._fn(*self._args, **self._kwargs)
        except Exception as exc:
            logger.exception("Background worker error: %s", exc)
            self.error.emit(exc)
        else:
            self.finished.emit()


def run_in_background(fn, on_success=None, on_error=None, parent=None):
    """
    Run *fn* on a QThread and call *on_success* / *on_error* on the main thread
    when it completes.  Returns (worker, thread) so the caller can keep references.
    """
    worker = Worker(fn)
    thread = QThread(parent)
    worker.moveToThread(thread)

    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit)
    worker.error.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)

    if on_success:
        worker.finished.connect(on_success)
    if on_error:
        worker.error.connect(on_error)

    thread.start()
    return worker, thread
