from __future__ import annotations

from types import SimpleNamespace

import pandas as pd

from src.features.behaviour_alignment.services.data_service import BehaviourDataService


class _Value:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


def test_calculate_z_score_rejects_baseline_outside_recording(monkeypatch):
    warnings = []
    monkeypatch.setattr(
        "src.features.behaviour_alignment.services.data_service.QMessageBox.warning",
        lambda _app, title, message: warnings.append((title, message)),
    )
    app = SimpleNamespace(
        selected_columns_var=_Value(["Signal"]),
        selected_column_var=_Value("Signal"),
        figure_display_dropdown=_Value("Raw data"),
        data_selection_frame=SimpleNamespace(
            baseline_start_entry=_Value("600"),
            baseline_end_entry=_Value("660"),
        ),
        dataframe=pd.DataFrame(
            {"Time (min)": [0.0, 1.0, 2.0], "Signal": [1.0, 2.0, 3.0]}
        ),
        z_score_computed=False,
    )

    result = BehaviourDataService(app).calculate_z_score()

    assert result is None
    assert warnings == [
        (
            "Baseline is outside the recording",
            "The baseline range must overlap the loaded recording.",
        )
    ]
