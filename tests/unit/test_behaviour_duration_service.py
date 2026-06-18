from __future__ import annotations

import sys
import types

import pandas as pd
import pytest
from matplotlib.figure import Figure


def _install_pyside_stub(monkeypatch):
    try:
        import PySide6  # noqa: F401
        return
    except ModuleNotFoundError:
        pass

    pyside_module = types.ModuleType("PySide6")
    qtcore_module = types.ModuleType("PySide6.QtCore")
    qtwidgets_module = types.ModuleType("PySide6.QtWidgets")

    class _Widget:
        def __init__(self, *args, **kwargs):
            pass

    qtcore_module.Qt = types.SimpleNamespace(Checked=2)
    qtwidgets_module.QCheckBox = _Widget
    qtwidgets_module.QComboBox = _Widget
    qtwidgets_module.QLineEdit = _Widget
    qtwidgets_module.QMessageBox = types.SimpleNamespace(
        critical=lambda *args, **kwargs: None,
        information=lambda *args, **kwargs: None,
    )

    monkeypatch.setitem(sys.modules, "PySide6", pyside_module)
    monkeypatch.setitem(sys.modules, "PySide6.QtCore", qtcore_module)
    monkeypatch.setitem(sys.modules, "PySide6.QtWidgets", qtwidgets_module)


def test_duration_cache_stores_minutes_independent_of_display_unit(monkeypatch):
    _install_pyside_stub(monkeypatch)

    from src.features.behaviour_alignment.services.manual_session_service import (
        BehaviourManualSessionService,
    )

    class GraphHelper:
        def convert_and_retrieve_time(self, value):
            raise AssertionError("duration cache should not use display conversion")

    app = types.SimpleNamespace(
        duration_data_cache={},
        graph_helper_service=GraphHelper(),
    )
    service = BehaviourManualSessionService(app)

    service.calculate_and_store_behavior_metrics(
        {"Explore": {"start_times": [0.0, 10.0], "end_times": [60.0, 70.0]}}
    )

    cached = app.duration_data_cache["Explore"]
    assert cached["mean_duration"] == pytest.approx(1.0)
    assert cached["sem_duration"] == 0.0
    assert cached["number_of_instances"] == 2


def test_duration_box_update_allows_canvas_to_be_embedded_later(monkeypatch):
    _install_pyside_stub(monkeypatch)

    from src.features.behaviour_alignment.services.plot_service import (
        update_duration_box,
    )

    class Value:
        def __init__(self, value):
            self.value = value

        def get(self):
            return self.value

    class GraphHelper:
        def get_time_scale(self, _unit):
            return 1.0

    fig = Figure()
    ax = fig.add_subplot(111)
    mean_sem_df = pd.DataFrame(
        {
            "Time": [-1.0, 0.0, 1.0],
            "Mean": [0.1, 0.4, 0.2],
            "SEM": [0.01, 0.02, 0.01],
        }
    )
    app = types.SimpleNamespace(
        fig=fig,
        figure_canvas=None,
        bar_items=[],
        behaviour_choice_graph=Value("Explore"),
        duration_data_cache={
            "Explore": {
                "mean_duration": 0.5,
                "sem_duration": 0.1,
                "mean_sem_df": mean_sem_df,
            }
        },
        graph_helper_service=GraphHelper(),
        graph_settings_container_instance=types.SimpleNamespace(
            display_duration_box_var=Value(True),
            time_unit_menu=Value("minutes"),
            duration_box_placement=Value("0.5"),
            bar_graph_size_entry=Value("0.1"),
            selected_bar_fill_color="#3366cc",
            selected_bar_border_color="#003399",
            selected_bar_sem_color="#111111",
        ),
    )

    update_duration_box(app, ax, mean_sem_df)

    assert app.bar_items
