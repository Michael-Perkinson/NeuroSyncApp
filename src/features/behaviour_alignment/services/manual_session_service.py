"""Controller for manual behaviour-file parsing and UI table updates."""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from PySide6.QtWidgets import QMessageBox

import pandas as pd

from src.data.json_handler import (
    load_behaviour_static_inputs,
    save_behaviour_static_inputs,
)
from src.file_management.file_loader import select_preferred_signal_column
from src.processing.behaviour_parser import process_behaviour_rows, read_behaviour_csv
from src.shared.persistence.app_paths import config_file_path
from src.processing.behavior_metrics import calculate_duration_metrics
from src.gui.shared.qt_bindings import ObservableValue
from src.gui.shared.messages_and_errors import show_action_error
from src.string_ops.string_utils import normalize_deduplicate_and_order_strings


class BehaviourManualSessionService:
    """Orchestrates manual behaviour parsing with UI-facing side effects."""

    def __init__(self, app):
        self.app = app

    def parse_manual_data(self, file_path: str) -> bool:
        try:
            if (
                self.app.checkbox_state
                and not self.app.data_selection_frame.baseline_button_pressed
            ):
                QMessageBox.information(
                    self.app,
                    "Baseline not saved",
                    "Please remember to save the baseline values.",
                )
                return False

            behaviour_settings = load_behaviour_static_inputs(config_file_path("behaviour_settings.json"))
            self.app.behaviour_table_panel.clear_table()
            df, column_names = self.read_and_process_file(file_path)
            table_data, behaviour_names, behavior_durations = self.process_each_row(
                df, column_names, behaviour_settings, file_path
            )

            self.calculate_and_store_behavior_metrics(behavior_durations)
            self.update_ui_with_manual_data(table_data, behaviour_names)
            return True
        except IOError as exc:
            show_action_error(
                "Behaviour file could not be opened",
                "NeuroSyncApp could not open the selected behaviour CSV",
                exc,
                self.app,
                "Close the file in other programs, check its permissions, and try again.",
            )
            return False
        except Exception as exc:
            show_action_error(
                "Behaviour file not recognised",
                "NeuroSyncApp could not import the selected behaviour CSV",
                exc,
                self.app,
                "Check the configured behaviour, start-time, and end-time column names, then retry.",
            )
            return False

    def read_and_process_file(self, file_path: str):
        column_names = self.app.column_mapping_store.prompt_column_names()
        time_unit = self.app.time_input_unit_var.get().lower()
        return read_behaviour_csv(file_path, column_names, time_unit)

    def process_each_row(self, df, column_names, behaviour_settings, file_path):
        synchronize_start_time = float(
            self.app.behaviour_event_input_frame.synchronize_start_time_entry.get()
        )
        return process_behaviour_rows(
            df,
            column_names,
            behaviour_settings,
            synchronize_start_time,
            file_path,
            self.app.selected_column_var.get(),
        )

    def calculate_and_store_behavior_metrics(self, behavior_durations) -> None:
        for behavior, times in behavior_durations.items():
            mean_duration, sem_duration = calculate_duration_metrics(
                times["start_times"], times["end_times"]
            )
            self.app.duration_data_cache[behavior] = {
                "mean_duration": mean_duration,
                "sem_duration": sem_duration,
                "mean_sem_df": None,
                "number_of_instances": len(times["start_times"]),
            }

    def update_ui_with_manual_data(self, table_data, behaviour_names) -> None:
        display_df = pd.DataFrame(
            table_data,
            columns=[
                "File Path",
                "Selected Column",
                "Behaviour Name",
                "Behaviour Type",
                "Pre Behaviour Time",
                "Post Behaviour Time",
                "Bin Size",
                "Start Time",
                "End Time",
            ],
        )

        unique_behaviour_names = normalize_deduplicate_and_order_strings(behaviour_names)

        for behaviour in unique_behaviour_names:
            self.app.behaviour_colors[behaviour] = self.update_behaviour_colors(behaviour)
            self.update_behaviour_display_status(behaviour)

        self.update_behaviour_dropdowns(unique_behaviour_names, table_data)
        self.app.behaviour_options_panel.create_behaviour_options(
            unique_behaviour_names
        )

        self.app.current_table_key = str(uuid.uuid4())
        self.app.tables[self.app.current_table_key] = display_df
        self.app.behaviour_table_panel.update_table(display_df, new=True)
        save_behaviour_static_inputs(display_df, config_file_path("behaviour_settings.json"))
        self.app.settings_manager.save_variables()

        if not hasattr(self.app, "original_table") or self.app.original_table is None:
            self.app.original_table = self.app.tables[self.app.current_table_key].copy()

        self.app.plot_service.handle_figure_display_selection(None)

    def update_behaviour_colors(self, behaviour):
        if behaviour in self.app.behaviour_colors:
            return self.app.behaviour_colors[behaviour]
        return self.app.graph_settings_container_instance.string_to_color(behaviour)

    def update_behaviour_display_status(self, behaviour) -> None:
        if behaviour not in self.app.behaviour_display_status:
            self.app.behaviour_display_status[behaviour] = ObservableValue(True)
        else:
            self.app.behaviour_display_status[behaviour].set(True)

    def update_behaviour_dropdowns(self, behaviour_names, table_data) -> None:
        sorted_behaviours = sorted(list(behaviour_names))

        self.update_menu(
            self.app.static_inputs_frame.behaviour_dropdown,
            ["All Behaviours"] + sorted_behaviours,
            self.app.static_inputs_frame.selected_behaviour,
        )

        single_instance_behaviours = self.get_single_instance_behaviours(table_data)
        self.update_menu(
            self.app.graph_settings_container_instance.behaviour_to_zero_dropdown,
            single_instance_behaviours,
            self.app.graph_settings_container_instance.selected_behaviour_to_zero,
        )

        if single_instance_behaviours:
            first_behaviour = single_instance_behaviours[0]
            self.app.graph_settings_container_instance.selected_behaviour_to_zero.set(
                first_behaviour
            )
            self.app.graph_settings_container_instance.selected_behaviour_to_zero.trace_add(
                "write", self.app.graph_helper_service.handle_behaviour_change
            )

        self.app.behaviour_choice_graph["values"] = sorted_behaviours
        self.app.behaviour_choice_graph["state"] = "normal"
        self.app.graph_settings_container_instance.behaviour_to_zero_dropdown["state"] = (
            "normal"
        )
        self.app.static_inputs_frame.behaviour_dropdown["state"] = "normal"

    def update_menu(self, menu_widget, choices, variable) -> None:
        menu = menu_widget["menu"]
        menu.delete(0, "end")
        for choice in choices:
            menu.add_command(label=choice, command=lambda value=choice: variable.set(value))

    def get_single_instance_behaviours(self, table_data):
        behaviour_counts = {}
        for data_tuple in table_data:
            behaviour_name = data_tuple[2]
            behaviour_counts[behaviour_name] = behaviour_counts.get(behaviour_name, 0) + 1
        return [behaviour for behaviour, count in behaviour_counts.items() if count == 1]

    def on_row_click(self, event) -> None:
        selected_row = self.app.table_treeview.focus()
        if not selected_row:
            return

        values = self.app.table_treeview.item(selected_row)["values"]
        behaviour_name = values[2]
        current_df = self.app.tables[self.app.current_table_key]
        selected_behaviour_df = current_df[current_df["Behaviour Name"] == behaviour_name]

        if not selected_behaviour_df.empty:
            self.app.start_time = float(selected_behaviour_df.iloc[0]["Start Time"]) / 60
            self.app.end_time = float(selected_behaviour_df.iloc[0]["End Time"]) / 60
            self.app.pre_behaviour_time = (
                float(selected_behaviour_df.iloc[0]["Pre Behaviour Time"]) / 60
            )
            self.app.post_behaviour_time = (
                float(selected_behaviour_df.iloc[0]["Post Behaviour Time"]) / 60
            )
            self.app.column_used = selected_behaviour_df.iloc[0]["Selected Column"]

        self.app.figure_display_dropdown.set("Single Row Display")
        self.app.plot_service.handle_figure_display_selection(event=None)

    def handle_new_data_file(
        self,
        file_path_var,
        selected_column_var,
        column_dropdown,
        mouse_name,
        dataframe,
        *args,
    ) -> None:
        if not hasattr(selected_column_var, "set") and hasattr(column_dropdown, "set"):
            selected_column_var, column_dropdown = column_dropdown, selected_column_var

        if not hasattr(file_path_var, "get"):
            normalized_file_path = ObservableValue(str(file_path_var))
            file_path_var = normalized_file_path

        self.app.file_path_var = file_path_var
        self.app.selected_column_var = selected_column_var
        self.app.column_dropdown = column_dropdown
        self.app.mouse_name = mouse_name

        # Extract recording date from filename (yy-mm-dd format)
        file_name = Path(file_path_var.get()).name
        date_match = re.search(r"(\d+)-(\d+)-(\d+)", file_name)
        self.app.date = (
            f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
            if date_match
            else None
        )

        self.app.dataframe = dataframe
        self.app.baseline_button_pressed = False
        self.app.z_score_computed = False
        self.app.baseline_data_mean = None
        self.app.baseline_data_std = None
        self.app.data_already_adjusted = False
        self.app.first_offset_time = None
        self.app.warning_shown = False

        self.app.graph_settings_container_instance.zero_x_axis_checkbox_var.set(0)

        self.app.selected_column_var.set(select_preferred_signal_column(dataframe))

        self.app.selected_column_var.trace(
            "w", lambda *trace_args: self.app.data_selection_frame.on_column_selection_changed()
        )

        self.app.behaviour_table_panel.clear_table()
        self.app.table_treeview.delete(*self.app.table_treeview.get_children())
        self.app.adjusted_behaviour_dataframes = {}

        self.app.figure_display_dropdown.set("Full Trace Display")
        self.app.selected_behaviour.set("")
        self.app.behaviour_choice_graph.configure(state="disabled")
        self.app.behaviour_options_panel.create_behaviour_options(
            self.app.no_behaviours, destroy_frame=True
        )

        if self.app.ax is not None:
            self.app.ax.clear()

        menu = self.app.graph_settings_container_instance.behaviour_to_zero_dropdown["menu"]
        menu.delete(0, "end")
        self.app.graph_settings_container_instance.selected_behaviour_to_zero.set("")
        self.app.graph_settings_container_instance.behaviour_to_zero_dropdown["state"] = (
            "disabled"
        )

        self.app.plot_service.handle_figure_display_selection(None)
