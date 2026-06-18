from unittest.mock import Mock

from src.gui.views.data_selection_frame import DataSelectionFrame


class _DummyVar:
    def __init__(self, value=""):
        self._value = value

    def set(self, value):
        self._value = value

    def get(self):
        return self._value


def test_on_select_file_passes_expected_callback_arguments(monkeypatch):
    file_path = r"E:\Code\NeuroSyncApp\sample_data.csv"
    dataframe = object()
    processed_data = {
        "dataframe": dataframe,
        "column_titles": ["Time (min)", "dFoF_465"],
        "selected_column": "dFoF_465",
        "is_time_based": True,
    }

    callback = Mock()
    frame = DataSelectionFrame.__new__(DataSelectionFrame)
    frame.file_path_var = _DummyVar()
    frame.selected_column = _DummyVar()
    frame.column_dropdown = object()
    frame.new_data_file_callback = callback
    frame._prompt_file_selection = Mock(return_value=file_path)
    frame._get_mouse_name = Mock(return_value="Mouse01")
    frame._update_ui_after_file_selection = Mock()

    monkeypatch.setattr("src.gui.views.data_selection_panel.load_data_file", lambda _p: dataframe)
    monkeypatch.setattr(
        "src.gui.views.data_selection_panel.process_loaded_data", lambda _df: processed_data
    )

    DataSelectionFrame._on_select_file(frame, frame.file_path_var)

    callback.assert_called_once_with(
        frame.file_path_var,
        frame.selected_column,
        frame.column_dropdown,
        "Mouse01",
        dataframe,
        True,
    )


def test_column_selection_change_does_not_redraw_during_file_load():
    frame = DataSelectionFrame.__new__(DataSelectionFrame)
    frame.settings_manager = Mock()
    frame.selected_column = _DummyVar("dFoF_470")
    frame.handle_figure_display_selection = Mock()
    frame._suppress_column_redraw = True

    DataSelectionFrame.on_column_selection_changed(frame)

    assert frame.settings_manager.selected_column_name == "dFoF_470"
    frame.handle_figure_display_selection.assert_not_called()
