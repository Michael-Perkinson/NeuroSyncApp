from __future__ import annotations

from types import SimpleNamespace

import pytest
from matplotlib.colors import to_rgba
from matplotlib.figure import Figure
from PySide6.QtWidgets import QApplication

from src.features.behaviour_alignment.data_processing_widget import (
    DataProcessingSingleInstance,
)
from src.features.behaviour_alignment.services.plot_service import (
    _column_colors,
    _column_sem_colors,
    _signal_y_axis_label,
    generate_behaviour_graph,
)
from src.features.behaviour_alignment.views.ui_builder import (
    _colour_control_labels,
    _trace_colour_control_labels,
)
from src.gui.framework.qt_graph_canvas import create_styled_figure


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


def test_trace_colour_controls_group_trace_and_sem_by_signal():
    assert _colour_control_labels(["dFoF_465", "dFoF_405"]) == [
        ("dFoF_465 Trace Colour:", "dFoF_465 SEM Colour:"),
        ("dFoF_405 Trace Colour:", "dFoF_405 SEM Colour:"),
    ]


def test_signal_y_axis_label_matches_plotted_values():
    columns = ["dFoF_465", "dFoF_405"]

    assert _signal_y_axis_label(columns, z_scored=False) == "dF/F"
    assert _signal_y_axis_label(columns, z_scored=True) == "Z-score"
    assert _signal_y_axis_label(["dFoF_465"], z_scored=False) == "dFoF_465"


def test_styled_behaviour_figure_hides_top_and_right_spines():
    _figure, axis = create_styled_figure()

    assert not axis.spines["top"].get_visible()
    assert not axis.spines["right"].get_visible()


def test_extra_signal_colours_are_distinct_without_overrides():
    class Settings:
        selected_trace_color = "green"

    class App:
        def __init__(self):
            self.settings_manager = Settings()
            self.column_colors = {}

    assert _column_colors(App(), ["dFoF_465", "dFoF_405", "filtered_465"]) == [
        "green",
        "#ff7f0e",
        "#2ca02c",
    ]


def test_extra_signal_sem_colours_are_independently_customisable():
    class Settings:
        selected_trace_color = "green"
        selected_sem_color = "black"

    class App:
        def __init__(self):
            self.settings_manager = Settings()
            self.column_colors = {"dFoF_405": "#123456"}
            self.column_sem_colors = {"dFoF_405": "#abcdef"}

    assert _column_sem_colors(App(), ["dFoF_465", "dFoF_405"]) == [
        "black",
        "#abcdef",
    ]


def test_behaviour_graph_uses_the_selected_signal_sem_colour():
    figure = Figure()
    axis = figure.add_subplot(111)
    app = SimpleNamespace(
        settings_manager=SimpleNamespace(
            selected_trace_color="#123456",
            selected_sem_color="#654321",
        ),
        selected_column_var=SimpleNamespace(get=lambda: "dFoF_405"),
        graph_helper_service=SimpleNamespace(
            convert_and_retrieve_time=lambda values, return_label=True: (
                values,
                "Time (s)",
            )
        ),
        graph_settings_container_instance=SimpleNamespace(
            line_width_entry=SimpleNamespace(get=lambda: "1.0")
        ),
    )

    generate_behaviour_graph(
        axis,
        app,
        {"instance_1": [0.0, 1.0, 2.0], "instance_2": [1.0, 2.0, 3.0]},
        [0, 1, 2],
        -1.0,
        1.0,
        color="#123456",
        sem_color="#abcdef",
    )

    assert axis.collections
    expected_facecolor = (*to_rgba("#abcdef")[:3], 0.5)
    assert axis.collections[0].get_facecolor()[0] == pytest.approx(expected_facecolor)
