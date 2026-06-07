from __future__ import annotations

from PySide6.QtWidgets import QApplication

from src.features.telemetry_alignment.app import TelemetryPhotomOptoProcessingApp


def test_telemetry_qt_app_instantiates():
    app = QApplication.instance() or QApplication([])
    widget = TelemetryPhotomOptoProcessingApp()
    assert widget.top_frame_layout.count() == 3
    assert widget.bottom_frame_layout.count() == 2
    widget.deleteLater()
