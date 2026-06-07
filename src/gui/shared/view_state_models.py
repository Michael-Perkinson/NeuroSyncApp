"""Plain Python state models for reusable GUI views."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DataSelectionViewState:
    file_path: str = ""
    selected_column: str = ""
    use_baseline: bool = False


@dataclass
class StaticInputsViewState:
    pre_behaviour_time: str = ""
    post_behaviour_time: str = ""
    bin_size: str = ""
    selected_behaviour: str = " " * 15


@dataclass
class ExportOptionsViewState:
    use_auc: bool = True
    use_max_amp: bool = True
    use_mean_dff: bool = True
    use_binned_data: bool = True
    combine_csv: bool = True
    image_format: str = "PNG"
    dpi: str = "600"
    width_cm: str = ""
    height_cm: str = ""
    xlabel_fontsize: str = ""
    ylabel_fontsize: str = ""
    xtick_fontsize: str = ""
    ytick_fontsize: str = ""
    y_axis_name: str = ""


@dataclass
class GraphSettingsViewState:
    selected_photometry_line_width: str = ""
    duration_box_placement: str = "1.0"
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
    activity_data_enabled: bool = True
    temperature_data_enabled: bool = True
    limit_axis_range: bool = False
    zero_x_axis_to_behaviour: int = 0
    selected_behaviour_to_zero: str = " " * 15
