from __future__ import annotations

import types

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.features.telemetry_alignment.services.plot_service import TelemetryPlotService
from src.features.telemetry_alignment.views.display_mode_presenter import (
    TelemetryDisplayPresenter,
)
from src.processing.telemetry_processing import AmbiguousTelemetryAlignmentError


class _Value:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class _Settings:
    def __init__(self):
        self.selected_temp_mean_line_color = "red"
        self.selected_temp_mean_line_width = 1
        self.selected_temp_mean_line_alpha = 1
        self.selected_temp_sem_color = "red"
        self.selected_temp_sem_line_alpha = 0.2
        self.selected_temp_desired_scale = 1
        self.selected_temp_desired_offset = 0.5
        self.selected_activity_desired_scale = 1
        self.selected_activity_num_bins = ""
        self.selected_activity_mean_bar_color = "blue"
        self.selected_activity_mean_bar_alpha = 0.5
        self.light_off_time_var = ""

    def save_variables(self):
        pass


class _GraphSettings:
    def __init__(self, remove_first_60=True):
        self.temperature_data_var = _Value(True)
        self.activity_data_var = _Value(True)
        self.remove_first_60_minutes_var = _Value(remove_first_60)
        self.time_unit_menu = _Value("minutes")


class _App:
    def __init__(self):
        self.settings_manager = _Settings()
        self.graph_settings_container_instance = _GraphSettings()
        self.selected_display = _Value("Full Trace Display")
        self.act_sample_rate = 10

    def scale_time_column(self, time_column):
        return pd.Series(time_column).reset_index(drop=True)


def test_temperature_overlay_skips_nonfinite_values_without_axis_error():
    service = TelemetryPlotService(_App())
    fig, ax = plt.subplots()
    temp_data = pd.DataFrame(
        {"Time (min)": [0.0, 1.0], "Data": [np.nan, np.inf]}
    )

    try:
        assert service.overlay_temp_on_figure(ax, temp_data) is None
    finally:
        plt.close(fig)


def test_temperature_overlay_pads_single_finite_value():
    service = TelemetryPlotService(_App())
    fig, ax = plt.subplots()
    temp_data = pd.DataFrame({"Time (min)": [0.0], "Data": [37.0]})

    try:
        ax_temp = service.overlay_temp_on_figure(ax, temp_data)

        assert ax_temp is not None
        ymin, ymax = ax_temp.get_ylim()
        assert np.isfinite(ymin)
        assert np.isfinite(ymax)
        assert ymin < ymax
    finally:
        plt.close(fig)


def test_activity_overlay_skips_nonfinite_values_without_axis_error():
    service = TelemetryPlotService(_App())
    fig, ax = plt.subplots()
    act_data = pd.DataFrame(
        {"Time (min)": [0.0, 1.0], "Data": [np.nan, np.inf]}
    )

    try:
        assert service.overlay_act_on_figure(ax, act_data, 0.0, 1.0) is None
    finally:
        plt.close(fig)


def test_cached_telemetry_display_shift_can_be_reverted_without_reextracting():
    app = _App()
    app.data_type = "photometry"
    app.seconds_removed = 3600
    app.raw_aligned_temp_data = pd.DataFrame(
        {"Time (min)": [0.0, 60.0, 120.0], "Data": [36.5, 37.0, 37.5]}
    )
    app.raw_aligned_act_data = pd.DataFrame(
        {"Time (min)": [0.0, 60.0, 120.0], "Data": [1.0, 2.0, 3.0]}
    )
    app.raw_extended_temp_data = pd.DataFrame(
        {"Time (min)": [-60.0, 0.0, 60.0], "Data": [36.0, 36.5, 37.0]}
    )
    app.raw_extended_act_data = pd.DataFrame(
        {"Time (min)": [-60.0, 0.0, 60.0], "Data": [0.0, 1.0, 2.0]}
    )
    service = TelemetryPlotService(app)

    service.apply_cached_telemetry_for_current_display()

    assert app.temp_data["Time (min)"].tolist() == [-60.0, 0.0, 60.0]
    assert app.act_data["Time (min)"].tolist() == [-60.0, 0.0, 60.0]
    assert app.extended_temp_data["Time (min)"].tolist() == [-120.0, -60.0, 0.0]
    assert app.raw_aligned_temp_data["Time (min)"].tolist() == [0.0, 60.0, 120.0]

    app.graph_settings_container_instance.remove_first_60_minutes_var.set(False)
    service.apply_cached_telemetry_for_current_display()

    assert app.temp_data["Time (min)"].tolist() == [0.0, 60.0, 120.0]
    assert app.act_data["Time (min)"].tolist() == [0.0, 60.0, 120.0]
    assert app.extended_temp_data["Time (min)"].tolist() == [-60.0, 0.0, 60.0]


