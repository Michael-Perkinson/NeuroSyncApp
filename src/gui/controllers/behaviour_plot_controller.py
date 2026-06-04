"""GUI-side plot mode orchestration for photometry-behaviour app."""

from __future__ import annotations

import copy
from PySide6.QtWidgets import QMessageBox

from src.gui.shared.qt_graph_canvas import (
    create_styled_figure,
    destroy_embedded_figure,
    embed_figure_in_qt,
)
from src.gui.shared.graph_plotter import (
    apply_figure_size_and_fonts,
    build_save_path,
    compute_bar_position,
    draw_duration_bar,
    draw_onset_line,
    draw_sem_band,
    draw_trace,
    save_figure,
)
from src.processing.behaviour_plotting import (
    build_adjusted_behaviour_df,
    compute_zeroed_time_axis,
    parse_optional_float,
    select_single_row_window,
)
from src.processing.image_export import build_image_export_request
from src.processing.behavior_metrics import generate_mean_sem_df


def _has_current_behaviour_table(app) -> bool:
    current_key = getattr(app, "current_table_key", None)
    tables = getattr(app, "tables", {})
    return current_key is not None and current_key in tables


def handle_figure_display_selection(app, event=None) -> None:
    """Render the selected figure display mode."""
    if app.dataframe is None:
        return

    selected_option = app.figure_display_dropdown.get()
    table_required_options = {"Single Row Display", "Behaviour Mean and SEM"}
    if selected_option in table_required_options and not _has_current_behaviour_table(app):
        selected_option = "Full Trace Display"
        app.figure_display_dropdown.blockSignals(True)
        app.figure_display_dropdown.set(selected_option)
        app.figure_display_dropdown.blockSignals(False)

    if (
        not app.is_file_parsed
        and app.data_selection_frame.baseline_button_pressed
    ):
        print("Please parse the file first.")
        app.data_already_adjusted = True

    if hasattr(app, "figure_canvas") and app.figure_canvas is not None:
        destroy_embedded_figure(app.figure_canvas, app.toolbar)
        app.figure_canvas = None
        app.toolbar = None

    app.fig, ax = create_styled_figure()
    app.ax = ax

    if selected_option == "Z-scored data" and app.checkbox_state:
        plot_z_scored_data(app, ax)

    elif selected_option == "Full Trace Display" or (
        selected_option == "Behaviour Mean and SEM"
        and app.behaviour_choice_graph.get() == ""
    ):
        plot_full_trace(app, ax)
        app.default_y_limits = ax.get_ylim()
        app.original_xticks = app.ax.get_xticks().tolist()
        app.original_xticklabels = [
            label.get_text() for label in app.ax.get_xticklabels()
        ]
        if selected_option == "Behaviour Mean and SEM":
            QMessageBox.information(
                app,
                "No Behaviour Selected",
                "Please select a behaviour to display the mean and SEM.",
            )
            app.figure_display_dropdown.set("Full Trace Display")

    elif selected_option == "Single Row Display":
        plot_single_row(app, ax)
        ax.set_ylim(auto=True)

    elif selected_option == "Behaviour Mean and SEM":
        plot_mean_and_sem_trace(app, ax)
        scale_factor = app.behaviour_graph_helpers_controller.get_time_scale(
            app.graph_settings_container_instance.time_unit_menu.get()
        )
        ax.set_xlim(
            app.min_x_for_behaviour_mean_and_sem * scale_factor,
            app.max_x_for_behaviour_mean_and_sem * scale_factor,
        )

    app.behaviour_graph_helpers_controller.determines_ax_tick_spacing(ax)

    if selected_option not in ["Single Row Display", "Behaviour Mean and SEM"]:
        current_xlim = ax.get_xlim()
        ax.set_xlim(left=current_xlim[0], right=current_xlim[1])

    app.figure_canvas, app.toolbar = embed_figure_in_qt(app.fig, app.graph_canvas)
    app.settings_manager.save_variables()


