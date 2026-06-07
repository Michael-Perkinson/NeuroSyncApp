from __future__ import annotations

from PySide6.QtWidgets import QApplication

from src.features.behaviour_alignment.app import DataProcessingSingleInstance


def test_behaviour_qt_app_instantiates():
    app = QApplication.instance() or QApplication([])
    widget = DataProcessingSingleInstance()
    assert widget.main_frame_layout.count() == 3
    assert widget.bottom_frame_layout.count() == 2
    widget.deleteLater()
