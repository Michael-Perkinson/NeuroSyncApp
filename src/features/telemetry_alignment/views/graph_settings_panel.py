"""Telemetry-specific graph settings panel composition."""

from __future__ import annotations

from src.shared.ui.graph_settings_panel import GraphSettingsPanel


def create_telemetry_graph_settings_panel(parent, app) -> GraphSettingsPanel:
    """Build the telemetry tool's graph settings panel."""
    panel = GraphSettingsPanel(
        parent,
        widgets_to_include=[
            "photometry_settings",
            "temperature_settings",
            "activity_settings",
            "remove_first_60_minutes",
            "number_of_minor_ticks",
            "graph_time_labels",
            "axis_range",
        ],
        appearance_section_title="Trace Controls",
        advanced_buttons_title=None,
        advanced_button_role="primary",
        axis_range_button_role="primary",
        photometry_button_text="Edit Photometry",
        temperature_button_text="Edit Temperature",
        activity_button_text="Edit Activity",
        overlay_visibility_in_appearance=True,
        show_visibility_card=False,
        app_name=app.app_name,
        settings_manager=app.settings_manager,
        refresh_graph_display_callback=app.refresh_graph_display,
        update_duration_box_callback=app.update_duration_box,
        handle_behaviour_change_callback=app.handle_behaviour_change,
        load_variables_callback=app.settings_manager.load_variables,
        create_behaviour_options_callback=app.create_cluster_options,
        update_box_colors_callback=app.update_box_colors_and_behaviour_options,
        save_and_close_axis_callback=app.save_and_close,
        redraw_graph_callback=app.redraw_graph,
    )
    panel.y_gridlines_label.hide()
    panel.y_gridlines_entry.hide()
    panel.time_unit_menu.set_options(["minutes", "seconds", "hours", "time of day"])

    if hasattr(panel, "remove_first_60_minutes_checkbox"):
        panel.remove_first_60_minutes_checkbox.clicked.disconnect()

        def _on_trim_toggled():
            if app.act_file_path and app.temp_file_path:
                if app.plot_service._has_cached_raw_telemetry():
                    app.plot_service.refresh_after_trim_toggle()
                else:
                    app.plot_service.overlay_temp_and_act()
            else:
                app.redraw_graph()

        panel.remove_first_60_minutes_checkbox.clicked.connect(_on_trim_toggled)

    return panel
