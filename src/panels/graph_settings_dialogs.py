from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from src.gui.framework.qt_view_styles import (
    apply_button_role,
    panel_stylesheet,
    section_stylesheet,
    subtitle_stylesheet,
    title_stylesheet,
)
from src.gui.framework.tk_compat_controls import LineEditControl, ObservableValue

if TYPE_CHECKING:
    from .graph_settings_panel import GraphSettingsPanel


class _GraphSettingsDialog(QDialog):
    """Shared chrome for GraphSettingsPanel's advanced-settings popups."""

    def __init__(self, panel: GraphSettingsPanel, heading: str, description: str = "") -> None:
        super().__init__(panel)
        self.panel = panel
        self.setWindowTitle(heading)
        self.setObjectName("graphSettingsPanel")
        self.setStyleSheet(
            panel_stylesheet("graphSettingsPanel")
            + section_stylesheet("graphSectionCard")
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel(heading, self)
        title.setStyleSheet(title_stylesheet())
        layout.addWidget(title)

        subtitle = QLabel(description, self)
        subtitle.setStyleSheet(subtitle_stylesheet())
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

    def _build_common_fields(
        self,
        controls: dict[str, ObservableValue],
        include_line_width: bool,
        include_sem: bool,
    ) -> QGridLayout:
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        self.layout().addLayout(grid)

        row = 0
        if include_line_width:
            grid.addWidget(QLabel("Line Width", self), row, 0)
            grid.addWidget(LineEditControl(controls["mean_line_width"], self), row, 1)
            row += 1

        color_key = "mean_line_color" if include_line_width else "mean_bar_color"
        color_label = "Mean Line Colour" if include_line_width else "Mean Bar Colour"
        grid.addWidget(QLabel(color_label, self), row, 0)
        mean_color_button = QPushButton(self)
        self.panel._set_color_button_style(mean_color_button, controls[color_key].get() or "black")
        mean_color_button.clicked.connect(
            lambda: self.panel._select_popup_color(controls[color_key], mean_color_button)
        )
        grid.addWidget(mean_color_button, row, 1)
        row += 1

        alpha_key = "mean_line_alpha" if include_line_width else "mean_bar_alpha"
        alpha_label = "Line Alpha" if include_line_width else "Bar Alpha"
        grid.addWidget(QLabel(alpha_label, self), row, 0)
        grid.addWidget(LineEditControl(controls[alpha_key], self), row, 1)
        row += 1

        if include_sem:
            grid.addWidget(QLabel("SEM Colour", self), row, 0)
            sem_button = QPushButton(self)
            self.panel._set_color_button_style(sem_button, controls["sem_color"].get() or "orange")
            sem_button.clicked.connect(
                lambda: self.panel._select_popup_color(controls["sem_color"], sem_button)
            )
            grid.addWidget(sem_button, row, 1)
            row += 1

            grid.addWidget(QLabel("SEM Alpha", self), row, 0)
            grid.addWidget(LineEditControl(controls["sem_line_alpha"], self), row, 1)
            row += 1

        grid.addWidget(QLabel("Desired Offset", self), row, 0)
        grid.addWidget(LineEditControl(controls["desired_offset"], self), row, 1)
        row += 1

        grid.addWidget(QLabel("Desired Scale", self), row, 0)
        grid.addWidget(LineEditControl(controls["desired_scale"], self), row, 1)
        row += 1

        grid.addWidget(QLabel("Y Axis Colour", self), row, 0)
        axis_button = QPushButton(self)
        self.panel._set_color_button_style(axis_button, controls["y_axis_color"].get() or "black")
        axis_button.clicked.connect(
            lambda: self.panel._select_popup_color(controls["y_axis_color"], axis_button)
        )
        grid.addWidget(axis_button, row, 1)
        row += 1

        grid.addWidget(QLabel("Number of Ticks", self), row, 0)
        grid.addWidget(LineEditControl(controls["num_ticks"], self), row, 1)
        row += 1

        if "num_bins" in controls:
            grid.addWidget(QLabel("Number of Bins", self), row, 0)
            grid.addWidget(LineEditControl(controls["num_bins"], self), row, 1)

        return grid


class AxisRangeDialog(_GraphSettingsDialog):
    def __init__(self, panel: GraphSettingsPanel) -> None:
        super().__init__(panel, "Axis Range")
        form = QGridLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)
        self.layout().addLayout(form)

        axis_fields = [
            ("X Min", panel.x_axis_min_var, "x_axis_min_entry"),
            ("X Max", panel.x_axis_max_var, "x_axis_max_entry"),
            ("Y Min", panel.y_axis_min_var, "y_axis_min_entry"),
            ("Y Max", panel.y_axis_max_var, "y_axis_max_entry"),
        ]
        for index, (label_text, value_model, attr_name) in enumerate(axis_fields):
            row = index // 2
            column = (index % 2) * 2
            form.addWidget(QLabel(label_text, self), row, column)
            entry = LineEditControl(value_model, self)
            entry.setMaximumWidth(120)
            setattr(panel, attr_name, entry)
            form.addWidget(entry, row, column + 1)

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(8)
        self.layout().addLayout(buttons)

        apply_button = QPushButton("Apply", self)
        apply_button_role(apply_button)
        apply_button.clicked.connect(
            lambda: panel.save_and_close_axis(popup=self, close=False)
        )
        buttons.addWidget(apply_button)

        save_button = QPushButton("Apply & Close", self)
        apply_button_role(save_button, "primary")
        save_button.clicked.connect(lambda: panel.save_and_close_axis(popup=self))
        buttons.addWidget(save_button)
        buttons.addStretch(1)


