"""Controller for graph/settings UI container setup and color selection."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QColorDialog,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.features.behaviour_alignment.services.plot_service import (
    _column_colors,
    _column_sem_colors,
    _selected_columns,
)
from src.gui.framework.qt_view_styles import panel_stylesheet
from src.gui.framework.tk_compat_controls import ComboBoxControl, ObservableValue
from src.gui.views.export_options_panel import ExportOptionsPanel
from src.panels.graph_settings_panel import GraphSettingsPanel


def _trace_colour_control_labels(columns: list[str]) -> tuple[str, str]:
    """Return trace/SEM control labels for the first selected signal."""
    primary = columns[0] if columns else "Primary"
    return f"{primary} Trace Colour:", f"{primary} SEM Colour:"


def _colour_control_labels(columns: list[str]) -> list[tuple[str, str]]:
    """Return trace/SEM labels grouped in selected-signal order."""
    return [
        (f"{column} Trace Colour:", f"{column} SEM Colour:")
        for column in columns
    ]


class BehaviourUiBuilder:
    """Owns app-specific widget setup for graph and settings panels."""

    def __init__(self, app):
        self.app = app

    def initialize_graph_settings(
        self, graph_settings_tab, export_options_tab, notebook_graphs
    ):
        self.app.graph_settings_container_instance = GraphSettingsPanel(
            graph_settings_tab,
            widgets_to_include=[
                "line_width",
                "box_height",
                "alpha",
                "bar_graph_size",
                "onset_line_thickness",
                "onset_line_style",
                "color_buttons",
                "checkboxes",
                "axis_range",
                "zero_x_axis_to_behaviour",
                "graph_time_labels",
            ],
            app_name=self.app.app_name,
            settings_manager=self.app.settings_manager,
            refresh_graph_display_callback=self.app.plot_service.handle_figure_display_selection,
            update_duration_box_callback=self.app.plot_service.update_duration_box,
            handle_behaviour_change_callback=self.app.graph_helper_service.handle_behaviour_change,
            load_variables_callback=self.app.settings_manager.load_variables,
            save_variables_callback=self.app.settings_manager.save_variables,
            create_behaviour_options_callback=self.app.behaviour_options_panel.create_behaviour_options,
            update_box_colors_callback=self.app.behaviour_options_panel.update_box_colors_and_behaviour_options,
            save_and_close_axis_callback=self.app.plot_service.save_and_close_axis_range,
        )

        self.app.export_options_container = ExportOptionsPanel(
            export_options_tab,
            file_path_var=self.app.file_path_var,
            settings_manager=self.app.settings_manager,
            extract_button_click_handler=self.app.behaviour_exporter.extract_button_click_handler,
            save_image=self.app.plot_service.save_image,
        )

        self.app.graph_settings_container_instance.complete_initialization()
        self._ensure_layout(graph_settings_tab).addWidget(
            self.app.graph_settings_container_instance
        )
        self._ensure_layout(export_options_tab).addWidget(
            self.app.export_options_container
        )

        graph_tab = QWidget(notebook_graphs)
        table_tab = QWidget(notebook_graphs)
        self._ensure_layout(graph_tab)
        self._ensure_layout(table_tab)

        notebook_graphs.addTab(graph_tab, "Graph")
        notebook_graphs.addTab(table_tab, "Table")

        return graph_tab, table_tab

    def _ensure_layout(self, container):
        layout = container.layout()
        if layout is None:
            layout = QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(10)
        return layout

    def create_graphs_container(self, frame) -> None:
        graphs_container_frame = QFrame(frame)
        graphs_container_frame.setObjectName("behaviourGraphsContainer")
        graphs_container_frame.setStyleSheet(
            panel_stylesheet("behaviourGraphsContainer")
        )
        frame.layout().addWidget(graphs_container_frame)

        container_layout = QVBoxLayout(graphs_container_frame)
        container_layout.setContentsMargins(10, 10, 10, 10)
        container_layout.setSpacing(10)

        toolbar_layout = QHBoxLayout()
        container_layout.addLayout(toolbar_layout)

        self.app.trace_colors_button = QPushButton(
            text="Trace Colours",
            parent=graphs_container_frame,
        )
        self.app.trace_colors_button.clicked.connect(self.open_trace_colors_popup)
        toolbar_layout.addWidget(self.app.trace_colors_button)

        self.app.selected_behaviour = ObservableValue("Choose behaviour to plot")

        def behaviour_selection_changed():
            if self.app.selected_behaviour.get() == "":
                return

            if self.app.selected_column_var.get() == "Behaviour Mean and SEM":
                self.app.plot_service.handle_figure_display_selection(None)
            else:
                self.app.figure_display_dropdown.set("Behaviour Mean and SEM")
                self.app.plot_service.handle_figure_display_selection(None)

        self.app.selected_behaviour.trace_add("write", behaviour_selection_changed)

        self.app.behaviour_choice_graph = ComboBoxControl(
            self.app.selected_behaviour, graphs_container_frame
        )
        self.app.behaviour_choice_graph.configure(state="disabled")
        toolbar_layout.addWidget(self.app.behaviour_choice_graph)
        self.app.figure_display_choices = [
            "Full Trace Display",
            "Single Row Display",
            "Behaviour Mean and SEM",
        ]
        self.app.figure_display_dropdown = ComboBoxControl(
            parent=graphs_container_frame
        )
        self.app.figure_display_dropdown.set_options(self.app.figure_display_choices)
        self.app.figure_display_dropdown.bind(
            "<<ComboboxSelected>>",
            self.app.plot_service.handle_figure_display_selection,
        )
        toolbar_layout.addWidget(self.app.figure_display_dropdown)

        self.app.figure_display_dropdown.set(self.app.figure_display_choices[0])
        self.app.data_selection_frame.set_figure_display_dropdown(
            self.app.figure_display_dropdown
        )
        self.app.data_selection_frame.set_figure_display_choices(
            self.app.figure_display_choices
        )

        self.app.graph_canvas = QWidget(graphs_container_frame)
        self._ensure_layout(self.app.graph_canvas)
        container_layout.addWidget(self.app.graph_canvas, 1)

    def open_trace_colors_popup(self) -> None:
        """Open a colour-picker popup, one row per currently selected column.

        Each selected column gets separate trace and SEM controls, grouped
        together so the relationship between a line and its uncertainty band
        is obvious.
        """
        popup = QDialog(self.app.graph_canvas)
        popup.setWindowTitle("Trace Colours")
        layout = QGridLayout(popup)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(8)

        selected_columns = _selected_columns(self.app)
        labels = _colour_control_labels(selected_columns)
        trace_colors = _column_colors(self.app, selected_columns)
        sem_colors = _column_sem_colors(self.app, selected_columns)
        row = 0
        for index, column in enumerate(selected_columns):
            trace_label, sem_label = labels[index]
            is_primary = index == 0

            layout.addWidget(QLabel(trace_label, popup), row, 0)
            trace_button = QPushButton(popup)
            trace_color = (
                self.app.settings_manager.selected_trace_color
                if is_primary
                else trace_colors[index]
            )
            self._style_color_button(trace_button, trace_color)
            trace_setter = (
                self._set_primary_trace_color
                if is_primary
                else lambda color, col=column: self.app.column_colors.update(
                    {col: color}
                )
            )
            trace_button.clicked.connect(
                lambda _checked=False, btn=trace_button, setter=trace_setter: self._pick_color(
                    btn, setter
                )
            )
            layout.addWidget(trace_button, row, 1)
            row += 1

            layout.addWidget(QLabel(sem_label, popup), row, 0)
            sem_button = QPushButton(popup)
            sem_color = (
                self.app.settings_manager.selected_sem_color
                if is_primary
                else sem_colors[index]
            )
            self._style_color_button(sem_button, sem_color)
            sem_setter = (
                self._set_primary_sem_color
                if is_primary
                else lambda color, col=column: self.app.column_sem_colors.update(
                    {col: color}
                )
            )
            sem_button.clicked.connect(
                lambda _checked=False, btn=sem_button, setter=sem_setter: self._pick_color(
                    btn, setter
                )
            )
            layout.addWidget(sem_button, row, 1)
            row += 1

        close_button = QPushButton("Close", popup)
        close_button.clicked.connect(popup.accept)
        layout.addWidget(close_button, row, 0, 1, 2)

        popup.exec()

    def _set_primary_trace_color(self, color: str) -> None:
        self.app.settings_manager.selected_trace_color = color

    def _set_primary_sem_color(self, color: str) -> None:
        self.app.settings_manager.selected_sem_color = color

    def _pick_color(self, button: QPushButton, apply_color) -> None:
        new_color = QColorDialog.getColor(parent=self.app.graph_canvas)
        if new_color.isValid():
            apply_color(new_color.name())
            self._style_color_button(button, new_color.name())
            self.app.plot_service.handle_figure_display_selection(None)

    @staticmethod
    def _style_color_button(button: QPushButton, color: str) -> None:
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QColor

        qc = QColor(color)
        brightness = (0.299 * qc.red() + 0.587 * qc.green() + 0.114 * qc.blue()) / 255
        fg = "white" if brightness < 0.56 else "#17324D"
        button.setCursor(Qt.PointingHandCursor)
        button.setStyleSheet(
            f"QPushButton {{ background: {color}; color: {fg}; border: 1px solid rgba(23,50,77,0.16);"
            f" border-radius: 10px; padding: 7px 12px; font-weight: 600; }}"
        )