def plot_z_scored_data(app, ax) -> None:
    """Plot the z-scored trace mode."""
    if not app.data_selection_frame.baseline_button_pressed:
        app.behaviour_data_controller.calculate_z_score()

    if (
        "baselined_z_score" not in app.dataframe
        or "z_scored_time" not in app.dataframe
    ):
        print("Required data columns are missing in the dataframe.")
        return

    z_scored_data = app.dataframe["baselined_z_score"]
    z_scored_time = app.dataframe["z_scored_time"]

    converted_time_data, x_label = app.behaviour_graph_helpers_controller.convert_and_retrieve_time(
        z_scored_time.copy(), return_label=True
    )
    ax.set_xlabel(x_label)

    behaviours = None
    adjusted_time = converted_time_data
    adjusted_start_times_min = []
    adjusted_end_times_min = []

    if app.original_table is not None and not app.original_table.empty:
        current_df = app.original_table.copy()
        app.behaviour_table_controller.update_table(current_df)

        behaviours, _, _, start_times_min, end_times_min = (
            app.behaviour_graph_helpers_controller.retrieve_and_process_behaviour_data(
                current_df
            )
        )
        app.behaviour_graph_helpers_controller.initialize_or_check_time_attributes(
            start_times_min, end_times_min
        )

        zeroing_active = (
            app.graph_settings_container_instance.zero_x_axis_checkbox_var.get() == 1
        )
        if zeroing_active:
            adjusted_start_times_min, adjusted_end_times_min, adjusted_time = (
                app.plot_controller.handle_zeroing(
                    behaviours, start_times_min, end_times_min, converted_time_data
                )
            )
        elif app.checkbox_state:
            adjusted_start_times_min = start_times_min
            adjusted_end_times_min = end_times_min
        else:
            adjusted_start_times_min = (
                app.original_start_times_min
                if app.original_start_times_min
                else start_times_min
            )
            adjusted_end_times_min = (
                app.original_end_times_min
                if app.original_end_times_min
                else end_times_min
            )

    ax.plot(
        adjusted_time,
        z_scored_data,
        color=app.settings_manager.selected_trace_color,
        linewidth=float(app.graph_settings_container_instance.line_width_entry.get()),
    )
    ax.set_ylabel("Z-score")

    app.xlim_min = adjusted_time.min()
    app.xlim_max = adjusted_time.max()

    if behaviours:
        app.behaviour_graph_helpers_controller.add_transparent_boxes(
            ax,
            z_scored_data,
            behaviours,
            adjusted_start_times_min,
            adjusted_end_times_min,
            adjusted_time,
        )

    ax.set_xlim(app.xlim_min, app.xlim_max)


def plot_full_trace(app, ax) -> None:
    """Plot the full trace mode."""
    selected_column = app.selected_column_var.get()
    time = app.dataframe.iloc[:, 0].copy()
    data = app.dataframe[selected_column]

    behaviours, _, _, start_times_min, end_times_min = (
        app.behaviour_graph_helpers_controller.retrieve_and_process_behaviour_data()
    )
    converted_time_data, x_label = app.behaviour_graph_helpers_controller.convert_and_retrieve_time(
        time, return_label=True
    )

    app.behaviour_graph_helpers_controller.initialize_or_check_time_attributes(
        start_times_min, end_times_min
    )
    zeroing_active = (
        app.graph_settings_container_instance.zero_x_axis_checkbox_var.get() == 1
    )

    if zeroing_active and behaviours:
        adjusted_start_times_min, adjusted_end_times_min, adjusted_time = (
            app.plot_controller.handle_zeroing(
                behaviours, start_times_min, end_times_min, converted_time_data
            )
        )
    else:
        adjusted_start_times_min = app.original_start_times_min
        adjusted_end_times_min = app.original_end_times_min
        adjusted_time = converted_time_data

    draw_trace(
        ax,
        adjusted_time,
        data,
        app.settings_manager.selected_trace_color,
        float(app.graph_settings_container_instance.line_width_entry.get()),
        x_label,
        selected_column,
    )

    app.xlim_min = adjusted_time.min()
    app.xlim_max = adjusted_time.max()

    if behaviours:
        app.behaviour_graph_helpers_controller.add_transparent_boxes(
            ax,
            data,
            behaviours,
            adjusted_start_times_min,
            adjusted_end_times_min,
            adjusted_time,
        )

    ax.set_xlim(app.xlim_min, app.xlim_max)


