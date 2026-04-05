"""Settings manager facade for app-specific settings."""

from __future__ import annotations

from src.core.settings_defaults import get_default_settings
from src.core.settings_store import load_settings, save_settings


class AppSettingsManager:
    """Coordinates settings defaults and persistence using plain Python state."""

    APP_TYPE_ALIASES = {
        "raw_photometry_processing_app": "raw_photometry_processing",
    }

    def __init__(self, app_type: str = "default"):
        self.app_type = self.APP_TYPE_ALIASES.get(app_type, app_type)
        self._initialize_default_settings()
        self.unique_behaviours = []
        self.selected_column_name = None

        self.display_duration_box_var = True
        self.num_instances_box_var = True

    def _initialize_default_settings(self) -> None:
        """Initialize default scalar settings on the manager."""
        self.behaviour_colors = {}
        self.default_settings = get_default_settings()
        for key, value in self.default_settings.items():
            setattr(self, key, value)
        self.selected_temp_line_width = self.selected_temp_mean_line_width

    def update_unique_behaviours(self, unique_behaviours) -> None:
        self.unique_behaviours = unique_behaviours

    def update_behaviour_colors(self, behaviour_colors) -> None:
        self.behaviour_colors = behaviour_colors

    def save_variables(self) -> None:
        config = self.construct_config(load_settings(self.app_type))
        save_settings(self.app_type, config)

    def load_existing_config(self) -> dict:
        return load_settings(self.app_type)

    def construct_config(self, existing_config: dict) -> dict:
        config = existing_config.copy()

        if self.app_type == "align_photometry_and_behaviour_app":
            config.update(self.shared_photom_config())
            config.update(self.align_specific_config())
        elif self.app_type == "telemetry_photom_opto":
            config.update(self.shared_photom_config())
            config.update(self.telemetry_photom_opto_specific_config())
        elif self.app_type == "raw_photometry_processing":
            config.update(self.raw_photometry_processing_specific_config())
        else:
            raise ValueError(f"Unknown app type: {self.app_type}")

        return config

    def shared_photom_config(self) -> dict:
        return {
            "selected_photometry_line_width": self.selected_photometry_line_width,
            "selected_bar_fill_color": self.selected_bar_fill_color,
            "selected_bar_border_color": self.selected_bar_border_color,
            "selected_line_color": self.selected_line_color,
            "selected_bar_sem_color": self.selected_bar_sem_color,
            "selected_trace_color": self.selected_trace_color,
            "selected_sem_color": self.selected_sem_color,
            "default_data_folder_path": self.default_data_folder_path,
            "selected_column_name": self.selected_column_name,
            "number_of_minor_ticks": self.number_of_minor_ticks,
        }

    def align_specific_config(self) -> dict:
        config = {
            "box_height_factor": self.box_height_factor,
            "alpha": self.alpha,
            "bar_graph_size": self.bar_graph_size,
            "onset_line_color": self.onset_line_color,
            "onset_line_thickness": self.onset_line_thickness,
            "onset_line_style": self.onset_line_style,
            "duration_box_placement": self.duration_box_placement,
            "display_duration_box_var": self.display_duration_box_var,
            "num_instances_box_var": self.num_instances_box_var,
            "behaviour_colors": {},
        }

        for behaviour, actual_color in getattr(self, "behaviour_colors", {}).items():
            if isinstance(actual_color, (tuple, list)):
                config["behaviour_colors"][behaviour] = actual_color

        return config

    def telemetry_photom_opto_specific_config(self) -> dict:
        return {
            "selected_cluster_box_color": self.selected_cluster_box_color,
            "selected_label_color": self.selected_label_color,
            "selected_label_symbol": self.selected_label_symbol,
            "selected_label_size": self.selected_label_size,
            "selected_y_offset_peak_symbol": self.selected_y_offset_peak_symbol,
            "selected_peak_count_color": self.selected_peak_count_color,
            "selected_peak_count_size": self.selected_peak_count_size,
            "selected_y_for_peak_count": self.selected_y_for_peak_count,
            "selected_baseline_multiplier": self.selected_baseline_multiplier,
            "selected_baseline_color": self.selected_baseline_color,
            "selected_baseline_style": self.selected_baseline_style,
            "selected_baseline_thickness": self.selected_baseline_thickness,
            "selected_cluster_box_alpha": self.selected_cluster_box_alpha,
            "selected_cluster_box_height_modifier": self.selected_cluster_box_height_modifier,
            "selected_column_name": self.selected_column_name,
            "light_off_time_var": self.light_off_time_var,
            "selected_photometry_line_color": self.selected_photometry_line_color,
            "selected_photometry_line_alpha": self.selected_photometry_line_alpha,
            "selected_temp_mean_line_width": self.selected_temp_mean_line_width,
            "selected_temp_mean_line_color": self.selected_temp_mean_line_color,
            "selected_temp_sem_color": self.selected_temp_sem_color,
            "selected_temp_mean_line_alpha": self.selected_temp_mean_line_alpha,
            "selected_temp_sem_line_alpha": self.selected_temp_sem_line_alpha,
            "selected_temp_desired_offset": self.selected_temp_desired_offset,
            "selected_temp_desired_scale": self.selected_temp_desired_scale,
            "selected_temp_y_axis_color": self.selected_temp_y_axis_color,
            "selected_temp_num_ticks": self.selected_temp_num_ticks,
            "selected_activity_mean_bar_color": self.selected_activity_mean_bar_color,
            "selected_activity_mean_bar_alpha": self.selected_activity_mean_bar_alpha,
            "selected_activity_desired_offset": self.selected_activity_desired_offset,
            "selected_activity_desired_scale": self.selected_activity_desired_scale,
            "selected_activity_y_axis_color": self.selected_activity_y_axis_color,
            "selected_activity_num_bins": self.selected_activity_num_bins,
            "selected_activity_num_ticks": self.selected_activity_num_ticks,
            "telemetry_folder_path": self.telemetry_folder_path,
            "remove_first_60_minutes_var": self.remove_first_60_minutes_var,
        }

    def raw_photometry_processing_specific_config(self) -> dict:
        return {
            "time_column": self.selected_time_column,
            "405nm_column": self.selected_405nm_column,
            "465nm_column": self.selected_465nm_column,
        }

    def save_config_to_file(self, config: dict) -> None:
        save_settings(self.app_type, config)

    def load_variables(self) -> None:
        settings = load_settings(self.app_type)
        if settings:
            self.apply_settings(settings)

    def apply_settings(self, settings: dict) -> None:
        for key, value in settings.items():
            if not hasattr(self, key):
                continue

            current_attribute = getattr(self, key)
            if isinstance(current_attribute, bool):
                setattr(self, key, self._coerce_bool(value))
            else:
                setattr(self, key, value)

        self.selected_temp_line_width = self.selected_temp_mean_line_width

    @staticmethod
    def _coerce_bool(value) -> bool:
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    def set_selected_y_axis_color(self, setting_type: str, value: str) -> None:
        if setting_type == "Temperature":
            self.selected_temp_y_axis_color = value
        elif setting_type == "Activity":
            self.selected_activity_y_axis_color = value
        else:
            raise ValueError(f"Unknown setting type: {setting_type}")
