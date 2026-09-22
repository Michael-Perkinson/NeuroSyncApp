from __future__ import annotations

import logging

import numpy as np
import pytest
from matplotlib.colors import to_hex
from PySide6.QtWidgets import QApplication, QLabel, QToolButton

import src.features.raw_photometry.photometry_processing_widget as raw_app
from src.dfer.df_common import expected_analysis_output_path
from src.dfer.pfer import _stats_output_path, _waveform_output_path
from src.features.raw_photometry.photometry_processing_widget import (
    RawPhotometryProcessingQt,
    _mpl_dfer_results_figure_from_frame,
)


@pytest.fixture(autouse=True)
def _isolated_neurosync_config(tmp_path, monkeypatch):
    monkeypatch.setenv("NEUROSYNCAPP_CONFIG_DIR", str(tmp_path / "config"))


def test_raw_shared_axis_limits_use_widest_signal_range_for_padding():
    signals = [
        np.array([0.0, 0.1]),
        np.array([100.0, 160.0]),
        np.array([500.0, 500.01]),
    ]

    lower, upper = raw_app._shared_signal_axis_limits(signals)

    assert np.isclose(lower, -2.4)
    assert np.isclose(upper, 502.41)


def test_raw_qt_app_instantiates():
    _app = QApplication.instance() or QApplication([])
    widget = RawPhotometryProcessingQt()
    assert widget.notebook_graphs.count() == 4
    assert widget.notebook_settings.count() == 2
    assert widget.file_path_edit.isReadOnly() is True
    assert widget.start_time_edit.placeholderText() == "start"
    assert widget.end_time_edit.placeholderText() == "end"
    assert widget.start_time_edit.width() == 63
    assert widget.end_time_edit.width() == 63
    assert widget._option_preview_combo.count() == 5
    assert widget._opt_buttons["5"].text().startswith("5 =")
    assert widget.total_time_label.minimumWidth() >= 84
    assert widget._dfer_show_405_checkbox.isChecked() is True
    assert widget._raw_individual_y_axes_toggle.isChecked() is False
    assert widget._raw_control_toggle.isChecked() is True
    assert widget._raw_graph_controls.isHidden() is True
    assert widget._raw_individual_y_axes_toggle.isVisible() is False
    assert widget._raw_individual_y_axes_toggle.isEnabled() is False
    assert "signal baseline" in widget._option_preview_combo.itemText(1)
    assert "465 baseline" not in widget._option_preview_combo.itemText(1)
    assert "no 405/410 control" in widget._option_preview_combo.itemText(4)
    assert widget.notebook_graphs.isTabEnabled(0) is True
    assert widget.notebook_graphs.isTabEnabled(1) is False
    assert widget.notebook_graphs.isTabEnabled(2) is False
    assert widget.notebook_graphs.isTabEnabled(3) is False
    widget.deleteLater()


def test_raw_qt_raw_y_axis_mode_is_saved_and_redrawn(monkeypatch):
    _app = QApplication.instance() or QApplication([])
    widget = RawPhotometryProcessingQt()
    widget._selected_file = "recording.ofrs"
    widget._raw_graph_controls.setVisible(True)
    widget._raw_individual_y_axes_toggle.setVisible(True)
    widget._raw_individual_y_axes_toggle.setEnabled(True)
    redraws = []
    saves = []

    monkeypatch.setattr(
        widget,
        "_draw_raw_graph",
        lambda file_path: redraws.append(file_path),
    )
    monkeypatch.setattr(
        widget.settings_manager,
        "save_variables",
        lambda: saves.append(widget.settings_manager.raw_dual_y_axis_mode),
    )

    widget._raw_individual_y_axes_toggle.setChecked(True)

    assert widget.settings_manager.raw_dual_y_axis_mode == "individual"
    assert saves == ["individual"]
    assert redraws == ["recording.ofrs"]
    widget.deleteLater()