def test_overlay_extraction_keeps_alignment_anchor_and_uses_raw_duration():
    app = _App()
    app.date = "24-1-2"
    app.act_file_path = "activity.xlsx"
    app.temp_file_path = "temperature.xlsx"
    app.mouse_name = "MouseA"
    app.full_dataframe = pd.DataFrame(
        {"Time (min)": [0.0, 1500.0], "Signal": [0.1, 0.2]}
    )
    app.duration_main_data = 120.0
    app.data_type = "photometry"
    app.seconds_removed = 3600
    app.display_dropdown = types.SimpleNamespace(configure=lambda **_kwargs: None)
    app.temp_and_act_start_time_var = _Value("12:34:56")
    app.start_time_timedelta = None
    app.light_off_time_var = _Value("")
    app.graph_canvas = object()
    app.calculate_sample_rate = lambda _timestamps: 60.0
    app.annotate_clusters_with_time_period = lambda: None
    app.precompute_all_clusters = lambda: None
    service = TelemetryPlotService(app)

    extracted_calls = []
    visualized = {}
    telemetry_rows = pd.DataFrame(
        {
            "Date Time": pd.date_range("2024-01-02 12:34:56", periods=12, freq="min"),
            "Data": np.arange(12, dtype=float),
        }
    )

    def fake_extract(
        file_path,
        sheet_name,
        target_date,
        target_time,
        duration,
        selected_alignment_datetime=None,
    ):
        extracted_calls.append(
            {
                "file_path": file_path,
                "sheet_name": sheet_name,
                "target_date": target_date,
                "target_time": target_time,
                "duration": duration,
                "selected_alignment_datetime": selected_alignment_datetime,
            }
        )
        return telemetry_rows.copy(), 0.0, pd.Timestamp("2024-01-02 12:34:56")

    service.extract_data_for_date_and_offset = fake_extract
    service.extract_and_trim_data = lambda *_args: pd.DataFrame(
        {"Time (min)": [0.0, 60.0, 120.0], "Data": [1.0, 2.0, 3.0]}
    )
    service.extract_data_with_buffer = lambda *_args: pd.DataFrame(
        {"Time (min)": [-60.0, 0.0, 60.0, 120.0], "Data": [0.0, 1.0, 2.0, 3.0]}
    )
    service.upsample_data = lambda dataframe: dataframe
    service.get_current_photometry_data = lambda: (
        pd.Series([0.0, 120.0]),
        pd.Series([0.1, 0.2]),
        [],
        [],
        {},
    )
    service.visualize_photometry_data_with_overlays = (
        lambda _time, _data, _peaks, _clusters, _canvas, temp_data, act_data, **_kwargs:
        visualized.update({"temp": temp_data.copy(), "act": act_data.copy()})
    )

    service.overlay_temp_and_act()

    assert [call["target_time"] for call in extracted_calls] == ["12:34:56", "12:34:56"]
    assert [call["duration"] for call in extracted_calls] == [1500.0, 1500.0]
    assert visualized["temp"]["Time (min)"].tolist() == [-60.0, 0.0, 60.0]
    assert visualized["act"]["Time (min)"].tolist() == [-60.0, 0.0, 60.0]
    assert app.duration_main_data == 120.0