class PhotometrySettingsDialog(_GraphSettingsDialog):
    def __init__(self, panel: GraphSettingsPanel) -> None:
        super().__init__(panel, "Photometry Settings")
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        self.layout().addLayout(grid)

        sm = panel.settings_manager
        self.line_color = ObservableValue(
            str(getattr(sm, "selected_photometry_line_color", "black"))
        )
        self.line_width = ObservableValue(
            str(getattr(sm, "selected_photometry_line_width", "0.5"))
        )
        self.line_alpha = ObservableValue(
            str(getattr(sm, "selected_photometry_line_alpha", "1.0"))
        )

        grid.addWidget(QLabel("Line Colour", self), 0, 0)
        colour_button = QPushButton(self)
        panel._set_color_button_style(colour_button, self.line_color.get() or "black")
        colour_button.clicked.connect(
            lambda: panel._select_popup_color(self.line_color, colour_button)
        )
        grid.addWidget(colour_button, 0, 1)

        grid.addWidget(QLabel("Line Width", self), 1, 0)
        grid.addWidget(LineEditControl(self.line_width, self), 1, 1)

        grid.addWidget(QLabel("Line Alpha", self), 2, 0)
        grid.addWidget(LineEditControl(self.line_alpha, self), 2, 1)

        save_button = QPushButton("Save & Close", self)
        apply_button_role(save_button, "primary")
        save_button.clicked.connect(self._save)
        self.layout().addWidget(save_button, alignment=Qt.AlignLeft)

    def _save(self) -> None:
        panel = self.panel
        panel.settings_manager.selected_photometry_line_color = self.line_color.get() or "black"
        panel.settings_manager.selected_photometry_line_width = self.line_width.get() or "0.5"
        panel.settings_manager.selected_photometry_line_alpha = self.line_alpha.get() or "1.0"
        panel.selected_photometry_line_width.set(
            panel.settings_manager.selected_photometry_line_width
        )
        panel._persist_and_redraw()
        self.accept()