def test_raw_qt_single_raw_graph_retains_405_control_signal():
    _app = QApplication.instance() or QApplication([])
    widget = RawPhotometryProcessingQt()
    widget._draw_single_raw(
        np.array([0.0, 1.0, 2.0]),
        np.array([10.0, 11.0, 12.0]),
        np.array([1.0, 1.1, 1.2]),
    )

    toolbar = widget.raw_graph_panel.toolbar
    assert toolbar is not None
    assert toolbar.objectName() == ""
    assert toolbar.isMovable() is True
    assert toolbar.isFloatable() is True
    assert "background: #DCE8F2" in toolbar.styleSheet()
    assert "QToolBar QLabel" in toolbar.styleSheet()
    assert "color: #17324D" in toolbar.styleSheet()
    assert toolbar.property("rawToolbarIconsTinted") is True
    assert any(
        button.defaultAction() is not None and not button.icon().isNull()
        for button in toolbar.findChildren(QToolButton)
    )
    assert [
        label.text()
        for label in widget.raw_graph_panel.findChildren(QLabel, "rawGraphAxisLabel")
    ] == ["465nm", "405nm"]

    ref = widget._raw_graph_ref
    assert ref is not None
    assert np.isclose(ref.figure.subplotpars.bottom, 0.09)
    assert ref.secondary_axis is not None
    assert ref.secondary_axis.get_ylabel() == "405nm"
    assert ref.primary_axis.get_ylabel() == "465nm"
    assert ref.primary_axis.yaxis.get_ticklabels()[0].get_color() == "green"
    assert np.isclose(
        np.ptp([1.0, 1.1, 1.2]) / np.ptp(ref.primary_axis.get_ylim()), 0.80
    )
    assert np.isclose(
        np.ptp([10.0, 11.0, 12.0]) / np.ptp(ref.secondary_axis.get_ylim()), 0.30
    )
    assert ref.primary_axis.lines[0].get_alpha() == 0.65
    assert ref.secondary_axis.lines[0].get_alpha() == 0.55
    assert np.asarray(ref.secondary_axis.lines[0].get_ydata()).tolist() == [
        10.0,
        11.0,
        12.0,
    ]
    assert [text.get_text() for text in ref.primary_axis.get_legend().texts] == [
        "Window start",
        "Window end",
    ]

    widget._raw_control_toggle.setChecked(False)
    widget._draw_single_raw(
        np.array([0.0, 1.0, 2.0]),
        np.array([10.0, 11.0, 12.0]),
        np.array([1.0, 1.1, 1.2]),
    )
    hidden_ref = widget._raw_graph_ref
    assert hidden_ref is not None
    assert hidden_ref.secondary_axis is not None
    assert hidden_ref.secondary_axis.get_visible() is False
    assert len(hidden_ref.secondary_axis.lines) == 0
    widget.deleteLater()


def test_raw_qt_single_raw_graph_uses_selected_490_signal_label():
    _app = QApplication.instance() or QApplication([])
    widget = RawPhotometryProcessingQt()
    widget._draw_single_raw(
        np.array([0.0, 1.0, 2.0]),
        np.array([10.0, 11.0, 12.0]),
        np.array([1.0, 1.1, 1.2]),
        "490nm",
    )

    ref = widget._raw_graph_ref
    assert ref is not None
    assert ref.primary_axis.get_ylabel() == "490nm"
    widget.deleteLater()