def plot_single_row(app, ax) -> None:
    """Plot the currently selected single-row window."""
    if not hasattr(app, "start_time") or not hasattr(app, "pre_behaviour_time"):
        return
    if app.checkbox_state:
        app.behaviour_data_controller.calculate_z_score()
        selected_column = "baselined_z_score"
    else:
        selected_column = app.selected_column_var.get()

    selected_data_to_plot, start_point, end_point = select_single_row_window(
        app.dataframe,
        app.start_time,
        app.pre_behaviour_time,
        app.post_behaviour_time,
    )

    if app.checkbox_state and "z_scored_time" in selected_data_to_plot:
        time_data = selected_data_to_plot["z_scored_time"].copy()
    else:
        time_data = selected_data_to_plot.iloc[:, 0].copy()
    converted_time_data, x_label = app.behaviour_graph_helpers_controller.convert_and_retrieve_time(
        time_data, return_label=True
    )

    onset_line_style = app.graph_settings_container_instance.onset_line_style_combobox.get()
    draw_trace(
        ax,
        converted_time_data,
        selected_data_to_plot[selected_column],
        app.settings_manager.selected_trace_color,
        float(app.graph_settings_container_instance.line_width_entry.get()),
        x_label,
        selected_column,
    )
    draw_onset_line(
        ax,
        app.settings_manager.selected_line_color,
        onset_line_style,
        1.0,
    )

    start_times_min = [app.start_time]
    end_times_min = [app.end_time]
    item = app.table_treeview.selection()[0]
    row_behaviour_name = app.table_treeview.item(item)["values"][2]
    app.behaviour_graph_helpers_controller.add_transparent_boxes(
        ax,
        selected_data_to_plot[selected_column],
        [row_behaviour_name],
        start_times_min,
        end_times_min,
        start_point,
        end_point,
    )


def plot_mean_and_sem_trace(app, ax) -> None:
    """Plot behaviour mean and SEM mode."""
    (
        behaviour_occurrences,
        column_used,
        pre_behaviour_times,
        post_behaviour_times,
    ) = app.behaviour_graph_helpers_controller.fetch_behaviour_data()

    if not behaviour_occurrences or not pre_behaviour_times or not post_behaviour_times:
        return

    start_times = [occurrence[0] for occurrence in behaviour_occurrences]
    end_times = [occurrence[1] for occurrence in behaviour_occurrences]
    start_time_adjusted = -pre_behaviour_times[0]
    end_time_adjusted = post_behaviour_times[0]

    app.current_start_times = start_times
    app.current_end_times = end_times

    behaviour_data_by_instance, time_points, _, _ = (
        app.behaviour_graph_helpers_controller.process_behaviour_data(
            behaviour_occurrences, column_used
        )
    )

    mean_sem_df = generate_behaviour_graph(
        ax,
        app,
        behaviour_data_by_instance,
        time_points,
        start_time_adjusted,
        end_time_adjusted,
    )

    current_behavior = app.behaviour_choice_graph.get()
    if current_behavior in app.duration_data_cache:
        app.duration_data_cache[current_behavior]["mean_sem_df"] = mean_sem_df
    else:
        print(
            f"Warning: Behavior '{current_behavior}' not found in cache to update mean_sem_df."
        )

    if app.graph_settings_container_instance.num_instances_box_var.get():
        num_instances = len(behaviour_data_by_instance)
        ax.text(
            0.95,
            0.95,
            f"n = {num_instances}",
            transform=ax.transAxes,
            ha="right",
            va="top",
            bbox=dict(facecolor="white", edgecolor="black", boxstyle="square,pad=0.5"),
        )

    app.min_x_for_behaviour_mean_and_sem = start_time_adjusted
    app.max_x_for_behaviour_mean_and_sem = end_time_adjusted

    onset_line_style = app.graph_settings_container_instance.onset_line_style_combobox.get()
    ax.axvline(
        x=0,
        color=app.graph_settings_container_instance.selected_line_color,
        linestyle=onset_line_style,
        linewidth=app.graph_settings_container_instance.onset_line_thickness_entry.get(),
    )

    if app.graph_settings_container_instance.limit_axis_range_var.get():
        y_min = app.graph_settings_container_instance.y_axis_min_var.get()
        y_max = app.graph_settings_container_instance.y_axis_max_var.get()
        ax.set_ylim(float(y_min), float(y_max))

    if hasattr(app, "bar_items") and app.bar_items:
        update_duration_box(app, ax, mean_sem_df)
    else:
        add_duration_box(app, ax, mean_sem_df)


