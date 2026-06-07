"""Feature-local view state for behaviour alignment."""

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