def test_raw_qt_raw_graph_toggles_are_configured_for_single_and_dual(monkeypatch):
    _app = QApplication.instance() or QApplication([])
    widget = RawPhotometryProcessingQt()
    file_type = {"value": "single"}

    monkeypatch.setattr(
        raw_app,
        "detect_photometry_file_type",
        lambda _file_path: (file_type["value"], 0),
    )
    monkeypatch.setattr(widget, "_draw_raw_graph", lambda _file_path: None)
    monkeypatch.setattr(widget, "_on_generate_options", lambda **_kwargs: None)

    widget._load_photometry_file("recording.csv")
    assert widget._raw_graph_controls.isHidden() is False
    assert widget._raw_control_toggle.text() == "Show 405 nm control"
    assert widget._raw_individual_y_axes_toggle.isHidden() is True
    assert widget._raw_individual_y_axes_toggle.isEnabled() is False

    file_type["value"] = "dual"
    widget._load_photometry_file("recording.ofrs")
    assert widget._raw_graph_controls.isHidden() is False
    assert widget._raw_control_toggle.text() == "Show 410 nm control"
    assert widget._raw_individual_y_axes_toggle.isHidden() is False
    assert widget._raw_individual_y_axes_toggle.isEnabled() is True
    widget.deleteLater()


def test_raw_qt_dual_raw_graph_includes_control_and_supports_axis_modes(monkeypatch):
    _app = QApplication.instance() or QApplication([])
    widget = RawPhotometryProcessingQt()
    t = np.array([0.0, 1.0, 2.0])
    y410 = np.array([10.0, 11.0, 12.0])
    y470 = np.array([1.0, 1.1, 1.2])
    y560 = np.array([100.0, 101.0, 102.0])

    assert widget._raw_y_axis_mode() == "shared"
    widget._draw_dual_raw(t, y410, y470, y560)
    shared_default_ref = widget._raw_graph_ref
    assert shared_default_ref is not None
    assert len(shared_default_ref.figure.axes) == 1
    assert shared_default_ref.primary_axis.get_ylabel() == "470nm"
    assert shared_default_ref.primary_axis.yaxis.label.get_color() == "black"
    assert (
        to_hex(shared_default_ref.primary_axis.spines["left"].get_edgecolor())
        == "#000000"
    )
    assert shared_default_ref.primary_axis.lines[0].get_alpha() == 0.55
    assert shared_default_ref.primary_axis.lines[1].get_alpha() == 0.65
    assert shared_default_ref.primary_axis.lines[2].get_alpha() == 0.65

    widget._raw_individual_y_axes_toggle.setChecked(True)
    widget._draw_dual_raw(t, y410, y470, y560)
    individual_ref = widget._raw_graph_ref
    assert individual_ref is not None
    figure = individual_ref.figure
    assert len(figure.axes) == 3
    assert np.isclose(figure.subplotpars.bottom, 0.09)
    assert np.isclose(figure.subplotpars.right, 0.90)
    assert [
        label.text()
        for label in widget.raw_graph_panel.findChildren(QLabel, "rawGraphAxisLabel")
    ] == ["470nm", "410nm", "560nm"]
    assert individual_ref.primary_axis.get_ylabel() == "470nm"
    assert individual_ref.primary_axis.yaxis.get_ticklabels()[0].get_color() == "green"
    assert (
        to_hex(individual_ref.primary_axis.spines["left"].get_edgecolor()) == "#008000"
    )
    assert individual_ref.primary_axis.get_ylim()[0] < float(y470.min())
    assert individual_ref.primary_axis.get_ylim()[1] > float(y470.max())
    assert np.isclose(
        np.ptp(y470) / np.ptp(individual_ref.primary_axis.get_ylim()), 0.50
    )
    assert individual_ref.secondary_axis is not None
    assert individual_ref.secondary_axis.get_ylabel() == "410nm"
    assert individual_ref.secondary_axis.get_ylim()[0] < float(y410.min())
    assert individual_ref.secondary_axis.get_ylim()[1] > float(y410.max())
    assert np.isclose(
        np.ptp(y410) / np.ptp(individual_ref.secondary_axis.get_ylim()), 0.30
    )
    assert individual_ref.primary_axis.lines[0].get_alpha() == 0.65
    assert individual_ref.secondary_axis.lines[0].get_alpha() == 0.55
    assert figure.axes[2].lines[0].get_alpha() == 0.65
    assert figure.axes[2].get_ylim()[0] < float(y560.min())
    assert figure.axes[2].get_ylim()[1] > float(y560.max())
    assert np.isclose(np.ptp(y560) / np.ptp(figure.axes[2].get_ylim()), 0.80)
    assert [
        str(line.get_label())
        for axis in figure.axes
        for line in axis.lines
        if not str(line.get_label()).startswith("Window")
    ] == ["470nm", "410nm control", "560nm"]
    individual_legend = figure.axes[0].get_legend()
    assert individual_legend is not None
    assert [text.get_text() for text in individual_legend.texts] == [
        "410nm control",
        "470nm",
        "560nm",
        "Window start",
        "Window end",
    ]

    widget._selected_file = "recording.ofrs"
    widget._raw_graph_controls.setVisible(True)
    widget._raw_individual_y_axes_toggle.setVisible(True)
    widget._raw_individual_y_axes_toggle.setEnabled(True)
    widget.start_time_edit.setText("0.5")
    widget.end_time_edit.setText("1.5")
    widget._refresh_time_preview()
    monkeypatch.setattr(
        widget,
        "_draw_raw_graph",
        lambda _file_path: widget._draw_dual_raw(t, y410, y470, y560),
    )
    widget._raw_individual_y_axes_toggle.setChecked(False)

    shared_ref = widget._raw_graph_ref
    assert shared_ref is not None
    shared_figure = shared_ref.figure
    assert len(shared_figure.axes) == 1
    assert [line.get_label() for line in shared_figure.axes[0].lines] == [
        "410nm control",
        "470nm",
        "560nm",
        "Window start",
        "Window end",
    ]
    assert np.asarray(shared_ref.start_line.get_xdata()).tolist() == [0.5, 0.5]
    assert np.asarray(shared_ref.end_line.get_xdata()).tolist() == [1.5, 1.5]

    widget._raw_control_toggle.setChecked(False)
    no_control_ref = widget._raw_graph_ref
    assert no_control_ref is not None
    assert [line.get_label() for line in no_control_ref.primary_axis.lines] == [
        "470nm",
        "560nm",
        "Window start",
        "Window end",
    ]
    widget.deleteLater()


