"""Controller for graph helper operations used by plot orchestration."""

from __future__ import annotations

import pandas as pd

from src.gui.shared.graph_plotter import (
    convert_time_data,
    draw_behaviour_boxes,
    process_behaviour_data as _process_behaviour_data,
    retrieve_behaviour_records,
    set_ax_tick_spacing,
)
from src.processing.behavior_metrics import get_time_scale
from src.processing.behaviour_plotting import extract_behaviour_occurrences


class BehaviourGraphHelperService:
    """Owns non-renderer graph helper logic for the behaviour app."""

    def __init__(self, app):
        self.app = app

    def add_transparent_boxes(
        self,
        ax,
        data,
        behaviours,
        start_times_min,
        end_times_min,
        start_point=None,
        end_point=None,
    ) -> None:
        time_unit = self.app.graph_settings_container_instance.time_unit_menu.get()
        time_factor = get_time_scale(time_unit)

        if self.app.checkbox_state:
            time_data = self.app.dataframe.get(
                "z_scored_time", self.app.data_service.calculate_z_score()[1]
            ).copy()
        else:
            time_data = self.app.dataframe.iloc[:, 0].copy()

        time_data = time_data * time_factor
        if start_point is not None:
            start_point = start_point * time_factor
        if end_point is not None:
            end_point = end_point * time_factor

        behaviour_display = {
            behaviour: bool(variable.get())
            for behaviour, variable in self.app.behaviour_display_status.items()
        }
        box_height_factor = float(
            self.app.graph_settings_container_instance.box_height_entry.get()
        )
        alpha = min(
            max(float(self.app.graph_settings_container_instance.alpha_entry.get()), 0),
            1,
        )

        new_boxes = draw_behaviour_boxes(
            ax,
            data,
            time_data,
            behaviours,
            start_times_min,
            end_times_min,
            self.app.behaviour_colors,
            behaviour_display,
            time_factor,
            box_height_factor,
            alpha,
            start_point,
            end_point,
        )
        for behaviour, boxes in new_boxes.items():
            if behaviour in self.app.behaviour_boxes:
                self.app.behaviour_boxes[behaviour].extend(boxes)
            else:
                self.app.behaviour_boxes[behaviour] = boxes

    def convert_and_retrieve_time(self, time_data, return_label=False):
        time_unit = self.app.graph_settings_container_instance.time_unit_menu.get()
        converted, label = convert_time_data(time_data, time_unit)
        if return_label:
            return converted, label
        return converted

    def get_time_scale(self, time_unit):
        return get_time_scale(time_unit)

    def determines_ax_tick_spacing(self, ax) -> None:
        set_ax_tick_spacing(
            ax,
            self.app.graph_settings_container_instance.x_gridlines_var.get(),
            self.app.graph_settings_container_instance.y_gridlines_var.get(),
        )

    def retrieve_and_process_behaviour_data(self, current_df=None):
        if current_df is None:
            current_df = self.app.tables.get(self.app.current_table_key, pd.DataFrame())
        return retrieve_behaviour_records(current_df)

    def initialize_or_check_time_attributes(self, start_times_min, end_times_min) -> None:
        if (
            not hasattr(self.app, "original_start_times_min")
            or not self.app.original_start_times_min
        ):
            self.app.original_start_times_min = start_times_min.copy()

        if (
            not hasattr(self.app, "original_end_times_min")
            or not self.app.original_end_times_min
        ):
            self.app.original_end_times_min = end_times_min.copy()

    def fetch_behaviour_data(self):
        return extract_behaviour_occurrences(
            self.app.tables[self.app.current_table_key],
            self.app.behaviour_choice_graph.get(),
            self.app.selected_column_var.get(),
            self.app.checkbox_state,
        )

    def process_behaviour_data(self, behaviour_occurrences, column_used):
        time_unit = self.app.graph_settings_container_instance.time_unit_menu.get()
        return _process_behaviour_data(
            self.app.dataframe,
            behaviour_occurrences,
            column_used,
            time_unit,
            self.app.checkbox_state,
        )

    def refresh_graph(self) -> None:
        self.app.ax.clear()
        self.app.plot_service.plot_full_trace(self.app.ax)
        self.app.figure_canvas.draw()

    def handle_behaviour_change(self, *args, **kwargs) -> None:
        selected_behaviour = (
            self.app.graph_settings_container_instance.selected_behaviour_to_zero.get()
        )
        if (
            self.app.graph_settings_container_instance.zero_x_axis_checkbox_var.get() == 1
            and (not selected_behaviour or selected_behaviour.strip() == "")
        ):
            return
        self.app.plot_service.handle_figure_display_selection(None)