def generate_behaviour_graph(
    ax,
    app,
    behaviour_data_by_instance,
    time_points,
    start_time_adjusted,
    end_time_adjusted,
):
    """Plot mean and SEM trace and return the mean/SEM dataframe."""
    mean_sem_df = generate_mean_sem_df(
        behaviour_data_by_instance,
        time_points,
        start_time_adjusted,
        end_time_adjusted,
    )

    converted_time_data, x_label = app.behaviour_graph_helpers_controller.convert_and_retrieve_time(
        mean_sem_df["Time"].copy(), return_label=True
    )
    ax.set_xlabel(x_label)
    ax.set_ylabel(getattr(app, "column_used", app.selected_column_var.get()))
    ax.plot(
        converted_time_data,
        mean_sem_df["Mean"],
        color=app.settings_manager.selected_trace_color,
        label="Mean",
        linewidth=float(app.graph_settings_container_instance.line_width_entry.get()),
    )
    draw_sem_band(
        ax,
        converted_time_data,
        mean_sem_df["Mean"],
        mean_sem_df["SEM"],
        app.settings_manager.selected_sem_color,
    )
    return mean_sem_df


def add_duration_box(app, ax, mean_sem_df) -> None:
    """Draw the duration bar box for the current behaviour."""
    if not app.graph_settings_container_instance.display_duration_box_var.get():
        return

    graphed_behaviour = app.behaviour_choice_graph.get()
    if graphed_behaviour not in app.duration_data_cache:
        print(f"Duration data for {graphed_behaviour} not found in cache.")
        return

    cached_data = app.duration_data_cache[graphed_behaviour]
    time_unit = app.graph_settings_container_instance.time_unit_menu.get()
    time_factor = app.behaviour_graph_helpers_controller.get_time_scale(time_unit)
    mean_duration = cached_data["mean_duration"] * time_factor
    sem_duration = cached_data["sem_duration"] * time_factor

    height_modifier = float(app.graph_settings_container_instance.duration_box_placement.get())
    size_factor = float(app.graph_settings_container_instance.bar_graph_size_entry.get())

    bar_y, bar_height = compute_bar_position(mean_sem_df, height_modifier, size_factor)
    app.bar_items = draw_duration_bar(
        ax,
        mean_duration,
        sem_duration,
        bar_y,
        bar_height,
        app.graph_settings_container_instance.selected_bar_fill_color,
        app.graph_settings_container_instance.selected_bar_border_color,
        app.graph_settings_container_instance.selected_bar_sem_color,
    )