def test_overlay_ambiguous_alignment_prompts_once_and_reuses_selection(monkeypatch):
    app = _App()
    app.date = "24-1-2"
    app.act_file_path = "activity.xlsx"
    app.temp_file_path = "temperature.xlsx"
    app.mouse_name = "MouseA"
    app.full_dataframe = pd.DataFrame(
        {"Time (min)": [0.0, 120.0], "Signal": [0.1, 0.2]}
    )
    app.duration_main_data = 120.0
    app.data_type = "photometry"
    app.seconds_removed = 0
    app.display_dropdown = types.SimpleNamespace(configure=lambda **_kwargs: None)
    app.temp_and_act_start_time_var = _Value("12:00:00")
    app.start_time_timedelta = None
    app.light_off_time_var = _Value("")
    app.graph_canvas = object()
    app.calculate_sample_rate = lambda _timestamps: 60.0
    app.annotate_clusters_with_time_period = lambda: None
    service = TelemetryPlotService(app)

    candidates = [
        {
            "target_datetime": pd.Timestamp("2024-01-02 12:00:00"),
            "previous_timestamp": pd.Timestamp("2024-01-02 12:00:00"),
            "offset": 0.0,
            "available_minutes": 240.0,
        },
        {
            "target_datetime": pd.Timestamp("2024-01-01 12:00:00"),
            "previous_timestamp": pd.Timestamp("2024-01-01 12:00:00"),
            "offset": 0.0,
            "available_minutes": 1680.0,
        },
    ]
    extracted_calls = []
    prompt_choices = []
    telemetry_rows = pd.DataFrame(
        {
            "Date Time": pd.date_range("2024-01-01 12:00:00", periods=12, freq="min"),
            "Data": np.arange(12, dtype=float),
        }
    )

    def fake_get_item(_parent, _title, _message, choices, _index, _editable):
        prompt_choices.append(list(choices))
        return choices[1], True

    monkeypatch.setattr(
        "src.features.telemetry_alignment.services.plot_service.QInputDialog.getItem",
        fake_get_item,
    )

    def fake_extract(
        file_path,
        sheet_name,
        target_date,
        target_time,
        duration,
        selected_alignment_datetime=None,
    ):
        extracted_calls.append(
            {
                "file_path": file_path,
                "selected_alignment_datetime": selected_alignment_datetime,
            }
        )
        if selected_alignment_datetime is None:
            raise AmbiguousTelemetryAlignmentError(candidates, duration)
        return telemetry_rows.copy(), 0.0, pd.Timestamp(selected_alignment_datetime)

    service.extract_data_for_date_and_offset = fake_extract
    service.extract_and_trim_data = lambda *_args: pd.DataFrame(
        {"Time (min)": [0.0, 60.0], "Data": [1.0, 2.0]}
    )
    service.extract_data_with_buffer = lambda *_args: pd.DataFrame(
        {"Time (min)": [-60.0, 0.0], "Data": [0.0, 1.0]}
    )
    service.upsample_data = lambda dataframe: dataframe
    service.get_current_photometry_data = lambda: (
        pd.Series([0.0, 120.0]),
        pd.Series([0.1, 0.2]),
        [],
        [],
        {},
    )
    service.visualize_photometry_data_with_overlays = lambda *_args, **_kwargs: None

    service.overlay_temp_and_act()

    selected = pd.Timestamp("2024-01-01 12:00:00")
    assert len(prompt_choices) == 1
    assert [call["file_path"] for call in extracted_calls] == [
        "activity.xlsx",
        "activity.xlsx",
        "temperature.xlsx",
    ]
    assert extracted_calls[0]["selected_alignment_datetime"] is None
    assert extracted_calls[1]["selected_alignment_datetime"] == selected
    assert extracted_calls[2]["selected_alignment_datetime"] == selected