def test_raw_qt_preview_uses_inline_compute_options_worker(monkeypatch):
    _app = QApplication.instance() or QApplication([])
    widget = RawPhotometryProcessingQt()
    captured = {}

    widget._selected_file = "recording.csv"
    widget.start_time_edit.setText("10")
    widget.end_time_edit.setText("120")
    monkeypatch.setattr(widget, "_set_busy", lambda busy: None)
    monkeypatch.setattr(
        widget,
        "_start_worker",
        lambda fn, kwargs, on_success, on_error: captured.update(
            {"fn": fn, "kwargs": kwargs}
        ),
    )

    widget._on_generate_options()

    assert captured["fn"] is raw_app.compute_options
    assert captured["kwargs"] == {
        "selectedfile": "recording.csv",
        "w_start": "10",
        "w_end": "120",
    }
    widget.deleteLater()


def test_raw_qt_window_aliases_normalise_to_full_range():
    _app = QApplication.instance() or QApplication([])
    widget = RawPhotometryProcessingQt()

    widget.start_time_edit.setText("start")
    widget.end_time_edit.setText("max")

    assert widget._window_inputs() == ("", "")

    widget.start_time_edit.setText("min")
    widget.end_time_edit.setText("end")

    assert widget._window_inputs() == ("", "")
    widget.deleteLater()


def test_raw_qt_options_done_does_not_leave_raw_tab(monkeypatch):
    _app = QApplication.instance() or QApplication([])
    widget = RawPhotometryProcessingQt()

    widget.notebook_graphs.setCurrentIndex(0)
    monkeypatch.setattr(widget, "_set_busy", lambda busy: None)
    monkeypatch.setattr(widget, "_render_option", lambda idx: None)

    widget._options_done({"file_type": "single", "signal_label": "465nm"})

    assert widget.notebook_graphs.currentIndex() == 0
    widget.deleteLater()


