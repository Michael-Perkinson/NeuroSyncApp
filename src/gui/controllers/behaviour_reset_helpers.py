"""GUI-only helpers for resetting behaviour-analysis widgets."""

from __future__ import annotations

from typing import Any


def clear_common_selections(app_context: Any) -> None:
    """Clear shared selections and reset UI state for behaviour workflows."""
    app_context.adjusted_behaviour_dataframes = {}
    app_context.original_start_times_min = None
    app_context.original_end_times_min = None
    app_context.bar_items = []
    app_context.mean_duration = None
    app_context.sem_duration = None
    app_context.mean_sem_df = None
    app_context.current_table_key = None

    app_context.behaviour_table_controller.clear_table()
    app_context.table_treeview.delete(*app_context.table_treeview.get_children())

    behaviour_dropdown_menu = app_context.graph_settings_container_instance.behaviour_to_zero_dropdown[
        "menu"
    ]
    behaviour_dropdown_menu.delete(0, "end")
    app_context.graph_settings_container_instance.behaviour_to_zero_dropdown[
        "state"
    ] = "disabled"

    app_context.figure_display_dropdown.set("Full Trace Display")
    app_context.selected_behaviour.set("")
    app_context.behaviour_choice_graph.configure(state="disabled")


def clear_photometry_app_specific_selections(app_context: Any) -> None:
    """Reset behaviour-specific options and refresh the displayed figure state."""
    app_context.create_behaviour_options(
        app_context.no_behaviours, destroy_frame=True
    )
    app_context.plot_controller.handle_figure_display_selection(None)
