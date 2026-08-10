from __future__ import annotations

from PySide6.QtWidgets import QApplication

from src.features.behaviour_alignment.data_processing_widget import (
    DataProcessingSingleInstance,
)
from src.features.behaviour_alignment.services.plot_service import (
    _signal_y_axis_label,
)
from src.features.behaviour_alignment.views.ui_builder import (
    _trace_colour_control_labels,
)


def test_behaviour_qt_app_instantiates():
    _app = QApplication.instance() or QApplication([])
    widget = DataProcessingSingleInstance()
    assert widget.main_frame_layout.count() == 3
    assert widget.bottom_frame_layout.count() == 2
    widget.deleteLater()


def test_trace_colour_controls_name_the_primary_signal():
    assert _trace_colour_control_labels(["dFoF_465", "dFoF_405"]) == (
        "dFoF_465 Trace Colour:",
        "dFoF_465 SEM Colour:",
    )


def test_signal_y_axis_label_matches_plotted_values():
    columns = ["dFoF_465", "dFoF_405"]

    assert _signal_y_axis_label(columns, z_scored=False) == "dF/F"
    assert _signal_y_axis_label(columns, z_scored=True) == "Z-score"
    assert _signal_y_axis_label(["dFoF_465"], z_scored=False) == "dFoF_465"
