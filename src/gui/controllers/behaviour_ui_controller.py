"""Controller for graph/settings UI container setup and color selection."""

from __future__ import annotations

import tkinter as tk
from tkinter import colorchooser, ttk

from src.gui.views.export_options_container import ExportOptionsContainer
from src.gui.views.graph_settings_container import GraphSettingsContainer


class BehaviourUIController:
    """Owns app-specific widget setup for graph and settings panels."""

    def __init__(self, app):
        self.app = app

    def initialize_graph_settings(
        self, graph_settings_tab, export_options_tab, notebook_graphs
    ):
        self.app.graph_settings_container_instance = GraphSettingsContainer(
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

        self.app.export_options_container = ExportOptionsContainer(
            export_options_tab,
            file_path_var=self.app.file_path_var,
            settings_manager=self.app.settings_manager,
            extract_button_click_handler=self.app.export_controller.extract_button_click_handler,
            save_image=self.app.plot_controller.save_image,
        )

        self.app.graph_settings_container_instance.complete_initialization()

        self.configure_grid(graph_settings_tab, row=0, weight=1)
        self.configure_grid(graph_settings_tab, column=0, weight=1)
        self.configure_grid(export_options_tab, row=0, weight=1)
        self.configure_grid(export_options_tab, column=0, weight=1)

        graph_tab = ttk.Frame(notebook_graphs, style="CustomNotebook.TFrame")
        table_tab = ttk.Frame(notebook_graphs, style="CustomNotebook.TFrame")

        self.configure_grid(graph_tab, row=0, weight=1)
        self.configure_grid(graph_tab, column=0, weight=1)
        self.configure_grid(table_tab, row=0, weight=1)
        self.configure_grid(table_tab, column=0, weight=1)

        notebook_graphs.add(graph_tab, text="Graph")
        notebook_graphs.add(table_tab, text="Table")

        return graph_tab, table_tab

    def configure_grid(self, container, row=None, column=None, weight=None) -> None:
        if row is not None:
            container.grid_rowconfigure(row, weight=weight)
        if column is not None:
            container.grid_columnconfigure(column, weight=weight)

    def create_graphs_container(self, frame) -> None:
        graphs_container_frame = ttk.Frame(
            frame, style="NoBorder.TFrame", borderwidth=2, relief="solid"
        )
        graphs_container_frame.grid(
            row=0, column=0, columnspan=3, padx=10, pady=10, sticky=tk.NSEW
        )
        graphs_container_frame.columnconfigure(0, weight=1)
        graphs_container_frame.rowconfigure(0, weight=1)

        color_button = tk.Button(
            graphs_container_frame,
            text="Main Trace Colour",
            bg="lightblue",
            command=self.handle_trace_color_selection,
        )
        color_button.grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)

        sem_color_button = tk.Button(
            graphs_container_frame,
            text="SEM Colour",
            bg="lightblue",
            command=self.handle_sem_color_selection,
        )
        sem_color_button.grid(row=0, column=1, padx=10, pady=10, sticky=tk.W)

        self.app.selected_behaviour = tk.StringVar(value="Choose behaviour to plot")

        def behaviour_selection_changed(*args):
            if self.app.selected_behaviour.get() == "":
                return

            if self.app.selected_column_var.get() == "Behaviour Mean and SEM":
                self.app.plot_controller.handle_figure_display_selection(None)
            else:
                self.app.figure_display_dropdown.set("Behaviour Mean and SEM")
                self.app.plot_controller.handle_figure_display_selection(None)

        self.app.selected_behaviour.trace("w", behaviour_selection_changed)

        self.app.behaviour_choice_graph = ttk.Combobox(
            graphs_container_frame,
            state="readonly",
            width=30,
            textvariable=self.app.selected_behaviour,
        )
        self.app.behaviour_choice_graph.grid(row=0, column=2, padx=5, sticky=tk.W)
        self.app.behaviour_choice_graph.configure(state=tk.DISABLED)
        self.app.figure_display_choices = [
            "Full Trace Display",
            "Single Row Display",
            "Behaviour Mean and SEM",
        ]
        self.app.figure_display_dropdown = ttk.Combobox(
            graphs_container_frame,
            state="readonly",
            values=self.app.figure_display_choices,
            width=30,
        )
        self.app.figure_display_dropdown.grid(row=0, column=3, padx=5, sticky=tk.W)
        self.app.figure_display_dropdown.bind(
            "<<ComboboxSelected>>", self.app.plot_controller.handle_figure_display_selection
        )

        self.app.figure_display_dropdown.set(self.app.figure_display_choices[0])
        self.app.data_selection_frame.set_figure_display_dropdown(
            self.app.figure_display_dropdown
        )
        self.app.data_selection_frame.set_figure_display_choices(
            self.app.figure_display_choices
        )

        self.app.graph_canvas = tk.Canvas(
            graphs_container_frame, bg="snow", highlightthickness=1
        )
        self.app.graph_canvas.grid(row=1, column=0, columnspan=4, sticky=tk.NSEW)

        self.configure_grid(graphs_container_frame, column=0, weight=1)
        self.configure_grid(graphs_container_frame, row=0, weight=0)
        self.configure_grid(graphs_container_frame, column=1, weight=1)
        self.configure_grid(graphs_container_frame, row=1, weight=1)

    def handle_sem_color_selection(self) -> None:
        new_color = colorchooser.askcolor(title="Choose SEM Colour")
        if new_color[1]:
            self.app.settings_manager.selected_sem_color = new_color[1]
            self.app.plot_controller.handle_figure_display_selection(None)

    def handle_trace_color_selection(self) -> None:
        new_color = colorchooser.askcolor(
            color=self.app.settings_manager.selected_trace_color
        )
        if new_color[1]:
            self.app.settings_manager.selected_trace_color = new_color[1]
            self.app.plot_controller.handle_figure_display_selection(None)
