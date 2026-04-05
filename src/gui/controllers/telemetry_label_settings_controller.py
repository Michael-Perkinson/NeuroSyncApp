"""Controller for telemetry peak/cluster label settings popup."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from src.gui.shared.qt_bindings import LineEditControl, ObservableValue


class TelemetryLabelSettingsController:
    """Owns label settings popup construction and save/apply behavior."""

    def __init__(self, app):
        self.app = app

    def open_label_settings_popup(self) -> None:
        self.app.popup = QDialog(self.app)
        self.app.popup.setWindowTitle("Cluster Label Settings")
        layout = QGridLayout(self.app.popup)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(12)

        self.app.symbol_options = ["o", "*", "s", "D", "^", "v", "<", ">"]
        self.app.baseline_style_options = ["-", "--", "-.", ":"]

        self.app.label_color_var = ObservableValue(
            self.app.settings_manager.selected_label_color
        )
        self.app.label_symbol_var = ObservableValue(
            self.app.settings_manager.selected_label_symbol
        )
        self.app.label_size_var = ObservableValue(
            str(self.app.settings_manager.selected_label_size)
        )
        self.app.y_offset_peak_symbol = ObservableValue(
            str(self.app.settings_manager.selected_y_offset_peak_symbol)
        )
        self.app.peak_count_color_var = ObservableValue(
            self.app.settings_manager.selected_peak_count_color
        )
        self.app.peak_count_size_var = ObservableValue(
            str(self.app.settings_manager.selected_peak_count_size)
        )
        self.app.y_for_peak_count = ObservableValue(
            str(self.app.settings_manager.selected_y_for_peak_count)
        )
        self.app.baseline_color = ObservableValue(
            self.app.settings_manager.selected_baseline_color
        )
        self.app.baseline_multiplier = ObservableValue(
            str(self.app.settings_manager.selected_baseline_multiplier)
        )
        self.app.baseline_style = ObservableValue(
            self.app.settings_manager.selected_baseline_style
        )
        self.app.baseline_thickness = ObservableValue(
            str(self.app.settings_manager.selected_baseline_thickness)
        )
        self.app.cluster_box_color = ObservableValue(
            self.app.settings_manager.selected_cluster_box_color
        )
        self.app.cluster_box_alpha = ObservableValue(
            str(self.app.settings_manager.selected_cluster_box_alpha)
        )
        self.app.cluster_box_height_modifier = ObservableValue(
            str(self.app.settings_manager.selected_cluster_box_height_modifier)
        )

        self.app.peak_label_frame = self._create_group("Peak Label Settings", self.app.popup)
        self._build_peak_settings(self.app.peak_label_frame.layout())
        layout.addWidget(self.app.peak_label_frame, 0, 0)

        self.app.peak_count_label_frame = self._create_group("Peak Count Settings", self.app.popup)
        self._build_peak_count_settings(self.app.peak_count_label_frame.layout())
        layout.addWidget(self.app.peak_count_label_frame, 1, 0)

        self.app.baseline_label_frame = self._create_group("Baseline Settings", self.app.popup)
        self._build_baseline_settings(self.app.baseline_label_frame.layout())
        layout.addWidget(self.app.baseline_label_frame, 0, 1)

        self.app.cluster_box_frame = self._create_group("Cluster Box Settings", self.app.popup)
        self._build_cluster_box_settings(self.app.cluster_box_frame.layout())
        layout.addWidget(self.app.cluster_box_frame, 1, 1)

        save_button = QPushButton("Save & Close", self.app.popup)
        save_button.clicked.connect(
            lambda: self.save_and_close_label_settings(self.app.popup)
        )
        layout.addWidget(save_button, 2, 0, 1, 2)
        self.app.popup.exec()

    def _create_group(self, title: str, parent: QWidget) -> QFrame:
        frame = QFrame(parent)
        frame.setObjectName("telemetrySettingsGroup")
        frame.setStyleSheet(
            "#telemetrySettingsGroup { background: white; border: 1px solid #d7dce2; }"
        )
        group_layout = QGridLayout(frame)
        group_layout.setContentsMargins(10, 10, 10, 10)
        group_layout.setHorizontalSpacing(10)
        group_layout.setVerticalSpacing(8)
        group_layout.addWidget(QLabel(f"<b>{title}</b>", frame), 0, 0, 1, 2)
        return frame

    def _build_peak_settings(self, layout: QGridLayout) -> None:
        button = QPushButton("Peak Symbol Colour", self.app.peak_label_frame)
        button.clicked.connect(self.choose_label_color)
        layout.addWidget(button, 1, 0, 1, 2)

        layout.addWidget(QLabel("Peak Symbol:", self.app.peak_label_frame), 2, 0)
        symbol_dropdown = QComboBox(self.app.peak_label_frame)
        symbol_dropdown.addItems(self.app.symbol_options)
        symbol_dropdown.setCurrentText(self.app.label_symbol_var.get())
        symbol_dropdown.currentTextChanged.connect(self.app.label_symbol_var.set)
        layout.addWidget(symbol_dropdown, 2, 1)

        layout.addWidget(QLabel("Peak Symbol Size:", self.app.peak_label_frame), 3, 0)
        layout.addWidget(LineEditControl(self.app.label_size_var, self.app.peak_label_frame), 3, 1)

        layout.addWidget(QLabel("Peak Symbol Y-Offset:", self.app.peak_label_frame), 4, 0)
        layout.addWidget(LineEditControl(self.app.y_offset_peak_symbol, self.app.peak_label_frame), 4, 1)

    def _build_peak_count_settings(self, layout: QGridLayout) -> None:
        button = QPushButton("Peak Number Colour", self.app.peak_count_label_frame)
        button.clicked.connect(self.choose_peak_count_color)
        layout.addWidget(button, 1, 0, 1, 2)

        layout.addWidget(QLabel("Peak Number Font Size:", self.app.peak_count_label_frame), 2, 0)
        layout.addWidget(LineEditControl(self.app.peak_count_size_var, self.app.peak_count_label_frame), 2, 1)

        layout.addWidget(QLabel("Y Offset:", self.app.peak_count_label_frame), 3, 0)
        layout.addWidget(LineEditControl(self.app.y_for_peak_count, self.app.peak_count_label_frame), 3, 1)

    def _build_baseline_settings(self, layout: QGridLayout) -> None:
        button = QPushButton("Baseline Symbol Colour", self.app.baseline_label_frame)
        button.clicked.connect(self.choose_baseline_color)
        layout.addWidget(button, 1, 0, 1, 2)

        layout.addWidget(
            QLabel("Cluster End Multiplier (Empty = Median):", self.app.baseline_label_frame),
            2,
            0,
        )
        layout.addWidget(LineEditControl(self.app.baseline_multiplier, self.app.baseline_label_frame), 2, 1)

        layout.addWidget(QLabel("Baseline Symbol Style:", self.app.baseline_label_frame), 3, 0)
        style_dropdown = QComboBox(self.app.baseline_label_frame)
        style_dropdown.addItems(self.app.baseline_style_options)
        style_dropdown.setCurrentText(self.app.baseline_style.get())
        style_dropdown.currentTextChanged.connect(self.app.baseline_style.set)
        layout.addWidget(style_dropdown, 3, 1)

        layout.addWidget(QLabel("Baseline Thickness:", self.app.baseline_label_frame), 4, 0)
        layout.addWidget(LineEditControl(self.app.baseline_thickness, self.app.baseline_label_frame), 4, 1)

    def _build_cluster_box_settings(self, layout: QGridLayout) -> None:
        button = QPushButton("Cluster Box Colour", self.app.cluster_box_frame)
        button.clicked.connect(self.choose_cluster_box_color)
        layout.addWidget(button, 1, 0, 1, 2)

        layout.addWidget(QLabel("Cluster Box Alpha:", self.app.cluster_box_frame), 2, 0)
        layout.addWidget(LineEditControl(self.app.cluster_box_alpha, self.app.cluster_box_frame), 2, 1)

        layout.addWidget(QLabel("Cluster Box Height Modifier:", self.app.cluster_box_frame), 3, 0)
        layout.addWidget(LineEditControl(self.app.cluster_box_height_modifier, self.app.cluster_box_frame), 3, 1)

    def choose_baseline_color(self):
        color = QColorDialog.getColor(parent=self.app.popup)
        if color.isValid():
            self.app.baseline_color.set(color.name())

    def choose_label_color(self):
        color = QColorDialog.getColor(parent=self.app.popup)
        if color.isValid():
            self.app.label_color_var.set(color.name())

    def choose_peak_count_color(self):
        color = QColorDialog.getColor(parent=self.app.popup)
        if color.isValid():
            self.app.peak_count_color_var.set(color.name())

    def choose_cluster_box_color(self):
        color = QColorDialog.getColor(parent=self.app.popup)
        if color.isValid():
            self.app.cluster_box_color.set(color.name())

    def save_and_close_label_settings(self, popup):
        current_baseline_multiplier = self.app.settings_manager.selected_baseline_multiplier

        self.app.settings_manager.selected_label_color = self.app.label_color_var.get()
        self.app.settings_manager.selected_label_symbol = self.app.label_symbol_var.get()
        self.app.settings_manager.selected_label_size = int(self.app.label_size_var.get())
        self.app.settings_manager.selected_y_offset_peak_symbol = int(
            self.app.y_offset_peak_symbol.get()
        )
        self.app.settings_manager.selected_peak_count_color = (
            self.app.peak_count_color_var.get()
        )
        self.app.settings_manager.selected_peak_count_size = int(
            self.app.peak_count_size_var.get()
        )
        self.app.settings_manager.selected_y_for_peak_count = int(
            self.app.y_for_peak_count.get()
        )
        self.app.settings_manager.selected_baseline_multiplier = (
            self.app.baseline_multiplier.get()
        )
        self.app.settings_manager.selected_baseline_color = self.app.baseline_color.get()
        self.app.settings_manager.selected_baseline_style = self.app.baseline_style.get()
        self.app.settings_manager.selected_baseline_thickness = (
            self.app.baseline_thickness.get()
        )
        self.app.settings_manager.selected_cluster_box_color = (
            self.app.cluster_box_color.get()
        )
        self.app.settings_manager.selected_cluster_box_alpha = (
            self.app.cluster_box_alpha.get()
        )
        self.app.settings_manager.selected_cluster_box_height_modifier = (
            self.app.cluster_box_height_modifier.get()
        )
        self.app.settings_manager.save_variables()

        if (
            current_baseline_multiplier
            != self.app.settings_manager.selected_baseline_multiplier
        ):
            self.app.reset_clusters_based_on_user_input()
            return

        if hasattr(self.app, "figure_canvas"):
            if self.app.act_data is not None and self.app.temp_data is not None:
                self.app.telemetry_plot_controller.visualize_photometry_data_with_overlays(
                    self.app.time_column,
                    self.app.data_column,
                    self.app.detected_peaks,
                    self.app.clusters_final,
                    self.app.graph_canvas,
                    self.app.temp_data,
                    self.app.act_data,
                    show_nighttime=True,
                )
            else:
                self.app.telemetry_plot_controller.visualize_photometry_data_with_overlays(
                    self.app.time_column,
                    self.app.data_column,
                    self.app.detected_peaks,
                    self.app.clusters_final,
                    self.app.graph_canvas,
                )

        popup.accept()