def test_raw_qt_remembers_selected_dfer_option(monkeypatch):
    _app = QApplication.instance() or QApplication([])
    widget = RawPhotometryProcessingQt()
    saved = []

    monkeypatch.setattr(
        widget.settings_manager,
        "save_variables",
        lambda: saved.append(widget.settings_manager.last_run_dfer_option),
    )

    widget._opt_buttons["3"].setChecked(True)
    assert widget._option_preview_combo.currentIndex() == 2
    widget._save_dfer_option_selection("3")

    widget._opt_buttons["5"].setChecked(True)
    assert widget._selected_option() == "5"
    assert widget._option_preview_combo.currentIndex() == 4

    assert widget.settings_manager.last_run_dfer_option == "3"
    assert saved == ["3"]

    widget._option_preview_combo.setCurrentIndex(0)
    assert widget._selected_option() == "1"

    widget.settings_manager.last_run_dfer_option = "4"
    widget._restore_dfer_option_selection()
    assert widget._selected_option() == "4"
    assert widget._option_preview_combo.currentIndex() == 3
    widget.deleteLater()


def test_raw_qt_late_logs_after_deleted_log_widget_are_ignored():
    _app = QApplication.instance() or QApplication([])
    widget = RawPhotometryProcessingQt()

    class DeletedLogEdit:
        def appendPlainText(self, _msg):
            raise RuntimeError("Internal C++ object already deleted")

    widget._log_edit = DeletedLogEdit()  # type: ignore[assignment]
    widget._append_log("late worker message")
    logging.getLogger("src.dfer.df_dual").info("late worker message")

    assert widget._log_edit is None
    assert widget._log_handler is None
    assert widget._log_signal_connected is False
    widget.deleteLater()


def test_raw_qt_final_dfer_uses_reference_plot_workflow(monkeypatch):
    _app = QApplication.instance() or QApplication([])
    widget = RawPhotometryProcessingQt()
    captured = {}

    widget._selected_file = "recording.csv"
    widget.start_time_edit.setText("5")
    widget.end_time_edit.setText("60")
    widget._opt_buttons["4"].setChecked(True)
    monkeypatch.setattr(widget, "_set_busy", lambda busy: None)
    monkeypatch.setattr(
        widget,
        "_start_worker",
        lambda fn, kwargs, on_success, on_error: captured.update(
            {"fn": fn, "kwargs": kwargs}
        ),
    )

    widget._on_run_final()

    assert captured["fn"] is raw_app.run_analysis
    assert captured["kwargs"] == {
        "selectedfile": "recording.csv",
        "w_start": "5",
        "w_end": "60",
        "analysis_path": "4",
        "make_plots": False,
        "mode": "full",
        "plot_stage": "final",
    }
    widget.deleteLater()


def test_raw_qt_pfer_uses_reference_plot_workflow(monkeypatch):
    _app = QApplication.instance() or QApplication([])
    widget = RawPhotometryProcessingQt()
    captured = {}

    widget._pfer_selected_csv = "dfer_output.csv"
    widget._pfer_start_edit.setText("1")
    widget._pfer_end_edit.setText("30")
    widget._prominence_spin.setValue(0.004)
    widget._artifact_spin.setValue(12)
    monkeypatch.setattr(widget, "_set_busy", lambda busy: None)
    monkeypatch.setattr(
        widget,
        "_start_worker",
        lambda fn, kwargs, on_success, on_error: captured.update(
            {"fn": fn, "kwargs": kwargs}
        ),
    )

    widget._on_run_pfer()

    assert captured["fn"] is raw_app.run_pfer
    assert captured["kwargs"] == {
        "csv_path": "dfer_output.csv",
        "w_start": "1",
        "w_end": "30",
        "prominence": 0.004,
        "artifact_threshold": 12,
        "make_plots": False,
    }
    widget.deleteLater()


