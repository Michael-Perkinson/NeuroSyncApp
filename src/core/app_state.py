"""Plain Python UI/app state models for GUI applications.

These models keep the source of truth out of Tk variables so the widget layer
can be swapped more easily in the future.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BehaviourViewState:
    file_path: str = ""
    pre_behaviour_time: str = ""
    post_behaviour_time: str = ""
    synchronize_start_time: str = ""
    duration_box_placement: str = "1"
    selected_column: str = ""
    display_duration_box: bool = True
    num_instances_box: bool = True
    time_unit: str = "minutes"
    time_input_unit: str = "seconds"
    x_gridlines: str = ""
    y_gridlines: str = ""
    x_axis_min: str = ""
    x_axis_max: str = ""
    y_axis_min: str = ""
    y_axis_max: str = ""
    behaviour_coding_file: str = ""


@dataclass
class TelemetryViewState:
    file_path: str = ""
    adjust_clustering: str = ""
    associated_temp_data: str = ""
    associated_act_data: str = ""
    light_off_time: str = ""
    temp_and_act_start_time: str = ""
    label_color: str = ""
    label_symbol: str = ""
    label_size: str = ""
    y_offset_peak_symbol: str = ""
    peak_count_color: str = ""
    peak_count_size: str = ""
    y_for_peak_count: str = ""
    baseline_multiplier: str = ""
    baseline_color: str = ""
    baseline_style: str = ""
    baseline_thickness: str = ""
    cluster_box_height_modifier: str = ""
    cluster_box_color: str = ""
    cluster_box_alpha: str = ""
    telemetry_folder_path: str = ""