class TemperatureSettingsDialog(_GraphSettingsDialog):
    def __init__(self, panel: GraphSettingsPanel) -> None:
        super().__init__(panel, "Temperature Settings")
        sm = panel.settings_manager
        self.controls = {
            "mean_line_width": ObservableValue(str(getattr(sm, "selected_temp_mean_line_width", "1"))),
            "mean_line_color": ObservableValue(str(getattr(sm, "selected_temp_mean_line_color", "red"))),
            "mean_line_alpha": ObservableValue(str(getattr(sm, "selected_temp_mean_line_alpha", "1.0"))),
            "sem_color": ObservableValue(str(getattr(sm, "selected_temp_sem_color", "orange"))),
            "sem_line_alpha": ObservableValue(str(getattr(sm, "selected_temp_sem_line_alpha", "0.1"))),
            "desired_offset": ObservableValue(str(getattr(sm, "selected_temp_desired_offset", "0.5"))),
            "desired_scale": ObservableValue(str(getattr(sm, "selected_temp_desired_scale", "0.4"))),
            "y_axis_color": ObservableValue(str(getattr(sm, "selected_temp_y_axis_color", "red"))),
            "num_ticks": ObservableValue(str(getattr(sm, "selected_temp_num_ticks", "10"))),
        }
        self._build_common_fields(self.controls, include_line_width=True, include_sem=True)

        save_button = QPushButton("Save & Close", self)
        apply_button_role(save_button, "primary")
        save_button.clicked.connect(self._save)
        self.layout().addWidget(save_button, alignment=Qt.AlignLeft)

    def _save(self) -> None:
        panel = self.panel
        sm = panel.settings_manager
        controls = self.controls
        sm.selected_temp_mean_line_width = controls["mean_line_width"].get() or "1"
        sm.selected_temp_line_width = sm.selected_temp_mean_line_width
        sm.selected_temp_mean_line_color = controls["mean_line_color"].get() or "red"
        sm.selected_temp_sem_color = controls["sem_color"].get() or "orange"
        sm.selected_temp_mean_line_alpha = controls["mean_line_alpha"].get() or "1.0"
        sm.selected_temp_sem_line_alpha = controls["sem_line_alpha"].get() or "0.1"
        sm.selected_temp_desired_offset = controls["desired_offset"].get() or "0.5"
        sm.selected_temp_desired_scale = controls["desired_scale"].get() or "0.4"
        sm.selected_temp_y_axis_color = controls["y_axis_color"].get() or "red"
        sm.selected_temp_num_ticks = controls["num_ticks"].get() or "10"
        panel._persist_and_redraw()
        self.accept()


class ActivitySettingsDialog(_GraphSettingsDialog):
    def __init__(self, panel: GraphSettingsPanel) -> None:
        super().__init__(panel, "Activity Settings")
        sm = panel.settings_manager
        self.controls = {
            "mean_bar_color": ObservableValue(str(getattr(sm, "selected_activity_mean_bar_color", "green"))),
            "mean_bar_alpha": ObservableValue(str(getattr(sm, "selected_activity_mean_bar_alpha", "0.5"))),
            "desired_offset": ObservableValue(str(getattr(sm, "selected_activity_desired_offset", "0"))),
            "desired_scale": ObservableValue(str(getattr(sm, "selected_activity_desired_scale", "0.3"))),
            "y_axis_color": ObservableValue(str(getattr(sm, "selected_activity_y_axis_color", "green"))),
            "num_ticks": ObservableValue(str(getattr(sm, "selected_activity_num_ticks", "10"))),
            "num_bins": ObservableValue(str(getattr(sm, "selected_activity_num_bins", ""))),
        }
        self._build_common_fields(self.controls, include_line_width=False, include_sem=False)

        save_button = QPushButton("Save & Close", self)
        apply_button_role(save_button, "primary")
        save_button.clicked.connect(self._save)
        self.layout().addWidget(save_button, alignment=Qt.AlignLeft)

    def _save(self) -> None:
        panel = self.panel
        sm = panel.settings_manager
        controls = self.controls
        sm.selected_activity_mean_bar_color = controls["mean_bar_color"].get() or "green"
        sm.selected_activity_mean_bar_alpha = controls["mean_bar_alpha"].get() or "0.5"
        sm.selected_activity_desired_offset = controls["desired_offset"].get() or "0"
        sm.selected_activity_desired_scale = controls["desired_scale"].get() or "0.3"
        sm.selected_activity_y_axis_color = controls["y_axis_color"].get() or "green"
        sm.selected_activity_num_ticks = controls["num_ticks"].get() or "10"
        sm.selected_activity_num_bins = controls["num_bins"].get() or ""
        panel._persist_and_redraw()
        self.accept()
