import tkinter as tk
from tkinter import ttk, filedialog, simpledialog
from tkinter import messagebox
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
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from tkinter import colorchooser
from datetime import datetime, time, timedelta

from src.gui.views.behaviour_event_input_frame import BehaviourInputFrame
from src.gui.views.data_selection_frame_legacy import DataSelectionFrame
from src.gui.views.graph_settings_container import GraphSettingsContainer
from src.gui.views.static_inputs_frame import StaticInputsFrame
from src.gui.views.export_options_container import ExportOptionsContainer
from src.gui.shared.tk_styles import define_custom_ttk_styles
from src.core.app_state import TelemetryViewState
from src.core.app_settings_manager import AppSettingsManager
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
    process_cluster_window as _process_cluster_window,
    process_data_for_clusters as _process_data_for_clusters,
    select_stim_clusters as _select_stim_clusters,
)
from src.processing.telemetry_processing import (
    apply_cluster_binning as _apply_cluster_binning,
    get_universal_times as _get_universal_times,
    align_and_concatenate_data as _align_and_concatenate_data,
    calculate_mean_and_sem as _calculate_mean_and_sem,
    compute_photometry_mean as _compute_photometry_mean,
    bin_data_dynamic as _bin_data_dynamic,
    create_universal_time_axis as _create_universal_time_axis,
    process_photometry_data as _process_photometry_data,
    trim_data_to_minimum_length as _trim_data_to_minimum_length,
)
from src.processing.image_export import build_image_export_request
from src.excel_ops.telemetry_exporter import (
    generate_cluster_headings as _generate_cluster_headings,
)
from src.gui.controllers.telemetry_table_controller import TelemetryTableController
from src.gui.controllers.telemetry_display_controller import TelemetryDisplayController
from src.gui.controllers.telemetry_file_controller import TelemetryFileController
from src.gui.controllers.telemetry_settings_controller import TelemetrySettingsController
from src.gui.controllers.telemetry_label_settings_controller import TelemetryLabelSettingsController
from src.gui.controllers.telemetry_excel_controller import TelemetryExcelController
from src.gui.controllers.telemetry_plot_controller import TelemetryPlotController
from src.gui.controllers.telemetry_cluster_controller import TelemetryClusterController

logger = logging.getLogger(__name__)