def test_overlay_reloads_activity_if_temperature_prompts_for_alignment(monkeypatch):
    app = _App()
    app.date = "24-1-2"
    app.act_file_path = "activity.xlsx"
    app.temp_file_path = "temperature.xlsx"
    app.mouse_name = "MouseA"
    app.full_dataframe = pd.DataFrame(
        {"Time (min)": [0.0, 120.0], "Signal": [0.1, 0.2]}
    )
    app.duration_main_data = 120.0
    app.data_type = "photometry"
    app.seconds_removed = 0
    app.display_dropdown = types.SimpleNamespace(configure=lambda **_kwargs: None)
    app.temp_and_act_start_time_var = _Value("12:00:00")
    app.start_time_timedelta = None
    app.light_off_time_var = _Value("")
    app.graph_canvas = object()
    app.calculate_sample_rate = lambda _timestamps: 60.0
    app.annotate_clusters_with_time_period = lambda: None
    service = TelemetryPlotService(app)

    candidates = [
        {
            "target_datetime": pd.Timestamp("2024-01-02 12:00:00"),
            "previous_timestamp": pd.Timestamp("2024-01-02 12:00:00"),
            "offset": 0.0,
            "available_minutes": 240.0,
        },
        {
            "target_datetime": pd.Timestamp("2024-01-01 12:00:00"),
            "previous_timestamp": pd.Timestamp("2024-01-01 12:00:00"),
            "offset": 0.0,
            "available_minutes": 1680.0,
        },
    ]
    extracted_calls = []
    telemetry_rows = pd.DataFrame(
        {
            "Date Time": pd.date_range("2024-01-01 12:00:00", periods=12, freq="min"),
            "Data": np.arange(12, dtype=float),
        }
    )

    monkeypatch.setattr(
        "src.features.telemetry_alignment.services.plot_service.QInputDialog.getItem",
        lambda _parent, _title, _message, choices, _index, _editable: (choices[1], True),
    )

    def fake_extract(
        file_path,
        sheet_name,
        target_date,
        target_time,
        duration,
        selected_alignment_datetime=None,
    ):
        extracted_calls.append(
            {
                "file_path": file_path,
                "selected_alignment_datetime": selected_alignment_datetime,
            }
        )
        if file_path == "temperature.xlsx" and selected_alignment_datetime is None:
            raise AmbiguousTelemetryAlignmentError(candidates, duration)
        return telemetry_rows.copy(), 0.0, pd.Timestamp(
            selected_alignment_datetime or "2024-01-02 12:00:00"
        )

    service.extract_data_for_date_and_offset = fake_extract
    service.extract_and_trim_data = lambda *_args: pd.DataFrame(
        {"Time (min)": [0.0, 60.0], "Data": [1.0, 2.0]}
    )
    service.extract_data_with_buffer = lambda *_args: pd.DataFrame(
        {"Time (min)": [-60.0, 0.0], "Data": [0.0, 1.0]}
    )
    service.upsample_data = lambda dataframe: dataframe
    service.get_current_photometry_data = lambda: (
        pd.Series([0.0, 120.0]),
        pd.Series([0.1, 0.2]),
        [],
        [],
        {},
    )
    service.visualize_photometry_data_with_overlays = lambda *_args, **_kwargs: None

    service.overlay_temp_and_act()

    selected = pd.Timestamp("2024-01-01 12:00:00")
    assert [call["file_path"] for call in extracted_calls] == [
        "activity.xlsx",
        "temperature.xlsx",
        "temperature.xlsx",
        "activity.xlsx",
    ]
    assert extracted_calls[-1]["selected_alignment_datetime"] == selected
    assert app.raw_aligned_act_data is not None
    assert app.raw_aligned_temp_data is not None


