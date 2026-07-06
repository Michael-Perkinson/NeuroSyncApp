from __future__ import annotations

import pandas as pd
from PySide6.QtWidgets import QApplication

from src.features.telemetry_alignment.app import TelemetryPhotomOptoProcessingApp


def test_telemetry_qt_app_instantiates():
    app = QApplication.instance() or QApplication([])
    widget = TelemetryPhotomOptoProcessingApp()
    assert widget.top_frame_layout.count() == 3
    assert widget.bottom_frame_layout.count() == 2
    widget.deleteLater()


def test_telemetry_sample_rate_uses_full_datetimes_across_midnight():
    app = QApplication.instance() or QApplication([])
    widget = TelemetryPhotomOptoProcessingApp()

    sample_rate = widget.calculate_sample_rate(
        pd.to_datetime(
            [
                "2024-01-01 23:59:50",
                "2024-01-02 00:00:00",
                "2024-01-02 00:00:10",
            ]
        ).to_list()
    )

    assert sample_rate == 10
    widget.deleteLater()