class TelemetryPhotomOptoProcessingApp(ttk.Frame):
    CONTROLLER_TYPES = {
        "telemetry_table_controller": TelemetryTableController,
        "telemetry_display_controller": TelemetryDisplayController,
        "telemetry_file_controller": TelemetryFileController,
        "telemetry_settings_controller": TelemetrySettingsController,
        "telemetry_label_settings_controller": TelemetryLabelSettingsController,
        "telemetry_excel_controller": TelemetryExcelController,
        "telemetry_plot_controller": TelemetryPlotController,
        "telemetry_cluster_controller": TelemetryClusterController,
    }

    def __init__(self, parent, **kwargs):
        """
        Initialize the application.

        Parameters:
        - parent: The parent widget.
        - **kwargs: Additional keyword arguments.
        """
        self.settings_manager = AppSettingsManager(
            app_type="telemetry_photom_opto")
        self.app_name = "telemetry_photom_opto"

        super().__init__(parent, style='Bordered.TFrame', **kwargs)
        self.initialize_attributes(parent)

        self.configure_main_frames()
        self.configure_notebooks()
        self.configure_tabs()
        self.create_widgets()

    def initialize_attributes(self, parent):
        """Initialize shared state, Tk variables, controller instances, and styles."""
        self.parent = parent
        define_custom_ttk_styles()
        self._initialize_state()
        self._initialize_tk_variables()
        self._initialize_controllers()
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
                "seconds_removed": 0,
                "figure_cache": {},
                "act_file_path": None,
                "temp_file_path": None,
                "file_path": None,
            },
        )

    def _bind_state_var(self, tk_var, state_field):
        tk_var.set(getattr(self.view_state, state_field))
        tk_var.trace_add(
            "write", lambda *_: setattr(self.view_state, state_field, tk_var.get())
        )

    def _set_state_var(self, tk_var, state_field, value):
        setattr(self.view_state, state_field, value)
        if tk_var.get() != value:
            tk_var.set(value)

    def _initialize_tk_variables(self):
        self.file_path_var = tk.StringVar()
        self.adjust_clustering_var = tk.StringVar()
        self.associated_temp_data_entry = tk.StringVar()
        self.associated_act_data_entry = tk.StringVar()
        self.light_off_time_var = tk.StringVar()
        self.temp_and_act_start_time_var = tk.StringVar()
        self.label_color_var = tk.StringVar()
        self.label_symbol_var = tk.StringVar()
        self.label_size_var = tk.StringVar()
        self.y_offset_peak_symbol = tk.StringVar()
        self.peak_count_color_var = tk.StringVar()
        self.peak_count_size_var = tk.StringVar()
        self.y_for_peak_count = tk.StringVar()
        self.baseline_multiplier = tk.StringVar()
        self.baseline_color = tk.StringVar()
        self.baseline_style = tk.StringVar()
        self.baseline_thickness = tk.StringVar()
        self.cluster_box_height_modifier = tk.StringVar()
        self.cluster_box_color = tk.StringVar()
        self.cluster_box_alpha = tk.StringVar()
        self.telemetry_folder_path = tk.StringVar()
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

    def _initialize_controllers(self):
        for attribute, controller_type in self.CONTROLLER_TYPES.items():
            setattr(self, attribute, controller_type(self))

    def _load_settings_into_variables(self):
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
        """Configure the main frames within the application."""
        self.top_frame = ttk.Frame(
            self, relief="groove", borderwidth=2, style="CustomFrame.TFrame")
        self.top_frame.grid(row=0, column=0, sticky="nsew")
        self.top_frame.grid_columnconfigure(0, weight=1)
        self.top_frame.grid_columnconfigure(1, weight=1)
        self.top_frame.grid_columnconfigure(2, weight=1)

        self.bottom_frame = ttk.Frame(
            self, relief="groove", borderwidth=2, style="CustomFrame.TFrame")
        self.bottom_frame.grid(row=1, column=0, sticky="nsew")
        self.bottom_frame.grid_rowconfigure(1, weight=1)
        self.bottom_frame.grid_columnconfigure(0, weight=1)

    def configure_notebooks(self):
        """Configure the notebooks for graphs and settings."""
        self.notebook_graphs = ttk.Notebook(
            self.bottom_frame, style="CustomNotebook.TNotebook", width=780)
        self.notebook_graphs.grid(
            row=1, column=0, columnspan=2, padx=10, sticky=tk.NSEW)

        self.notebook_settings = ttk.Notebook(
            self.bottom_frame, style="CustomNotebook.TNotebook", height=520, width=540)
        self.notebook_settings.grid(row=1, column=3, padx=10, sticky=tk.NSEW)

        self.graph_settings_tab = ttk.Frame(self.notebook_settings)
        self.export_options_tab = ttk.Frame(self.notebook_settings)

        self.notebook_settings.add(
            self.graph_settings_tab, text="Graph Settings")
        self.notebook_settings.add(
            self.export_options_tab, text="Export Options")

        self.notebook_settings.columnconfigure(0, weight=1)

    def configure_tabs(self):
        """ Initialize and configure the tabs for graph settings, export options, graph display, and table display."""
        self.graph_settings_container_instance = GraphSettingsContainer(
            self.graph_settings_tab,
            widgets_to_include=[
                'photometry_settings',
                'temperature_settings',
                'activity_settings',
                'remove_first_60_minutes',
                'number_of_minor_ticks',
                'graph_time_labels',
                'axis_range',
            ],
            app_name=self.app_name,
            settings_manager=self.settings_manager,
            refresh_graph_display_callback=self.refresh_graph_display,
            update_duration_box_callback=self.update_duration_box,
            handle_behaviour_change_callback=self.handle_behaviour_change,
            load_variables_callback=self.settings_manager.load_variables,
            create_behaviour_options_callback=self.create_cluster_options,
            update_box_colors_callback=self.update_box_colors_and_behaviour_options,
            save_and_close_axis_callback=self.save_and_close,
            redraw_graph_callback=self.redraw_graph,
        )

        self.graph_settings_container_instance.y_gridlines_label.grid_forget()
        self.graph_settings_container_instance.y_gridlines_entry.grid_forget()

        curr_row, curr_col = self.graph_settings_container_instance.update_button.grid_info()['row'], \
            self.graph_settings_container_instance.update_button.grid_info()[
            'column']

        self.graph_settings_container_instance.update_button.grid(
            row=curr_row + 1, column=curr_col - 1)

        self.export_options_container = ExportOptionsContainer(
            self.export_options_tab,
            file_path_var=self.file_path_var,
            settings_manager=self.settings_manager,
            extract_button_click_handler=self.extract_button_click_handler,
            save_image=self.save_image
        )

        self.graph_settings_container_instance.complete_initialization()

        self.graph_settings_tab.grid_rowconfigure(0, weight=1)
        self.graph_settings_tab.grid_columnconfigure(0, weight=1)
        self.export_options_tab.grid_rowconfigure(0, weight=1)
        self.export_options_tab.grid_columnconfigure(0, weight=1)

        self.graph_tab = ttk.Frame(self.notebook_graphs)
        self.table_tab = ttk.Frame(self.notebook_graphs)

        self.notebook_graphs.add(self.graph_tab, text="Graph")
        self.notebook_graphs.add(self.table_tab, text="Table")

        self.create_graphs_container(self.graph_tab)
        self.create_table_container(self.table_tab)

        self.graph_tab.grid_rowconfigure(0, weight=1)
        self.graph_tab.grid_columnconfigure(0, weight=1)
        self.table_tab.grid_rowconfigure(0, weight=1)
        self.table_tab.grid_columnconfigure(0, weight=1)

    def create_table_container(self, frame):
        self.telemetry_table_controller.create_table_container(frame)

    def treeview_sort_column(self, tv, col, reverse):
        self.telemetry_table_controller.treeview_sort_column(tv, col, reverse)

    def create_graphs_container(self, frame):
        self.telemetry_display_controller.create_graphs_container(frame)

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
        self.telemetry_display_controller.on_cluster_selection_changed(event)

    def compute_data_for_cluster(self, selected_peak_count, changed_static_inputs=None):
        self.telemetry_cluster_controller.compute_data_for_cluster(
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
        self.telemetry_cluster_controller.precompute_all_clusters(updated_clusters)

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
        self.telemetry_display_controller.visualize_mean_cluster(selected_cluster_string)

    def display_no_data_figure(self):
        self.telemetry_display_controller.display_no_data_figure()

    def find_longest_times(self, cluster_number):
        return self.telemetry_cluster_controller.find_longest_times(cluster_number)

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
        if isinstance(timestamps[0], datetime):
            times = [timestamp.time() for timestamp in timestamps]

            # Calculate differences in seconds between successive timestamps
            time_diffs = [
                self.time_to_seconds(times[i + 1]) -
                self.time_to_seconds(times[i])
                for i in range(len(times) - 1)
            ]
        else:
            time_diffs = [
                timestamps[i + 1] - timestamps[i]
                for i in range(len(timestamps) - 1)
            ]

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

    def process_cluster_data(self, cluster_data, longest_pre_peak, longest_post_peak, is_stim=False):
        return _process_cluster_window(
            cluster_data,
            longest_pre_peak,
            longest_post_peak,
            self.extended_temp_data,
            self.extended_act_data,
            is_stim=is_stim,
        )

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

    def extract_and_prepare_temp_and_act_data(self, longest_pre_peak, longest_post_peak, cluster_number):
        return self.telemetry_cluster_controller.extract_and_prepare_temp_and_act_data(
            longest_pre_peak, longest_post_peak, cluster_number
        )

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

    def get_universal_times(self, peak_time, longest_pre_peak, longest_post_peak):
        return _get_universal_times(peak_time, longest_pre_peak, longest_post_peak)

    def align_and_concatenate_data(self, all_data, universal_time_axis):
        return _align_and_concatenate_data(all_data, universal_time_axis)

    def extract_and_prepare_photometry_data(self, longest_pre_peak, longest_post_peak, cluster_number):
        return self.telemetry_cluster_controller.extract_and_prepare_photometry_data(
            longest_pre_peak, longest_post_peak, cluster_number
        )

    def process_photometry_data(self, truncated_data):
        return _process_photometry_data(truncated_data)

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
        time_factor = self.get_time_scale(time_unit)
        show_time_of_day = (time_unit == 'time of day')

        if self.selected_display.get() != 'Full Trace Display' and show_time_of_day:
            time_factor = self.get_time_scale("minutes")

        if not show_time_of_day and time_factor is not None:
            return pd.Series([time * time_factor for time in time_column])
        else:
            return pd.Series(time_column)

    def plot_mean_cluster(self, mean_temp_data, mean_act_data, photometry_cluster_data_df, cluster_count=None):
        self.telemetry_display_controller.plot_mean_cluster(
            mean_temp_data, mean_act_data, photometry_cluster_data_df, cluster_count
        )

    def add_stims_to_plot(self, ax, cluster_count):
        self.telemetry_display_controller.add_stims_to_plot(ax, cluster_count)

    def populate_static_input_dropdown(self):
        """Populate the dropdown menu for cluster or stimulation selection based on the data type."""
        if self.data_type == 'photometry':
            peak_counts = self.get_peak_counts()
            peak_counts.append("All Clusters")
        elif self.data_type == 'optogenetics':
            stim_counts = self.get_stim_counts()
            stim_counts.append("All Stims")

        menu = self.static_inputs_frame.behaviour_dropdown["menu"]
        menu.delete(0, "end")

        options = peak_counts if self.data_type == 'photometry' else stim_counts

        for option in options:
            menu.add_command(label=option, command=tk._setit(
                self.static_inputs_frame.selected_behaviour, option))

        if options:
            self.static_inputs_frame.selected_behaviour.set(
                options[0])

        self.static_inputs_frame.behaviour_dropdown.configure(
            state=tk.NORMAL if options else tk.DISABLED)

    def create_widgets(self):
        """Creates and configures various widgets for the GUI, including data selection frames, buttons, labels, and entry fields."""
        self.data_selection_frame = DataSelectionFrame(
            self.top_frame,
            settings_manager=self.settings_manager,
            new_data_file_callback=self.telemetry_file_controller.handle_new_data_file,
        )
        self.data_selection_frame.grid(
            row=0, column=0, padx=5, pady=5, sticky=tk.NSEW)

        self.behaviour_input_frame = BehaviourInputFrame(
            self.top_frame,
            select_column_names_callback=self.select_column_names,
            select_event_file_callback=self.select_behaviour_file,
        )
        self.behaviour_input_frame.grid(
            row=0, column=1, padx=5, pady=5, sticky=tk.NSEW)

        self.behaviour_input_frame.behaviour_input_label.config(
            text="Change Associated Files and Align Time")
        self.behaviour_input_frame.behaviour_input_label.grid(
            row=0, column=0, columnspan=5, padx=10, pady=(10, 5))

        self.behaviour_input_frame.column_names_button.grid_forget()
        self.behaviour_input_frame.import_behaviour_button.grid_forget()
        self.behaviour_input_frame.behaviour_coding_frame.grid_forget()

        self.temp_file_name_label = tk.Entry(self.behaviour_input_frame, width=15, font=('Helvetica', 10), fg='black', bg='snow',
                                             state='readonly', textvariable=self.associated_temp_data_entry)
        self.temp_file_name_label.grid(row=1, column=1, padx=5, pady=(10, 5))

        self.activity_file_name_label = tk.Entry(self.behaviour_input_frame, width=15, font=('Helvetica', 10), fg='black', bg='snow',
                                                 state='readonly', textvariable=self.associated_act_data_entry)
        self.activity_file_name_label.grid(
            row=1, column=3, padx=5, pady=(10, 5))

        self.change_associated_temp_file_button = tk.Button(self.behaviour_input_frame, text="Temperature File: ", font=('Helvetica', 10),
                                                            bg='lightblue',
                                                            command=self.change_associated_temp_file)
        self.change_associated_temp_file_button.grid(
            row=1, column=0, padx=5, pady=(10, 5))

        self.change_associated_act_file_button = tk.Button(self.behaviour_input_frame, text="Activity File: ", font=('Helvetica', 10),
                                                           bg='lightblue',
                                                           command=self.change_associated_act_file)
        self.change_associated_act_file_button.grid(
            row=1, column=2, padx=5, pady=(10, 5))

        self.temp_and_act_start_time = tk.Label(self.behaviour_input_frame, text="Associated files Start Time (hh:mm:ss): ", bg='snow',
                                                font=('Helvetica', 10), wraplength=120)
        self.temp_and_act_start_time.grid(
            row=2, column=0, padx=5, pady=(10, 5))

        self.temp_and_act_start_time_entry = tk.Entry(
            self.behaviour_input_frame, width=10, textvariable=self.temp_and_act_start_time_var)
        self.temp_and_act_start_time_entry.grid(
            row=2, column=1, padx=5, pady=(10, 5))

        self.adjust_clustering_label = tk.Label(self.behaviour_input_frame, text="Adjust clustering minimum time between clusters (s):", bg='snow',
                                                font=('Helvetica', 10),
                                                wraplength=120)
        self.adjust_clustering_label.grid(
            row=2, column=2, padx=5, pady=(10, 5))

        self.adjust_clustering_entry = tk.Entry(
            self.behaviour_input_frame, width=10, textvariable=self.adjust_clustering_var)
        self.adjust_clustering_entry.grid(
            row=2, column=3, padx=5, pady=(10, 5))
        self.adjust_clustering_entry.bind('<FocusOut>', self.on_focus_out)
        self.adjust_clustering_entry.bind(
            '<Key>', lambda event: self.set_adjusted_false())

        self.adjust_clustering_entry.bind(
            '<Return>', lambda event: self.reset_clusters_based_on_user_input())

        self.light_off_time_label = tk.Label(self.behaviour_input_frame, text="Lights off (hh:mm:ss): ", bg='snow',
                                             font=('Helvetica', 10), wraplength=120)
        self.light_off_time_label.grid(row=3, column=0, padx=5, pady=(10, 5))

        self.light_off_time_entry = tk.Entry(
            self.behaviour_input_frame, width=10, textvariable=self.light_off_time_var)
        self.light_off_time_entry.grid(row=3, column=1, padx=5, pady=(10, 5))
        self.light_off_time_entry.delete(0, tk.END)  # Clear current value
        self.light_off_time_entry.insert(
            0, self.settings_manager.light_off_time_var)  # Insert the loaded value

        self.overlay_temp_and_act_button = tk.Button(self.behaviour_input_frame, text="Align Temperature and Activity with Photometry",
                                                     font=('Helvetica', 10), bg='lightblue', command=self.telemetry_plot_controller.overlay_temp_and_act)
        self.overlay_temp_and_act_button.grid(
            row=3, column=2, columnspan=3, padx=5, pady=(10, 5))

        self.static_inputs_frame = StaticInputsFrame(
            self.top_frame,
            save_inputs_callback=self.telemetry_settings_controller.save_inputs,
        )
        self.static_inputs_frame.grid(
            row=0, column=2, padx=5, pady=5, sticky=tk.NSEW)

        self.static_inputs_frame.pre_behaviour_time_label.config(
            text="Pre-Cluster time (s): ")
        self.static_inputs_frame.post_behaviour_time_label.config(
            text="Post-Cluster time (s): ")

        self.top_frame.grid_columnconfigure(0, weight=1)
        self.top_frame.grid_columnconfigure(1, weight=1)
        self.top_frame.grid_columnconfigure(2, weight=1)

        self.behaviour_input_frame.grid_columnconfigure(0, weight=1)
        self.behaviour_input_frame.grid_columnconfigure(1, weight=1)
        self.behaviour_input_frame.grid_columnconfigure(2, weight=1)
        self.behaviour_input_frame.grid_columnconfigure(3, weight=1)

    def set_adjusted_false(self):
        """Set the 'adjusted' attribute to False."""
        self.adjusted = False

    def on_focus_out(self, event):
        """
        Handle the event when the focus leaves the clustering adjustment entry.

        Parameters:
            event (tk.Event): The event object associated with the focus out event.
        """
        value = self.view_state.adjust_clustering.strip()
        if value and not self.adjusted:
            messagebox.showinfo(
                "Reminder", "After typing into the clustering adjustment please click back into the box and press Enter to apply changes.")

    def create_cluster_options(self, destroy_frame=True):
        """
        Create the cluster options frame based on cluster sizes.

        Parameters:
            destroy_frame (bool, optional): Whether to destroy the existing frame if it exists. Defaults to True.
        """
        if self.cluster_options_created:
            return
        if destroy_frame:
            if hasattr(self, "cluster_frame"):
                self.cluster_frame.destroy()

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

        select_all_button = tk.Button(
            self.graph_settings_container_instance.behaviour_frame, text='Select All', command=self.select_all_clusters)
        select_all_button.grid(row=0, column=1, padx=10,
                               pady=(5, 2), sticky=tk.W)

        deselect_all_button = tk.Button(self.graph_settings_container_instance.behaviour_frame,
                                        text='Deselect All', command=self.deselect_all_clusters)
        deselect_all_button.grid(
            row=0, column=2, padx=10, pady=(5, 2), sticky=tk.W)

        save_peak_alignment_button = tk.Button(
            self.graph_settings_container_instance.behaviour_frame, text='Save peak alignment', command=self.save_peak_alignment)
        save_peak_alignment_button.grid(
            row=0, column=3, padx=10, pady=(5, 2), sticky=tk.W)

        cluster_list_label = tk.Label(self.graph_settings_container_instance.behaviour_frame,
                                      text='Clusters', bg='snow', font=('Helvetica', 12, 'bold'))
        cluster_list_label.grid(row=0, column=0, padx=10,
                                pady=(5, 2), sticky=tk.W)

        cluster_sizes = [len(cluster_data['peaks'])
                         for cluster_data in self.cluster_dict.values()]
        self.cluster_display_status = {self.format_cluster_string(
            size): tk.BooleanVar(value=True) for size in set(cluster_sizes)}

        for i, cluster_size in enumerate(sorted_cluster_sizes, start=1):
            cluster_button = tk.Button(
                self.graph_settings_container_instance.behaviour_frame,
                text=self.format_cluster_string(cluster_size),
                command=lambda cs=cluster_size: self.choose_cluster_color(cs)
            )
            cluster_button.grid(row=i, column=0, padx=10, pady=5, sticky=tk.W)
            self.cluster_buttons[cluster_size] = cluster_button

            cluster_count_label = tk.Label(self.graph_settings_container_instance.behaviour_frame, text=str(
                cluster_size_counts[cluster_size]), bg='snow')
            cluster_count_label.grid(
                row=i, column=1, padx=10, pady=5, sticky=tk.W)

            cluster_var = self.cluster_display_status[self.format_cluster_string(
                cluster_size)]
            cluster_checkbox = tk.Checkbutton(self.graph_settings_container_instance.behaviour_frame, variable=cluster_var, command=self.refresh_cluster_options,
                                              bg='snow')
            cluster_checkbox.grid(
                row=i, column=2, padx=10, pady=5, sticky=tk.W)
            self.cluster_checkboxes[cluster_size] = cluster_checkbox

            peak_alignment_var = tk.StringVar(value='1')  # Default value is 1
            peak_alignment_var.trace(
                'w', lambda *args: self.validate_peak_alignment(cluster_size))
            self.peak_alignment_vars[cluster_size] = peak_alignment_var
            tk.Label(self.graph_settings_container_instance.behaviour_frame, text="Peak Alignment:", bg='snow').grid(
                row=i, column=3, sticky=tk.W, padx=10, pady=5)
            tk.Entry(self.graph_settings_container_instance.behaviour_frame, textvariable=peak_alignment_var,
                     width=7).grid(row=i, column=4, padx=10, pady=5)

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
        color = colorchooser.askcolor()
        if color[1]:
            self.cluster_colors[cluster_size].set(color[1])
            self.cluster_buttons[cluster_size].config(bg=color[1])

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

        threshold = 0.3 * data_column.max()  # This my need work?

        peaks, _ = find_peaks(
            data_column, height=threshold, distance=min_distance)

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

    def identify_clusters(self, time_column, data_column, peak_indices):
        return _identify_clusters(
            time_column,
            data_column,
            peak_indices,
            self.view_state.baseline_multiplier,
            self.view_state.adjust_clustering,
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
        self.telemetry_file_controller.handle_opto_data_file()

        self.visualize_opto_data_with_overlays(show_nighttime=True)

        self.mean_cluster_data = {}
        self.telemetry_settings_controller.populate_data_dict(replace_existing=True)
        self.telemetry_table_controller.populate_table()
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
        return self.telemetry_plot_controller.custom_date_parser(date_str)

    def calculate_nighttime_period(self):
        self.telemetry_plot_controller.calculate_nighttime_period()

    def add_nighttime_shading_to_plot(self, ax, time_column):
        self.telemetry_plot_controller.add_nighttime_shading_to_plot(ax, time_column)

    def overlay_temp_and_act(self):
        return self.telemetry_plot_controller.overlay_temp_and_act()

    def visualize_opto_data_with_overlays(self, show_nighttime=False):
        self.telemetry_plot_controller.visualize_opto_data_with_overlays(show_nighttime)

    def redraw_graph(self):
        self.telemetry_plot_controller.redraw_graph()

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
        self.telemetry_plot_controller.visualize_photometry_data_with_overlays(
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
        return self.telemetry_plot_controller.find_time_column(dataframe)

    def overlay_temp_on_figure(self, ax, trimmed_temp_df, sem_temp_data=None, left_axis=True):
        return self.telemetry_plot_controller.overlay_temp_on_figure(
            ax, trimmed_temp_df, sem_temp_data, left_axis
        )
    def mean_of_top_five(self, data_column):
        return self.telemetry_plot_controller.mean_of_top_five(data_column)

    def overlay_act_on_figure(self, ax, act_data, ymin_photometry, ymax_photometry, sem_act_data=None):
        return self.telemetry_plot_controller.overlay_act_on_figure(
            ax, act_data, ymin_photometry, ymax_photometry, sem_act_data
        )

    def calculate_dynamic_bins(self, n, b_ref=600, t_ref=1200, k=5):
        return self.telemetry_plot_controller.calculate_dynamic_bins(n, b_ref, t_ref, k)

    def get_single_cluster_data(self, cluster_dropdown_value, pre_time=0.0, post_time=0.0):
        return self.telemetry_plot_controller.get_single_cluster_data(
            cluster_dropdown_value, pre_time, post_time
        )

    def visualize_single_cluster(self, cluster_dropdown_value):
        self.telemetry_display_controller.visualize_single_cluster(
            cluster_dropdown_value
        )

    def extract_and_trim_data(self, dataframe, previous_time, offset, duration, sample_rate, data_type):
        return self.telemetry_plot_controller.extract_and_trim_data(
            dataframe, previous_time, offset, duration, sample_rate, data_type
        )

    def extract_data_for_date_and_offset(self, file_path, sheet_name, target_date, target_time):
        return self.telemetry_plot_controller.extract_data_for_date_and_offset(
            file_path, sheet_name, target_date, target_time
        )

    def extract_data_with_buffer(self, dataframe, previous_time, offset, duration, sample_rate):
        return self.telemetry_plot_controller.extract_data_with_buffer(
            dataframe, previous_time, offset, duration, sample_rate
        )

    def upsample_data(self, dataframe):
        return self.telemetry_plot_controller.upsample_data(dataframe)

    def change_associated_temp_file(self):
        """Change the associated temperature file."""
        current_file_path = self._get_current_file_path()
        initial_dir = os.path.dirname(current_file_path) if current_file_path else ""
        file_path = filedialog.askopenfilename(initialdir=initial_dir, title="Select file",
                                               filetypes=(("csv and Excel files", ("*.csv", "*.xlsx")),))

        if file_path:
            file_name = os.path.basename(file_path)
            self.associated_temp_data_entry.set(file_name)
            self.temp_file_path = file_path

    def change_associated_act_file(self):
        """Change the associated activity file."""
        current_file_path = self._get_current_file_path()
        initial_dir = os.path.dirname(current_file_path) if current_file_path else ""
        file_path = filedialog.askopenfilename(initialdir=initial_dir, title="Select file",
                                               filetypes=(("csv and Excel files", ("*.csv", "*.xlsx")),))

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
        return self.telemetry_file_controller.select_folder_for_telemetry_data(date)

    def common_setup(self, file_path_var, dataframe, mouse_name):
        self.telemetry_file_controller.common_setup(file_path_var, dataframe, mouse_name)

    def process_opto_data_file(self):
        """
        Process the optogenetic data file.
        """
        self.data_type = 'optogenetics'
        self.telemetry_file_controller.handle_opto_data_file()

        # self.display_dropdown.configure(state=tk.DISABLED)
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
        self.telemetry_file_controller.process_photometry_data_file()

    def calculate_stim_timings(self, stim_data_df):
        return self.telemetry_plot_controller.calculate_stim_timings(stim_data_df)

    def prepare_figure(self, time_column, show_nighttime=False, show_time_of_day=False):
        return self.telemetry_plot_controller.prepare_figure(
            time_column, show_nighttime, show_time_of_day
        )

    def overlay_data(self, ax, temp_data=None, act_data=None, ymin=None, ymax=None):
        return self.telemetry_plot_controller.overlay_data(ax, temp_data, act_data, ymin, ymax)

    def overlay_opto_stimulations(self, ax):
        self.telemetry_plot_controller.overlay_opto_stimulations(ax)

    def save_static_inputs(self, df):
        self.telemetry_settings_controller.save_static_inputs(df)

    def load_static_inputs(self):
        return self.telemetry_settings_controller.load_static_inputs()

    def populate_table(self):
        self.telemetry_table_controller.populate_table()

    def populate_data_dict(self, replace_existing: bool = False):
        self.telemetry_settings_controller.populate_data_dict(replace_existing)

    def populate_photometry_data_dict(self, file_path_str):
        return self.telemetry_settings_controller.populate_photometry_data_dict(
            file_path_str
        )

    def populate_opto_data_dict(self, file_path_str):
        return self.telemetry_settings_controller.populate_opto_data_dict(file_path_str)

    def update_cluster_inputs(self):
        self.telemetry_settings_controller.update_cluster_inputs()

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
        return self.telemetry_plot_controller.find_offset_for_previous_time(
            dataframe, target_time_str
        )

    def precalculate_data_versions(self):
        self.telemetry_plot_controller.precalculate_data_versions()

    def get_current_photometry_data(self):
        return self.telemetry_plot_controller.get_current_photometry_data()

    def get_time_scale(self, time_unit):
        """Return scaling factor for *time_unit*, or None for 'time of day'."""
        if time_unit == 'time of day':
            return None
        return _get_time_scale(time_unit)

    def create_photometry_figure(self, ax, time_column, data_column, peak_indices, clusters, show_nighttime=False):
        return self.telemetry_plot_controller.create_photometry_figure(
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
        """
        Embed the given figure into the Tkinter canvas.

        Parameters:
        - fig (matplotlib.figure.Figure): The figure to embed.
        - graph_canvas (tk.Canvas): The Tkinter canvas to embed the figure into.
        """
        if hasattr(self, "current_fig"):
            plt.close(self.current_fig)

        self.figure_canvas = FigureCanvasTkAgg(fig, master=graph_canvas)

        self.current_fig = fig

        self.figure_canvas.draw()

        self.figure_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.toolbar = NavigationToolbar2Tk(self.figure_canvas, graph_canvas)
        self.toolbar.update()

        self.toolbar.config(background="snow")
        self.toolbar._message_label.config(background="snow")

        self.toolbar._message_label.config(
            foreground="black", font=("Arial", 10))

        self.figure_canvas.get_tk_widget().configure(
            borderwidth=0, highlightthickness=0)

        self.toolbar.configure(background="snow", bd=0)
        self.toolbar._message_label.configure(background="snow", bd=0)

        self.toolbar.pack(side="top", fill="x")

    def delete_current_figure(self):
        """Delete the current figure from the canvas."""
        if self.figure_canvas:
            self.figure_canvas.get_tk_widget().destroy()
            self.figure_canvas = None
        if self.toolbar:
            self.toolbar.destroy()
            self.toolbar = None

    def save_and_close_label_settings(self, popup):
        self.telemetry_label_settings_controller.save_and_close_label_settings(popup)

    def extract_date_and_mouse_number(self, file_path_var, mouse_name):
        return self.telemetry_file_controller.extract_date_and_mouse_number(
            file_path_var, mouse_name
        )

    def retrieve_associated_files(self, date, file_path_var):
        return self.telemetry_file_controller.retrieve_associated_files(
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
                popup.destroy()
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
            popup.destroy()

    def populate_raw_data_sheet(self, writer, sheet_name, cluster_number):
        self.telemetry_excel_controller.populate_raw_data_sheet(
            writer, sheet_name, cluster_number
        )

    def add_home_hyperlink(self, worksheet, writer, col_idx, row_idx):
        self.telemetry_excel_controller.add_home_hyperlink(
            worksheet, writer, col_idx, row_idx
        )

    def write_raw_data_to_sheet(self, worksheet, writer, row_idx, col_idx, period, data_type, data):
        return self.telemetry_excel_controller.write_raw_data_to_sheet(
            worksheet, writer, row_idx, col_idx, period, data_type, data
        )

    def add_navigation_hyperlink(self, worksheet, writer, period, row_idx, col_idx):
        self.telemetry_excel_controller.add_navigation_hyperlink(
            worksheet, writer, period, row_idx, col_idx
        )

    def populate_cluster_sheet(self, writer, sheet_name, cluster_number):
        self.telemetry_excel_controller.populate_cluster_sheet(
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
        self.telemetry_excel_controller.write_cluster_details(
            worksheet, cluster_number, file_data, cluster_dict
        )

    def write_cluster_data_to_worksheet(self, worksheet, clusters, row_idx_for_basic_data, col_idx, rows_to_skip, initial_row_idx_for_peak_data, cluster_number):
        return self.telemetry_excel_controller.write_cluster_data_to_worksheet(
            worksheet,
            clusters,
            row_idx_for_basic_data,
            col_idx,
            rows_to_skip,
            initial_row_idx_for_peak_data,
            cluster_number,
        )

    def write_vertical_headings(self, worksheet, row_idx, headings):
        return self.telemetry_excel_controller.write_vertical_headings(
            worksheet, row_idx, headings
        )

    def write_headings(self, worksheet, row_idx, cluster_headings, headings, rows_to_skip):
        return self.telemetry_excel_controller.write_headings(
            worksheet, row_idx, cluster_headings, headings, rows_to_skip
        )

    def write_cluster_data_in_columns(self, worksheet, row_idx, col_idx, data_list):
        return self.telemetry_excel_controller.write_cluster_data_in_columns(
            worksheet, row_idx, col_idx, data_list
        )

    def write_peak_data_in_columns(self, worksheet, row_idx, col_idx, data_list, row_idx_for_basic_data, rows_to_skip):
        return self.telemetry_excel_controller.write_peak_data_in_columns(
            worksheet, row_idx, col_idx, data_list, row_idx_for_basic_data, rows_to_skip
        )

    def write_cluster_static_inputs(self, worksheet, row_idx, col_idx, cluster_number, file_data):
        return self.telemetry_excel_controller.write_cluster_static_inputs(
            worksheet, row_idx, col_idx, cluster_number, file_data
        )

    def extract_button_click_handler(self):
        """
        Handle the extract button click event, perform data binning, and save the data to an Excel file.

        Parameters:
        - file_path_var (tk.StringVar): StringVar containing the file path.
        """
        if self.export_options_container.use_binned_data_var.get() == 1:
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
                    self.telemetry_excel_controller.create_sheets_for_clusters(writer)
            except PermissionError:
                logger.error(
                    "Could not write export to %s because it is already open. "
                    "Close the existing file with the same name and try again.",
                    output_file_path,
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
        """Saves the current figure to a file, applying user-defined font and label settings."""
        current_xlabel = self.fig.axes[0].get_xlabel()
        current_ylabel = self.fig.axes[0].get_ylabel()
        fig_copy = copy.deepcopy(self.fig)
        request = build_image_export_request(
            self.export_options_container.height_entry.get().strip(),
            self.export_options_container.width_entry.get().strip(),
            self.export_options_container.image_format_combobox.get(),
            self.export_options_container.dpi_entry.get().strip(),
            self.figure_display_dropdown.get(),
            self.behaviour_choice_graph.get(),
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