def test_current_photometry_data_uses_full_trace_baseline_reference():
    app = _App()
    app.data_selection_frame = types.SimpleNamespace(
        selected_column_var=_Value("Signal")
    )
    app.full_dataframe = pd.DataFrame(
        {"Time (min)": [0.0, 1.0, 2.0], "Signal": [4.0, 4.0, 5.0]}
    )
    app.trimmed_dataframe = pd.DataFrame(
        {"Time (min)": [0.0, 1.0, 2.0], "Signal": [0.0, 5.0, 0.0]}
    )
    captured = {}
    app.detect_peaks_with_optimal_prominence = lambda _series: [1]
    app.group_clusters_by_peak_count = lambda cluster_dict: cluster_dict

    def identify_clusters(_time, _data, _peaks, baseline_reference_column=None):
        captured["baseline_reference"] = baseline_reference_column.copy()
        return [], {}

    app.identify_clusters = identify_clusters
    service = TelemetryPlotService(app)

    service.get_current_photometry_data()

    assert captured["baseline_reference"].tolist() == [4.0, 4.0, 5.0]


def test_trim_toggle_refresh_rebuilds_cluster_static_data_without_precompute():
    app = _App()
    app.data_type = "photometry"
    app.seconds_removed = 3600
    app.raw_aligned_temp_data = pd.DataFrame(
        {"Time (min)": [0.0, 60.0, 120.0], "Data": [36.5, 37.0, 37.5]}
    )
    app.raw_aligned_act_data = pd.DataFrame(
        {"Time (min)": [0.0, 60.0, 120.0], "Data": [1.0, 2.0, 3.0]}
    )
    app.raw_extended_temp_data = app.raw_aligned_temp_data.copy()
    app.raw_extended_act_data = app.raw_aligned_act_data.copy()
    app.mean_cluster_data = {1: {"full": "stale"}}
    app.graph_canvas = object()
    app.annotate_clusters_with_time_period = lambda: call_order.append("annotate")
    app.precompute_all_clusters = lambda: call_order.append("precompute")
    app.populate_static_input_dropdown = lambda: call_order.append("dropdown")

    class StaticSettingsStore:
        def populate_data_dict(self, replace_existing=False):
            call_order.append(("populate", replace_existing))

    class ClusterTablePanel:
        def populate_table(self):
            call_order.append("table")

    app.static_settings_store = StaticSettingsStore()
    app.cluster_table_panel = ClusterTablePanel()

    service = TelemetryPlotService(app)
    call_order = []
    service.calculate_nighttime_period = lambda: call_order.append("night")
    service.get_current_photometry_data = lambda: (
        pd.Series([0.0, 120.0]),
        pd.Series([0.1, 0.2]),
        [],
        [],
        {},
    )
    service.visualize_photometry_data_with_overlays = lambda *_args, **_kwargs: call_order.append("visualize")

    service.refresh_after_trim_toggle()

    assert ("populate", True) in call_order
    assert call_order.index(("populate", True)) < call_order.index("visualize")
    assert "precompute" not in call_order
    assert app.mean_cluster_data == {}


def test_mean_cluster_display_lazily_computes_selected_cluster():
    app = types.SimpleNamespace()
    app.selected_period = _Value("Full")
    app.mean_cluster_data = {}
    computed = []
    plotted = {}

    def compute_data_for_cluster(cluster_number):
        computed.append(cluster_number)
        app.mean_cluster_data[cluster_number] = {
            "full": {
                "mean_temp_data": "temp",
                "mean_act_data": "act",
                "photometry_cluster_data": pd.DataFrame({"Time (min)": [0.0]}),
            }
        }

    app.compute_data_for_cluster = compute_data_for_cluster
    app.compute_data_for_stim_cluster = lambda _cluster_number: None

    presenter = TelemetryDisplayPresenter(app)
    presenter.plot_mean_cluster = (
        lambda mean_temp, mean_act, photometry_data, *args:
        plotted.update(
            {
                "mean_temp": mean_temp,
                "mean_act": mean_act,
                "photometry_rows": len(photometry_data),
            }
        )
    )
    presenter.display_no_data_figure = lambda: plotted.update({"no_data": True})

    presenter.visualize_mean_cluster("2 Peaks")

    assert computed == [2]
    assert plotted == {
        "mean_temp": "temp",
        "mean_act": "act",
        "photometry_rows": 1,
    }