def test_raw_qt_file_selection_unlocks_options_and_locks_results(monkeypatch):
    _app = QApplication.instance() or QApplication([])
    widget = RawPhotometryProcessingQt()

    monkeypatch.setattr(widget, "_draw_raw_graph", lambda file_path: None)
    monkeypatch.setattr(
        raw_app, "detect_photometry_file_type", lambda file_path: ("single", 0)
    )
    monkeypatch.setattr(widget, "_refresh_time_preview", lambda: None)
    monkeypatch.setattr(widget, "_on_generate_options", lambda **kwargs: None)
    widget.notebook_graphs.setTabEnabled(2, True)
    widget.notebook_graphs.setTabEnabled(3, True)

    widget._load_photometry_file("recording.csv")

    assert widget.notebook_graphs.isTabEnabled(1) is True
    assert widget.notebook_graphs.isTabEnabled(2) is False
    assert widget.notebook_graphs.isTabEnabled(3) is False
    assert widget._output_folder == str(
        raw_app.Path("recording.csv").parent / "dfof_results"
    )
    widget.deleteLater()


def test_raw_qt_dual_file_selection_exports_above_session_folder(monkeypatch):
    _app = QApplication.instance() or QApplication([])
    widget = RawPhotometryProcessingQt()

    monkeypatch.setattr(widget, "_draw_raw_graph", lambda file_path: None)
    monkeypatch.setattr(
        raw_app, "detect_photometry_file_type", lambda file_path: ("dual", 0)
    )
    monkeypatch.setattr(widget, "_refresh_time_preview", lambda: None)
    monkeypatch.setattr(widget, "_on_generate_options", lambda **kwargs: None)

    widget._load_photometry_file(str(raw_app.Path("parent/session/Fluorescence.csv")))

    assert widget._output_folder == str(
        raw_app.Path("parent/session/Fluorescence.csv").parent.parent / "dfof_results"
    )
    widget.deleteLater()


def test_raw_qt_ofrs_raw_graph_uses_dual_loader(tmp_path, monkeypatch):
    import pandas as pd

    _app = QApplication.instance() or QApplication([])
    widget = RawPhotometryProcessingQt()
    file_path = tmp_path / "recording.ofrs"
    frame = pd.DataFrame(
        {
            "TimeStamp": [0.0, 100.0, 200.0],
            "CH1-410": [1.0, 1.1, 1.2],
            "CH1-470": [2.0, 2.1, 2.2],
            "CH1-560": [3.0, 3.1, 3.2],
        }
    )
    captured = {}

    monkeypatch.setattr(
        raw_app,
        "detect_photometry_file_type",
        lambda path: ("dual", 0),
    )
    monkeypatch.setattr(
        raw_app,
        "load_dual_photometry",
        lambda path, skiprows: frame,
    )
    monkeypatch.setattr(
        widget,
        "_draw_dual_raw",
        lambda t, y410, y470, y560: captured.update(
            {"t": t, "y410": y410, "y470": y470, "y560": y560}
        ),
    )

    widget._draw_raw_graph(str(file_path))

    assert captured["t"].tolist() == [0.0, 0.1, 0.2]
    assert captured["y410"].tolist() == [1.0, 1.1, 1.2]
    assert captured["y470"].tolist() == [2.0, 2.1, 2.2]
    assert captured["y560"].tolist() == [3.0, 3.1, 3.2]
    widget.deleteLater()


def test_raw_qt_wrong_dual_file_reports_required_schema(tmp_path, monkeypatch):
    _app = QApplication.instance() or QApplication([])
    widget = RawPhotometryProcessingQt()
    wrong_file = tmp_path / "processed.csv"
    wrong_file.write_text(
        "TimeStamp,CH1-410,CH1-560\n0,1,1\n1000,1,1\n2000,1,1\n",
        encoding="utf-8",
    )
    captured = {}
    monkeypatch.setattr(
        raw_app,
        "show_action_error",
        lambda title, summary, error, parent, recovery: captured.update(
            {
                "title": title,
                "summary": summary,
                "error": error,
                "recovery": recovery,
            }
        ),
    )

    widget._load_photometry_file(str(wrong_file))

    assert captured["title"] == "Photometry file not recognised"
    assert "missing required column" in str(captured["error"])
    assert "original raw photometry CSV" in captured["recovery"]
    assert widget._selected_file is None
    widget.deleteLater()


