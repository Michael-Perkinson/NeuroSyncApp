from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

import src.features.raw_photometry.app as raw_app
from src.dfer.df_common import expected_analysis_output_path
from src.dfer.pfer import _stats_output_path, _waveform_output_path
from src.features.raw_photometry.app import (
    RawPhotometryProcessingQt,
    _mpl_dfer_results_figure_from_frame,
)


@pytest.fixture(autouse=True)
def _isolated_neurosync_config(tmp_path, monkeypatch):
    monkeypatch.setenv("NEUROSYNCAPP_CONFIG_DIR", str(tmp_path / "config"))


def test_raw_qt_app_instantiates():
    app = QApplication.instance() or QApplication([])
    widget = RawPhotometryProcessingQt()
    assert widget.notebook_graphs.count() == 4
    assert widget.notebook_settings.count() == 2
    assert widget.file_path_edit.isReadOnly() is True
    assert widget.start_time_edit.placeholderText() == "start"
    assert widget.end_time_edit.placeholderText() == "end"
    assert widget.start_time_edit.width() == 63
    assert widget.end_time_edit.width() == 63
    assert widget.total_time_label.minimumWidth() >= 84
    assert widget._dfer_show_405_checkbox.isChecked() is True
    assert widget.notebook_graphs.isTabEnabled(0) is True
    assert widget.notebook_graphs.isTabEnabled(1) is False
    assert widget.notebook_graphs.isTabEnabled(2) is False
    assert widget.notebook_graphs.isTabEnabled(3) is False
    widget.deleteLater()


def test_raw_qt_preview_uses_inline_compute_options_worker(monkeypatch):
    app = QApplication.instance() or QApplication([])
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
    app = QApplication.instance() or QApplication([])
    widget = RawPhotometryProcessingQt()

    widget.start_time_edit.setText("start")
    widget.end_time_edit.setText("max")

    assert widget._window_inputs() == ("", "")

    widget.start_time_edit.setText("min")
    widget.end_time_edit.setText("end")

    assert widget._window_inputs() == ("", "")
    widget.deleteLater()


def test_raw_qt_options_done_does_not_leave_raw_tab(monkeypatch):
    app = QApplication.instance() or QApplication([])
    widget = RawPhotometryProcessingQt()

    widget.notebook_graphs.setCurrentIndex(0)
    monkeypatch.setattr(widget, "_set_busy", lambda busy: None)
    monkeypatch.setattr(widget, "_render_option", lambda idx: None)

    widget._options_done({"file_type": "single", "signal_label": "465nm"})

    assert widget.notebook_graphs.currentIndex() == 0
    widget.deleteLater()


def test_raw_qt_remembers_selected_dfer_option(monkeypatch):
    app = QApplication.instance() or QApplication([])
    widget = RawPhotometryProcessingQt()
    saved = []

    monkeypatch.setattr(
        widget.settings_manager,
        "save_variables",
        lambda: saved.append(widget.settings_manager.last_run_dfer_option),
    )

    widget._opt_buttons["3"].setChecked(True)
    widget._save_dfer_option_selection("3")

    assert widget.settings_manager.last_run_dfer_option == "3"
    assert saved == ["3"]

    widget.settings_manager.last_run_dfer_option = "4"
    widget._restore_dfer_option_selection()
    assert widget._selected_option() == "4"
    widget.deleteLater()


def test_raw_qt_final_dfer_uses_reference_plot_workflow(monkeypatch):
    app = QApplication.instance() or QApplication([])
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
    app = QApplication.instance() or QApplication([])
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
    app = QApplication.instance() or QApplication([])
    widget = RawPhotometryProcessingQt()

    monkeypatch.setattr(widget, "_draw_raw_graph", lambda file_path: None)
    monkeypatch.setattr(raw_app, "detect_photometry_file_type", lambda file_path: ("single", 0))
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
    app = QApplication.instance() or QApplication([])
    widget = RawPhotometryProcessingQt()

    monkeypatch.setattr(widget, "_draw_raw_graph", lambda file_path: None)
    monkeypatch.setattr(raw_app, "detect_photometry_file_type", lambda file_path: ("dual", 0))
    monkeypatch.setattr(widget, "_refresh_time_preview", lambda: None)
    monkeypatch.setattr(widget, "_on_generate_options", lambda **kwargs: None)

    widget._load_photometry_file(str(raw_app.Path("parent/session/Fluorescence.csv")))

    assert widget._output_folder == str(
        raw_app.Path("parent/session/Fluorescence.csv").parent.parent / "dfof_results"
    )
    widget.deleteLater()


def test_raw_qt_signal_selector_matches_file_type():
    app = QApplication.instance() or QApplication([])
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

    app = QApplication.instance() or QApplication([])
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


def test_raw_qt_plot_export_paths_are_session_numbered(tmp_path):
    app = QApplication.instance() or QApplication([])
    widget = RawPhotometryProcessingQt()
    widget._output_folder = str(tmp_path / "dfof_results")
    widget._dfer_result_csv = str(tmp_path / "dfof_results" / "recording_Data.csv")

    first = widget._next_plot_path("dfer_result")
    second = widget._next_plot_path("dfer_result")

    assert first == tmp_path / "plots" / "recording" / "recording_plot_1.png"
    assert second == tmp_path / "plots" / "recording" / "recording_plot_2.png"
    widget.deleteLater()


def test_raw_qt_dual_plot_export_uses_recording_folder_name(tmp_path):
    app = QApplication.instance() or QApplication([])
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
