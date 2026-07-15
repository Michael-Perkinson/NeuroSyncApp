from __future__ import annotations

import logging

import numpy as np
import shiboken6
from PySide6.QtWidgets import QApplication, QWidget

from src.app.dashboard import QtDashboard
from src.features.raw_photometry.app import RawPhotometryProcessingQt
from src.gui.shared.qt_log_handler import QtTextHandler
from src.gui.views.export_options_panel import ExportOptionsPanel


def test_shared_log_handler_detaches_after_deleted_text_widget():
    root_logger = logging.getLogger()
    original_level = root_logger.level

    class DeletedTextWidget:
        def appendPlainText(self, _message):
            raise RuntimeError("Internal C++ object already deleted")

    handler = QtTextHandler(DeletedTextWidget())
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    try:
        root_logger.info("late log")

        assert handler.text_widget is None
        assert handler not in root_logger.handlers
    finally:
        root_logger.removeHandler(handler)
        root_logger.setLevel(original_level)


def test_export_options_prepare_for_unload_detaches_log_handler():
    app = QApplication.instance() or QApplication([])
    panel = ExportOptionsPanel(
        None,
        file_path_var=None,
        settings_manager=None,
        extract_button_click_handler=lambda: None,
        save_image=lambda: None,
    )
    handler = panel.log_handler

    assert handler in logging.getLogger().handlers

    assert panel.prepare_for_unload() is True

    assert panel.log_handler is None
    assert handler not in logging.getLogger().handlers
    panel.deleteLater()


def test_dashboard_calls_unload_hook_before_deleting_content(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(QtDashboard, "_load_initial_app", lambda self: None)
    dashboard = QtDashboard()

    class UnloadAwareWidget(QWidget):
        def __init__(self):
            super().__init__()
            self.prepared = False

        def prepare_for_unload(self):
            self.prepared = True
            return True

    widget = UnloadAwareWidget()
    dashboard.content_layout.addWidget(widget)

    assert dashboard._clear_content() is True
    assert widget.prepared is True
    assert shiboken6.isValid(widget) is False
    dashboard.deleteLater()


def test_dashboard_keeps_content_when_unload_hook_blocks(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(QtDashboard, "_load_initial_app", lambda self: None)
    dashboard = QtDashboard()

    class BlockingWidget(QWidget):
        def prepare_for_unload(self):
            return False

    widget = BlockingWidget()
    dashboard.content_layout.addWidget(widget)

    assert dashboard._clear_content() is False
    assert dashboard.content_layout.count() == 1
    dashboard.content_layout.takeAt(0)
    widget.deleteLater()
    dashboard.deleteLater()


def test_raw_prepare_for_unload_detaches_log_handler():
    app = QApplication.instance() or QApplication([])
    widget = RawPhotometryProcessingQt()
    handler = widget._log_handler

    assert handler in logging.getLogger("src.dfer").handlers

    assert widget.prepare_for_unload() is True

    assert widget._log_handler is None
    assert handler not in logging.getLogger("src.dfer").handlers
    widget.deleteLater()


def test_dashboard_repeatedly_switches_tools_after_raw_canvas_creation(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(QtDashboard, "_load_initial_app", lambda self: None)
    dashboard = QtDashboard()

    dashboard.load_app("raw_analysis")
    raw_widget = dashboard.content_layout.itemAt(0).widget()
    time_values = np.array([0.0, 1.0, 2.0])
    raw_widget._draw_single_raw(
        time_values,
        np.array([1.0, 1.1, 1.2]),
        np.array([2.0, 2.1, 2.2]),
    )
    app.processEvents()

    previous_widget = raw_widget
    for tool_id in (
        "single_animal",
        "raw_analysis",
        "telemetry_photom_opto",
        "raw_analysis",
    ):
        dashboard.load_app(tool_id)
        assert shiboken6.isValid(previous_widget) is False
        previous_widget = dashboard.content_layout.itemAt(0).widget()
        app.processEvents()

    dashboard.close()
    app.processEvents()


def test_raw_failed_unload_restores_log_handler(monkeypatch):
    app = QApplication.instance() or QApplication([])
    widget = RawPhotometryProcessingQt()

    class RunningThread:
        quit_called = False

        @staticmethod
        def isRunning():
            return True

        def quit(self):
            self.quit_called = True

        @staticmethod
        def wait(_milliseconds):
            return False

    thread = RunningThread()
    widget._thread = thread
    monkeypatch.setattr(
        "src.features.raw_photometry.app.QMessageBox.information",
        lambda *_args, **_kwargs: None,
    )

    assert widget.prepare_for_unload() is False
    assert thread.quit_called is True
    assert widget._unloading is False
    assert widget._log_handler is not None
    assert widget._log_signal_connected is True

    widget._thread = None
    assert widget.prepare_for_unload() is True
    widget.deleteLater()