def test_raw_qt_signal_selector_matches_file_type():
    _app = QApplication.instance() or QApplication([])
    widget = RawPhotometryProcessingQt()
    widget.notebook_graphs.setTabEnabled(1, True)

    widget._options_data = {"file_type": "single", "signal_label": "490nm"}
    widget._configure_option_signal_selector(is_dual=False)
    assert widget._dual_option_display_combo.currentText() == "490nm"
    assert widget._dual_option_display_combo.isEnabled() is False

    widget._options_data = {"file_type": "dual"}
    widget._configure_option_signal_selector(is_dual=True)
    assert [
        widget._dual_option_display_combo.itemText(i)
        for i in range(widget._dual_option_display_combo.count())
    ] == ["Both", "470nm", "560nm"]
    assert widget._dual_option_display_combo.isEnabled() is True
    widget.deleteLater()


def test_dfer_results_graph_has_no_title():
    import pandas as pd

    fig = _mpl_dfer_results_figure_from_frame(
        pd.DataFrame(
            {
                "t_min": [0.0, 1.0],
                "dFoF_405": [0.0, 0.1],
                "dFoF_465": [0.2, 0.3],
                "Z_405": [0.0, 1.0],
                "Z_465": [1.0, 0.0],
            }
        ),
        "dfof",
    )

    assert fig.axes[0].get_title() == ""


def test_dfer_results_graph_can_hide_405():
    import pandas as pd

    fig = _mpl_dfer_results_figure_from_frame(
        pd.DataFrame(
            {
                "t_min": [0.0, 1.0],
                "dFoF_405": [0.0, 0.1],
                "dFoF_465": [0.2, 0.3],
                "Z_405": [0.0, 1.0],
                "Z_465": [1.0, 0.0],
            }
        ),
        "dfof",
        show_405=False,
    )

    assert [line.get_label() for line in fig.axes[0].lines] == ["465nm dF/F"]


def test_dfer_results_graph_softens_dual_traces():
    import pandas as pd

    fig = _mpl_dfer_results_figure_from_frame(
        pd.DataFrame(
            {
                "t_min": [0.0, 1.0],
                "dFoF_470": [0.0, 0.1],
                "dFoF_560": [0.2, 0.3],
                "Z_470": [0.0, 1.0],
                "Z_560": [1.0, 0.0],
            }
        ),
        "dfof",
    )

    assert [line.get_alpha() for line in fig.axes[0].lines] == [0.55, 0.4]
    assert [line.get_linewidth() for line in fig.axes[0].lines] == [0.6, 0.6]


def test_raw_qt_dfer_results_405_checkbox_disables_for_dual():
    import pandas as pd

    _app = QApplication.instance() or QApplication([])
    widget = RawPhotometryProcessingQt()
    widget._dfer_result_frame = pd.DataFrame(
        {
            "t_min": [0.0, 1.0],
            "dFoF_470": [0.0, 0.1],
            "dFoF_560": [0.2, 0.3],
            "Z_470": [0.0, 1.0],
            "Z_560": [1.0, 0.0],
        }
    )
    widget._dfer_result_csv = "dual.csv"

    widget._render_dfer_results("dual.csv")

    assert widget._dfer_show_405_checkbox.isEnabled() is False
    assert widget._dfer_show_405_checkbox.isChecked() is False
    widget.deleteLater()


