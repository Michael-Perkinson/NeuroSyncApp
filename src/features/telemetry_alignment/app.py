from __future__ import annotations

import logging
import os
import re
import json
import copy
import pandas as pd
import numpy as np
import math

from scipy.signal import find_peaks
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
from datetime import datetime, time, timedelta
from PySide6.QtWidgets import (
    QApplication,
    QColorDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.gui.views.behaviour_event_input_frame import BehaviourInputFrame
from src.gui.views.data_selection_panel import DataSelectionPanel
from src.features.telemetry_alignment.views.graph_settings_panel import (
    create_telemetry_graph_settings_panel,
)
from src.gui.views.static_inputs_frame import StaticInputsFrame
from src.gui.views.export_options_panel import ExportOptionsPanel
from src.core.app_settings_manager import AppSettingsManager
from src.features.telemetry_alignment.models import TelemetryViewState
from src.gui.shared.qt_bindings import CheckBoxControl, LineEditControl, ObservableValue
from src.gui.shared.qt_graph_canvas import (
    destroy_embedded_figure,
    embed_figure_in_qt,
)
from src.gui.shared.qt_view_styles import APP_TABS_STYLESHEET, PALETTE, apply_button_role
from src.gui.shared.graph_plotter import (
    apply_figure_size_and_fonts,
    build_save_path,
    save_figure,
)
from src.processing.behavior_metrics import (
    get_time_scale as _get_time_scale,
)
from src.processing.cluster_detection import (
    group_clusters_by_time_period as _group_clusters_by_time_period,
    identify_clusters as _identify_clusters,
    process_data_for_clusters as _process_data_for_clusters,
    select_stim_clusters as _select_stim_clusters,
)
from src.gui.shared.messages_and_errors import show_action_error
from src.processing.telemetry_processing import (
    apply_cluster_binning as _apply_cluster_binning,
    align_and_concatenate_data as _align_and_concatenate_data,
    calculate_mean_and_sem as _calculate_mean_and_sem,
    compute_photometry_mean as _compute_photometry_mean,
    bin_data_dynamic as _bin_data_dynamic,
    create_universal_time_axis as _create_universal_time_axis,
    trim_data_to_minimum_length as _trim_data_to_minimum_length,
)
from src.processing.image_export import build_image_export_request
from src.features.telemetry_alignment.exporters.export_frames import (
    generate_cluster_headings as _generate_cluster_headings,
)
from src.features.telemetry_alignment.views.cluster_table_panel import (
    TelemetryClusterTablePanel,
)
from src.features.telemetry_alignment.views.display_mode_presenter import (
    TelemetryDisplayPresenter,
)
from src.features.telemetry_alignment.io.associated_file_locator import (
    TelemetryAssociatedFileLocator,
)
from src.features.telemetry_alignment.io.static_settings_store import (
    TelemetryStaticSettingsStore,
)
from src.features.telemetry_alignment.views.label_settings_dialog import (
    TelemetryLabelSettingsDialog,
)
from src.features.telemetry_alignment.exporters.workbook_exporter import (
    TelemetryWorkbookExporter,
)
from src.features.telemetry_alignment.services.plot_service import TelemetryPlotService
from src.features.telemetry_alignment.services.cluster_analysis import (
    TelemetryClusterService,
)

logger = logging.getLogger(__name__)


class TelemetryPhotomOptoProcessingApp(QWidget):
    COMPONENT_TYPES = {
        "cluster_table_panel": TelemetryClusterTablePanel,
        "display_presenter": TelemetryDisplayPresenter,
        "associated_file_locator": TelemetryAssociatedFileLocator,
        "static_settings_store": TelemetryStaticSettingsStore,
        "label_settings_dialog": TelemetryLabelSettingsDialog,
        "workbook_exporter": TelemetryWorkbookExporter,
        "plot_service": TelemetryPlotService,
        "cluster_service": TelemetryClusterService,
    }

    def __init__(self, parent: QWidget | None = None, **kwargs):
        self.settings_manager = AppSettingsManager(app_type="telemetry_photom_opto")
        self.app_name = "telemetry_photom_opto"

        super().__init__(parent, **kwargs)
        self.initialize_attributes()

        self.configure_main_frames()
        self.configure_notebooks()
        self.configure_tabs()
        self.create_widgets()

    def initialize_attributes(self):
        """Initialize shared state, value models, and feature components."""
        self.setWindowTitle("Align Telemetry Data")
        self._initialize_state()
        self._initialize_tk_variables()
        self._initialize_components()
        self._load_settings_into_variables()

    @staticmethod
    def _assign_defaults(target, values):
        for attribute, value in values.items():
            setattr(target, attribute, value)

    def _initialize_state(self):
        self.view_state = TelemetryViewState()
        self._assign_defaults(
            self,
            {
                "table_data": [],
                "table_treeview": None,
                "tables": {},
                "data_dict": {},
                "mean_cluster_data": {},
                "duration_data_cache": {},
                "current_fig": None,
                "mouse_name": None,
                "figure_canvas": None,
                "toolbar": None,
                "dataframe": None,
                "trimmed_dataframe": None,
                "full_dataframe": None,
                "duration_main_data": None,
                "time_column": None,
                "data_column": None,
                "data_type": None,
                "detected_peaks": None,
                "clusters_final": None,
                "adjusted": False,
                "press": None,
                "cluster_boxes": {},
                "cluster_display_status": {},
                "cluster_options_created": False,
                "peak_alignment_vars": {},
                "cluster_colors": {},
                "act_data": None,
                "temp_data": None,
                "extended_temp_data": None,
                "extended_act_data": None,
                "raw_aligned_act_data": None,
                "raw_aligned_temp_data": None,
                "raw_extended_act_data": None,
                "raw_extended_temp_data": None,
                "seconds_removed": 0,
                "figure_cache": {},
                "act_file_path": None,
                "temp_file_path": None,
                "file_path": None,
            },
        )

    def _bind_state_var(self, value_var, state_field):
        value_var.set(getattr(self.view_state, state_field))
        value_var.trace_add("write", lambda: setattr(self.view_state, state_field, value_var.get()))

    def _set_state_var(self, value_var, state_field, value):
        setattr(self.view_state, state_field, value)
        if value_var.get() != value:
            value_var.set(value)

    def _initialize_tk_variables(self):
        self.file_path_var = ObservableValue("")
        self.adjust_clustering_var = ObservableValue("")
        self.associated_temp_data_entry = ObservableValue("")
        self.associated_act_data_entry = ObservableValue("")
        self.light_off_time_var = ObservableValue("")
        self.temp_and_act_start_time_var = ObservableValue("")
        self.label_color_var = ObservableValue("")
        self.label_symbol_var = ObservableValue("")
        self.label_size_var = ObservableValue("")
        self.y_offset_peak_symbol = ObservableValue("")
        self.peak_count_color_var = ObservableValue("")
        self.peak_count_size_var = ObservableValue("")
        self.y_for_peak_count = ObservableValue("")
        self.baseline_multiplier = ObservableValue("")
        self.baseline_color = ObservableValue("")
        self.baseline_style = ObservableValue("")
        self.baseline_thickness = ObservableValue("")
        self.cluster_box_height_modifier = ObservableValue("")
        self.cluster_box_color = ObservableValue("")
        self.cluster_box_alpha = ObservableValue("")
        self.telemetry_folder_path = ObservableValue("")
        self._bind_state_var(self.file_path_var, "file_path")
        self._bind_state_var(self.adjust_clustering_var, "adjust_clustering")
        self._bind_state_var(
            self.associated_temp_data_entry, "associated_temp_data"
        )
        self._bind_state_var(self.associated_act_data_entry, "associated_act_data")
        self._bind_state_var(self.light_off_time_var, "light_off_time")
        self._bind_state_var(
            self.temp_and_act_start_time_var, "temp_and_act_start_time"
        )
        self._bind_state_var(self.label_color_var, "label_color")
        self._bind_state_var(self.label_symbol_var, "label_symbol")
        self._bind_state_var(self.label_size_var, "label_size")
        self._bind_state_var(self.y_offset_peak_symbol, "y_offset_peak_symbol")
        self._bind_state_var(self.peak_count_color_var, "peak_count_color")
        self._bind_state_var(self.peak_count_size_var, "peak_count_size")
        self._bind_state_var(self.y_for_peak_count, "y_for_peak_count")
        self._bind_state_var(self.baseline_multiplier, "baseline_multiplier")
        self._bind_state_var(self.baseline_color, "baseline_color")
        self._bind_state_var(self.baseline_style, "baseline_style")
        self._bind_state_var(self.baseline_thickness, "baseline_thickness")
        self._bind_state_var(
            self.cluster_box_height_modifier, "cluster_box_height_modifier"
        )
        self._bind_state_var(self.cluster_box_color, "cluster_box_color")
        self._bind_state_var(self.cluster_box_alpha, "cluster_box_alpha")
        self._bind_state_var(self.telemetry_folder_path, "telemetry_folder_path")

    def _initialize_components(self):
        for attribute, component_type in self.COMPONENT_TYPES.items():
            setattr(self, attribute, component_type(self))

    def _load_settings_into_variables(self):
        light_off_time = (
            self.settings_manager.light_off_time_var
            or self.settings_manager.default_settings.get("light_off_time_var", "19:00:00")
        )
        self.settings_manager.light_off_time_var = light_off_time
        self._set_state_var(
            self.light_off_time_var,
            "light_off_time",
            light_off_time,
        )
        self._set_state_var(
            self.label_color_var, "label_color", self.settings_manager.selected_label_color
        )
        self._set_state_var(
            self.label_symbol_var,
            "label_symbol",
            self.settings_manager.selected_label_symbol,
        )
        self._set_state_var(
            self.label_size_var, "label_size", self.settings_manager.selected_label_size
        )
        self._set_state_var(
            self.y_offset_peak_symbol,
            "y_offset_peak_symbol",
            self.settings_manager.selected_y_offset_peak_symbol,
        )
        self._set_state_var(
            self.peak_count_color_var,
            "peak_count_color",
            self.settings_manager.selected_peak_count_color,
        )
        self._set_state_var(
            self.peak_count_size_var,
            "peak_count_size",
            self.settings_manager.selected_peak_count_size,
        )
        self._set_state_var(
            self.y_for_peak_count,
            "y_for_peak_count",
            self.settings_manager.selected_y_for_peak_count,
        )
        self._set_state_var(
            self.baseline_multiplier,
            "baseline_multiplier",
            self.settings_manager.selected_baseline_multiplier,
        )
        self._set_state_var(
            self.baseline_color,
            "baseline_color",
            self.settings_manager.selected_baseline_color,
        )
        self._set_state_var(
            self.baseline_style,
            "baseline_style",
            self.settings_manager.selected_baseline_style,
        )
        self._set_state_var(
            self.baseline_thickness,
            "baseline_thickness",
            self.settings_manager.selected_baseline_thickness,
        )
        self._set_state_var(
            self.cluster_box_height_modifier,
            "cluster_box_height_modifier",
            self.settings_manager.selected_cluster_box_height_modifier,
        )
        self._set_state_var(
            self.cluster_box_color,
            "cluster_box_color",
            self.settings_manager.selected_cluster_box_color,
        )
        self._set_state_var(
            self.cluster_box_alpha,
            "cluster_box_alpha",
            self.settings_manager.selected_cluster_box_alpha,
        )
        self._set_state_var(
            self.telemetry_folder_path,
            "telemetry_folder_path",
            self.settings_manager.telemetry_folder_path,
        )

    def configure_main_frames(self):
        """Configure the root layout and main frames."""
        self.setObjectName("telemetryAppRoot")
        self.setStyleSheet(
            f"#telemetryAppRoot {{ background: {PALETTE['app_bg']}; }}"
        )
        self._root_layout = QVBoxLayout(self)
        self._root_layout.setContentsMargins(10, 10, 10, 10)
        self._root_layout.setSpacing(10)

        self.top_frame = QWidget(self)
        self.top_frame_layout = QGridLayout(self.top_frame)
        self.top_frame_layout.setContentsMargins(0, 0, 0, 0)
        self.top_frame_layout.setHorizontalSpacing(10)
        self.top_frame_layout.setVerticalSpacing(10)
        self._root_layout.addWidget(self.top_frame)

        self.bottom_frame = QWidget(self)
        self.bottom_frame_layout = QGridLayout(self.bottom_frame)
        self.bottom_frame_layout.setContentsMargins(0, 0, 0, 0)
        self.bottom_frame_layout.setHorizontalSpacing(10)
        self.bottom_frame_layout.setVerticalSpacing(0)
        self._root_layout.addWidget(self.bottom_frame, 1)

    def configure_notebooks(self):
        """Configure the notebooks for graphs and settings."""
        self.notebook_graphs = QTabWidget(self.bottom_frame)
        self.notebook_settings = QTabWidget(self.bottom_frame)
        self.notebook_graphs.setStyleSheet(APP_TABS_STYLESHEET)
        self.notebook_settings.setStyleSheet(APP_TABS_STYLESHEET)
        self.bottom_frame_layout.addWidget(self.notebook_graphs, 0, 0)
        self.bottom_frame_layout.addWidget(self.notebook_settings, 0, 1)
        self.bottom_frame_layout.setColumnStretch(0, 3)
        self.bottom_frame_layout.setColumnStretch(1, 2)

        self.graph_settings_tab = QWidget(self.notebook_settings)
        self.graph_settings_tab.setLayout(QVBoxLayout())
        self.graph_settings_tab.layout().setContentsMargins(0, 0, 0, 0)
        self.export_options_tab = QWidget(self.notebook_settings)
        self.export_options_tab.setLayout(QVBoxLayout())
        self.export_options_tab.layout().setContentsMargins(0, 0, 0, 0)

        self.notebook_settings.addTab(self.graph_settings_tab, "Graph Settings")
        self.notebook_settings.addTab(self.export_options_tab, "Export Options")

    def configure_tabs(self):
        """ Initialize and configure the tabs for graph settings, export options, graph display, and table display."""
        self.graph_settings_container_instance = create_telemetry_graph_settings_panel(
            self.graph_settings_tab,
            self,
        )
        self.graph_settings_tab.layout().addWidget(self.graph_settings_container_instance)

        self.export_options_container = ExportOptionsPanel(
            self.export_options_tab,
            file_path_var=self.file_path_var,
            settings_manager=self.settings_manager,
            extract_button_click_handler=self.extract_button_click_handler,
            save_image=self.save_image
        )
        self.export_options_tab.layout().addWidget(self.export_options_container)

        self.graph_settings_container_instance.complete_initialization()

        self.graph_tab = QWidget(self.notebook_graphs)
        self.graph_tab.setLayout(QVBoxLayout())
        self.graph_tab.layout().setContentsMargins(0, 0, 0, 0)
        self.table_tab = QWidget(self.notebook_graphs)
        self.table_tab.setLayout(QVBoxLayout())
        self.table_tab.layout().setContentsMargins(0, 0, 0, 0)

        self.notebook_graphs.addTab(self.graph_tab, "Graph")
        self.notebook_graphs.addTab(self.table_tab, "Table")

        self.create_graphs_container(self.graph_tab)
        self.create_table_container(self.table_tab)

    def create_table_container(self, frame):
        self.cluster_table_panel.create_table_container(frame)

    def treeview_sort_column(self, tv, col, reverse):
        self.cluster_table_panel.treeview_sort_column(tv, col, reverse)

    def create_graphs_container(self, frame):
        self.display_presenter.create_graphs_container(frame)

    def valid_clusters(self, cluster_names):
        """
        Returns a list of cluster names that have valid data (non-empty specified fields).

        Parameters:
        - cluster_names: List of cluster names to validate.

        Returns:
        - List of cluster names that have valid data.
        """
        return [name for name in cluster_names if not self.has_empty_inputs(next(iter(self.data_dict.values())).get(name))]

    def on_cluster_selection_changed(self, event=None):
        self.display_presenter.on_cluster_selection_changed(event)

    def compute_data_for_cluster(self, selected_peak_count, changed_static_inputs=None):
        self.cluster_service.compute_data_for_cluster(
            selected_peak_count, changed_static_inputs
        )

    def annotate_clusters_with_time_period(self):
        """Annotates each cluster and stim with information about whether it occurs during daytime or nighttime."""
        for key, cluster_info in self.cluster_dict.items():
            cluster_start_time = cluster_info['start_time']
            if self.is_cluster_in_nighttime(cluster_start_time):
                cluster_info['time_period'] = 'Night'
            else:
                cluster_info['time_period'] = 'Day'

        for file_path, clusters in self.data_dict.items():
            for cluster_name, cluster_info in clusters.items():
                if 'stim' in cluster_name:
                    cluster_start_time = cluster_info['stim_start']
                    if self.is_cluster_in_nighttime(cluster_start_time):
                        cluster_info['time_period'] = 'Night'
                    else:
                        cluster_info['time_period'] = 'Day'

    def export_raw_data_to_excel(self, cluster_number, output_filepath):
        """
        Export the raw data for the specified cluster to an Excel file.

        Parameters:
        - cluster_number: The number of the cluster to export data for.
        - output_filepath: The file path where the Excel file will be saved.
        """
        mean_temp_data = self.mean_cluster_data[cluster_number]["mean_temp_data"]
        mean_act_data = self.mean_cluster_data[cluster_number]["mean_act_data"]
        mean_temp_data['gap'] = ''

        combined_data = pd.concat([mean_temp_data, mean_act_data], axis=1)

        with pd.ExcelWriter(output_filepath, engine='openpyxl') as writer:
            combined_data.to_excel(
                writer, sheet_name=f"Cluster_{cluster_number}_Raw", index=False)

    def get_peak_counts(self):
        """
        Retrieves and formats unique peak counts from cluster keys.

        Returns:
            list: Sorted list of unique peak counts extracted from cluster keys.
        """
        unique_peak_counts = set()
        for cluster_key in self.cluster_dict.keys():
            peak_count = cluster_key[2]
            unique_peak_counts.add(peak_count)

        return sorted(unique_peak_counts)

    def get_stim_counts(self):
        """
        Retrieves and formats unique stimulation counts from cluster keys in data_dict.

        Returns:
            list: Sorted list of unique stimulation counts extracted from data_dict keys.
        """
        unique_stim_counts = set()
        for file_path, clusters in self.data_dict.items():
            for cluster_name in clusters.keys():
                if 'stim' in cluster_name:
                    stim_count = int(
                        re.search(r'(\d+)_stim', cluster_name).group(1))
                    unique_stim_counts.add(stim_count)

        return sorted(unique_stim_counts)

    def precompute_all_clusters(self, updated_clusters=None):
        self.cluster_service.precompute_all_clusters(updated_clusters)

    def ensure_all_mean_cluster_data(self):
        """Populate all mean-cluster data when an export needs it."""
        if self.extended_temp_data is None or self.extended_act_data is None:
            return

        expected_cluster_numbers = set(self.get_peak_counts()) | set(self.get_stim_counts())
        missing_cluster_numbers = [
            cluster_number
            for cluster_number in expected_cluster_numbers
            if cluster_number not in self.mean_cluster_data
        ]
        if missing_cluster_numbers:
            self.precompute_all_clusters()

    def compute_data_for_stim_cluster(self, selected_stim_count, changed_static_inputs=None):
        """
        Compute data for the specified stim cluster and store the processed data for each period.

        Parameters:
        - selected_stim_count: The number of stims in the selected cluster.
        - changed_static_inputs: Optional; any static inputs that have changed (default is None).
        """
        cluster_number = selected_stim_count

        processed_data, raw_data, native_data = self.extract_and_prepare_temp_and_act_data_for_stim(
            cluster_number)

        def convert_seconds_to_minutes(seconds):
            return [s / 60 for s in seconds]

        self.mean_cluster_data[cluster_number] = {
            "full": {
                "mean_temp_data": processed_data['full']['temp'],
                "mean_act_data": processed_data['full']['act'],
                "universal_time_axis_temp": processed_data['full']['temp']['Time (s)'].tolist(),
                "universal_time_axis_act": processed_data['full']['act']['Time (s)'].tolist(),
                "universal_time_axis_temp_min": convert_seconds_to_minutes(raw_data['full']['temp']['Time (s)'].tolist()),
                "raw_temp_data": raw_data['full']['temp'],
                "raw_act_data": raw_data['full']['act'],
                "native_temp_segments": native_data["full"]["temp"],
                "native_act_segments": native_data["full"]["act"],
            },
            "day": {
                "mean_temp_data": processed_data['day']['temp'],
                "mean_act_data": processed_data['day']['act'],
                "universal_time_axis_temp": processed_data['full']['temp']['Time (s)'].tolist(),
                "universal_time_axis_act": processed_data['full']['act']['Time (s)'].tolist(),
                "universal_time_axis_temp_min": convert_seconds_to_minutes(raw_data['full']['temp']['Time (s)'].tolist()),
                "raw_temp_data": raw_data['day']['temp'],
                "raw_act_data": raw_data['day']['act'],
                "native_temp_segments": native_data["day"]["temp"],
                "native_act_segments": native_data["day"]["act"],
            },
            "night": {
                "mean_temp_data": processed_data['night']['temp'],
                "mean_act_data": processed_data['night']['act'],
                "universal_time_axis_temp": processed_data['full']['temp']['Time (s)'].tolist(),
                "universal_time_axis_act": processed_data['full']['act']['Time (s)'].tolist(),
                "universal_time_axis_temp_min": convert_seconds_to_minutes(raw_data['full']['temp']['Time (s)'].tolist()),
                "raw_temp_data": raw_data['night']['temp'],
                "raw_act_data": raw_data['night']['act'],
                "native_temp_segments": native_data["night"]["temp"],
                "native_act_segments": native_data["night"]["act"],
            }
        }

        if changed_static_inputs is not None:
            selected_cluster_string = self.selected_cluster.get()
            selected_display_type = self.selected_display.get()

            if selected_display_type == "Single Cluster Display":
                self.visualize_single_cluster(selected_cluster_string)
            elif selected_display_type == "Mean Cluster Display":
                self.visualize_mean_cluster(selected_cluster_string)

    def find_stim_times(self, stim_number):
        """
        Find the adjusted pre-stim and post-stim times for a given stimulation number.

        Parameters:
            stim_number (int): The stimulation number to search for in the data.

        Returns:
            tuple: The adjusted pre-stim time and post-stim time for the given stimulation number.
        """
        pre_stim_time, post_stim_time = 0, 0

        for _, stim_dict in self.data_dict.items():
            for cluster_key, cluster_vals in stim_dict.items():
                if f"{stim_number}_stim" in cluster_key:
                    pre_stim_time = float(cluster_vals['pre_stim_time'])
                    post_stim_time = float(cluster_vals['post_stim_time'])
                    stim_start = cluster_vals['stim_start']
                    stim_end = cluster_vals['stim_end']

                    adjusted_pre_stim = pre_stim_time / 60
                    adjusted_post_stim = (
                        stim_end - stim_start) + (post_stim_time / 60)

                    return adjusted_pre_stim, adjusted_post_stim

        return None  # Return None if the specified stim_number is not found

    def extract_and_prepare_temp_and_act_data_for_stim(self, stim_number):
        """
        Extract and prepare temperature and activity data for stim clusters.

        Parameters:
            stim_number (int): The stim number to process.

        Returns:
            two tuples: Processed data and raw data dictionaries for 'full', 'day', and 'night' periods.
                Each dictionary contains 'temp' and 'act' keys with corresponding data.
        """

        all_clusters = _select_stim_clusters(self.data_dict, stim_number)
        clusters_by_period = _group_clusters_by_time_period(all_clusters)

        processed_data = {
            'full': {'temp': None, 'act': None},
            'day': {'temp': None, 'act': None},
            'night': {'temp': None, 'act': None}
        }

        raw_data = {
            'full': {'temp': None, 'act': None},
            'day': {'temp': None, 'act': None},
            'night': {'temp': None, 'act': None}
        }
        native_data = {
            'full': {'temp': [], 'act': []},
            'day': {'temp': [], 'act': []},
            'night': {'temp': [], 'act': []}
        }

        stim_times = self.find_stim_times(stim_number)
        if stim_times is None:
            return processed_data, raw_data

        for period, clusters in clusters_by_period.items():

            if not clusters:
                continue  # Skip to the next period if there are no clusters

            all_temp_data, all_act_data = self.process_data_for_clusters(
                clusters, stim_times[0], stim_times[1], is_stim=True)
            native_data[period]['temp'] = all_temp_data
            native_data[period]['act'] = all_act_data

            axis_time_start = -stim_times[0] * 60
            axis_time_end = stim_times[1] * 60
            universal_time_axis_temp = self.create_universal_time_axis(
                axis_time_start, axis_time_end, self.temp_sample_rate)
            universal_time_axis_act = self.create_universal_time_axis(
                axis_time_start, axis_time_end, self.act_sample_rate)

            all_temp_data = self.trim_data_to_minimum_length(all_temp_data)
            all_act_data = self.trim_data_to_minimum_length(all_act_data)

            concatenated_temp_data = self.align_and_concatenate_data(
                all_temp_data, universal_time_axis_temp)
            concatenated_act_data = self.align_and_concatenate_data(
                all_act_data, universal_time_axis_act)

            concatenated_temp_data = concatenated_temp_data.iloc[::-1].dropna(
                how='all').iloc[::-1]

            concatenated_act_data = concatenated_act_data.iloc[::-1].dropna(
                how='all').iloc[::-1]

            final_temp_data = self.calculate_mean_and_sem(
                concatenated_temp_data)
            final_act_data = self.calculate_mean_and_sem(concatenated_act_data)

            processed_data[period]['temp'] = final_temp_data
            processed_data[period]['act'] = final_act_data

            raw_data[period]['temp'] = concatenated_temp_data
            raw_data[period]['act'] = concatenated_act_data

        return processed_data, raw_data, native_data

    def has_empty_inputs(self, cluster_data):
        """
        Check if the specified fields in cluster_data are empty.

        Parameters:
        - cluster_data: Dictionary containing cluster data.

        Returns:
        - bool: True if any of the specified fields in cluster_data are empty, False otherwise.
        """
        if cluster_data is None:
            return True

        fields_to_check = ['pre_cluster_time', 'post_cluster_time', 'bin_size']
        return any(not cluster_data[field] for field in fields_to_check)

    def visualize_mean_cluster(self, selected_cluster_string):
        self.display_presenter.visualize_mean_cluster(selected_cluster_string)

    def display_no_data_figure(self):
        self.display_presenter.display_no_data_figure()

    def find_longest_times(self, cluster_number):
        return self.cluster_service.find_longest_times(cluster_number)

    def get_minimum_length(self, data_list):
        """
        Find the minimum length among a list of DataFrames.

        Parameters:
            data_list (list): List of pandas DataFrames.

        Returns:
            int: The minimum length among all DataFrames in the list.
        """
        return min(len(data) for data in data_list)

    def calculate_sample_rate(self, timestamps):
        """
        Calculate the sample rate based on a list of timestamps.

        Parameters:
            timestamps (list): List of timestamps, which can be either datetime objects or floats.

        Returns:
            float: The calculated sample rate.
        """
        if isinstance(timestamps[0], (datetime, pd.Timestamp, np.datetime64)):
            parsed_timestamps = pd.to_datetime(pd.Series(timestamps), errors="coerce")
            time_diffs = (
                parsed_timestamps.diff().dt.total_seconds().dropna().tolist()
            )
        else:
            time_diffs = [
                timestamps[i + 1] - timestamps[i]
                for i in range(len(timestamps) - 1)
            ]

        time_diffs = [diff for diff in time_diffs if diff > 0]
        if not time_diffs:
            raise ValueError("Could not calculate a positive telemetry sample interval.")
        return sum(time_diffs) / len(time_diffs)

    def separate_clusters_by_time_period(self):
        """
        Separate clusters into daytime and nighttime based on their time period.

        Returns:
            tuple: A tuple containing three lists:
                - all_clusters: List of all clusters.
                - daytime_clusters: List of clusters during the daytime.
                - nighttime_clusters: List of clusters during the nighttime.
        """
        daytime_clusters = []
        nighttime_clusters = []
        all_clusters = []

        for _, cluster_dict in self.data_dict.items():
            for _, cluster_data in cluster_dict.items():
                all_clusters.append(cluster_data)
                if cluster_data['time_period'] == 'Night':
                    nighttime_clusters.append(cluster_data)
                else:
                    daytime_clusters.append(cluster_data)

        return all_clusters, daytime_clusters, nighttime_clusters

    def process_data_for_clusters(self, clusters, longest_pre_peak, longest_post_peak, is_stim=False):
        return _process_data_for_clusters(
            clusters,
            longest_pre_peak,
            longest_post_peak,
            self.extended_temp_data,
            self.extended_act_data,
            is_stim=is_stim,
        )

    def calculate_mean_and_sem(self, concatenated_data):
        return _calculate_mean_and_sem(concatenated_data)

    def trim_data_to_minimum_length(self, all_data):
        return _trim_data_to_minimum_length(all_data)

    def create_universal_time_axis(self, axis_time_start, axis_time_end, sample_rate):
        return _create_universal_time_axis(axis_time_start, axis_time_end, sample_rate)

    def is_valid_cluster(self, cluster_name, cluster_number):
        """
        Check if the cluster name is valid based on the cluster number.

        Parameters:
            cluster_name (str): The name of the cluster.
            cluster_number (int): The cluster number to validate against.

        Returns:
            bool: True if the cluster name is valid for the given cluster number, False otherwise.
        """
        return f"{cluster_number} Peak" in cluster_name or f"{cluster_number} Peaks" in cluster_name

    def align_and_concatenate_data(self, all_data, universal_time_axis):
        return _align_and_concatenate_data(all_data, universal_time_axis)

    def create_linear_time_index(self, start, end, step):
        """
        Create a linear time index from start to end with a given step size.

        Parameters:
            start (float): The starting time.
            end (float): The ending time.
            step (float): The step size for the time index.

        Returns:
            numpy.ndarray: An array representing the linear time index.
        """
        return np.arange(start, end + step, step)

    def scale_time_column(self, time_column):
        """
        Scale the time column based on the selected time unit and display settings.

        Parameters:
            time_column (pandas.Series): The original time column to be scaled.

        Returns:
            pandas.Series: The scaled time column.
        """
        time_unit = self.graph_settings_container_instance.time_unit_menu.get()
        if time_unit == "time of day" and self.selected_display.get() == "Mean Cluster Display":
            time_unit = "minutes"

        time_factor = self.get_time_scale(time_unit)

        if time_factor is not None:
            return pd.Series([time * time_factor for time in time_column])
        return pd.Series(time_column)

    def plot_mean_cluster(self, mean_temp_data, mean_act_data, photometry_cluster_data_df, cluster_count=None):
        self.display_presenter.plot_mean_cluster(
            mean_temp_data, mean_act_data, photometry_cluster_data_df, cluster_count
        )

    def add_stims_to_plot(self, ax, cluster_count):
        self.display_presenter.add_stims_to_plot(ax, cluster_count)

    def populate_static_input_dropdown(self):
        """Populate the dropdown menu for cluster or stimulation selection based on the data type."""
        if self.data_type == 'photometry':
            options = [
                f"{count} Peak" if count == 1 else f"{count} Peaks"
                for count in self.get_peak_counts()
            ]
            options.append("All Clusters")
        elif self.data_type == 'optogenetics':
            options = [f"{count} stim" for count in self.get_stim_counts()]
            options.append("All Stims")
        else:
            options = []

        if options:
            self.static_inputs_frame.set_behaviour_options(options)
            self.static_inputs_frame.selected_behaviour.set(options[0])
        else:
            self.static_inputs_frame.set_behaviour_options([])

    def create_widgets(self):
        """Create and configure the Qt widget sections used by the telemetry tool."""
        self.data_selection_frame = DataSelectionPanel(
            self.top_frame,
            width=500,
            settings_manager=self.settings_manager,
            new_data_file_callback=self.associated_file_locator.handle_new_data_file,
        )
        self.top_frame_layout.addWidget(self.data_selection_frame, 0, 0)

        self.behaviour_input_frame = BehaviourInputFrame(
            self.top_frame,
            select_event_file_callback=self.select_behaviour_file,
            show_column_names=False,
        )
        self.top_frame_layout.addWidget(self.behaviour_input_frame, 0, 1)

        self.behaviour_input_frame.behaviour_input_label.setText(
            "Change Associated Files and Align Time"
        )

        self.behaviour_input_frame.import_behaviour_button.hide()
        self.behaviour_input_frame.behaviour_coding_frame.hide()

        associated_files_frame = QFrame(self.behaviour_input_frame)
        associated_files_frame.setObjectName("behaviourInputSection")
        associated_layout = QGridLayout(associated_files_frame)
        associated_layout.setContentsMargins(8, 8, 8, 8)
        associated_layout.setHorizontalSpacing(8)
        associated_layout.setVerticalSpacing(6)
        associated_layout.setColumnStretch(0, 0)
        associated_layout.setColumnStretch(1, 1)
        associated_layout.setColumnStretch(2, 0)
        associated_layout.setColumnStretch(3, 1)
        self.behaviour_input_frame.layout().addWidget(associated_files_frame, 1, 0, 1, 2)

        self.change_associated_temp_file_button = QPushButton(
            "Temperature File:",
            associated_files_frame,
        )
        self.change_associated_temp_file_button.clicked.connect(
            self.change_associated_temp_file
        )
        apply_button_role(self.change_associated_temp_file_button, "primary")
        self.change_associated_temp_file_button.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        associated_layout.addWidget(self.change_associated_temp_file_button, 0, 0)

        self.temp_file_name_label = LineEditControl(
            self.associated_temp_data_entry, associated_files_frame
        )
        self.temp_file_name_label.setReadOnly(True)
        self.temp_file_name_label.setMinimumWidth(150)
        self.temp_file_name_label.setMaximumWidth(260)
        self.temp_file_name_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        associated_layout.addWidget(self.temp_file_name_label, 0, 1)

        self.change_associated_act_file_button = QPushButton(
            "Activity File:",
            associated_files_frame,
        )
        self.change_associated_act_file_button.clicked.connect(
            self.change_associated_act_file
        )
        apply_button_role(self.change_associated_act_file_button, "primary")
        self.change_associated_act_file_button.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        associated_layout.addWidget(self.change_associated_act_file_button, 0, 2)

        self.activity_file_name_label = LineEditControl(
            self.associated_act_data_entry, associated_files_frame
        )
        self.activity_file_name_label.setReadOnly(True)
        self.activity_file_name_label.setMinimumWidth(150)
        self.activity_file_name_label.setMaximumWidth(260)
        self.activity_file_name_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        associated_layout.addWidget(self.activity_file_name_label, 0, 3)

        self.temp_and_act_start_time = QLabel(
            "Associated files Start Time (hh:mm:ss): ",
            associated_files_frame,
        )
        self.temp_and_act_start_time.setWordWrap(True)
        self.temp_and_act_start_time.setMaximumWidth(140)
        associated_layout.addWidget(self.temp_and_act_start_time, 1, 0)

        self.temp_and_act_start_time_entry = LineEditControl(
            self.temp_and_act_start_time_var, associated_files_frame
        )
        self.temp_and_act_start_time_entry.setMinimumWidth(90)
        self.temp_and_act_start_time_entry.setMaximumWidth(140)
        self.temp_and_act_start_time_entry.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        associated_layout.addWidget(self.temp_and_act_start_time_entry, 1, 1)

        self.adjust_clustering_label = QLabel(
            "Adjust clustering minimum time between clusters (s):",
            associated_files_frame,
        )
        self.adjust_clustering_label.setWordWrap(True)
        self.adjust_clustering_label.setMaximumWidth(175)
        associated_layout.addWidget(self.adjust_clustering_label, 1, 2)

        self.adjust_clustering_entry = LineEditControl(
            self.adjust_clustering_var, associated_files_frame
        )
        self.adjust_clustering_entry.setMinimumWidth(90)
        self.adjust_clustering_entry.setMaximumWidth(140)
        self.adjust_clustering_entry.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        associated_layout.addWidget(self.adjust_clustering_entry, 1, 3)
        self.adjust_clustering_entry.editingFinished.connect(lambda: self.on_focus_out(None))
        self.adjust_clustering_entry.textEdited.connect(lambda *_args: self.set_adjusted_false())
        self.adjust_clustering_entry.returnPressed.connect(self.reset_clusters_based_on_user_input)

        self.light_off_time_label = QLabel(
            "Lights off (hh:mm:ss): ",
            associated_files_frame,
        )
        self.light_off_time_label.setWordWrap(True)
        self.light_off_time_label.setMaximumWidth(120)
        associated_layout.addWidget(self.light_off_time_label, 2, 0)

        self.light_off_time_entry = LineEditControl(
            self.light_off_time_var, associated_files_frame
        )
        self.light_off_time_entry.setMinimumWidth(90)
        self.light_off_time_entry.setMaximumWidth(140)
        self.light_off_time_entry.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        associated_layout.addWidget(self.light_off_time_entry, 2, 1)

        self.overlay_temp_and_act_button = QPushButton(
            "Align Temperature and Activity with Photometry",
            associated_files_frame,
        )
        self.overlay_temp_and_act_button.clicked.connect(
            self.plot_service.overlay_temp_and_act
        )
        apply_button_role(self.overlay_temp_and_act_button, "primary")
        self.overlay_temp_and_act_button.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        associated_layout.addWidget(self.overlay_temp_and_act_button, 2, 2, 1, 2)

        self.static_inputs_frame = StaticInputsFrame(
            self.top_frame,
            save_inputs_callback=self.static_settings_store.save_inputs,
        )
        self.top_frame_layout.addWidget(self.static_inputs_frame, 0, 2)

        self.static_inputs_frame.pre_behaviour_time_label.setText("Pre-Cluster time (s): ")
        self.static_inputs_frame.post_behaviour_time_label.setText("Post-Cluster time (s): ")

        self.top_frame_layout.setColumnStretch(0, 1)
        self.top_frame_layout.setColumnStretch(1, 1)
        self.top_frame_layout.setColumnStretch(2, 1)

    def update_idletasks(self):
        QApplication.processEvents()

    def set_adjusted_false(self):
        """Set the 'adjusted' attribute to False."""
        self.adjusted = False

    def on_focus_out(self, event):
        """
        Handle the event when the focus leaves the clustering adjustment entry.

        Parameters:
            event: The event object associated with the focus out event.
        """
        value = self.view_state.adjust_clustering.strip()
        if value and not self.adjusted:
            QMessageBox.information(
                self,
                "Reminder",
                "After typing into the clustering adjustment please click back into the box and press Enter to apply changes.",
            )

    def create_cluster_options(self, destroy_frame=True):
        """
        Create the cluster options frame based on cluster sizes.

        Parameters:
            destroy_frame (bool, optional): Whether to destroy the existing frame if it exists. Defaults to True.
        """
        if not hasattr(self.graph_settings_container_instance, "behaviour_frame"):
            return
        if self.cluster_options_created:
            return
        if destroy_frame:
            if hasattr(self, "cluster_frame") and self.cluster_frame is not None:
                self.cluster_frame.setParent(None)
                self.cluster_frame.deleteLater()
                self.cluster_frame = None

        self.graph_settings_container_instance.setup_canvas()

        cluster_sizes = [len(cluster_data['peaks'])
                         for cluster_data in self.cluster_dict.values()]
        cluster_size_counts = {size: cluster_sizes.count(
            size) for size in set(cluster_sizes)}

        sorted_cluster_sizes = sorted(cluster_size_counts.keys())

        self.cluster_checkboxes = {}
        self.cluster_buttons = {}

        self.peak_alignment_vars = {}
        self.cluster_colors = {}

        self.cluster_frame = QFrame(self.graph_settings_container_instance.behaviour_frame)
        cluster_layout = QGridLayout(self.cluster_frame)
        cluster_layout.setContentsMargins(0, 0, 0, 0)
        cluster_layout.setHorizontalSpacing(10)
        cluster_layout.setVerticalSpacing(8)
        self.graph_settings_container_instance.behaviour_frame_layout.addWidget(
            self.cluster_frame
        )

        cluster_list_label = QLabel("Clusters", self.cluster_frame)
        cluster_layout.addWidget(cluster_list_label, 0, 0)

        select_all_button = QPushButton("Select All", self.cluster_frame)
        select_all_button.clicked.connect(self.select_all_clusters)
        cluster_layout.addWidget(select_all_button, 0, 1)

        deselect_all_button = QPushButton("Deselect All", self.cluster_frame)
        deselect_all_button.clicked.connect(self.deselect_all_clusters)
        cluster_layout.addWidget(deselect_all_button, 0, 2)

        save_peak_alignment_button = QPushButton("Save peak alignment", self.cluster_frame)
        save_peak_alignment_button.clicked.connect(self.save_peak_alignment)
        cluster_layout.addWidget(save_peak_alignment_button, 0, 3)

        cluster_sizes = [len(cluster_data['peaks'])
                         for cluster_data in self.cluster_dict.values()]
        self.cluster_display_status = {self.format_cluster_string(
            size): ObservableValue(True) for size in set(cluster_sizes)}

        for i, cluster_size in enumerate(sorted_cluster_sizes, start=1):
            color_value = ObservableValue(
                self.settings_manager.selected_cluster_box_color
            )
            self.cluster_colors[cluster_size] = color_value

            cluster_button = QPushButton(
                self.format_cluster_string(cluster_size),
                self.cluster_frame,
            )
            cluster_button.clicked.connect(
                lambda _checked=False, cs=cluster_size: self.choose_cluster_color(cs)
            )
            cluster_button.setStyleSheet(
                f"background-color: {color_value.get()}; color: black;"
            )
            cluster_layout.addWidget(cluster_button, i, 0)
            self.cluster_buttons[cluster_size] = cluster_button

            cluster_count_label = QLabel(str(cluster_size_counts[cluster_size]), self.cluster_frame)
            cluster_layout.addWidget(cluster_count_label, i, 1)

            cluster_var = self.cluster_display_status[self.format_cluster_string(
                cluster_size)]
            cluster_checkbox = CheckBoxControl("", cluster_var, self.cluster_frame)
            cluster_checkbox.stateChanged.connect(
                lambda _state, self=self: self.refresh_cluster_options()
            )
            cluster_layout.addWidget(cluster_checkbox, i, 2)
            self.cluster_checkboxes[cluster_size] = cluster_checkbox

            peak_alignment_var = ObservableValue('1')
            peak_alignment_var.trace_add(
                'write', lambda cs=cluster_size: self.validate_peak_alignment(cs)
            )
            self.peak_alignment_vars[cluster_size] = peak_alignment_var
            cluster_layout.addWidget(QLabel("Peak Alignment:", self.cluster_frame), i, 3)
            cluster_layout.addWidget(LineEditControl(peak_alignment_var, self.cluster_frame), i, 4)

        self.cluster_options_created = True

    def save_peak_alignment(self):
        """
        Save an alignment peak index to each cluster in self.cluster_dict.
        The alignment peak index is specified in self.peak_alignment_vars.
        If the specified index exceeds the number of peaks, defaults to the index of the last peak.

        Raises:
            ValueError: If the alignment peak index specified is not a valid integer.
        """
        for (start, end), cluster_data in self.cluster_dict.items():
            peaks = cluster_data['peaks']
            try:
                # -1 because GUI is 1-indexed, but Python is 0-indexed
                alignment_peak_index = int(
                    self.peak_alignment_vars[len(peaks)].get()) - 1
            except ValueError:
                logger.warning(
                    "Invalid alignment index for cluster size %s. Defaulting to the last peak.",
                    len(peaks),
                )
                alignment_peak_index = -1

            # Check if the index is in the valid range
            if alignment_peak_index < 0 or alignment_peak_index >= len(peaks):
                logger.warning(
                    "Out-of-range alignment index for cluster size %s. Defaulting to the last peak.",
                    len(peaks),
                )
                alignment_peak_index = -1

            # Save the alignment peak index
            self.cluster_dict[(start, end)
                              ]['alignment_index'] = alignment_peak_index

    def validate_peak_alignment(self, cluster_size):
        """
        Save an alignment peak index to each cluster in self.cluster_dict.

        The alignment peak index is specified in self.peak_alignment_vars.
        If the specified index exceeds the number of peaks, defaults to the index of the last peak.
        """
        try:
            value = int(self.peak_alignment_vars[cluster_size].get())
            max_value = cluster_size

            if value > max_value:
                self.peak_alignment_vars[cluster_size].set(str(max_value))
        except ValueError:
            self.peak_alignment_vars[cluster_size].set('1')

    def choose_cluster_color(self, cluster_size):
        """
        Choose a color for a cluster of a specified size using a color chooser dialog.

        Parameters:
            cluster_size (int): The size of the cluster for which the color is being chosen.
        """
        color = QColorDialog.getColor(parent=self)
        if color.isValid():
            color_name = color.name()
            self.cluster_colors[cluster_size].set(color_name)
            self.cluster_buttons[cluster_size].setStyleSheet(
                f"background-color: {color_name}; color: black;"
            )

    def select_all_clusters(self):
        """Function to select all clusters."""
        for cluster_size, checkbox in self.cluster_checkboxes.items():
            checkbox.select()
            self.cluster_display_status[self.format_cluster_string(
                cluster_size)].set(1)
        self.refresh_cluster_options()

    def deselect_all_clusters(self):
        """Function to deselect all clusters."""
        for cluster_size, checkbox in self.cluster_checkboxes.items():
            checkbox.deselect()
            self.cluster_display_status[self.format_cluster_string(
                cluster_size)].set(0)
        self.refresh_cluster_options()

    def refresh_cluster_options(self):
        """Refresh the cluster options"""
        for cluster_size in self.cluster_boxes:
            if not self.cluster_display_status[cluster_size].get():
                for box in self.cluster_boxes[cluster_size]:
                    box.set_visible(False)
            else:
                for box in self.cluster_boxes[cluster_size]:
                    box.set_visible(True)

        self.figure_canvas.draw_idle()

    def detect_peaks_with_optimal_prominence(self, data_column, min_distance=150):
        """
        Detect peaks in the data using an optimal prominence threshold.

        Parameters:
            data_column (pd.Series or np.ndarray): The data column in which peaks are to be detected.
            prominence_threshold (float, optional): The prominence threshold for peak detection (default is 0.70).
            min_distance (int, optional): The minimum distance between peaks (default is 150).
            height_threshold (float, optional): The minimum height threshold for peak detection.

        Returns:
            np.ndarray: An array containing the indices of the detected peaks.
        """

        if isinstance(data_column, pd.Series):
            data_column = data_column.values

        data_column = np.asarray(data_column, dtype=float)
        if data_column.size == 0 or np.all(np.isnan(data_column)):
            return np.array([], dtype=int)

        amp = np.nanpercentile(data_column, 99.9)
        threshold = 0.3 * amp
        prominence = 0.35 * amp

        peaks, _ = find_peaks(
            data_column, prominence=prominence, height=threshold, distance=min_distance)

        return peaks

    def detect_sub_threshold_peaks(self, data_column, min_distance=150):
        """
        Detect sub-threshold peaks in the data that are between 20% and 30% of the maximum value.

        Parameters:
            data_column (pd.Series or np.ndarray): The data column in which sub-threshold peaks are to be detected.
            min_distance (int, optional): The minimum distance between peaks (default is 150).

        Returns:
            np.ndarray: An array containing the indices of the detected sub-threshold peaks.
        """

        # TODO add this to the photometry output?

        if isinstance(data_column, pd.Series):
            data_column = data_column.values

        max_value = data_column.max()
        lower_threshold = 0.2 * max_value
        upper_threshold = 0.3 * max_value

        peaks, properties = find_peaks(
            data_column, height=lower_threshold, distance=min_distance)

        sub_threshold_peaks = peaks[(properties['peak_heights'] >= lower_threshold) & (
            properties['peak_heights'] < upper_threshold)]

        return sub_threshold_peaks

    def identify_clusters(
        self,
        time_column,
        data_column,
        peak_indices,
        baseline_reference_column=None,
    ):
        return _identify_clusters(
            time_column,
            data_column,
            peak_indices,
            self.view_state.baseline_multiplier,
            self.view_state.adjust_clustering,
            baseline_reference_column=baseline_reference_column,
        )

    def reset_clusters_based_on_user_input(self):
        """Reset clusters or stimulations based on user input."""
        if self.data_type == 'photometry':
            self.reset_photometry_data()
        elif self.data_type == 'optogenetics':
            self.reset_opto_data()

    def reset_photometry_data(self):
        """Reset and visualize photometry data based on user input."""
        time_column, data_column, detected_peaks, clusters_final, grouped_clusters = self.get_current_photometry_data()

        self.time_column = time_column
        self.data_column = data_column
        self.detected_peaks = detected_peaks
        self.clusters_final = clusters_final
        self.grouped_clusters = grouped_clusters

        self.visualize_photometry_data_with_overlays(self.time_column, self.data_column, self.detected_peaks, self.clusters_final, self.graph_canvas, self.temp_data,
                                                     self.act_data, show_nighttime=True) if self.act_data is not None and self.temp_data is not None else self.visualize_photometry_data_with_overlays(
            self.time_column, self.data_column, self.detected_peaks, self.clusters_final, self.graph_canvas)

        self.mean_cluster_data = {}
        self.populate_data_dict(replace_existing=True)
        self.populate_table()
        self.populate_static_input_dropdown()
        if self.act_data is not None and self.temp_data is not None:
            self.annotate_clusters_with_time_period()
            self.precompute_all_clusters()

        self.adjusted = True
        self.settings_manager.save_variables()

    def reset_opto_data(self):
        """Reset and visualize optogenetic data based on user input."""
        self.associated_file_locator.handle_opto_data_file()

        self.visualize_opto_data_with_overlays(show_nighttime=True)

        self.mean_cluster_data = {}
        self.static_settings_store.populate_data_dict(replace_existing=True)
        self.cluster_table_panel.populate_table()
        self.populate_static_input_dropdown()

        self.adjusted = True
        self.settings_manager.save_variables()

    def group_clusters_by_peak_count(self, cluster_dict):
        """
        Group clusters based on the number of peaks they contain.

        Parameters:
        - cluster_dict (dict): A dictionary where keys are clusters and values are lists of peak times within each cluster.

        Returns:
        - grouped_clusters (dict): A dictionary where keys are the number of peaks and values are lists of clusters (and their peak times)
        that have that number of peaks.
        """
        grouped_clusters = {}

        for cluster, peak_times in cluster_dict.items():
            num_peaks = len(peak_times)
            if num_peaks not in grouped_clusters:
                grouped_clusters[num_peaks] = []
            grouped_clusters[num_peaks].append((cluster, peak_times))

        return grouped_clusters

    def custom_date_parser(self, date_str):
        return self.plot_service.custom_date_parser(date_str)

    def calculate_nighttime_period(self):
        self.plot_service.calculate_nighttime_period()

    def add_nighttime_shading_to_plot(self, ax, time_column):
        self.plot_service.add_nighttime_shading_to_plot(ax, time_column)

    def overlay_temp_and_act(self):
        return self.plot_service.overlay_temp_and_act()

    def visualize_opto_data_with_overlays(self, show_nighttime=False):
        self.plot_service.visualize_opto_data_with_overlays(show_nighttime)

    def redraw_graph(self):
        self.plot_service.redraw_graph()

    def _get_current_file_path(self) -> str:
        """Return the currently selected main data file path, if any."""
        if self.view_state.file_path:
            return self.view_state.file_path
        if hasattr(self.file_path, "get"):
            return self.file_path.get()
        if self.file_path:
            return self.file_path
        return self.file_path_var.get()

    def visualize_photometry_data_with_overlays(self, time_column, data_column, detected_peaks, clusters, graph_canvas, temp_data=None, act_data=None, show_nighttime=False):
        self.plot_service.visualize_photometry_data_with_overlays(
            time_column,
            data_column,
            detected_peaks,
            clusters,
            graph_canvas,
            temp_data,
            act_data,
            show_nighttime,
        )

    def find_time_column(self, dataframe):
        return self.plot_service.find_time_column(dataframe)

    def overlay_temp_on_figure(self, ax, trimmed_temp_df, sem_temp_data=None, left_axis=True):
        return self.plot_service.overlay_temp_on_figure(
            ax, trimmed_temp_df, sem_temp_data, left_axis
        )
    def mean_of_top_five(self, data_column):
        return self.plot_service.mean_of_top_five(data_column)

    def overlay_act_on_figure(self, ax, act_data, ymin_photometry, ymax_photometry, sem_act_data=None):
        return self.plot_service.overlay_act_on_figure(
            ax, act_data, ymin_photometry, ymax_photometry, sem_act_data
        )

    def calculate_dynamic_bins(self, n, b_ref=600, t_ref=1200, k=5):
        return self.plot_service.calculate_dynamic_bins(n, b_ref, t_ref, k)

    def get_single_cluster_data(self, cluster_dropdown_value, pre_time=0.0, post_time=0.0):
        return self.plot_service.get_single_cluster_data(
            cluster_dropdown_value, pre_time, post_time
        )

    def visualize_single_cluster(self, cluster_dropdown_value):
        self.display_presenter.visualize_single_cluster(
            cluster_dropdown_value
        )

    def extract_and_trim_data(self, dataframe, previous_time, offset, duration, sample_rate, data_type):
        return self.plot_service.extract_and_trim_data(
            dataframe, previous_time, offset, duration, sample_rate, data_type
        )

    def extract_data_for_date_and_offset(
        self,
        file_path,
        sheet_name,
        target_date,
        target_time,
        duration=None,
        selected_alignment_datetime=None,
    ):
        return self.plot_service.extract_data_for_date_and_offset(
            file_path,
            sheet_name,
            target_date,
            target_time,
            duration,
            selected_alignment_datetime,
        )

    def extract_data_with_buffer(self, dataframe, previous_time, offset, duration, sample_rate):
        return self.plot_service.extract_data_with_buffer(
            dataframe, previous_time, offset, duration, sample_rate
        )

    def upsample_data(self, dataframe):
        return self.plot_service.upsample_data(dataframe)

    def change_associated_temp_file(self):
        """Change the associated temperature file."""
        current_file_path = self._get_current_file_path()
        initial_dir = os.path.dirname(current_file_path) if current_file_path else ""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select file",
            initial_dir,
            "csv and Excel files (*.csv *.xlsx)",
        )

        if file_path:
            file_name = os.path.basename(file_path)
            self.associated_temp_data_entry.set(file_name)
            self.temp_file_path = file_path

    def change_associated_act_file(self):
        """Change the associated activity file."""
        current_file_path = self._get_current_file_path()
        initial_dir = os.path.dirname(current_file_path) if current_file_path else ""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select file",
            initial_dir,
            "csv and Excel files (*.csv *.xlsx)",
        )

        if file_path:
            file_name = os.path.basename(file_path)
            self.associated_act_data_entry.set(file_name)
            self.act_file_path = file_path

    def select_column_names(self):
        pass

    def select_behaviour_file(self):
        pass

    def data_dict_to_df(self, data_dict):
        """
        Convert data_dict to DataFrame.

        Parameters:
        - data_dict (dict): Dictionary containing the data.

        Returns:
        - pd.DataFrame: DataFrame containing the data from the dictionary.
        """
        rows = []
        for file_name, clusters in data_dict.items():
            for cluster_name, cluster_data in clusters.items():
                row = cluster_data.copy()
                row['Cluster Name'] = cluster_name
                rows.append(row)
        return pd.DataFrame(rows)

    def clear_table(self):
        """Clear and cache the table."""
        self.table_data.clear()
        self.duration_data_cache = {}

    def select_folder_for_telemetry_data(self, date):
        return self.associated_file_locator.select_folder_for_telemetry_data(date)

    def common_setup(self, file_path_var, dataframe, mouse_name):
        self.associated_file_locator.common_setup(file_path_var, dataframe, mouse_name)

    def process_opto_data_file(self):
        """
        Process the optogenetic data file.
        """
        self.data_type = 'optogenetics'
        self.associated_file_locator.handle_opto_data_file()

        self.selected_display.set("Full Trace Display")

    def update_column_headings(self):
        """Update the column headings based on the current data type."""
        columns = ['file_name', 'number_of_peaks', 'pre_cluster_time',
                   'post_cluster_time', 'bin_size', 'start_time', 'end_time']
        if self.data_type == 'optogenetics':
            column_headings = {
                'number_of_peaks': 'Number of stims',
                'pre_cluster_time': 'Pre-stim time',
                'post_cluster_time': 'Post-stim time'
            }
        else:
            column_headings = {
                'number_of_peaks': 'Number of peaks',
                'pre_cluster_time': 'Pre-cluster time',
                'post_cluster_time': 'Post-cluster time'
            }

        for column in columns:
            # Update headings with custom or default text
            heading_text = column_headings.get(
                column, column.capitalize().replace('_', ' '))
            self.table_treeview.heading(column, text=heading_text)

    def process_photometry_data_file(self):
        self.associated_file_locator.process_photometry_data_file()

    def calculate_stim_timings(self, stim_data_df):
        return self.plot_service.calculate_stim_timings(stim_data_df)

    def prepare_figure(self, time_column, show_nighttime=False, show_time_of_day=False):
        return self.plot_service.prepare_figure(
            time_column, show_nighttime, show_time_of_day
        )

    def overlay_data(self, ax, temp_data=None, act_data=None, ymin=None, ymax=None):
        return self.plot_service.overlay_data(ax, temp_data, act_data, ymin, ymax)

    def overlay_opto_stimulations(self, ax):
        self.plot_service.overlay_opto_stimulations(ax)

    def save_static_inputs(self, df):
        self.static_settings_store.save_static_inputs(df)

    def load_static_inputs(self):
        return self.static_settings_store.load_static_inputs()

    def populate_table(self):
        self.cluster_table_panel.populate_table()

    def populate_data_dict(self, replace_existing: bool = False):
        self.static_settings_store.populate_data_dict(replace_existing)

    def populate_photometry_data_dict(self, file_path_str):
        return self.static_settings_store.populate_photometry_data_dict(
            file_path_str
        )

    def populate_opto_data_dict(self, file_path_str):
        return self.static_settings_store.populate_opto_data_dict(file_path_str)

    def update_cluster_inputs(self):
        self.static_settings_store.update_cluster_inputs()

    def time_to_seconds(self, time_input):
        """
        Convert a time input to seconds.

        Parameters:
        - time_input (str or datetime.time): The time input to convert.

        Returns:
        - int: The equivalent time in seconds.

        Raises:
        - ValueError: If the input type is invalid.
        """
        if isinstance(time_input, str):
            h, m, s = map(int, time_input.split(':'))
            return h * 3600 + m * 60 + s
        elif isinstance(time_input, time):
            return time_input.hour * 3600 + time_input.minute * 60 + time_input.second
        else:
            raise ValueError("Invalid input type for time_to_seconds function")

    def find_offset_for_previous_time(self, dataframe, target_time_str):
        return self.plot_service.find_offset_for_previous_time(
            dataframe, target_time_str
        )

    def precalculate_data_versions(self):
        self.plot_service.precalculate_data_versions()

    def get_current_photometry_data(self):
        return self.plot_service.get_current_photometry_data()

    def get_time_scale(self, time_unit):
        """Return scaling factor for *time_unit*, or None for 'time of day'."""
        if time_unit == 'time of day':
            return None
        return _get_time_scale(time_unit)

    def create_photometry_figure(self, ax, time_column, data_column, peak_indices, clusters, show_nighttime=False):
        return self.plot_service.create_photometry_figure(
            ax, time_column, data_column, peak_indices, clusters, show_nighttime
        )

    def is_cluster_in_nighttime(self, cluster_start_minutes):
        """
        Check if a cluster's start time falls within the nighttime periods.

        Parameters:
        - cluster_start_minutes (float): The start time of the cluster in minutes since the start of data collection.

        Returns:
        - bool: True if the cluster start time is within a nighttime period, False otherwise.
        """
        if not self.date or not getattr(self, "nighttime_periods", None):
            return False

        start_time_value = (self.view_state.temp_and_act_start_time or "").strip()
        if not start_time_value:
            return False

        parsed_start_time = pd.to_datetime(
            start_time_value, format='%H:%M:%S', errors="coerce"
        )
        if pd.isna(parsed_start_time):
            return False

        base_date = datetime.strptime(self.date, '%y-%m-%d').date()
        start_time = parsed_start_time.time()

        for night_start_time, night_end_time in self.nighttime_periods:
            night_start_datetime = datetime.combine(
                base_date, night_start_time)
            night_end_datetime = datetime.combine(base_date, night_end_time)

            if night_end_time < night_start_time:
                night_end_datetime += timedelta(days=1)

            night_start_minutes = (
                night_start_datetime - datetime.combine(base_date, start_time)).total_seconds() / 60
            night_end_minutes = (
                night_end_datetime - datetime.combine(base_date, start_time)).total_seconds() / 60

            if night_start_minutes <= cluster_start_minutes <= night_end_minutes:
                return True
        return False

    def format_cluster_string(self, burst_count):
        """
        Format the cluster string based on the burst count.

        Parameters:
        - burst_count (int): The number of peaks in the cluster.

        Returns:
        - str: Formatted cluster string.
        """
        if burst_count == 1:
            return "Clusters with 1 Peak"
        else:
            return f"Clusters with {burst_count} Peaks"

    def embed_figure_in_canvas(self, fig, graph_canvas):
        if hasattr(self, "current_fig"):
            plt.close(self.current_fig)

        self.current_fig = fig
        self.figure_canvas, self.toolbar = embed_figure_in_qt(fig, graph_canvas)

    def delete_current_figure(self):
        """Delete the current figure from the canvas."""
        if self.current_fig is not None:
            plt.close(self.current_fig)
            self.current_fig = None
        destroy_embedded_figure(self.figure_canvas, self.toolbar)
        self.figure_canvas = None
        self.toolbar = None

    def prepare_for_unload(self) -> bool:
        export_options = getattr(self, "export_options_container", None)
        if export_options is not None:
            export_options.prepare_for_unload()
        self.delete_current_figure()
        return True

    def closeEvent(self, event) -> None:  # pragma: no cover - Qt lifecycle
        self.prepare_for_unload()
        super().closeEvent(event)

    def save_and_close_label_settings(self, popup):
        self.label_settings_dialog.save_and_close_label_settings(popup)

    def extract_date_and_mouse_number(self, file_path_var, mouse_name):
        return self.associated_file_locator.extract_date_and_mouse_number(
            file_path_var, mouse_name
        )

    def retrieve_associated_files(self, date, file_path_var):
        return self.associated_file_locator.retrieve_associated_files(
            date, file_path_var
        )

    def refresh_graph_display(self):
        self.redraw_graph()

    def update_duration_box(self):
        self.redraw_graph()

    def handle_behaviour_change(self, *args, **kwargs):
        self.redraw_graph()

    def update_box_colors_and_behaviour_options(self, behaviour, color_rgb):
        self.redraw_graph()

    def save_and_close(self, popup=None, close=True):
        if not hasattr(self, "current_fig") or self.current_fig is None:
            if close and popup:
                if hasattr(popup, "accept"):
                    popup.accept()
                else:
                    popup.close()
            return

        ax = self.current_fig.axes[0]
        x_min = self.graph_settings_container_instance.x_axis_min_var.get()
        x_max = self.graph_settings_container_instance.x_axis_max_var.get()
        y_min = self.graph_settings_container_instance.y_axis_min_var.get()
        y_max = self.graph_settings_container_instance.y_axis_max_var.get()

        if self.graph_settings_container_instance.limit_axis_range_var.get():
            if x_min and x_max:
                ax.set_xlim(float(x_min), float(x_max))
            if y_min and y_max:
                ax.set_ylim(float(y_min), float(y_max))
        else:
            self.redraw_graph()
            ax = self.current_fig.axes[0]

        if self.figure_canvas is not None:
            self.figure_canvas.draw()
        self.settings_manager.save_variables()

        if close and popup:
            if hasattr(popup, "accept"):
                popup.accept()
            else:
                popup.close()

    def populate_raw_data_sheet(self, writer, sheet_name, cluster_number):
        self.workbook_exporter.populate_raw_data_sheet(
            writer, sheet_name, cluster_number
        )

    def add_home_hyperlink(self, worksheet, writer, col_idx, row_idx):
        self.workbook_exporter.add_home_hyperlink(
            worksheet, writer, col_idx, row_idx
        )

    def write_raw_data_to_sheet(self, worksheet, writer, row_idx, col_idx, period, data_type, data):
        return self.workbook_exporter.write_raw_data_to_sheet(
            worksheet, writer, row_idx, col_idx, period, data_type, data
        )

    def add_navigation_hyperlink(self, worksheet, writer, period, row_idx, col_idx):
        self.workbook_exporter.add_navigation_hyperlink(
            worksheet, writer, period, row_idx, col_idx
        )

    def populate_cluster_sheet(self, writer, sheet_name, cluster_number):
        self.workbook_exporter.populate_cluster_sheet(
            writer, sheet_name, cluster_number
        )

    def generate_cluster_headings(self, file_data, cluster_number):
        return _generate_cluster_headings(file_data, cluster_number, self.data_type)

    def generate_cluster_headings_from_list(self, cluster_list):
        """
        Generate cluster headings from a list of clusters.

        Parameters:
        - cluster_list (list): List of clusters, each represented as a dictionary.

        Returns:
        - cluster_headings (list): List of cluster headings.
        """
        cluster_headings = ['Cluster ID'] + [cluster['name']
                                             for cluster in cluster_list]
        return cluster_headings

    def write_cluster_details(self, worksheet, cluster_number, file_data, cluster_dict):
        self.workbook_exporter.write_cluster_details(
            worksheet, cluster_number, file_data, cluster_dict
        )

    def write_cluster_data_to_worksheet(self, worksheet, clusters, row_idx_for_basic_data, col_idx, rows_to_skip, initial_row_idx_for_peak_data, cluster_number):
        return self.workbook_exporter.write_cluster_data_to_worksheet(
            worksheet,
            clusters,
            row_idx_for_basic_data,
            col_idx,
            rows_to_skip,
            initial_row_idx_for_peak_data,
            cluster_number,
        )

    def write_vertical_headings(self, worksheet, row_idx, headings):
        return self.workbook_exporter.write_vertical_headings(
            worksheet, row_idx, headings
        )

    def write_headings(self, worksheet, row_idx, cluster_headings, headings, rows_to_skip):
        return self.workbook_exporter.write_headings(
            worksheet, row_idx, cluster_headings, headings, rows_to_skip
        )

    def write_cluster_data_in_columns(self, worksheet, row_idx, col_idx, data_list):
        return self.workbook_exporter.write_cluster_data_in_columns(
            worksheet, row_idx, col_idx, data_list
        )

    def write_peak_data_in_columns(self, worksheet, row_idx, col_idx, data_list, row_idx_for_basic_data, rows_to_skip):
        return self.workbook_exporter.write_peak_data_in_columns(
            worksheet, row_idx, col_idx, data_list, row_idx_for_basic_data, rows_to_skip
        )

    def write_cluster_static_inputs(self, worksheet, row_idx, col_idx, cluster_number, file_data):
        return self.workbook_exporter.write_cluster_static_inputs(
            worksheet, row_idx, col_idx, cluster_number, file_data
        )

    def extract_button_click_handler(self):
        try:
            return self._extract_button_click_handler()
        except Exception as exc:
            show_action_error(
                "Telemetry export failed",
                "NeuroSyncApp could not export the telemetry analysis",
                exc,
                self,
                "Check that data have been loaded and clustered, close any existing output workbook, and try again.",
            )
            return None

    def _extract_button_click_handler(self):
        """
        Handle the extract button click event, perform data binning, and save the data to an Excel file.

        Parameters:
        - file_path_var: Variable containing the file path.
        """
        if self.export_options_container.use_binned_data_var.get() == 1:
            self.ensure_all_mean_cluster_data()
            self.bin_all_cluster_data()
            file_path = self._get_current_file_path()
            original_file_name = os.path.splitext(
                os.path.basename(file_path))[0]
            folder_path = os.path.join(os.path.dirname(file_path), os.path.splitext(
                os.path.basename(file_path))[0] + "_MRP_Script")
            os.makedirs(folder_path, exist_ok=True)

            selected_column_name = self.data_selection_frame.selected_column_var.get()
            original_file_name += f"_{selected_column_name}"

            output_file_path = os.path.join(
                folder_path, f"{original_file_name}.xlsx")

            try:
                with pd.ExcelWriter(output_file_path, engine='xlsxwriter') as writer:
                    self.workbook_exporter.create_sheets_for_clusters(writer)
            except PermissionError as exc:
                show_action_error(
                    "Telemetry export file is unavailable",
                    "NeuroSyncApp could not write the telemetry workbook",
                    exc,
                    self,
                    "Close the existing workbook in Excel and try the export again.",
                )
                return

            logger.info("Telemetry export created at %s", output_file_path)

    def set_variable_column_widths(self, worksheet):
        """
        Set variable column widths for specified columns.

        Parameters:
        - worksheet (xlsxwriter.worksheet.Worksheet): The worksheet instance to set column widths for.
        """
        worksheet.set_column(0, 4, 15)
        worksheet.set_column(5, 5, 5)
        worksheet.set_column(6, 6, 27)
        worksheet.set_column(7, 14, 28)

    def bin_all_cluster_data(self):
        """Bin all mean-cluster data using the persisted per-cluster bin sizes."""
        self.ensure_all_mean_cluster_data()
        file_data = list(self.data_dict.values())[0]
        _apply_cluster_binning(self.mean_cluster_data, file_data)

    def compute_photometry_mean(self, photometry_data_list):
        return _compute_photometry_mean(photometry_data_list)

    def bin_data_dynamic(self, data, bin_size_sec):
        return _bin_data_dynamic(data, bin_size_sec)

    def float_range(self, start, stop, step):
        """
        Generate a range of floating-point numbers.

        Parameters:
        start (float): The starting value.
        stop (float): The end value.
        step (float): The step size.

        Yields:
        float: The next value in the range.
        """
        while start < stop:
            yield start
            start += step

    def generate_bin_axis(self, pre_time, post_time, bin_size):
        """
        Generate the bin axis (labels) based on pre-time, post-time, and bin size.

        Parameters:
        - pre_time (float): Pre-time (negative value).
        - post_time (float): Post-time (positive value).
        - bin_size (int): Size of each bin.

        Returns:
        - bin_labels (list): List of bin labels.
        """
        bin_ranges = np.linspace(pre_time, post_time, int(
            (pre_time + post_time) / bin_size), endpoint=False)
        bin_labels = [f'{start} - {start + bin_size}' for start in bin_ranges]
        return bin_labels

    def save_image(self):
        try:
            return self._save_image()
        except Exception as exc:
            show_action_error(
                "Image could not be saved",
                "NeuroSyncApp could not save the current telemetry plot",
                exc,
                self,
                "Check the image settings and output-folder permissions, then try again.",
            )
            return None

    def _save_image(self):
        """Saves the current figure to a file, applying user-defined font and label settings."""
        current_xlabel = self.fig.axes[0].get_xlabel()
        current_ylabel = self.fig.axes[0].get_ylabel()
        fig_copy = copy.deepcopy(self.fig)
        request = build_image_export_request(
            self.export_options_container.height_entry.get().strip(),
            self.export_options_container.width_entry.get().strip(),
            self.export_options_container.image_format_combobox.get(),
            self.export_options_container.dpi_entry.get().strip(),
            self.selected_display.get() if hasattr(self, "selected_display") else "",
            self.static_inputs_frame.selected_behaviour.get()
            if hasattr(self, "static_inputs_frame")
            else "",
        )

        if request.axis_width_cm is not None and request.axis_height_cm is not None:
            apply_figure_size_and_fonts(
                fig_copy,
                request.axis_width_cm,
                request.axis_height_cm,
                self.export_options_container.font_settings,
                current_xlabel,
                current_ylabel,
            )

        file_path = self._get_current_file_path()
        output_path = build_save_path(
            file_path,
            self.mouse_name,
            request.figure_display,
            request.behaviour_choice,
            request.image_format,
        )
        save_figure(fig_copy, output_path, request.image_format, request.dpi)

