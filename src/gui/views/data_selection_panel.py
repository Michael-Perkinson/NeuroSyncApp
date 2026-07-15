from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional
import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QPushButton,
    QSizePolicy,
    QWidget,
)
import pandas as pd

from src.core.app_settings_manager import AppSettingsManager
from src.file_management.file_loader import (
    load_data_file,
    process_loaded_data,
    select_preferred_signal_column,
)
from src.gui.shared.checkable_column_selector import CheckableColumnSelector
from src.gui.shared.messages_and_errors import show_action_error
from src.shared.persistence.column_selection_memory import (
    recall_selection,
    remember_selection,
)
from src.gui.shared.qt_bindings import CheckBoxControl, LineEditControl, ObservableValue
from src.gui.shared.qt_view_styles import (
    apply_button_role,
    panel_stylesheet,
    section_stylesheet,
    title_stylesheet,
)
from src.gui.shared.view_state_models import DataSelectionViewState
from src.processing.data_utils import extract_mouse_name

logger = logging.getLogger(__name__)


class DataSelectionPanel(QFrame):
    def __init__(
        self,
        parent: QWidget | None,
        settings_manager: AppSettingsManager,
        width: Optional[int] = None,
        figure_display_callback: Optional[Callable] = None,
        new_data_file_callback: Optional[Callable] = None,
        figure_display_dropdown=None,
        figure_display_choices: Optional[list[str]] = None,
        baseline_button_pressed: bool = False,
        update_table_from_frame_callback: Optional[Callable] = None,
        **kwargs,
    ) -> None:
        super().__init__(parent, **kwargs)
        self.settings_manager = settings_manager
        self.width = width
        self.handle_figure_display_selection = figure_display_callback
        self.new_data_file_callback = new_data_file_callback
        self.figure_display_dropdown = figure_display_dropdown
        self.figure_display_choices = figure_display_choices or []
        self.baseline_button_pressed = baseline_button_pressed
        self.update_table_from_frame = update_table_from_frame_callback
        self.view_state = DataSelectionViewState()

        self.file_path_var = ObservableValue("")
        self.selected_column = ObservableValue("")
        self.selected_column_var = self.selected_column
        self.selected_columns_var = ObservableValue([])
        self.use_baseline_var = ObservableValue(False)
        self.file_path_var.trace_add(
            "write", lambda: setattr(self.view_state, "file_path", self.file_path_var.get() or "")
        )
        self.selected_column.trace_add(
            "write", lambda: setattr(self.view_state, "selected_column", self.selected_column.get() or "")
        )
        self.use_baseline_var.trace_add(
            "write", lambda: setattr(self.view_state, "use_baseline", bool(self.use_baseline_var.get()))
        )

        self.column_titles: list[str] = []
        self.figure_canvas = None
        self.warning_shown = False
        self.checkbox_state = False
        self._suppress_column_redraw = False

        self._build_ui()
        self.use_baseline_var.trace_add("write", self.toggle_baseline_entries)

    def _build_ui(self) -> None:
        self.setObjectName("dataSelectionPanel")
        self.setStyleSheet(
            panel_stylesheet("dataSelectionPanel")
            + section_stylesheet("dataSelectionSection")
            + section_stylesheet("dataSelectionSectionAlt", alt=True)
        )
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        layout = QGridLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(6)
        layout.setRowStretch(1, 1)

        title = QLabel("Data Selection", self)
        title.setStyleSheet(title_stylesheet())
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title, 0, 0)

        file_card = QFrame(self)
        file_card.setObjectName("dataSelectionSection")
        file_layout = QGridLayout(file_card)
        file_layout.setContentsMargins(8, 8, 8, 8)
        file_layout.setHorizontalSpacing(8)
        file_layout.setVerticalSpacing(6)
        layout.addWidget(file_card, 1, 0)

        folder_button = QPushButton("Select Folder", file_card)
        apply_button_role(folder_button, "primary")
        folder_button.clicked.connect(self.select_default_data_folder)
        folder_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        file_layout.addWidget(folder_button, 0, 0)

        select_button = QPushButton("Select File", file_card)
        apply_button_role(select_button, "primary")
        select_button.clicked.connect(lambda: self._on_select_file(self.file_path_var))
        select_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        file_layout.addWidget(select_button, 0, 1)

        self.file_name_entry = LineEditControl(self.file_path_var, file_card)
        self.file_name_entry.setReadOnly(True)
        file_layout.addWidget(self.file_name_entry, 0, 2, 1, 2)

        self.column_label = QLabel("Column Title", file_card)
        file_layout.addWidget(self.column_label, 1, 0)

        self.column_selector = CheckableColumnSelector(file_card)
        self.column_selector.setEnabled(False)
        self.column_selector.selectionChanged.connect(self._on_columns_changed)
        self.column_dropdown = self.column_selector
        file_layout.addWidget(self.column_selector, 1, 1, 1, 3)

        self.baseline_note_frame = QFrame(self)
        self.baseline_note_frame.setObjectName("dataSelectionSectionAlt")
        baseline_layout = QHBoxLayout(self.baseline_note_frame)
        baseline_layout.setContentsMargins(8, 8, 8, 8)
        baseline_layout.setSpacing(10)
        layout.addWidget(self.baseline_note_frame, 2, 0)

        baseline_checkbox = CheckBoxControl(
            "Baselined z-score", self.use_baseline_var, self.baseline_note_frame
        )
        baseline_layout.addWidget(baseline_checkbox)

        baseline_layout.addWidget(QLabel("Start Time (s):", self.baseline_note_frame))
        self.baseline_start_entry = LineEditControl(parent=self.baseline_note_frame)
        self.baseline_start_entry.setMaximumWidth(90)
        self.baseline_start_entry.configure(state="disabled")
        self.baseline_start_entry.bind("<KeyRelease>", self.reset_baseline_button_state)
        baseline_layout.addWidget(self.baseline_start_entry)

        baseline_layout.addWidget(QLabel("End Time (s):", self.baseline_note_frame))
        self.baseline_end_entry = LineEditControl(parent=self.baseline_note_frame)
        self.baseline_end_entry.setMaximumWidth(90)
        self.baseline_end_entry.configure(state="disabled")
        self.baseline_end_entry.bind("<KeyRelease>", self.reset_baseline_button_state)
        baseline_layout.addWidget(self.baseline_end_entry)

        self.baseline_save_button = QPushButton("Save Baseline", self.baseline_note_frame)
        apply_button_role(self.baseline_save_button, "primary")
        self.baseline_save_button.clicked.connect(self._on_save_baseline)
        baseline_layout.addWidget(self.baseline_save_button)

    def _on_select_file(self, file_path_var: ObservableValue[str]) -> None:
        file_path = self._prompt_file_selection()
        if not file_path:
            return

        self._suppress_column_redraw = True
        try:
            file_path_var.set(file_path)
            dataframe = load_data_file(file_path)
            if dataframe is None or getattr(dataframe, "empty", False):
                raise ValueError("The selected file did not contain usable tabular data.")

            processed_data = process_loaded_data(dataframe)
            dataframe = processed_data["dataframe"]
            column_titles = processed_data["column_titles"]
            self.selected_column.set(processed_data["selected_column"])
            is_time_based = processed_data["is_time_based"]
        except Exception as exc:
            logger.warning("Failed to load data file %s: %s", file_path, exc)
            file_path_var.set("")
            show_action_error(
                "Data file not recognised",
                "NeuroSyncApp could not load the selected data file",
                exc,
                self,
                "Choose a CSV or Excel data file with a time column and at least one numeric signal column.",
            )
            self._suppress_column_redraw = False
            return

        try:
            self._update_ui_after_file_selection(
                dataframe, column_titles, self.selected_column
            )
            mouse_name = self._get_mouse_name(file_path)

            if self.new_data_file_callback:
                self.new_data_file_callback(
                    self.file_path_var,
                    self.selected_column,
                    self.column_dropdown,
                    mouse_name,
                    dataframe,
                    is_time_based,
                )
        finally:
            self._suppress_column_redraw = False

    def _prompt_file_selection(self) -> str:
        initial_dir = getattr(self.settings_manager, "default_data_folder_path", None) or ""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Data File",
            initial_dir,
            "Supported Files (*.csv *.xlsx);;CSV Files (*.csv);;Excel Files (*.xlsx)",
        )
        return file_path

    def _update_ui_after_file_selection(
        self,
        dataframe: pd.DataFrame,
        column_titles: list[str],
        selected_column: ObservableValue[str],
    ) -> None:
        self.column_titles = column_titles
        preferred = select_preferred_signal_column(dataframe)
        # If the user previously ticked columns for a file with this same set
        # of columns, restore that selection (dual-signal users batch many
        # identically-laid-out files). Otherwise fall back to the single
        # auto-detected preferred column.
        remembered = recall_selection(column_titles)
        checked = remembered if remembered else ([preferred] if preferred else [])
        self.column_selector.set_columns(column_titles, checked)
        primary = checked[0] if checked else preferred
        selected_column.set(primary)
        self.selected_columns_var.set(checked)
        self.baseline_button_pressed = False

    def _get_mouse_name(self, file_path: str) -> str:
        mouse_name = extract_mouse_name(file_path)
        if not mouse_name:
            value, accepted = QInputDialog.getText(
                self,
                "Input",
                "No mouse number found in the filename. Please enter the mouse name or identifying code:",
            )
            mouse_name = value if accepted else ""
        return mouse_name if mouse_name else Path(file_path).name[:12]

    def select_default_data_folder(self) -> None:
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Default Data Folder",
            self.settings_manager.default_data_folder_path or "",
        )
        if folder_path:
            self.settings_manager.default_data_folder_path = folder_path
            self.settings_manager.save_variables()

    def on_column_selection_changed(self) -> None:
        self.settings_manager.selected_column_name = self.selected_column.get()
        if getattr(self, "_suppress_column_redraw", False):
            return
        if self.handle_figure_display_selection:
            self.handle_figure_display_selection(None)

    def _on_columns_changed(self, columns: list[str]) -> None:
        primary = columns[0] if columns else ""
        self.selected_columns_var.set(columns)
        if columns and getattr(self, "column_titles", None):
            remember_selection(self.column_titles, columns)
        if self.selected_column.get() != primary:
            self.selected_column.set(primary)
        else:
            self.on_column_selection_changed()

    def _on_save_baseline(self) -> None:
        self.save_baseline_values(self.figure_display_dropdown)

    def toggle_baseline_entries(self) -> None:
        enabled = bool(self.use_baseline_var.get())
        state = "normal" if enabled else "disabled"
        self.baseline_start_entry.config(state=state)
        self.baseline_end_entry.config(state=state)
        self._update_figure_display_dropdown(enabled)
        self.checkbox_state = enabled

    def _update_figure_display_dropdown(self, enabled: bool) -> None:
        if self.figure_display_dropdown is None:
            return

        current_values = list(self.figure_display_dropdown["values"])
        if enabled and "Z-scored data" not in current_values:
            self.figure_display_dropdown["values"] = current_values + ["Z-scored data"]
        elif not enabled and "Z-scored data" in current_values:
            self.figure_display_dropdown["values"] = [
                value for value in current_values if value != "Z-scored data"
            ]

    def save_baseline_values(self, figure_display_dropdown) -> None:
        if figure_display_dropdown is not None and hasattr(figure_display_dropdown, "set"):
            figure_display_dropdown.set("Z-scored data")
        self.baseline_button_pressed = True

        if self.handle_figure_display_selection:
            self.handle_figure_display_selection(None)
        if self.update_table_from_frame:
            self.update_table_from_frame()

    def set_figure_display_dropdown(self, dropdown) -> None:
        self.figure_display_dropdown = dropdown

    def set_figure_display_choices(self, choices) -> None:
        self.figure_display_choices = choices

    def reset_baseline_button_state(self, _event=None) -> None:
        self.baseline_button_pressed = False