def test_raw_qt_dfer_results_405_checkbox_disables_for_option_five():
    import pandas as pd

    _app = QApplication.instance() or QApplication([])
    widget = RawPhotometryProcessingQt()
    widget._dfer_result_frame = pd.DataFrame(
        {
            "t_min": [0.0, 1.0],
            "dFoF_405": [float("nan"), float("nan")],
            "dFoF_465": [0.2, 0.3],
            "Z_405": [float("nan"), float("nan")],
            "Z_465": [1.0, 0.0],
        }
    )
    widget._dfer_result_frame.attrs["dfer_option"] = 5
    widget._dfer_result_csv = "option-five.csv"

    widget._render_dfer_results("option-five.csv")

    assert widget._dfer_show_405_checkbox.isEnabled() is False
    assert widget._dfer_show_405_checkbox.isChecked() is False
    widget.deleteLater()


def test_raw_qt_plot_export_paths_are_session_numbered(tmp_path):
    _app = QApplication.instance() or QApplication([])
    widget = RawPhotometryProcessingQt()
    widget._output_folder = str(tmp_path / "dfof_results")
    widget._dfer_result_csv = str(tmp_path / "dfof_results" / "recording_Data.csv")

    first = widget._next_plot_path("dfer_result")
    second = widget._next_plot_path("dfer_result")

    assert first == tmp_path / "plots" / "recording" / "recording_plot_1.png"
    assert second == tmp_path / "plots" / "recording" / "recording_plot_2.png"
    widget.deleteLater()


def test_raw_qt_dual_plot_export_uses_recording_folder_name(tmp_path):
    _app = QApplication.instance() or QApplication([])
    widget = RawPhotometryProcessingQt()
    widget._output_folder = str(tmp_path / "dfof_results")
    widget._dfer_result_csv = str(tmp_path / "dfof_results" / "session_Dual_Data.csv")

    assert widget._next_plot_path("dfer_result") == (
        tmp_path / "plots" / "session" / "session_Dual_plot_1.png"
    )
    widget.deleteLater()


def test_dfer_results_graph_uses_exact_time_axis():
    import pandas as pd

    fig = _mpl_dfer_results_figure_from_frame(
        pd.DataFrame(
            {
                "t_min": [0.0, 10.0],
                "dFoF_405": [0.0, 0.1],
                "dFoF_465": [0.2, 0.3],
                "Z_405": [0.0, 1.0],
                "Z_465": [1.0, 0.0],
            }
        ),
        "dfof",
    )

    assert tuple(fig.axes[0].get_xlim()) == (-0.05, 10.05)


def test_dfer_output_path_is_beside_input_file(tmp_path):
    raw_file = tmp_path / "mouse_a.csv"
    raw_file.write_text("#time(seconds),405nm,465nm\n0,1,1\n1,1,1\n", encoding="utf-8")

    assert expected_analysis_output_path(raw_file, file_type="single") == (
        tmp_path / "dfof_results" / "mouse_a_Data.csv"
    )


def test_dual_dfer_output_path_uses_parent_folder_name(tmp_path):
    raw_dir = tmp_path / "mouse_a_session"
    raw_dir.mkdir()
    raw_file = raw_dir / "Fluorescence.csv"
    raw_file.write_text(
        "TimeStamp,CH1-410,CH1-470,CH1-560\n0,1,1,1\n1,1,1,1\n",
        encoding="utf-8",
    )

    assert expected_analysis_output_path(raw_file, file_type="dual") == (
        raw_dir.parent / "dfof_results" / "mouse_a_session_Dual_Data.csv"
    )


def test_pfer_output_paths_are_beside_dfer_csv(tmp_path):
    outdir = tmp_path / "dfof_results"
    dfer_csv = outdir / "mouse_a_Data.csv"
    dfer_csv.parent.mkdir()
    dfer_csv.write_text("t_min,dFoF_465,dFoF_405\n0,0,0\n", encoding="utf-8")

    assert _stats_output_path(outdir, dfer_csv.stem, "465", False) == (
        outdir / "mouse_a_Data_Peak_STATS.csv"
    )
    assert _waveform_output_path(outdir, dfer_csv.stem, "465", False) == (
        outdir / "mouse_a_Data_Peak_WAVEFORM.csv"
    )