def update_duration_box(app, ax=None, mean_sem_df=None) -> None:
    """Redraw duration bar box after style/placement updates."""
    if not app.graph_settings_container_instance.display_duration_box_var.get():
        return

    ax = app.fig.gca()

    if hasattr(app, "bar_items"):
        for item in app.bar_items:
            try:
                item.remove()
            except (AttributeError, ValueError):
                pass

    current_behavior = app.behaviour_choice_graph.get()
    app.current_cache_key = current_behavior

    try:
        cached_data = app.duration_data_cache[app.current_cache_key]
        mean_sem_df = cached_data["mean_sem_df"]
    except KeyError:
        add_duration_box(app, ax, mean_sem_df)
        return

    time_unit = app.graph_settings_container_instance.time_unit_menu.get()
    time_factor = app.behaviour_graph_helpers_controller.get_time_scale(time_unit)
    mean_duration = cached_data["mean_duration"] * time_factor
    sem_duration = cached_data["sem_duration"] * time_factor

    height_modifier = float(app.graph_settings_container_instance.duration_box_placement.get())
    size_factor = float(app.graph_settings_container_instance.bar_graph_size_entry.get())
    bar_y, bar_height = compute_bar_position(mean_sem_df, height_modifier, size_factor)

    old_items = set(ax.get_children())
    draw_duration_bar(
        ax,
        mean_duration,
        sem_duration,
        bar_y,
        bar_height,
        app.graph_settings_container_instance.selected_bar_fill_color,
        app.graph_settings_container_instance.selected_bar_border_color,
        app.graph_settings_container_instance.selected_bar_sem_color,
    )
    new_items = set(ax.get_children())
    app.bar_items = list(new_items - old_items)

    app.figure_canvas.draw_idle()


def save_and_close_axis_range(app, popup=None, close: bool = True) -> None:
    """Apply axis range settings, redraw, and optionally close popup."""
    x_min = app.graph_settings_container_instance.x_axis_min_var.get()
    x_max = app.graph_settings_container_instance.x_axis_max_var.get()
    y_min = app.graph_settings_container_instance.y_axis_min_var.get()
    y_max = app.graph_settings_container_instance.y_axis_max_var.get()

    selected_option = None
    if hasattr(app, "figure_display_dropdown"):
        selected_option = app.figure_display_dropdown.get()

    if app.graph_settings_container_instance.limit_axis_range_var.get():
        if x_min and x_max and selected_option != "Behaviour Mean and SEM":
            app.ax.set_xlim(float(x_min), float(x_max))
        if y_min and y_max:
            app.ax.set_ylim(float(y_min), float(y_max))
    else:
        if selected_option != "Behaviour Mean and SEM":
            app.ax.set_xlim(app.xlim_min, app.xlim_max)
        app.ax.set_ylim(app.default_y_limits)

    if (
        not app.graph_settings_container_instance.x_axis_min_var.get()
        and not app.graph_settings_container_instance.y_axis_min_var.get()
    ):
        QMessageBox.critical(app, "Error", "Please enter values for both x and y!")
        return

    app.figure_canvas.draw()
    app.settings_manager.save_variables()

    if close and popup:
        if hasattr(popup, "accept"):
            popup.accept()
        elif hasattr(popup, "close"):
            popup.close()


def handle_zeroing(app, behaviours, start_times_min, end_times_min, converted_time_data):
    """Zero behaviour times and return adjusted start/end/time arrays."""
    selected_behaviour = app.graph_settings_container_instance.selected_behaviour_to_zero.get()
    time_unit = app.graph_settings_container_instance.time_unit_menu.get()
    time_factor = app.behaviour_graph_helpers_controller.get_time_scale(time_unit)
    baseline_start_time_min = parse_optional_float(
        app.data_selection_frame.baseline_start_entry.get()
    )
    if baseline_start_time_min is not None:
        baseline_start_time_min /= 60.0

    adjusted_df = adjust_behavior_times(
        app, behaviours, start_times_min, end_times_min, selected_behaviour
    )

    adjusted_time = converted_time_data.copy()
    if adjusted_df is None:
        print("Adjusted DataFrame is None. Returning original times.")
        return start_times_min, end_times_min, adjusted_time

    adjusted_start_times_min = adjusted_df["Adjusted Start Time"].tolist()
    adjusted_end_times_min = adjusted_df["Adjusted End Time"].tolist()
    adjusted_time, app.first_offset_time = compute_zeroed_time_axis(
        converted_time_data=converted_time_data,
        behaviours=behaviours,
        original_start_times_min=app.original_start_times_min,
        selected_behaviour=selected_behaviour,
        time_factor=time_factor,
        data_already_adjusted=app.data_already_adjusted,
        first_offset_time_min=app.first_offset_time,
        baseline_start_time_min=baseline_start_time_min,
        checkbox_state=app.checkbox_state,
        figure_display=app.figure_display_dropdown.get(),
    )
    return adjusted_start_times_min, adjusted_end_times_min, adjusted_time


