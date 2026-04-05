from __future__ import annotations

from dataclasses import dataclass

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.core.app_settings_manager import AppSettingsManager
from src.file_management.file_loader import load_data_file
from src.gui.shared.qt_view_styles import (
    APP_TABS_STYLESHEET,
    PALETTE,
    apply_button_role,
)
from src.math_ops.time_converters import is_time_data
from src.processing.raw_photometry_processing import PhotometryRawProcessor


@dataclass
class GraphReference:
    figure: Figure
    primary_axis: object
    secondary_axis: object
    start_line: object
    end_line: object


class GraphPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.canvas: FigureCanvasQTAgg | None = None
        self.toolbar: NavigationToolbar2QT | None = None
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(6)

    def set_figure(self, figure: Figure) -> None:
        self.clear()
        self.canvas = FigureCanvasQTAgg(figure)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        self._layout.addWidget(self.canvas, 1)
        self._layout.addWidget(self.toolbar)
        self.canvas.draw()

    def clear(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()


class RawPhotometryProcessingQt(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings_manager = AppSettingsManager(app_type="raw_photometry_processing")
        self.settings_manager.load_variables()
        self.processor: PhotometryRawProcessor | None = None
        self.all_graphs_reference: dict[int, GraphReference] = {}
        self.column_options: list[str] = []
        self._build_ui()

    def _build_ui(self) -> None:
        self.setObjectName("rawPhotometryRoot")
        self.setStyleSheet(
            f"""
#rawPhotometryRoot {{
    background: {PALETTE["app_bg"]};
}}
#rawPhotometryRoot QGroupBox {{
    background: {PALETTE["panel_bg"]};
    border: 1px solid {PALETTE["border"]};
    border-radius: 16px;
    margin-top: 10px;
    padding-top: 12px;
    font-weight: 700;
    color: {PALETTE["text"]};
}}
#rawPhotometryRoot QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}}
#rawPhotometryRoot QLineEdit,
#rawPhotometryRoot QComboBox {{
    background: white;
    border: 1px solid {PALETTE["border"]};
    border-radius: 10px;
    padding: 6px 8px;
    color: {PALETTE["text"]};
}}
"""
            + APP_TABS_STYLESHEET
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)
        root.addLayout(top_row)
        top_row.addWidget(self._create_data_group(), 2)
        top_row.addWidget(self._create_time_group(), 1)
        top_row.addWidget(self._create_export_group(), 1)

        self.notebook = QTabWidget(self)
        self.notebook.setDocumentMode(True)
        self.notebook.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.raw_graph_panel = GraphPanel(self)
        self.noise_graph_panel = GraphPanel(self)
        self.final_graph_panel = GraphPanel(self)
        self.notebook.addTab(self.raw_graph_panel, "Raw Data")
        self.notebook.addTab(self.noise_graph_panel, "Noise Correction Options")
        self.notebook.addTab(self.final_graph_panel, "Final Data")
        root.addWidget(self.notebook, 1)

    def _create_data_group(self) -> QGroupBox:
        group = QGroupBox("Data Selection", self)
        layout = QGridLayout(group)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(8)

        folder_button = QPushButton("Select Folder", group)
        apply_button_role(folder_button)
        folder_button.clicked.connect(self._select_default_data_folder)
        layout.addWidget(folder_button, 0, 0)

        file_button = QPushButton("Select File", group)
        apply_button_role(file_button, "primary")
        file_button.clicked.connect(self._select_file)
        layout.addWidget(file_button, 0, 1)

        self.file_path_edit = QLineEdit(group)
        self.file_path_edit.setReadOnly(True)
        layout.addWidget(self.file_path_edit, 0, 2, 1, 2)

        layout.addWidget(QLabel("Time column:", group), 1, 0)
        self.time_combo = QComboBox(group)
        self.time_combo.setEnabled(False)
        layout.addWidget(self.time_combo, 1, 1, 1, 3)

        layout.addWidget(QLabel("405nm column:", group), 2, 0)
        self.signal_405_combo = QComboBox(group)
        self.signal_405_combo.setEnabled(False)
        layout.addWidget(self.signal_405_combo, 2, 1, 1, 3)

        layout.addWidget(QLabel("465nm column:", group), 3, 0)
        self.signal_465_combo = QComboBox(group)
        self.signal_465_combo.setEnabled(False)
        layout.addWidget(self.signal_465_combo, 3, 1, 1, 3)

        self.time_combo.currentTextChanged.connect(
            lambda value: self._persist_column_setting("selected_time_column", value)
        )
        self.signal_405_combo.currentTextChanged.connect(
            lambda value: self._persist_column_setting("selected_405nm_column", value)
        )
        self.signal_465_combo.currentTextChanged.connect(
            lambda value: self._persist_column_setting("selected_465nm_column", value)
        )
        return group

    def _create_time_group(self) -> QGroupBox:
        group = QGroupBox("Time Selection for Analysis", self)
        layout = QGridLayout(group)
        layout.addWidget(QLabel("Start Time (s):", group), 0, 0)
        self.start_time_edit = QLineEdit(group)
        layout.addWidget(self.start_time_edit, 0, 1)
        layout.addWidget(QLabel("End Time (s):", group), 1, 0)
        self.end_time_edit = QLineEdit(group)
        layout.addWidget(self.end_time_edit, 1, 1)
        layout.addWidget(QLabel("Total Time:", group), 2, 0)
        self.total_time_label = QLabel("0 s", group)
        self.total_time_label.setStyleSheet("color: #1f5fbf; font-weight: 700;")
        layout.addWidget(self.total_time_label, 2, 1)

        save_button = QPushButton("Save Times", group)
        apply_button_role(save_button, "primary")
        save_button.clicked.connect(self.save_times)
        layout.addWidget(save_button, 3, 1, alignment=Qt.AlignLeft)

        self.start_time_edit.textChanged.connect(self.refresh_time_selection_preview)
        self.end_time_edit.textChanged.connect(self.refresh_time_selection_preview)
        return group

    def _create_export_group(self) -> QGroupBox:
        group = QGroupBox("Export Options", self)
        layout = QGridLayout(group)
        layout.addWidget(QLabel("Choose Noise Correction", group), 0, 0, 1, 2)
        layout.addWidget(QLabel("Analysis Option:", group), 1, 0)
        self.analysis_option_combo = QComboBox(group)
        self.analysis_option_combo.addItems(["1", "2", "3", "4"])
        layout.addWidget(self.analysis_option_combo, 1, 1)
        return group

    def _select_default_data_folder(self) -> None:
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select Default Data Folder", self.settings_manager.default_data_folder_path or ""
        )
        if folder_path:
            self.settings_manager.default_data_folder_path = folder_path
            self.settings_manager.save_variables()

    def _select_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Photometry Data File",
            self.settings_manager.default_data_folder_path or "",
            "Data Files (*.csv *.xlsx);;CSV Files (*.csv);;Excel Files (*.xlsx)",
        )
        if file_path:
            self.handle_new_data_file(file_path)

    def _persist_column_setting(self, setting_name: str, value: str) -> None:
        if value:
            setattr(self.settings_manager, setting_name, value)
            self.settings_manager.save_variables()

    def _set_combo_items(self, combo: QComboBox, values: list[str], preferred: str | None) -> None:
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(values)
        combo.setEnabled(bool(values))
        if preferred in values:
            combo.setCurrentText(preferred)
        elif values:
            combo.setCurrentIndex(0)
        combo.blockSignals(False)

    def handle_new_data_file(self, file_path: str) -> None:
        try:
            dataframe = load_data_file(file_path)
            self.processor = PhotometryRawProcessor(file_path=file_path, dataframe=dataframe)
            self.column_options = list(self.processor.raw_data.columns)
            time_column, signal_405_column, signal_465_column = self._identify_columns()
            raw_signals = self.processor.load_data_to_numpy(
                time_column, signal_405_column, signal_465_column
            )
        except Exception as exc:
            QMessageBox.critical(self, "Load Error", str(exc))
            return

        self.file_path_edit.setText(file_path)
        self._set_combo_items(self.time_combo, self.column_options, self.settings_manager.selected_time_column or time_column)
        self._set_combo_items(self.signal_405_combo, self.column_options, self.settings_manager.selected_405nm_column or signal_405_column)
        self._set_combo_items(self.signal_465_combo, self.column_options, self.settings_manager.selected_465nm_column or signal_465_column)
        self.clear_graphs()
        self._draw_raw_graph(raw_signals)
        self.refresh_time_selection_preview()

    def _identify_columns(self) -> tuple[str, str, str]:
        if self.processor is None:
            raise ValueError("No data has been loaded.")

        time_column = next((column for column in self.column_options if is_time_data(self.processor.raw_data[[column]])), None)
        if not time_column:
            raise ValueError("No suitable time column found in the data.")

        column_candidates = [column for column in self.column_options if column != time_column]
        signal_405_column = "405nm" if "405nm" in column_candidates else column_candidates[0]
        signal_465_column = "465nm" if "465nm" in column_candidates else "490nm" if "490nm" in column_candidates else column_candidates[1]
        return time_column, signal_405_column, signal_465_column

    def _draw_raw_graph(self, raw_signals) -> None:
        figure = Figure(figsize=(10, 4), dpi=100)
        axis_465 = figure.add_subplot(111)
        axis_405 = axis_465.twinx()
        time_values, signal_405, signal_465 = raw_signals

        signal_405_min = min(signal_405)
        signal_405_max = max(signal_405)
        y_top_405 = signal_405_max + signal_405_min
        y_bottom_405 = signal_405_min - (0.01 * signal_405_min)
        range_405 = y_top_405 - y_bottom_405

        signal_465_min = min(signal_465)
        signal_465_max = max(signal_465)
        axis_465.plot(time_values, signal_465, color="green", linewidth=0.8)
        axis_405.plot(time_values, signal_405, color="purple", linewidth=0.5, alpha=0.5)
        axis_465.set_ylabel("465nm Signal", color="green")
        axis_405.set_ylabel("405nm Signal", color="purple")
        axis_465.tick_params(axis="y", labelcolor="green")
        axis_405.tick_params(axis="y", labelcolor="purple")
        axis_465.set_ylim([signal_465_min - (0.5 * range_405), signal_465_max * 1.02])
        axis_405.set_ylim(y_bottom_405, y_top_405)

        start_line = axis_465.axvline(x=time_values[0], color="red", linestyle="--", linewidth=1.5)
        end_line = axis_465.axvline(x=time_values[-1], color="blue", linestyle="--", linewidth=1.5)
        axis_465.set_title("Raw Data")
        axis_465.set_xlabel("Time (min)")
        axis_465.set_xlim([time_values[0] - 1, time_values[-1] + 1])
        figure.tight_layout()

        self.all_graphs_reference[0] = GraphReference(figure, axis_465, axis_405, start_line, end_line)
        self.raw_graph_panel.set_figure(figure)

    def _selected_time_range_minutes(self) -> tuple[float, float] | None:
        graph = self.all_graphs_reference.get(0)
        if graph is None or not graph.primary_axis.lines:
            return None
        x_data = graph.primary_axis.lines[0].get_xdata()
        if len(x_data) == 0:
            return None
        time_min = float(x_data[0])
        time_max = float(x_data[-1])
        try:
            start_time = float(self.start_time_edit.text()) / 60 if self.start_time_edit.text().strip() else time_min
            end_time = float(self.end_time_edit.text()) / 60 if self.end_time_edit.text().strip() else time_max
        except ValueError:
            return None
        start_time = min(max(start_time, time_min), time_max)
        end_time = min(max(end_time, time_min), time_max)
        if end_time < start_time:
            end_time = time_max
        return start_time, end_time

    def save_times(self) -> None:
        selected_range = self._selected_time_range_minutes()
        if selected_range is None:
            self.total_time_label.setText("Invalid")
            return
        self.update_lines(*selected_range)

    def refresh_time_selection_preview(self) -> None:
        selected_range = self._selected_time_range_minutes()
        if selected_range is None:
            self.total_time_label.setText("Invalid")
            return
        start_time, end_time = selected_range
        total_seconds = round((end_time - start_time) * 60)
        self.total_time_label.setText(f"{total_seconds} s" if total_seconds > 0 else "Invalid")
        self.update_lines(start_time, end_time)

    def update_lines(self, start_time: float, end_time: float) -> None:
        graph = self.all_graphs_reference.get(0)
        if graph is None:
            return
        graph.start_line.set_xdata([start_time, start_time])
        graph.end_line.set_xdata([end_time, end_time])
        if graph.figure.canvas is not None:
            graph.figure.canvas.draw_idle()

    def clear_graphs(self) -> None:
        self.all_graphs_reference.clear()
        self.raw_graph_panel.clear()
        self.noise_graph_panel.clear()
        self.final_graph_panel.clear()
