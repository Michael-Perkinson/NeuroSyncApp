"""Controller for graph/settings UI container setup and color selection."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QColorDialog,
    QFrame,
    QHBoxLayout,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.gui.shared.qt_bindings import ComboBoxControl, ObservableValue
from src.gui.shared.qt_view_styles import panel_stylesheet
from src.gui.views.export_options_panel import ExportOptionsPanel
from src.gui.views.graph_settings_panel import GraphSettingsPanel


class BehaviourUIController:
    """Owns app-specific widget setup for graph and settings panels."""

    BEHAVIOUR_DISPLAY_CHOICES = [
        "Full Trace Display",
        "Single Row Display",
        "Behaviour Mean and SEM",
    ]

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
            refresh_graph_display_callback=self.app.plot_controller.handle_figure_display_selection,
            update_duration_box_callback=self.app.plot_controller.update_duration_box,
            handle_behaviour_change_callback=self.app.behaviour_graph_helpers_controller.handle_behaviour_change,
            load_variables_callback=self.app.settings_manager.load_variables,
            save_variables_callback=self.app.settings_manager.save_variables,
            create_behaviour_options_callback=self.app.behaviour_options_controller.create_behaviour_options,
            update_box_colors_callback=self.app.behaviour_options_controller.update_box_colors_and_behaviour_options,
            save_and_close_axis_callback=self.app.plot_controller.save_and_close_axis_range,
        )

        self.app.export_options_container = ExportOptionsPanel(
            export_options_tab,
            file_path_var=self.app.file_path_var,
            settings_manager=self.app.settings_manager,
            extract_button_click_handler=self.app.export_controller.extract_button_click_handler,
            save_image=self.app.plot_controller.save_image,
        )

        self.app.graph_settings_container_instance.complete_initialization()
        self._ensure_layout(graph_settings_tab).addWidget(
            self.app.graph_settings_container_instance
        )
        self._ensure_layout(export_options_tab).addWidget(self.app.export_options_container)

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

        self.app.trace_color_button = QPushButton(
            text="Main Trace Colour",
            parent=graphs_container_frame,
        )
        self.app.trace_color_button.clicked.connect(self.handle_trace_color_selection)
        self._style_color_button(
            self.app.trace_color_button,
            self.app.settings_manager.selected_trace_color,
        )
        toolbar_layout.addWidget(self.app.trace_color_button)

        self.app.sem_color_button = QPushButton(
            text="SEM Colour",
            parent=graphs_container_frame,
        )
        self.app.sem_color_button.clicked.connect(self.handle_sem_color_selection)
        self._style_color_button(
            self.app.sem_color_button,
            self.app.settings_manager.selected_sem_color,
        )
        toolbar_layout.addWidget(self.app.sem_color_button)

        self.app.selected_behaviour = ObservableValue("Choose behaviour to plot")

        def behaviour_selection_changed():
            if self.app.selected_behaviour.get() == "":
                return
            if (
                not self._has_current_behaviour_table()
                or not self.app.behaviour_choice_graph.isEnabled()
            ):
                return

            if self.app.figure_display_dropdown.get() == "Behaviour Mean and SEM":
                self.app.plot_controller.handle_figure_display_selection(None)
            else:
                self.app.figure_display_dropdown.set("Behaviour Mean and SEM")
                self.app.plot_controller.handle_figure_display_selection(None)

        self.app.selected_behaviour.trace_add("write", behaviour_selection_changed)

        self.app.behaviour_choice_graph = ComboBoxControl(
            self.app.selected_behaviour, graphs_container_frame
        )
        self.app.behaviour_choice_graph.configure(state="disabled")
        toolbar_layout.addWidget(self.app.behaviour_choice_graph)
        self.app.figure_display_choices = self.BEHAVIOUR_DISPLAY_CHOICES.copy()
        self.app.figure_display_dropdown = ComboBoxControl(parent=graphs_container_frame)
        self.app.figure_display_dropdown.set_options(["Full Trace Display"])
        self.app.figure_display_dropdown.bind(
            "<<ComboboxSelected>>", self.app.plot_controller.handle_figure_display_selection
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

    def _has_current_behaviour_table(self) -> bool:
        current_key = getattr(self.app, "current_table_key", None)
        tables = getattr(self.app, "tables", {})
        return current_key is not None and current_key in tables

    def update_graph_mode_controls(
        self, behaviour_sheet_available: bool | None = None
    ) -> None:
        if not hasattr(self.app, "figure_display_dropdown"):
            return

        if behaviour_sheet_available is None:
            behaviour_sheet_available = self._has_current_behaviour_table()

        choices = ["Full Trace Display"]
        if behaviour_sheet_available:
            choices.extend(["Single Row Display", "Behaviour Mean and SEM"])

        baseline_enabled = bool(
            getattr(self.app, "checkbox_state", False)
            or self.app.data_selection_frame.use_baseline_var.get()
        )
        if baseline_enabled:
            choices.append("Z-scored data")

        current_choice = self.app.figure_display_dropdown.get()
        self.app.figure_display_dropdown.set_options(choices)
        if current_choice in choices:
            self.app.figure_display_dropdown.set(current_choice)
        else:
            self.app.figure_display_dropdown.set("Full Trace Display")

        if not behaviour_sheet_available:
            self.app.selected_behaviour.set("")
            self.app.behaviour_choice_graph.configure(state="disabled")
        elif self.app.behaviour_choice_graph.count() > 0:
            self.app.behaviour_choice_graph.configure(state="normal")

    def handle_sem_color_selection(self) -> None:
        new_color = QColorDialog.getColor(parent=self.app.graph_canvas)
        if new_color.isValid():
            self.app.settings_manager.selected_sem_color = new_color.name()
            self._style_color_button(self.app.sem_color_button, new_color.name())
            self.app.plot_controller.handle_figure_display_selection(None)

    def handle_trace_color_selection(self) -> None:
        new_color = QColorDialog.getColor(parent=self.app.graph_canvas)
        if new_color.isValid():
            self.app.settings_manager.selected_trace_color = new_color.name()
            self._style_color_button(self.app.trace_color_button, new_color.name())
            self.app.plot_controller.handle_figure_display_selection(None)

    @staticmethod
    def _style_color_button(button: QPushButton, color: str) -> None:
        from PySide6.QtGui import QColor
        from PySide6.QtCore import Qt
        qc = QColor(color)
        brightness = (0.299 * qc.red() + 0.587 * qc.green() + 0.114 * qc.blue()) / 255
        fg = "white" if brightness < 0.56 else "#17324D"
        button.setCursor(Qt.PointingHandCursor)
        button.setStyleSheet(
            f"QPushButton {{ background: {color}; color: {fg}; border: 1px solid rgba(23,50,77,0.16);"
            f" border-radius: 10px; padding: 7px 12px; font-weight: 600; }}"
        )
