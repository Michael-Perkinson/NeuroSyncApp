"""Feature-local view state for telemetry alignment."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TelemetryViewState:
    file_path: str = ""
    adjust_clustering: str = ""
    associated_temp_data: str = ""
    associated_act_data: str = ""
    light_off_time: str = "19:00:00"
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