def adjust_behavior_times(
    app, behaviours, start_times_min, end_times_min, selected_behaviour
):
    """Return adjusted behaviour timing table if zeroing is active."""
    zero_axis_enabled = (
        app.graph_settings_container_instance.zero_x_axis_checkbox_var.get() == 1
    )
    adjusted_df = build_adjusted_behaviour_df(
        behaviours,
        start_times_min,
        end_times_min,
        selected_behaviour,
        zero_axis_enabled,
    )
    if adjusted_df is None:
        print(
            f"Selected behaviour {selected_behaviour} not found or checkbox not active."
        )
        return None
    app.adjusted_behaviour_dataframes[selected_behaviour] = adjusted_df
    return adjusted_df


def save_image(app) -> None:
    """Save current figure using normalized export settings."""
    current_xlabel = app.fig.axes[0].get_xlabel()
    current_ylabel = app.fig.axes[0].get_ylabel()
    fig_copy = copy.deepcopy(app.fig)

    request = build_image_export_request(
        app.export_options_container.height_entry.get().strip(),
        app.export_options_container.width_entry.get().strip(),
        app.export_options_container.image_format_combobox.get(),
        app.export_options_container.dpi_entry.get().strip(),
        app.figure_display_dropdown.get(),
        app.behaviour_choice_graph.get(),
    )

    if request.axis_width_cm is not None and request.axis_height_cm is not None:
        apply_figure_size_and_fonts(
            fig_copy,
            request.axis_width_cm,
            request.axis_height_cm,
            app.export_options_container.font_settings,
            current_xlabel,
            current_ylabel,
        )

    output_path = build_save_path(
        app.file_path_var.get(),
        app.mouse_name,
        request.figure_display,
        request.behaviour_choice,
        request.image_format,
    )
    save_figure(fig_copy, output_path, request.image_format, request.dpi)


class BehaviourPlotController:
    """Object interface around plot orchestration for cleaner app delegation."""

    def __init__(self, app):
        self.app = app

    def handle_figure_display_selection(self, event=None) -> None:
        handle_figure_display_selection(self.app, event)

    def plot_z_scored_data(self, ax) -> None:
        plot_z_scored_data(self.app, ax)

    def plot_full_trace(self, ax) -> None:
        plot_full_trace(self.app, ax)

    def plot_single_row(self, ax) -> None:
        plot_single_row(self.app, ax)

    def plot_mean_and_sem_trace(self, ax) -> None:
        plot_mean_and_sem_trace(self.app, ax)

    def generate_behaviour_graph(
        self,
        ax,
        behaviour_data_by_instance,
        time_points,
        start_time_adjusted,
        end_time_adjusted,
    ):
        return generate_behaviour_graph(
            ax,
            self.app,
            behaviour_data_by_instance,
            time_points,
            start_time_adjusted,
            end_time_adjusted,
        )

    def add_duration_box(self, ax, mean_sem_df) -> None:
        add_duration_box(self.app, ax, mean_sem_df)

    def update_duration_box(self, ax=None, mean_sem_df=None) -> None:
        update_duration_box(self.app, ax, mean_sem_df)

    def save_and_close_axis_range(self, popup=None, close: bool = True) -> None:
        save_and_close_axis_range(self.app, popup, close)

    def handle_zeroing(
        self, behaviours, start_times_min, end_times_min, converted_time_data
    ):
        return handle_zeroing(
            self.app, behaviours, start_times_min, end_times_min, converted_time_data
        )

    def adjust_behavior_times(
        self, behaviours, start_times_min, end_times_min, selected_behaviour
    ):
        return adjust_behavior_times(
            self.app, behaviours, start_times_min, end_times_min, selected_behaviour
        )

    def save_image(self) -> None:
        save_image(self.app)
