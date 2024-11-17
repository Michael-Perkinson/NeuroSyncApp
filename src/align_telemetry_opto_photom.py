import tkinter as tk
from tkinter import ttk, filedialog, simpledialog
from tkinter import messagebox
import tkinter.font as tkf
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

from src.behaviour_event_input_frame import BehaviourInputFrame
from src.data_selection_frame import DataSelectionFrame
from src.graph_settings_container import GraphSettingsContainer
from src.static_inputs_frame import StaticInputsFrame
from src.export_options_container import ExportOptionsContainer
from src.app_settings_manager import AppSettingsManager
from src.window_utils import center_window_on_screen


class MenopauseDataProcessingApp(ttk.Frame):
    def __init__(self, parent, **kwargs):
        """
        Initialize the application.

        Parameters:
        - parent: The parent widget.
        - **kwargs: Additional keyword arguments.
        """
        style = ttk.Style()
        style.configure('Custom.TFrame', background='snow')
        style.configure('Bordered.TFrame', background='snow',
                        borderwidth=2, relief='solid', bordercolor='black')
        style.configure('Custom.TCheckbutton', background='snow', foreground='black', font=('Helvetica', 10), compound='left', padding=(20, 0, 0, 0),
                        wraplength=150)
        style.configure("CustomScale.TScale", background="snow",
                        troughcolor="lightgray", gripcount=0)
        style.configure("NoBorder.TFrame", background="snow",
                        borderwidth=0, padding=0)
        style.configure("CustomNotebook.TNotebook", background="snow")
        style.configure("Custom.TMenubutton", background='snow', width=10, font=('Helvetica', 8), bd=1, relief="solid",
                        indicatoron=True)

        super().__init__(parent, style='Bordered.TFrame', **kwargs)

        self.parent = parent

        self.table_data = []
        self.table_treeview = None
        self.tables = {}
        self.data_dict = {}
        self.mean_cluster_data = {}
        self.duration_data_cache = {}
        self.current_fig = None
        self.mouse_name = None
        self.figure_canvas = None
        self.toolbar = None
        self.dataframe = None
        self.trimmed_dataframe = None
        self.full_dataframe = None
        self.duration_main_data = None
        self.time_column = None
        self.data_column = None
        self.data_type = None
        self.detected_peaks = None
        self.clusters_final = None
        self.adjusted = False
        self.press = None
        self.cluster_boxes = {}
        self.cluster_display_status = {}
        self.cluster_options_created = False
        self.peak_alignment_vars = {}
        self.cluster_colors = {}
        self.act_data = None
        self.temp_data = None
        self.extended_temp_data = None
        self.extended_act_data = None
        self.seconds_removed = 0
        self.figure_cache = {}

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
        self.act_file_path = tk.StringVar()
        self.temp_file_path = tk.StringVar()

        self.settings_manager = AppSettingsManager(app_type="Menopause_app")
        self.app_name = "Menopause_app"

        self.configure_main_frames()
        self.configure_notebooks()
        self.configure_tabs()
        self.create_widgets()

        self.label_color_var = tk.StringVar(
            value=self.settings_manager.selected_label_color)
        self.label_symbol_var = tk.StringVar(
            value=self.settings_manager.selected_label_symbol)
        self.label_size_var = tk.StringVar(
            value=self.settings_manager.selected_label_size)
        self.y_offset_peak_symbol = tk.StringVar(
            value=self.settings_manager.selected_y_offset_peak_symbol)
        self.peak_count_color_var = tk.StringVar(
            value=self.settings_manager.selected_peak_count_color)
        self.peak_count_size_var = tk.StringVar(
            value=self.settings_manager.selected_peak_count_size)
        self.y_for_peak_count = tk.StringVar(
            value=self.settings_manager.selected_y_for_peak_count)
        self.baseline_multiplier = tk.StringVar(
            value=self.settings_manager.selected_baseline_multiplier)
        self.baseline_color = tk.StringVar(
            value=self.settings_manager.selected_baseline_color)
        self.baseline_style = tk.StringVar(
            value=self.settings_manager.selected_baseline_style)
        self.baseline_thickness = tk.StringVar(
            value=self.settings_manager.selected_baseline_thickness)
        self.cluster_box_height_modifier = tk.StringVar(
            value=self.settings_manager.selected_cluster_box_height_modifier)
        self.cluster_box_color = tk.StringVar(
            value=self.settings_manager.selected_cluster_box_color)
        self.cluster_box_alpha = tk.StringVar(
            value=self.settings_manager.selected_cluster_box_alpha)
        self.telemetry_folder_path = tk.StringVar(
            value=self.settings_manager.telemetry_folder_path)

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

        self.settings_manager.update_graph_settings_container(
            self.graph_settings_container_instance)
        self.settings_manager.update_export_options_container(
            self.export_options_container)
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
        """
        Create and initialize table container for clusters.

        Parameters:
        - frame: The parent frame in which the table container is created.
        """
        style = ttk.Style()
        style.configure("Treeview", rowheight=25)
        style.map('Treeview', background=[('selected', 'blue')])
        style.configure("Treeview", selectbackground='blue',
                        selectforeground='white')
        style.configure("Treeview", relief="flat", borderwidth=0)
        style.configure("Treeview.Heading", relief="flat", borderwidth=0)
        style.map('Treeview.Heading', background=[('', 'grey')])

        table_container_frame = ttk.Frame(frame, style='NoBorder.TFrame')
        table_container_frame.grid(
            row=0, column=0, columnspan=3, padx=10, pady=10, sticky=tk.NSEW)

        table_hscrollbar = ttk.Scrollbar(
            table_container_frame, orient=tk.HORIZONTAL)
        table_hscrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.table_vscrollbar = ttk.Scrollbar(
            table_container_frame, orient="vertical")
        self.table_vscrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.table_canvas = tk.Canvas(table_container_frame, xscrollcommand=table_hscrollbar.set,
                                      yscrollcommand=self.table_vscrollbar.set, height=430)
        self.table_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        table_scroll_frame = ttk.Frame(self.table_canvas)
        self.table_canvas.create_window(
            (0, 0), window=table_scroll_frame, anchor='nw')

        def configure_scroll_region(event):
            """
            Configure the scroll region to encompass the full height of the frame.

            Parameters:
            - event: The event that triggers the configuration.
            """
            self.table_canvas.configure(
                scrollregion=self.table_canvas.bbox("all"), height=420)

        table_scroll_frame.bind("<Configure>", configure_scroll_region)

        columns = ['file_name', 'number_of_peaks', 'pre_cluster_time',
                   'post_cluster_time', 'bin_size', 'start_time', 'end_time']
        column_headings = {
            'file_name': 'File name',
            'number_of_peaks': 'Number of peaks',
            'pre_cluster_time': 'Pre-cluster time',
            'post_cluster_time': 'Post-cluster time',
            'bin_size': 'Bin size',
            'start_time': 'Start time',
            'end_time': 'End time'
        }

        self.table_treeview = ttk.Treeview(table_scroll_frame,
                                           columns=columns,
                                           show='headings', name='treeview')

        table_height = 30
        self.table_treeview.configure(height=table_height)
        self.table_treeview.pack(fill=tk.BOTH, expand=True)

        self.table_treeview.tag_configure('Even', background='white')
        self.table_treeview.tag_configure('Odd', background='lightgray')

        for column in columns:
            heading_text = column_headings.get(
                column, column.capitalize().replace('_', ' '))
            self.table_treeview.heading(column, text=heading_text, command=lambda _col=column: self.treeview_sort_column(
                self.table_treeview, _col, False))

        for column in columns:
            self.table_treeview.column(
                column, width=(tkf.Font().measure(column) + 11))

        table_hscrollbar.configure(command=self.table_canvas.xview)
        self.table_vscrollbar.configure(command=self.table_treeview.yview)

        table_container_frame.grid_rowconfigure(0, weight=1)
        table_container_frame.grid_columnconfigure(0, weight=1)

    def treeview_sort_column(self, tv, col, reverse):
        """
        Function to sort the treeview by column.

        Parameters:
        - tv: The treeview widget.
        - col: The column to sort by.
        - reverse: Boolean indicating the sort direction.
        """
        values = [(tv.set(k, col), k) for k in tv.get_children('')]

        def convert(val):
            """
            Convert the value to a float if possible.

            Parameters:
            - val: The value to convert.

            Raises:
            - ValueError: If the value cannot be converted to a float.

            Returns:
            - The converted float value, or None if the value is an empty string, or the original value if conversion fails.
            """
            if val == '':
                return None
            try:
                return float(val)
            except ValueError:
                return val

        values = [(convert(val), k) for val, k in values]

        if reverse:
            values.sort(key=lambda t: float('-inf')
                        if t[0] is None else t[0], reverse=True)
        else:
            values.sort(key=lambda t: float('inf') if t[0] is None else t[0])

        for index, (_, k) in enumerate(values):
            tv.move(k, '', index)

        tv.heading(col, command=lambda _col=col: self.treeview_sort_column(
            tv, _col, not reverse))

    def create_graphs_container(self, frame):
        """
        Create and initialize the graphs container.

        Parameters:
        - frame: The parent frame to contain the graphs container.

        Returns:
        - None
        """
        graphs_container_frame = ttk.Frame(
            frame, style='NoBorder.TFrame', borderwidth=2, relief='solid')
        graphs_container_frame.grid(
            row=0, column=0, columnspan=3, padx=10, pady=10, sticky=tk.NSEW)
        graphs_container_frame.columnconfigure(0, weight=1)
        graphs_container_frame.rowconfigure(0, weight=1)

        self.display_choices = ["Full Trace Display",
                                "Single Cluster Display", "Mean Cluster Display"]
        self.selected_display = tk.StringVar(value=self.display_choices[0])
        self.display_dropdown = ttk.Combobox(graphs_container_frame, state="readonly",
                                             values=self.display_choices, textvariable=self.selected_display, width=20)
        self.display_dropdown.bind(
            "<<ComboboxSelected>>", self.on_cluster_display_selection_changed)
        self.display_dropdown.grid(
            row=0, column=1, padx=5, pady=5, sticky=tk.W)
        self.display_dropdown.configure(state=tk.DISABLED)

        self.selected_period = tk.StringVar(value="Full")
        self.period_dropdown = ttk.Combobox(graphs_container_frame, state="readonly", values=[
                                            "Full", "Day", "Night"], textvariable=self.selected_period, width=10)
        self.period_dropdown.bind(
            "<<ComboboxSelected>>", self.on_cluster_selection_changed)
        self.period_dropdown.grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.period_dropdown.configure(state=tk.DISABLED)

        self.selected_cluster = tk.StringVar(value="")
        self.cluster_dropdown = ttk.Combobox(
            graphs_container_frame, state="readonly", textvariable=self.selected_cluster, width=30)
        self.cluster_dropdown.bind(
            "<<ComboboxSelected>>", self.on_cluster_selection_changed)
        self.cluster_dropdown.grid(
            row=0, column=3, padx=5, pady=5, sticky=tk.W)
        self.cluster_dropdown.configure(state=tk.DISABLED)

        self.label_settings_button = tk.Button(graphs_container_frame, text="Peak & Cluster Settings",
                                               command=self.open_label_settings_popup, bg='lightblue')
        self.label_settings_button.grid(
            row=0, column=0, padx=5, pady=5, sticky=tk.W)

        self.graph_canvas = tk.Canvas(
            graphs_container_frame, bg='snow', highlightthickness=1)
        self.graph_canvas.grid(row=1, column=0, columnspan=4, sticky=tk.NSEW)

        graphs_container_frame.grid_columnconfigure(0, weight=1)
        graphs_container_frame.grid_rowconfigure(0, weight=0)
        graphs_container_frame.grid_columnconfigure(0, weight=1)
        graphs_container_frame.grid_rowconfigure(1, weight=1)

    def on_cluster_display_selection_changed(self, event):
        """
        Handle the selection change event for the cluster display dropdown.

        Parameters:
        - event: The event object representing the selection change.
        """
        choice = self.selected_display.get()

        if choice == "Full Trace Display":
            self.cluster_dropdown['values'] = []
            self.selected_cluster.set("")
            self.cluster_dropdown.configure(state=tk.DISABLED)
            self.period_dropdown.configure(state=tk.DISABLED)
            if self.act_data is not None and self.temp_data is not None:
                self.visualize_photometry_data_with_overlays(
                    self.time_column, self.data_column, self.detected_peaks,
                    self.clusters_final, self.graph_canvas, self.temp_data,
                    self.act_data, show_nighttime=True
                )
            else:
                self.visualize_photometry_data_with_overlays(
                    self.time_column, self.data_column, self.detected_peaks,
                    self.clusters_final, self.graph_canvas
                )

        elif choice == "Single Cluster Display":
            cluster_ids = [
                f"Cluster {index + 1}" for index in range(len(self.cluster_dict))]
            self.cluster_dropdown['values'] = cluster_ids
            self.selected_cluster.set(cluster_ids[0])
            self.cluster_dropdown.configure(state=tk.NORMAL)
            self.period_dropdown.configure(state=tk.DISABLED)
            self.on_cluster_selection_changed()

        elif choice == "Mean Cluster Display":
            if self.data_type == 'photometry':
                peak_counts = self.get_peak_counts()
                self.cluster_dropdown['values'] = peak_counts
                if event.widget == self.display_dropdown and peak_counts:
                    self.selected_cluster.set(peak_counts[0])
            elif self.data_type == 'optogenetics':
                stim_counts = self.get_stim_counts()
                self.cluster_dropdown['values'] = stim_counts
                if event.widget == self.display_dropdown and stim_counts:
                    self.selected_cluster.set(stim_counts[0])
            self.cluster_dropdown.configure(state=tk.NORMAL)
            self.period_dropdown.configure(state=tk.NORMAL)
            self.on_cluster_selection_changed()

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
        """
        Handle the event when a cluster selection is changed.

        Parameters:
        - event: Optional; The event object (default is None).

        Behavior:
        - If the selected display type is "Single Cluster Display," it visualizes the selected single cluster.
        - If the selected display type is "Mean Cluster Display," it visualizes the selected mean cluster.
        """
        selected_cluster_string = self.selected_cluster.get()
        selected_display_type = self.selected_display.get()

        if selected_display_type == "Single Cluster Display":
            self.visualize_single_cluster(selected_cluster_string)
        elif selected_display_type == "Mean Cluster Display":
            self.visualize_mean_cluster(selected_cluster_string)

    def compute_data_for_cluster(self, selected_peak_count, changed_static_inputs=None):
        """
        Compute data for the specified cluster and store the processed data for each period.

        Parameters:
        - selected_peak_count: The number of peaks selected.
        - changed_static_inputs: Optional; any static inputs that have changed (default is None).
        """
        cluster_number = selected_peak_count

        longest_pre_peak, longest_post_peak = self.find_longest_times(
            cluster_number)

        photometry_data_list = self.extract_and_prepare_photometry_data(
            longest_pre_peak, longest_post_peak, cluster_number)
        processed_data, raw_data = self.extract_and_prepare_temp_and_act_data(
            longest_pre_peak, longest_post_peak, cluster_number)

        self.mean_cluster_data[cluster_number] = {
            "full": {
                "mean_temp_data": processed_data['full']['temp'],
                "mean_act_data": processed_data['full']['act'],
                "photometry_cluster_data": photometry_data_list['full']['Clusters'],
                "universal_time_axis_temp": processed_data['full']['temp']['Time (s)'].tolist(),
                "universal_time_axis_act": processed_data['full']['act']['Time (s)'].tolist(),
                "raw_temp_data": raw_data['full']['temp'],
                "raw_act_data": raw_data['full']['act']
            },
            "day": {
                "mean_temp_data": processed_data['day']['temp'],
                "mean_act_data": processed_data['day']['act'],
                "photometry_cluster_data": photometry_data_list['day']['Clusters'],
                "universal_time_axis_temp": processed_data['full']['temp']['Time (s)'].tolist(),
                "universal_time_axis_act": processed_data['full']['act']['Time (s)'].tolist(),
                "raw_temp_data": raw_data['day']['temp'],
                "raw_act_data": raw_data['day']['act']
            },
            "night": {
                "mean_temp_data": processed_data['night']['temp'],
                "mean_act_data": processed_data['night']['act'],
                "photometry_cluster_data": photometry_data_list['night']['Clusters'],
                "universal_time_axis_temp": processed_data['full']['temp']['Time (s)'].tolist(),
                "universal_time_axis_act": processed_data['full']['act']['Time (s)'].tolist(),
                "raw_temp_data": raw_data['night']['temp'],
                "raw_act_data": raw_data['night']['act']
            }
        }

        if changed_static_inputs is not None:
            selected_cluster_string = self.selected_cluster.get()
            selected_display_type = self.selected_display.get()

            if selected_display_type == "Single Cluster Display":
                self.visualize_single_cluster(selected_cluster_string)
            elif selected_display_type == "Mean Cluster Display":
                self.visualize_mean_cluster(selected_cluster_string)

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
        """
        Precompute data for all clusters or a subset of updated clusters.

        Parameters:
        - updated_clusters: List of clusters that have been updated (default is None).
        """
        unique_peak_counts = self.get_peak_counts()
        unique_stim_counts = self.get_stim_counts()

        if updated_clusters is not None:
            updated_peak_counts = set()
            updated_stim_counts = set()

            for cluster_name in updated_clusters:
                if 'Peak' in cluster_name:
                    peak_count = int(
                        re.search(r'(\d+)', cluster_name).group(1))
                    updated_peak_counts.add(peak_count)
                elif 'stim' in cluster_name:
                    stim_count = int(
                        re.search(r'(\d+)', cluster_name).group(1))
                    updated_stim_counts.add(stim_count)

            unique_peak_counts = [
                peak_count for peak_count in unique_peak_counts if peak_count in updated_peak_counts]
            unique_stim_counts = [
                stim_count for stim_count in unique_stim_counts if stim_count in updated_stim_counts]

        unique_peak_counts = sorted(unique_peak_counts)
        unique_stim_counts = sorted(unique_stim_counts)

        for peak_count in unique_peak_counts:
            if updated_clusters is not None:
                self.compute_data_for_cluster(
                    peak_count, changed_static_inputs=True)
            else:
                self.compute_data_for_cluster(peak_count)

        for stim_count in unique_stim_counts:
            if updated_clusters is not None:
                self.compute_data_for_stim_cluster(
                    stim_count, changed_static_inputs=True)
            else:
                self.compute_data_for_stim_cluster(stim_count)

    def compute_data_for_stim_cluster(self, selected_stim_count, changed_static_inputs=None):
        """
        Compute data for the specified stim cluster and store the processed data for each period.

        Parameters:
        - selected_stim_count: The number of stims in the selected cluster.
        - changed_static_inputs: Optional; any static inputs that have changed (default is None).
        """
        cluster_number = selected_stim_count

        processed_data, raw_data = self.extract_and_prepare_temp_and_act_data_for_stim(
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
                "raw_act_data": raw_data['full']['act']
            },
            "day": {
                "mean_temp_data": processed_data['day']['temp'],
                "mean_act_data": processed_data['day']['act'],
                "universal_time_axis_temp": processed_data['full']['temp']['Time (s)'].tolist(),
                "universal_time_axis_act": processed_data['full']['act']['Time (s)'].tolist(),
                "universal_time_axis_temp_min": convert_seconds_to_minutes(raw_data['full']['temp']['Time (s)'].tolist()),
                "raw_temp_data": raw_data['day']['temp'],
                "raw_act_data": raw_data['day']['act']
            },
            "night": {
                "mean_temp_data": processed_data['night']['temp'],
                "mean_act_data": processed_data['night']['act'],
                "universal_time_axis_temp": processed_data['full']['temp']['Time (s)'].tolist(),
                "universal_time_axis_act": processed_data['full']['act']['Time (s)'].tolist(),
                "universal_time_axis_temp_min": convert_seconds_to_minutes(raw_data['full']['temp']['Time (s)'].tolist()),
                "raw_temp_data": raw_data['night']['temp'],
                "raw_act_data": raw_data['night']['act']
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

        all_clusters = []

        for file_path, clusters in self.data_dict.items():
            for cluster_key, cluster_data in clusters.items():
                if 'stim' in cluster_key and int(re.search(r'(\d+)_stim', cluster_key).group(1)) == stim_number and 'time_period' in cluster_data:
                    all_clusters.append(cluster_data)

        daytime_clusters = [
            cluster for cluster in all_clusters if cluster['time_period'] == 'Day']
        nighttime_clusters = [
            cluster for cluster in all_clusters if cluster['time_period'] == 'Night']

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

        stim_times = self.find_stim_times(stim_number)
        if stim_times is None:
            return processed_data, raw_data

        for period, clusters in [('full', all_clusters), ('day', daytime_clusters), ('night', nighttime_clusters)]:

            if not clusters:
                continue  # Skip to the next period if there are no clusters

            all_temp_data, all_act_data = self.process_data_for_clusters(
                clusters, stim_times[0], stim_times[1], is_stim=True)

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

        return processed_data, raw_data

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
        """
        Visualize the mean cluster data for a selected cluster.

        Parameters:
        - selected_cluster_string: String representing the selected cluster.
        """
        period = self.selected_period.get().lower()

        # Extract cluster count and determine if it's a peak or stim based on the input string
        cluster_count = int(
            re.search(r'(\d+)', selected_cluster_string).group(1))
        is_peak = 'peak' in selected_cluster_string.lower()

        cluster_data = self.mean_cluster_data[cluster_count][period]

        photometry_data = cluster_data.get("photometry_cluster_data")

        if is_peak and photometry_data is None:
            self.display_no_data_figure()
            return

        else:
            if is_peak:
                self.plot_mean_cluster(
                    cluster_data["mean_temp_data"],
                    cluster_data["mean_act_data"],
                    photometry_data
                )
            else:
                self.plot_mean_cluster(
                    cluster_data["mean_temp_data"],
                    cluster_data["mean_act_data"],
                    photometry_data,
                    cluster_count
                )

    def display_no_data_figure(self):
        """Display a figure indicating that no clusters are present in the selected time period."""
        self.delete_current_figure()

        fig, ax = plt.subplots(figsize=(6, 4))

        ax.text(0.5, 0.5, 'No clusters in time period',
                horizontalalignment='center',
                verticalalignment='center',
                transform=ax.transAxes,
                fontsize=12)

        ax.set_xticks([])
        ax.set_yticks([])

        self.embed_figure_in_canvas(fig, self.graph_canvas)

    def find_longest_times(self, cluster_number):
        """
        Find the longest pre-peak and post-peak times for the given cluster number.

        Parameters:
            cluster_number (int): The number of peaks for the cluster to search.

        Returns:
            tuple: The longest pre-peak time and the longest post-peak time.
        """
        longest_pre_peak = 0
        longest_post_peak = 0

        for _, cluster_dict in self.data_dict.items():
            for cluster_name, cluster_data in cluster_dict.items():
                if f"{cluster_number} Peak" in cluster_name or f"{cluster_number} Peaks" in cluster_name:

                    peak_time = cluster_data['peaks'][cluster_data['alignment_index']]
                    end_time = float(
                        cluster_data['end_time'] + (float(cluster_data['post_cluster_time']) / 60))
                    start_time = max(0, float(
                        cluster_data['peaks'][0]) - (float(cluster_data['pre_cluster_time']) / 60))

                    pre_peak_time = peak_time - start_time
                    post_peak_time = end_time - peak_time

                    longest_pre_peak = max(longest_pre_peak, pre_peak_time)
                    longest_post_peak = max(longest_post_peak, post_peak_time)

        return longest_pre_peak, longest_post_peak

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
        """
        Process cluster data to truncate temperature and activity data around the peak time or stim time.

        Parameters:
            cluster_data (dict): Dictionary containing cluster information.
            longest_pre_peak (float): Longest pre-peak duration across all clusters.
            longest_post_peak (float): Longest post-peak duration across all clusters.
            is_stim (bool): Flag to indicate if the cluster is a stim cluster.

        Returns:
            tuple: Two DataFrames:
                - truncated_temp_data: Truncated temperature data.
                - truncated_act_data: Truncated activity data.
        """
        if is_stim:
            stim_start = cluster_data['stim_start']
            stim_end = cluster_data['stim_end']
            time_period = cluster_data['time_period']
            universal_start_time = stim_start - longest_pre_peak
            universal_end_time = stim_end + longest_post_peak
            cluster_name = f"{cluster_data['cluster_size']}_stim_cluster_{time_period}"
            peak_time = stim_start

        else:
            peak_time = cluster_data['peaks'][cluster_data['alignment_index']]
            universal_start_time, universal_end_time = self.get_universal_times(
                peak_time, longest_pre_peak, longest_post_peak)
            cluster_name = cluster_data['name']

        truncated_temp_data = self.extended_temp_data[
            (self.extended_temp_data['Time (min)'] >= universal_start_time) &
            (self.extended_temp_data['Time (min)'] <= universal_end_time)
        ].copy()

        truncated_temp_data['Time (min)'] -= peak_time

        truncated_act_data = self.extended_act_data[
            (self.extended_act_data['Time (min)'] >= universal_start_time) &
            (self.extended_act_data['Time (min)'] <= universal_end_time)
        ].copy()

        truncated_act_data['Time (min)'] -= peak_time

        truncated_temp_data = truncated_temp_data.reset_index(drop=True)
        truncated_act_data = truncated_act_data.reset_index(drop=True)

        truncated_temp_data['Cluster Name'] = cluster_name
        truncated_act_data['Cluster Name'] = cluster_name

        return truncated_temp_data, truncated_act_data

    def process_data_for_clusters(self, clusters, longest_pre_peak, longest_post_peak, is_stim=False):
        """
        Process data for multiple clusters, truncating temperature and activity data around each cluster's peak time or stim time.

        Parameters:
            clusters (list): List of cluster data dictionaries.
            longest_pre_peak (float): Longest pre-peak duration across all clusters.
            longest_post_peak (float): Longest post-peak duration across all clusters.
            is_stim (bool): Flag to indicate if the clusters are stim clusters.

        Returns:
            tuple: Two lists of DataFrames:
                - all_temp_data: List of truncated temperature data DataFrames.
                - all_act_data: List of truncated activity data DataFrames.
        """
        all_temp_data = []
        all_act_data = []

        for cluster_data in clusters:
            temp_data, act_data = self.process_cluster_data(
                cluster_data, longest_pre_peak, longest_post_peak, is_stim)
            all_temp_data.append(temp_data)
            all_act_data.append(act_data)

        return all_temp_data, all_act_data

    def calculate_mean_and_sem(self, concatenated_data):
        """
        Calculate the mean and standard error of the mean (SEM) for the given concatenated data.

        Parameters:
            concatenated_data (pd.DataFrame): DataFrame containing concatenated data, with the first column excluded from calculations.

        Returns:
            pd.DataFrame: The original DataFrame with added columns for the calculated mean and SEM.
        """
        data_for_calculation = concatenated_data.iloc[:, 1:]

        mean_data = data_for_calculation.mean(axis=1)
        sem_data = data_for_calculation.sem(axis=1).fillna(0)

        concatenated_data['Mean'] = mean_data
        concatenated_data['SEM'] = sem_data

        return concatenated_data

    def trim_data_to_minimum_length(self, all_data):
        """
        Trim each DataFrame in a list to the minimum length found among them.

        Parameters:
            all_data (list of pd.DataFrame): List of pandas DataFrames.

        Returns:
            list of pd.DataFrame: List of DataFrames, each trimmed to the minimum length.
        """
        min_length = min(len(dataframe) for dataframe in all_data)

        return [dataframe.iloc[:min_length] for dataframe in all_data]

    def create_universal_time_axis(self, axis_time_start, axis_time_end, sample_rate):
        """
        Create a universal time axis based on the given start and end times and sample rate.

        Parameters:
            axis_time_start (float): Start time for the universal time axis.
            axis_time_end (float): End time for the universal time axis.
            sample_rate (float): Sample rate to determine the time intervals.

        Returns:
            np.ndarray: Array representing the universal time axis.
        """
        return np.arange(axis_time_start, axis_time_end + sample_rate, sample_rate)

    def extract_and_prepare_temp_and_act_data(self, longest_pre_peak, longest_post_peak, cluster_number):
        """
        Extract and prepare temperature and activity data for clusters.

        Parameters:
            longest_pre_peak (float): The longest pre-peak time.
            longest_post_peak (float): The longest post-peak time.
            cluster_number (int): The cluster number to process.

        Returns:
            two tuples: Processed data and raw data dictionaries for 'full', 'day', and 'night' periods.
                Each dictionary contains 'temp' and 'act' keys with corresponding data.
        """
        all_clusters = [cluster_data for cluster_key, cluster_data in self.cluster_dict.items()
                        if cluster_key[2] == cluster_number and 'time_period' in cluster_data]

        daytime_clusters = [
            cluster for cluster in all_clusters if cluster['time_period'] == 'Day']
        nighttime_clusters = [
            cluster for cluster in all_clusters if cluster['time_period'] == 'Night']

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

        for period, clusters in [('full', all_clusters), ('day', daytime_clusters), ('night', nighttime_clusters)]:
            if not clusters:
                continue

            all_temp_data, all_act_data = self.process_data_for_clusters(
                clusters, longest_pre_peak, longest_post_peak)

            if not all_temp_data or all(all_temp.empty for all_temp in all_temp_data):
                print(
                    f"No temperature data to concatenate for period: {period}")
                continue
            if not all_act_data or all(all_act.empty for all_act in all_act_data):
                print(f"No activity data to concatenate for period: {period}")
                continue

            axis_time_start = -longest_pre_peak * 60
            axis_time_end = longest_post_peak * 60

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

            if concatenated_temp_data.empty:
                print(
                    f"Concatenated temperature data is empty for period: {period}")
                continue
            if concatenated_act_data.empty:
                print(
                    f"Concatenated activity data is empty for period: {period}")
                continue

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

        return processed_data, raw_data

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
        """
        Calculate the universal start and end times based on the peak time and the longest pre- and post-peak durations.

        Parameters:
            peak_time (float): The time of the peak event.
            longest_pre_peak (float): The longest duration before the peak.
            longest_post_peak (float): The longest duration after the peak.

        Returns:
            tuple: A tuple containing the universal start time and universal end time.
        """
        universal_start_time = peak_time - longest_pre_peak
        universal_end_time = peak_time + longest_post_peak

        return universal_start_time, universal_end_time

    def align_and_concatenate_data(self, all_data, universal_time_axis):
        """
        Align and concatenate multiple DataFrames based on a universal time axis.

        Parameters:
            all_data (list of pandas.DataFrame): List of DataFrames to be aligned and concatenated.
            universal_time_axis (numpy.ndarray): Universal time axis to align the DataFrames.

        Returns:
            pandas.DataFrame: Concatenated DataFrame with aligned data.
        """
        aligned_data = []
        min_length_after_alignment = float('inf')

        for df in all_data:
            if 'Time (min)' in df.columns and not df.empty:
                aligned_df = pd.DataFrame({'Time (s)': universal_time_axis})

                # Find the index in df that is closest to the first value of universal_time_axis
                start_idx = np.argmin(
                    np.abs(df['Time (min)'] - universal_time_axis[0]))

                num_points_to_insert = min(
                    len(df) - start_idx, len(aligned_df))

                source_data = df.iloc[start_idx:start_idx +
                                      num_points_to_insert, df.columns.get_loc('Data')].values

                num_points_to_insert = min(
                    num_points_to_insert, len(aligned_df))
                num_points_to_insert = min(
                    num_points_to_insert, len(source_data))

                aligned_df.loc[:num_points_to_insert - 1,
                               'Data'] = source_data[:num_points_to_insert]

                aligned_df = aligned_df.rename(
                    columns={'Data': df['Cluster Name'].iloc[0]})

                num_points_after_start = len(df) - start_idx
                min_length_after_alignment = min(
                    min_length_after_alignment, num_points_after_start)

                aligned_data.append(aligned_df)

            else:
                print("DataFrame is empty or 'Time (min)' column is missing.")
                continue

        min_length = min(min_length_after_alignment, len(universal_time_axis))
        trimmed_time_axis = universal_time_axis[:min_length]

        time_column = pd.DataFrame(trimmed_time_axis, columns=['Time (s)'])
        data_columns = pd.concat(
            [df.loc[:min_length - 1, df.columns[1]] for df in aligned_data], axis=1)
        concatenated_data = pd.concat([time_column, data_columns], axis=1)

        return concatenated_data

    def extract_and_prepare_photometry_data(self, longest_pre_peak, longest_post_peak, cluster_number):
        """
        Extract and prepare photometry data and separate into full, day, and night datasets.

        Parameters:
            longest_pre_peak (int): The longest duration before the peak in minutes.
            longest_post_peak (int): The longest duration after the peak in minutes.
            cluster_number (int): The target number of peaks in the clusters.

        Returns:
            dict: Processed photometry data for 'full', 'day', and 'night' periods.
                Each key contains a nested dictionary with 'Clusters' holding the aligned and concatenated data.
        """
        photometry_data = {
            'full': {'Clusters': None},
            'day': {'Clusters': None},
            'night': {'Clusters': None}
        }

        data_column = self.data_selection_frame.selected_column_var.get()
        df_copy = self.dataframe.copy()

        extra_buffer = 0.5  # Extra buffer time in minutes

        all_clusters = [cluster_data for cluster_key, cluster_data in self.cluster_dict.items()
                        if cluster_key[2] == cluster_number and 'time_period' in cluster_data]

        daytime_clusters = [
            cluster for cluster in all_clusters if cluster['time_period'] == 'Day']
        nighttime_clusters = [
            cluster for cluster in all_clusters if cluster['time_period'] == 'Night']

        # Establish a common time axis based on the longest pre-peak and post-peak durations
        step_size = 1 / 600
        common_time_axis = pd.Series([i * step_size for i in range(
            int((longest_pre_peak + longest_post_peak + step_size) / step_size))])
        common_time_axis -= longest_pre_peak  # Center around zero

        for period, clusters in [('full', all_clusters), ('day', daytime_clusters), ('night', nighttime_clusters)]:
            if not clusters:
                continue

            cluster_data_frames = []

            for cluster_data in clusters:
                peak_time = cluster_data['peaks'][cluster_data['alignment_index']]
                universal_start_time, universal_end_time = self.get_universal_times(
                    peak_time, longest_pre_peak, longest_post_peak)

                extended_start_time = universal_start_time - extra_buffer
                extended_end_time = universal_end_time + extra_buffer

                extended_truncated_data = df_copy[(df_copy.iloc[:, 0] >= extended_start_time) &
                                                  (df_copy.iloc[:, 0] <= extended_end_time)][[df_copy.columns[0], data_column]].copy()

                processed_data = self.process_photometry_data(
                    extended_truncated_data)

                processed_data.iloc[:, 0] -= peak_time
                processed_data.set_index(
                    processed_data.columns[0], inplace=True)

                aligned_data = processed_data.reindex(
                    common_time_axis, method='nearest', tolerance=0.002).interpolate()

                aligned_data.columns = [cluster_data['name']]
                cluster_data_frames.append(aligned_data)

            if cluster_data_frames:
                combined_data = pd.concat(cluster_data_frames, axis=1)
                combined_data.reset_index(inplace=True)
                combined_data.columns = [
                    'Time (min)'] + [df.columns[0] for df in cluster_data_frames]
                photometry_data[period]['Clusters'] = combined_data

        return photometry_data

    def process_photometry_data(self, truncated_data):
        """
        Process the photometry data by reindexing and interpolating.

        Parameters:
            truncated_data (DataFrame): The truncated photometry data.

        Returns:
            DataFrame: The processed photometry data.
        """
        reference_time_index = self.create_linear_time_index(
            truncated_data.iloc[0, 0], truncated_data.iloc[-1, 0], 0.00167
        )

        tolerance = 0.002
        truncated_data.set_index(truncated_data.columns[0], inplace=True)
        processed_data = truncated_data.reindex(
            reference_time_index, method='nearest', tolerance=tolerance).reset_index()
        processed_data.interpolate(method='linear', inplace=True)

        return processed_data

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
        """
        Plot the mean cluster data along with optional temperature and activity data overlays.

        Parameters:
            mean_temp_data (DataFrame or None): DataFrame containing mean temperature data with 'Mean' and 'SEM' columns.
            mean_act_data (DataFrame or None): DataFrame containing mean activity data with 'Mean' and 'SEM' columns.
            photometry_cluster_data_df (DataFrame): DataFrame containing photometry cluster data, where each column represents a cluster.
        """
        'testing for calls3'
        self.delete_current_figure()

        fig, ax = plt.subplots(figsize=(6, 4))

        color_palette = cm.get_cmap('Set1')

        if self.data_type == 'photometry':
            scaled_time_column = self.scale_time_column(
                photometry_cluster_data_df['Time (min)'])

            for i, cluster_name in enumerate(photometry_cluster_data_df.columns[1:]):
                color = color_palette(i % 10)
                ax.plot(scaled_time_column, photometry_cluster_data_df[cluster_name], label=cluster_name, color=color,
                        alpha=0.5)

        elif self.data_type == 'optogenetics':
            scaled_time_column = self.scale_time_column(
                self.mean_cluster_data[cluster_count]['full']['universal_time_axis_temp_min'])

        ax.set_xlim(scaled_time_column.iloc[0], scaled_time_column.iloc[-1])
        ax.set_xlabel('Time')

        # ax.xaxis.set_minor_locator(ticker.AutoMinorLocator(self.settings_manager.number_of_minor_ticks))

        temp_present = mean_temp_data is not None and self.graph_settings_container_instance.temperature_data_var.get()
        act_present = mean_act_data is not None and self.graph_settings_container_instance.activity_data_var.get()

        if temp_present and act_present:
            sem_temp_data = mean_temp_data['SEM']
            sem_act_data = mean_act_data['SEM']

            ax.yaxis.set_visible(False)

            self.overlay_temp_on_figure(
                ax, mean_temp_data, sem_temp_data, left_axis=True)
            self.overlay_act_on_figure(ax, mean_act_data, ax.get_ylim()[
                                       0], ax.get_ylim()[1], sem_act_data)

        elif temp_present:
            sem_temp_data = mean_temp_data['SEM']
            self.overlay_temp_on_figure(
                ax, mean_temp_data, sem_temp_data, left_axis=False)
        elif act_present:
            sem_act_data = mean_act_data['SEM']
            self.overlay_act_on_figure(ax, mean_act_data, ax.get_ylim()[
                                       0], ax.get_ylim()[1], sem_act_data)

        if self.data_type == 'optogenetics':
            self.add_stims_to_plot(ax, cluster_count)

        self.embed_figure_in_canvas(fig, self.graph_canvas)

    def add_stims_to_plot(self, ax, cluster_count):
        """
        Overlay optogenetic stimulations on the plot for a specific cluster count.

        Parameters:
        - ax (matplotlib.axes.Axes): The axes on which to overlay the stimulations.
        - cluster_count (int): The specific cluster count for which to overlay stimulations.
        """
        if self.stim_timings is None:
            return

        ymin, ymax = ax.get_ylim()

        stim_cluster = next(
            (timings for size, timings in self.stim_timings if size == cluster_count), None)
        if not stim_cluster:
            return

        cluster_start_time = stim_cluster[0][0]

        for stim_start, stim_end in stim_cluster:
            time_unit = self.graph_settings_container_instance.time_unit_menu.get()
            time_factor = self.get_time_scale(time_unit)

            adjusted_stim_start = (
                stim_start - cluster_start_time) * time_factor
            adjusted_stim_end = (stim_end - cluster_start_time) * time_factor

            rect = plt.Rectangle(
                (adjusted_stim_start, ymin), adjusted_stim_end - adjusted_stim_start, ymax - ymin, color='blue', alpha=0.3)
            ax.add_patch(rect)

        ax.set_ylim(ymin, ymax)

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
            figure_display_callback=self.reset_clusters_based_on_user_input,
            new_data_file_callback=self.handle_new_data_file
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
                                                     font=('Helvetica', 10), bg='lightblue', command=self.overlay_temp_and_act)
        self.overlay_temp_and_act_button.grid(
            row=3, column=2, columnspan=3, padx=5, pady=(10, 5))

        self.static_inputs_frame = StaticInputsFrame(
            self.top_frame, save_inputs_callback=self.save_inputs)
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
        value = self.adjust_clustering_var.get().strip()
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
                print(
                    f"Invalid alignment index for cluster of size {len(peaks)}. Defaulting to the last peak.")
                alignment_peak_index = -1

            # Check if the index is in the valid range
            if alignment_peak_index < 0 or alignment_peak_index >= len(peaks):
                print(
                    f"Invalid alignment index for cluster of size {len(peaks)}. Defaulting to the last peak.")
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
        """
        Identify clusters based on data staying above a certain baseline and ensuring the presence of at least one peak.

        Parameters:
            - time_column (pd.Series): The column of time data.
            - data_column (pd.Series): The column of data in which to identify clusters.
            - peak_indices (list): The indices of detected peaks.

        Returns:
            - List of tuples: Each tuple contains the start and end indices of a valid cluster.
        """
        median_value = data_column.median()
        mean_value = data_column.mean()

        baseline_value = mean_value if median_value == 0 else median_value

        baseline_multiplier = float(
            self.baseline_multiplier.get().strip() or 1) - 1

        end_baseline = baseline_value + \
            (baseline_multiplier * abs(baseline_value))

        clusters = []
        start = None
        was_below_median = True

        for i in range(len(data_column)):
            if was_below_median and data_column.iloc[i] > median_value:
                start = i
                was_below_median = False
            elif not was_below_median and data_column.iloc[i] <= end_baseline:
                if start is not None:
                    clusters.append((start, i))
                    start = None
                was_below_median = True
            elif data_column.iloc[i] < median_value:
                was_below_median = True

        if start is not None:
            clusters.append((start, len(data_column) - 1))

        valid_clusters = [cluster for cluster in clusters if any(
            peak in range(cluster[0], cluster[1]) for peak in peak_indices)]

        adjust_clustering_value = self.adjust_clustering_var.get().strip()
        if adjust_clustering_value:
            adjust_clustering_value = float(adjust_clustering_value) / 60
            merged_clusters = []
            prev_cluster = None
            for cluster in valid_clusters:
                if prev_cluster:
                    time_between_clusters = time_column.iloc[cluster[0]
                                                             ] - time_column.iloc[prev_cluster[1]]

                    if time_between_clusters < adjust_clustering_value:
                        merged_cluster = (prev_cluster[0], cluster[1])
                        merged_clusters[-1] = merged_cluster
                        prev_cluster = merged_cluster
                    else:
                        merged_clusters.append(cluster)
                        prev_cluster = cluster
                else:
                    merged_clusters.append(cluster)
                    prev_cluster = cluster

            valid_clusters = merged_clusters

        cluster_dict = {}
        cluster_id = 1

        for cluster in valid_clusters:
            peak_times_within_cluster = [time_column.iloc[peak]
                                         for peak in peak_indices if cluster[0] <= peak < cluster[1]]
            peak_amplitudes_within_cluster = [
                data_column.iloc[peak] - median_value for peak in peak_indices if cluster[0] <= peak < cluster[1]]

            if len(peak_times_within_cluster) > 1:
                interpeak_intervals = [peak_times_within_cluster[i + 1] - peak_times_within_cluster[i]
                                       for i in range(len(peak_times_within_cluster) - 1)]
            else:
                interpeak_intervals = None

            cluster_duration = time_column.iloc[cluster[1]
                                                ] - time_column.iloc[cluster[0]]
            peak_count = len(peak_times_within_cluster)

            if peak_count == 1:
                cluster_name = f"1 Peak in Cluster_{cluster_id}"
            else:
                cluster_name = f"{peak_count} Peaks in Cluster_{cluster_id}"

            # Use a tuple (start_index, end_index, peak_count) as the key
            key = (cluster[0], cluster[1], peak_count)

            cluster_dict[key] = {
                'name': cluster_name,
                'start_time': time_column.iloc[cluster[0]],
                'end_time': time_column.iloc[cluster[1]],
                'peaks': peak_times_within_cluster,
                'peak_amplitudes': peak_amplitudes_within_cluster,
                'alignment_index': 0,
                'interpeak_intervals': interpeak_intervals,
                'cluster_duration': cluster_duration,
            }

            cluster_id += 1

        return valid_clusters, cluster_dict

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

        self.populate_data_dict()
        self.populate_table()
        self.populate_static_input_dropdown()
        if self.act_data is not None and self.temp_data is not None:
            self.annotate_clusters_with_time_period()

        self.adjusted = True
        self.settings_manager.save_variables()

    def reset_opto_data(self):
        """Reset and visualize optogenetic data based on user input."""
        self.handle_opto_data_file()

        self.visualize_opto_data_with_overlays(show_nighttime=True)

        self.populate_data_dict()
        self.populate_table()
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
        """
        Parses a date string in the format "year-month-day" where year is the first two digits interpreted as 20YY.

        Parameters:
        - date_str (str): The date string to parse in the format "YY-MM-DD".

        Returns:
        - datetime object: A datetime object representing the parsed date.
        """
        year, month, day = date_str.split('-')
        year = "20" + year
        return datetime.strptime(f"{day}-{month}-{year}", '%d-%m-%Y')

    def calculate_nighttime_period(self):
        """Calculate the nighttime period based on user-defined start time and lights-off time."""
        start_time_str = self.temp_and_act_start_time_var.get()

        if not start_time_str:
            start_time_str = self.start_time_timedelta

        start_time = datetime.strptime(start_time_str, '%H:%M:%S').time()

        lights_off_time_str = self.light_off_time_var.get()
        lights_off_time = datetime.strptime(
            lights_off_time_str, '%H:%M:%S').time()

        base_date = datetime.strptime(self.date, '%y-%m-%d').date()

        start_datetime = datetime.combine(base_date, start_time)
        lights_off_datetime = datetime.combine(base_date, lights_off_time)

        if lights_off_datetime < start_datetime:
            night_start = start_datetime
            night_end = datetime.combine(
                base_date, lights_off_time) + timedelta(hours=12)
        else:
            night_start = lights_off_datetime
            night_end = lights_off_datetime + timedelta(hours=12)

        # Adjust night end to the next day if it crosses midnight
        if night_end.time() < night_start.time():
            night_end = datetime.combine(
                night_start.date() + timedelta(days=1), night_end.time())

        end_datetime = start_datetime + \
            timedelta(minutes=self.duration_main_data)

        nighttime_periods = []
        if night_end > end_datetime:
            night_end = end_datetime

        nighttime_periods.append((night_start.time(), night_end.time()))
        self.nighttime_periods = nighttime_periods

        self.settings_manager.light_off_time_var = lights_off_time_str

        self.settings_manager.save_variables()

    def add_nighttime_shading_to_plot(self, ax, time_column):
        """
        Add nighttime shading to a plot.

        Parameters:
        - ax (matplotlib.axes.Axes): The plot axis to add shading to.
        - time_column (pd.Series): Series containing the time data for the x-axis.
        """
        start_time = pd.to_datetime(
            self.temp_and_act_start_time_var.get(), format='%H:%M:%S').time()
        recording_date = datetime.strptime(self.date, '%y-%m-%d').date()

        for night_start_time, night_end_time in self.nighttime_periods:
            night_start_datetime = datetime.combine(
                recording_date, night_start_time)
            night_end_datetime = datetime.combine(
                recording_date, night_end_time)

            if night_end_time < start_time:
                night_end_datetime += timedelta(days=1)

            night_start_minutes = (
                night_start_datetime - datetime.combine(recording_date, start_time)).total_seconds() / 60
            night_end_minutes = (
                night_end_datetime - datetime.combine(recording_date, start_time)).total_seconds() / 60

            night_end_minutes = min(night_end_minutes, time_column.iloc[-1])

            if night_start_minutes <= time_column.iloc[-1]:
                ax.axvspan(night_start_minutes, night_end_minutes,
                           color='gray', alpha=0.3, label='Nighttime')

    def overlay_temp_and_act(self):
        """Overlay temperature and activity data, process the data, and visualize it with optional nighttime shading."""
        target_date = self.date
        act_file_path = self.act_file_path
        temp_file_path = self.temp_file_path
        duration_main_data = self.duration_main_data
        extended_duration = duration_main_data + 60

        self.display_dropdown.configure(state=tk.NORMAL)

        parsed_date = self.custom_date_parser(target_date)
        formatted_date = parsed_date.strftime('%m/%d/%Y')

        if not self.temp_and_act_start_time_var.get().strip():
            if self.start_time_timedelta is not None:
                target_time = self.start_time_timedelta
            else:
                messagebox.showerror(
                    "Input Error", "Please enter a valid file alignment time.")
                return None, None
        else:
            target_time = self.temp_and_act_start_time_var.get().strip()
        print(target_time)

        act_data, act_offset, act_previous_time = self.extract_data_for_date_and_offset(
            act_file_path, self.mouse_name, formatted_date, target_time)
        temp_data, temp_offset, temp_previous_time = self.extract_data_for_date_and_offset(
            temp_file_path, self.mouse_name, formatted_date, target_time)

        act_timestamps_5_to_10 = act_data["Date Time"].iloc[4:10].tolist()
        temp_timestamps_5_to_10 = temp_data["Date Time"].iloc[4:10].tolist()

        temp_sample_rate = self.calculate_sample_rate(temp_timestamps_5_to_10)
        act_sample_rate = self.calculate_sample_rate(act_timestamps_5_to_10)

        self.act_sample_rate = act_sample_rate

        if self.data_type == "photometry":
            temp_data = self.upsample_data(temp_data)
            temp_sample_rate = 0.1

        self.temp_sample_rate = temp_sample_rate

        trimmed_temp_df = self.extract_and_trim_data(
            temp_data, temp_previous_time, temp_offset, duration_main_data, temp_sample_rate, 'temp')

        trimmed_act_df = self.extract_and_trim_data(
            act_data, act_previous_time, act_offset, duration_main_data, act_sample_rate, 'act')

        self.extended_temp_data = self.extract_data_with_buffer(
            temp_data, temp_previous_time, temp_offset, extended_duration, temp_sample_rate)

        self.extended_act_data = self.extract_data_with_buffer(
            act_data, act_previous_time, act_offset, extended_duration, act_sample_rate)

        # TODO FIX THIS

        self.act_data = trimmed_act_df
        self.temp_data = trimmed_temp_df

        self.calculate_nighttime_period()

        if self.data_type == "photometry":
            self.annotate_clusters_with_time_period()

            self.precompute_all_clusters()

            self.visualize_photometry_data_with_overlays(self.time_column, self.data_column, self.detected_peaks, self.clusters_final, self.graph_canvas, trimmed_temp_df,
                                                         trimmed_act_df, show_nighttime=True)

        elif self.data_type == "optogenetics":
            self.update_column_headings()
            self.populate_data_dict()
            self.populate_table()
            self.populate_static_input_dropdown()
            self.annotate_clusters_with_time_period()
            self.precompute_all_clusters()
            self.visualize_opto_data_with_overlays(show_nighttime=True)

    def visualize_opto_data_with_overlays(self, show_nighttime=False):
        """
        Visualize optogenetics data with overlays.

        Parameters:
        - show_nighttime (bool, optional): Whether to show nighttime shading. Defaults to False.
        """
        temp_data = self.temp_data
        act_data = self.act_data
        time_column = temp_data['Time (min)']

        self.display_dropdown.configure(state=tk.NORMAL)

        fig, ax, scaled_time_column = self.prepare_figure(
            time_column, show_nighttime, show_time_of_day=False)

        ymin_photometry, ymax_photometry = ax.get_ylim()

        ax_act = self.overlay_data(
            ax, temp_data, act_data, ymin_photometry, ymax_photometry)

        self.overlay_opto_stimulations(ax_act)

        self.embed_figure_in_canvas(fig, self.graph_canvas)

    def redraw_graph(self):
        """
        Redraw the graph with updated photometry data and overlays.
        """
        if self.data_type == "photometry":
            time_column, data_column, detected_peaks, clusters_final, _ = self.get_current_photometry_data()

            if self.act_data is not None and self.temp_data is not None:
                self.visualize_photometry_data_with_overlays(time_column, data_column, detected_peaks, clusters_final, self.graph_canvas, self.temp_data, self.act_data,
                                                             show_nighttime=True)
            else:
                self.visualize_photometry_data_with_overlays(
                    time_column, data_column, detected_peaks, clusters_final, self.graph_canvas)

        elif self.data_type == "optogenetics":
            self.visualize_opto_data_with_overlays(show_nighttime=True)

        self.settings_manager.save_variables()

    def visualize_photometry_data_with_overlays(self, time_column, data_column, detected_peaks, clusters, graph_canvas, temp_data=None, act_data=None, show_nighttime=False):
        """
        Visualize photometry data with overlays.

        Parameters:
        - time_column (pd.Series): Series containing the time data for the x-axis.
        - data_column (pd.Series): Series containing the data to plot.
        - detected_peaks (np.ndarray): Array containing the indices of detected peaks.
        - clusters (dict): Dictionary containing information about the clusters.
        - graph_canvas (tk.Canvas): The canvas to embed the figure in.
        - temp_data (pd.DataFrame, optional): DataFrame containing the temperature data. Defaults to None.
        - act_data (pd.DataFrame, optional): DataFrame containing the activity data. Defaults to None.
        - show_nighttime (bool, optional): Whether to show nighttime shading. Defaults to False.
        """
        fig, ax, scaled_time_column = self.prepare_figure(
            time_column, show_nighttime)

        ax = self.create_photometry_figure(
            ax, time_column, data_column, detected_peaks, clusters, show_nighttime)

        ymin_photometry, ymax_photometry = ax.get_ylim()

        self.overlay_data(ax, temp_data, act_data,
                          ymin_photometry, ymax_photometry)

        self.embed_figure_in_canvas(fig, graph_canvas)

    def find_time_column(self, dataframe):
        for col in dataframe.columns:
            if re.match(r"^Time\s", col):
                return col
        return None

    def overlay_temp_on_figure(self, ax, trimmed_temp_df, sem_temp_data=None, left_axis=True):
        """
        Overlay temperature data on the figure.

        Parameters:
        - ax (matplotlib.axes.Axes): The plot axis to add the temperature overlay to.
        - trimmed_temp_df (pd.DataFrame): DataFrame containing the trimmed temperature data.
        - sem_temp_data (pd.DataFrame or pd.Series, optional): DataFrame or Series containing the SEM of temperature data. Defaults to None.
        - left_axis (bool, optional): Whether to plot the temperature data on the left y-axis. Defaults to True.
        """

        time_column_name = self.find_time_column(trimmed_temp_df)

        time_data = trimmed_temp_df[time_column_name].copy()
        if "s" in time_column_name.lower():
            time_data = time_data / 60

        time_column = self.scale_time_column(time_data)

        if sem_temp_data is not None:
            temp_values = trimmed_temp_df['Mean']
        else:
            temp_values = trimmed_temp_df['Data']

        if left_axis:
            ax_temp = ax.twinx()
            ax_temp.spines['right'].set_visible(False)
            ax_temp.spines['left'].set_position(('outward', 0))
            ax_temp.yaxis.set_ticks_position('left')
            ax_temp.yaxis.set_label_position('left')
        else:
            ax_temp = ax.twinx()
            ax_temp.spines["right"].set_position(("outward", 0))

        ax_temp.plot(time_column, temp_values, color=self.settings_manager.selected_temp_mean_line_color, label="Temperature",
                     linewidth=self.settings_manager.selected_temp_mean_line_width, alpha=float(self.settings_manager.selected_temp_mean_line_alpha))

        if sem_temp_data is not None:
            if isinstance(sem_temp_data, pd.DataFrame):
                sem_values = sem_temp_data.iloc[:, 0].values
            else:
                sem_values = sem_temp_data.values

            temp_values = np.array(temp_values, dtype=float)
            sem_values = np.array(sem_values, dtype=float)

            lower_bound = temp_values - sem_values
            upper_bound = temp_values + sem_values
            ax_temp.fill_between(time_column, lower_bound, upper_bound, color=self.settings_manager.selected_temp_sem_color,
                                 alpha=float(self.settings_manager.selected_temp_sem_line_alpha))

        ax_temp.set_ylabel('Temperature (°C)',
                           color=self.settings_manager.selected_temp_sem_color)
        ax_temp.tick_params(
            axis='y', labelcolor=self.settings_manager.selected_temp_sem_color)

        if sem_temp_data is not None and 'SEM' in trimmed_temp_df.columns:
            sem_min = trimmed_temp_df['SEM'].min()
            sem_max = trimmed_temp_df['SEM'].max()

            actual_temp_min = min(trimmed_temp_df['Mean'].min(
            ) - sem_min, trimmed_temp_df['Mean'].min())
            actual_temp_max = max(trimmed_temp_df['Mean'].max(
            ) + sem_max, trimmed_temp_df['Mean'].max())
        else:
            actual_temp_min = trimmed_temp_df['Data'].min()
            actual_temp_max = trimmed_temp_df['Data'].max()

        temp_difference = actual_temp_max - actual_temp_min
        temp_desired_scale = float(
            self.settings_manager.selected_temp_desired_scale)
        temp_position_factor = float(
            self.settings_manager.selected_temp_desired_offset)

        scaled_temp_difference = temp_difference / temp_desired_scale
        total_padding = scaled_temp_difference - temp_difference

        bottom_padding = total_padding * temp_position_factor
        top_padding = total_padding - bottom_padding

        temp_desired_range_min = actual_temp_min - bottom_padding
        temp_desired_range_max = actual_temp_max + top_padding

        ax_temp.set_ylim(temp_desired_range_min, temp_desired_range_max)
        ax_temp.spines["top"].set_visible(False)

    def mean_of_top_five(self, data_column):
        """
        Calculate the mean of the top five values in a data column.

        Parameters:
        - data_column (pd.Series): Series containing the data.

        Returns:
        - float: Mean of the top five values, or mean of available values if fewer than five.
        """
        # Convert the column to numeric, coercing errors to NaN
        numeric_column = pd.to_numeric(data_column, errors='coerce')

        # Drop NaN values to avoid issues with nlargest
        numeric_column = numeric_column.dropna()

        # Ensure there are enough values to get the top five
        if len(numeric_column) >= 5:
            top_five_values = numeric_column.nlargest(
                5)
            return top_five_values.mean()
        else:
            # Handle cases with fewer than 5 values (e.g., return the mean of available values)
            return numeric_column.mean()

    def overlay_act_on_figure(self, ax, act_data, ymin_photometry, ymax_photometry, sem_act_data=None):
        """
        Overlay activity data on the figure.

        Parameters:
        - ax (matplotlib.axes.Axes): The plot axis to add the activity overlay to.
        - act_data (pd.DataFrame): DataFrame containing the activity data.
        - ymin_photometry (float): Minimum y-axis value for photometry data.
        - ymax_photometry (float): Maximum y-axis value for photometry data.
        - sem_act_data (pd.DataFrame or pd.Series, optional): DataFrame or Series containing the SEM of activity data. Defaults to None.
        """
        time_column_name = self.find_time_column(act_data)

        time_data = act_data[time_column_name].copy()
        if "s" in time_column_name.lower():
            time_data = time_data / 60

        time_column = self.scale_time_column(time_data)

        if sem_act_data is not None:
            act_values = act_data['Mean']
        else:
            act_values = act_data['Data']

        ax_act = ax.twinx()

        max_act_modifier = float(
            self.settings_manager.selected_activity_desired_scale)
        baseline_modifier = max_act_modifier * 0

        desired_baseline = ymin_photometry - baseline_modifier

        if sem_act_data is not None:
            histogram_height = self.mean_of_top_five(
                act_data['Mean']) / max_act_modifier
        else:
            histogram_height = self.mean_of_top_five(
                act_data['Data']) / max_act_modifier

        act_ymax_with_offset = desired_baseline + histogram_height
        ax.set_ylim((ymin_photometry - baseline_modifier),
                    ymax_photometry + (0.05 * ymax_photometry))

        ax_act.spines["right"].set_position(("outward", 0))

        ax_act.spines["right"].set_visible(True)

        num_bins = self.settings_manager.selected_activity_num_bins

        if self.selected_display.get() == "Mean Cluster Display":
            num_bins = int(
                (time_data.iloc[-1] - time_data.iloc[0]) / self.act_sample_rate * 60)
        elif num_bins == '':
            num_bins = self.calculate_dynamic_bins(len(time_column))
            print(len(time_column))

        else:
            num_bins = int(num_bins)

        ax_act.hist(time_column, weights=act_values, bins=num_bins, align='mid', color=self.settings_manager.selected_activity_mean_bar_color, label="Activity",
                    alpha=float(self.settings_manager.selected_activity_mean_bar_alpha))

        ax_act.set_ylabel(
            'Activity (counts)', color=self.settings_manager.selected_activity_mean_bar_color)
        ax_act.tick_params(
            axis='y', labelcolor=self.settings_manager.selected_activity_mean_bar_color, labelright=True)

        ax_act.spines["left"].set_visible(False)
        ax_act.spines["top"].set_visible(False)

        ax_act.set_ylim(0, act_ymax_with_offset)
        return ax_act

    def calculate_dynamic_bins(self, n, b_ref=600, t_ref=1200, k=5):
        """
        Dynamically calculate the number of bins for the histogram using logarithmic scaling.

        Parameters:
        - n (int): Number of data points.
        - b_ref (int): Preferred number of bins for the reference duration.
        - t_ref (int): Reference duration in seconds.
        - k (int): Scaling factor for logarithmic effect.

        Returns:
        - int: Number of bins for the histogram.
        """
        bins = int(b_ref * math.log(1 + (n * k / t_ref)))
        return min(n, bins)

    def get_single_cluster_data(self, cluster_dropdown_value, pre_time=0.0, post_time=0.0):
        """
        Get the data for a single cluster based on the cluster dropdown value and the pre and post cluster times.

        Parameters:
        - cluster_dropdown_value (str): The value selected from the cluster dropdown.
        - pre_time (float, optional): Time to include before the cluster. Defaults to 0.0.
        - post_time (float, optional): Time to include after the cluster. Defaults to 0.0.

        Returns:
        - time_column (pd.Series): Time column for the selected cluster.
        - data_column (pd.Series): Data column for the selected cluster.
        """
        cluster_number = int(cluster_dropdown_value.split()
                             [-1])

        cluster_indices = list(self.cluster_dict.keys())[cluster_number - 1]
        start_index, end_index, _ = cluster_indices

        original_start_time = self.time_column[start_index]
        original_end_time = self.time_column[end_index]

        adjusted_start_time = max(0, original_start_time - pre_time)
        adjusted_end_time = min(
            self.time_column.iloc[-1], original_end_time + post_time)

        adjusted_start_index = (
            self.time_column - adjusted_start_time).abs().idxmin()
        adjusted_end_index = (
            self.time_column - adjusted_end_time).abs().idxmin()

        time_column = self.time_column.iloc[adjusted_start_index:adjusted_end_index]
        data_column = self.data_column.iloc[adjusted_start_index:adjusted_end_index]

        return time_column, data_column

    def visualize_single_cluster(self, cluster_dropdown_value):
        """
        Visualize data for a single cluster selected from the dropdown.

        Parameters:
        - cluster_dropdown_value (str): The value selected from the cluster dropdown.
        """
        self.delete_current_figure()

        file_path_str = os.path.basename(self.file_path.get())

        cluster_number = cluster_dropdown_value.split()[-1]

        matching_key = next((key for key in self.data_dict[file_path_str].keys(
        ) if f"Cluster_{cluster_number}" in key), None)

        if matching_key is None:
            print(f"No matching key found for {cluster_dropdown_value}.")
            return

        cluster_data = self.data_dict[file_path_str][matching_key]

        original_start_time = float(cluster_data['start_time'])
        original_end_time = float(cluster_data['end_time'])
        pre_time = float(cluster_data['pre_cluster_time']) / 60
        post_time = float(cluster_data['post_cluster_time']) / 60

        adjusted_start_time = max(0, original_start_time - pre_time)
        adjusted_end_time = min(
            self.temp_data['Time (min)'].max(), original_end_time + post_time)

        time_column, data_column = self.get_single_cluster_data(
            cluster_dropdown_value, pre_time, post_time)

        truncated_temp_data = self.temp_data[(self.temp_data['Time (min)'] >= adjusted_start_time) &
                                             (self.temp_data['Time (min)'] <= adjusted_end_time)] if self.temp_data is not None else None
        truncated_act_data = self.act_data[(self.act_data['Time (min)'] >= adjusted_start_time) &
                                           (self.act_data['Time (min)'] <= adjusted_end_time)] if self.act_data is not None else None

        fig, ax, scaled_time_column = self.prepare_figure(
            time_column, show_nighttime=True)

        self.create_photometry_figure(ax,
                                      scaled_time_column, data_column, [], [], [])

        ax.set_xlim((adjusted_start_time), adjusted_end_time)

        # ax.xaxis.set_minor_locator(ticker.AutoMinorLocator(self.settings_manager.number_of_minor_ticks))

        ymin_photometry, ymax_photometry = ax.get_ylim()

        temp_present = truncated_temp_data is not None and self.graph_settings_container_instance.temperature_data_var.get()
        act_present = truncated_act_data is not None and self.graph_settings_container_instance.activity_data_var.get()

        if temp_present and act_present:
            ax.yaxis.set_visible(False)
            self.overlay_temp_on_figure(
                ax, truncated_temp_data, left_axis=True)
            self.overlay_act_on_figure(
                ax, truncated_act_data, ymin_photometry, ymax_photometry)

        elif temp_present:
            self.overlay_temp_on_figure(
                ax, truncated_temp_data, left_axis=False)
        elif act_present:
            self.overlay_act_on_figure(
                ax, truncated_act_data, ymin_photometry, ymax_photometry)

        self.embed_figure_in_canvas(fig, self.graph_canvas)

    def extract_and_trim_data(self, dataframe, previous_time, offset, duration, sample_rate, data_type):
        """
        Extract data for the equivalent duration from the provided dataframe and trim to the target time.

        Parameters:
        - dataframe (pd.DataFrame): DataFrame containing the data.
        - previous_time (str): The previous time as a reference point.
        - offset (float): Offset in minutes from the previous time.
        - duration (float): Duration in minutes to extract data for.
        - sample_rate (float): Sample rate of the data in seconds.
        - data_type (str): The type of data ('temp' or 'act').

        Returns:
        - trimmed_df (pd.DataFrame): The trimmed dataframe with time reset.
        """
        start_index = dataframe[dataframe["Date Time"].astype(
            str).str.contains(previous_time)].index[0]

        num_data_points = int(((duration + offset) * 60) / sample_rate)

        extracted_data = dataframe.loc[start_index:start_index +
                                       num_data_points - 1]

        sample_interval_seconds = sample_rate
        rows_to_trim = math.ceil((offset * 60) / sample_interval_seconds)

        trimmed_df = extracted_data.iloc[rows_to_trim:].copy()

        trimmed_df['Time (min)'] = [(i * (sample_rate / 60))
                                    for i in range(len(trimmed_df))]

        return trimmed_df

    def extract_data_for_date_and_offset(self, file_path, sheet_name, target_date, target_time):
        """
        Extract data for a specific date from the provided Excel sheet and find the closest time offset.

        Parameters:
        - file_path (str): Path to the Excel file.
        - sheet_name (str): Name of the sheet (should correspond to mouse name).
        - target_date (str): Date in the format "mm/dd/yyyy" for which to extract data.
        - target_time (str): Time in the format "HH:MM:SS" for which to find the offset.

        Returns:
        - date_data (pd.DataFrame): DataFrame containing the extracted data from the target date and all subsequent dates.
        - offset (float): Offset in seconds.
        - previous_time (str): Actual starting time from the data that's closest to the target time.
        """
        def find_sheet_name(sheet_names, target_name):
            """Find the correct sheet name in a case-insensitive manner."""
            for name in sheet_names:
                if name == target_name:
                    return name
            return None

        def find_sheet_name_case_insensitive(sheet_names, target_name):
            """Find the correct sheet name after converting to uppercase."""
            target_name_upper = target_name.upper()
            sheet_names_upper = [name.upper() for name in sheet_names]
            if target_name_upper in sheet_names_upper:
                return sheet_names[sheet_names_upper.index(target_name_upper)]
            return None

        excel_file = pd.ExcelFile(file_path)
        sheet_names = excel_file.sheet_names

        correct_sheet_name = find_sheet_name(sheet_names, sheet_name)

        if not correct_sheet_name:
            correct_sheet_name = find_sheet_name_case_insensitive(
                sheet_names, sheet_name)
            if not correct_sheet_name:
                raise ValueError(
                    f"Sheet name '{sheet_name}' not found in the Excel file.")

        data = pd.read_excel(file_path, sheet_name=correct_sheet_name)

        if 'Time' not in data.columns:
            print(
                "Time column not found in the data. Searching for 'Time' label in the data.")
            time_label_row = data[data.eq('Time').any(axis=1)]
            if not time_label_row.empty:
                start_data_index = time_label_row.index[0] + 1
                print("Found the 'Time' label in the data.")
            else:
                raise ValueError(
                    "Couldn't locate the 'Time' label in the data.")
        else:
            start_data_index = data[data['Time'] == 'Time'].index[0] + 1

        data = data.iloc[start_data_index:]

        data.columns = [col.upper() for col in data.columns]
        sheet_name_upper = sheet_name.upper()

        if sheet_name_upper in data.columns:
            data = data.rename(
                columns={"NAME": "Date Time", sheet_name_upper: "Data"})

        data["Date Time"] = pd.to_datetime(data["Date Time"], errors='coerce')

        # Date Filtering: Get data from the target date and all subsequent dates
        date_data = data[data["Date Time"].dt.date >=
                         pd.to_datetime(target_date).date()]

        offset, previous_time = self.find_offset_for_previous_time(
            date_data, target_time)

        return date_data, offset, previous_time

    def extract_data_with_buffer(self, dataframe, previous_time, offset, duration, sample_rate):
        """
        Extract data for the specified duration with an additional buffer from the provided dataframe.

        Parameters:
        - dataframe (pd.DataFrame): DataFrame containing the data.
        - previous_time (str): The previous time as a reference point.
        - offset (float): Offset in minutes from the previous time.
        - duration (float): Duration in minutes to extract data for.
        - sample_rate (float): Sample rate of the data in seconds.

        Returns:
        - extracted_extended_data (pd.DataFrame): Extracted data for the specified duration and buffer, with time reset to start from -15 minutes.
        """
        try:
            start_index = dataframe[dataframe["DateTime"].astype(
                str).str.contains(previous_time)].index[0]
        except IndexError:
            raise ValueError(
                "The previous_time provided is not found in the dataframe.")

        fifteen_minutes_data_points = int((15 * 60) / sample_rate)
        start_index = (max(0, start_index - fifteen_minutes_data_points)) + 10

        num_data_points = int(((duration + 60 + offset) * 60) / sample_rate)

        largest_index = dataframe.index.max()

        end_index = min(largest_index, start_index + num_data_points)

        extracted_extended_data = dataframe

        start_offset = extracted_extended_data.iloc[0]['Offset'].total_seconds(
        ) / 60
        extracted_extended_data['Time (min)'] = [
            (i * (sample_rate / 60) - start_offset) for i in range(len(extracted_extended_data))
        ]

        return extracted_extended_data

    def upsample_data(self, dataframe):
        """
        Upsample the data in the dataframe to a frequency of 100 ms.

        Parameters:
        - dataframe (pd.DataFrame): DataFrame containing the data.

        Returns:
        - upsampled_df (pd.DataFrame): Upsampled dataframe with interpolated values and original structure.
        """
        dataframe['DateTime'] = pd.to_datetime(dataframe['DateTime'])
        dataframe = dataframe.set_index('DateTime')

        dataframe['Data'] = pd.to_numeric(dataframe['Data'], errors='coerce')

        # Upsample the dataframe to a frequency of 100 ms
        upsampled_df = dataframe.resample('100ms').interpolate()

        upsampled_df = upsampled_df.reset_index()

        upsampled_df['Date Time'] = upsampled_df['DateTime'].dt.strftime(
            '%Y-%m-%d %H:%M:%S.%f').str[:-3]
        upsampled_df = upsampled_df[[
            'Date Time', 'Data', 'DateTime', 'Offset']]

        return upsampled_df

    def change_associated_temp_file(self):
        """Change the associated temperature file."""
        file_path = filedialog.askopenfilename(initialdir=self.file_path, title="Select file",
                                               filetypes=(("csv and Excel files", ("*.csv", "*.xlsx")),))

        if file_path:
            file_name = os.path.basename(file_path)
            self.associated_temp_data_entry.set(file_name)
            self.temp_file_path = file_path

    def change_associated_act_file(self):
        """Change the associated activity file."""
        file_path = filedialog.askopenfilename(initialdir=self.file_path, title="Select file",
                                               filetypes=(("csv and Excel files", ("*.csv", "*.xlsx")),))

        if file_path:
            file_name = os.path.basename(file_path)
            self.associated_act_data_entry.set(file_name)
            self.act_file_path = file_path

    def select_column_names(self):
        pass

    def select_behaviour_file(self):
        pass

    def save_inputs(self):
        """Save the user input values for pre-cluster time, post-cluster time, and bin size to the relevant clusters."""
        selected_cluster_label = self.static_inputs_frame.selected_behaviour.get().strip()

        pre_time = self.static_inputs_frame.pre_behaviour_time_entry.get()
        post_time = self.static_inputs_frame.post_behaviour_time_entry.get()
        bin_size = self.static_inputs_frame.bin_size_entry.get()

        updated_clusters = set()
        is_stim_update = 'stim' in selected_cluster_label.lower()

        if selected_cluster_label == "All Clusters" or selected_cluster_label == "All Stims":
            for filename, clusters in self.data_dict.items():
                for cluster_name, data in clusters.items():
                    if is_stim_update:
                        if "stim" in cluster_name:
                            data['pre_stim_time'] = pre_time
                            data['post_stim_time'] = post_time
                            data['bin_size'] = bin_size
                            updated_clusters.add(cluster_name)
                    else:
                        data['pre_cluster_time'] = pre_time
                        data['post_cluster_time'] = post_time
                        data['bin_size'] = bin_size
                        updated_clusters.add(cluster_name)

        elif is_stim_update:
            match = re.search(r'(\d+) stim', selected_cluster_label)
            if match:
                stim_count = int(match.group(1))
                for filename, clusters in self.data_dict.items():
                    for cluster_name, data in clusters.items():
                        if f"{stim_count}_stim" in cluster_name:
                            data['pre_stim_time'] = pre_time
                            data['post_stim_time'] = post_time
                            data['bin_size'] = bin_size
                            updated_clusters.add(cluster_name)
        else:
            match = re.search(r'(\d+) Peak', selected_cluster_label)
            if match:
                num_peaks_in_selected_cluster = int(match.group(1))
                for filename, clusters in self.data_dict.items():
                    for cluster_name, data in clusters.items():
                        if f"{num_peaks_in_selected_cluster} Peaks" in cluster_name:
                            data['pre_cluster_time'] = pre_time
                            data['post_cluster_time'] = post_time
                            data['bin_size'] = bin_size
                            updated_clusters.add(cluster_name)

        df = self.data_dict_to_df(self.data_dict)
        self.update_cluster_inputs()
        if self.temp_data is not None and self.act_data is not None:
            self.precompute_all_clusters(updated_clusters)
        self.save_static_inputs(df)

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
        """
        Select a folder for telemetry data and set the paths for temperature and activity files.

        Parameters:
        - date (str): The date to filter the telemetry files.

        Returns:
        - act_file_path (str or None): Path to the activity file or None if not found.
        - temp_file_path (str or None): Path to the temperature file or None if not found.
        """
        root = tk.Tk()
        root.withdraw()
        folder_path = filedialog.askdirectory(
            title=f"Select folder for telemetry data of {date}")
        root.destroy()

        if not folder_path:
            print("No folder selected.")
            return None, None

        self.settings_manager.telemetry_folder_path = folder_path

        temp_files = [f for f in os.listdir(
            folder_path) if 'temp' in f.lower() and date in f]
        act_files = [f for f in os.listdir(
            folder_path) if 'act' in f.lower() and date in f]

        temp_file_path = os.path.join(
            folder_path, temp_files[0]) if temp_files else None
        act_file_path = os.path.join(
            folder_path, act_files[0]) if act_files else None

        if not act_file_path or not temp_file_path:
            print(
                f"Could not find the associated Act or Temp files for the date: {date}")

        if temp_file_path:
            file_name = os.path.basename(temp_file_path)
            self.associated_temp_data_entry.set(file_name)

        if act_file_path:
            file_name = os.path.basename(act_file_path)
            self.associated_act_data_entry.set(file_name)

        self.settings_manager.save_variables()

        return act_file_path, temp_file_path

    def handle_new_data_file(self, file_path_var, selected_column_var, column_dropdown, mouse_name, dataframe, is_time_based_data):
        """
        Handle the loading and processing of a new data file.

        Parameters:
        - file_path_var (str): Path to the new data file.
        - selected_column_var (str): Selected column from the data file.
        - column_dropdown (tk.OptionMenu): Dropdown menu for selecting columns.
        - mouse_name (str): Name of the mouse.
        - dataframe (pd.DataFrame): DataFrame containing the data.
        - args (tuple): Additional arguments.
        """
        self.common_setup(file_path_var, dataframe, mouse_name)

        self.selected_column_var = selected_column_var
        self.column_dropdown = column_dropdown

        if is_time_based_data is not None:
            if not is_time_based_data:
                self.data_type = "optogenetics"
                self.process_opto_data_file()
                return

        self.data_type = "photometry"
        self.process_photometry_data_file()

    def common_setup(self, file_path_var, dataframe, mouse_name):
        """
        Perform common setup tasks for handling new data files.

        Parameters:
        - file_path_var (str): Path to the new data file.
        - dataframe (pd.DataFrame): DataFrame containing the data.
        - mouse_name (str): Name of the mouse.
        """
        self.file_path = file_path_var
        self.dataframe = dataframe
        self.cluster_options_created = False
        self.clear_table()
        self.table_treeview.delete(*self.table_treeview.get_children())
        self.data_dict = {}
        self.seconds_removed = 0
        self.cluster_dict = {}
        self.mean_cluster_data = {}
        self.data_type = None
        self.start_time_timedelta = None

        date, mouse_number = self.extract_date_and_mouse_number(
            file_path_var, mouse_name)

        self.mouse_name = mouse_name
        self.date = date

        if not date or not mouse_number:
            print("Could not extract date or mouse number from the main file name.")
            return

        self.act_file_path, self.temp_file_path = self.retrieve_associated_files(
            date, file_path_var)

        if not self.act_file_path or not self.temp_file_path:
            self.act_file_path, self.temp_file_path = self.select_folder_for_telemetry_data(
                date)

    def process_opto_data_file(self):
        """
        Process the optogenetic data file.
        """
        self.data_type = 'optogenetics'
        self.handle_opto_data_file()

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
        """
        Process the photometry data file.
        """
        self.update_column_headings()

        self.precalculate_data_versions()

        time_column, data_column, detected_peaks, clusters_final, grouped_clusters = self.get_current_photometry_data()

        self.time_column = time_column
        self.data_column = data_column
        self.detected_peaks = detected_peaks
        self.clusters_final = clusters_final
        self.grouped_clusters = grouped_clusters

        self.duration_main_data = time_column.iloc[-1] - time_column.iloc[0]

        self.visualize_photometry_data_with_overlays(
            time_column, data_column, detected_peaks, clusters_final, self.graph_canvas)

        self.populate_data_dict()
        self.populate_table()
        self.populate_static_input_dropdown()

        self.display_dropdown.configure(state=tk.DISABLED)
        self.selected_display.set("Full Trace Display")

    def handle_opto_data_file(self):
        """Handle the loading and processing of an optogenetics data file."""
        self.stim_timings = None
        file_path = self.file_path.get()
        file_extension = os.path.splitext(file_path)[1].lower()

        if file_extension == '.csv':
            stim_data_df = pd.read_csv(file_path)
        elif file_extension in ['.xls', '.xlsx']:
            stim_data_df = pd.read_excel(file_path)
        else:
            raise ValueError(f"Unsupported file extension: {file_extension}")

        self.label_settings_button.grid_remove()

        # Convert 'Stim onset (hh:mm:ss)' and 'Start time (hh:mm:ss)' from string to timedelta
        stim_data_df['Stim onset (hh:mm:ss)'] = stim_data_df['Stim onset (hh:mm:ss)'].apply(
            lambda x: pd.to_timedelta(datetime.strptime(
                x, '%I:%M:%S %p').strftime('%H:%M:%S'))
            if 'am' in x.lower() or 'pm' in x.lower()
            else pd.to_timedelta(datetime.strptime(x, '%H:%M:%S').strftime('%H:%M:%S'))
        )
        stim_data_df['Start time (hh:mm:ss)'] = stim_data_df['Start time (hh:mm:ss)'].apply(
            lambda x: pd.to_timedelta(datetime.strptime(
                x, '%I:%M:%S %p').strftime('%H:%M:%S'))
            if pd.notna(x) and ('am' in x.lower() or 'pm' in x.lower())
            else pd.to_timedelta(datetime.strptime(x, '%H:%M:%S').strftime('%H:%M:%S')) if pd.notna(x)
            else pd.NaT
        )

        self.data_selection_frame.selected_column_var.set("Not used")
        self.data_selection_frame.column_dropdown['state'] = 'disabled'

        start_time_timedelta = stim_data_df['Start time (hh:mm:ss)'].iloc[0]
        self.start_time_timedelta = str(
            start_time_timedelta).split(" days ")[-1]

        self.duration_main_data = stim_data_df['Duration of test (min)'].iloc[0]

        self.temp_and_act_start_time_var.set(self.start_time_timedelta)

        self.stim_timings = self.calculate_stim_timings(stim_data_df)

        expected_length = int(stim_data_df['Duration of test (min)'].iloc[0])

        self.duration_main_data = expected_length

        print(self.stim_timings)

        self.overlay_temp_and_act()

    def calculate_stim_timings(self, stim_data_df):
        """
        Calculate the stimulation timings from the given DataFrame.

        Parameters:
        - stim_data_df (pd.DataFrame): DataFrame containing the stimulation data.

        Returns:
        - stim_timings (dict): Dictionary containing stimulation start and end times for each instance.
        """
        stim_timings = []
        start_time_str = self.temp_and_act_start_time_var.get()
        start_time = (datetime.strptime(start_time_str, '%H:%M:%S') -
                      datetime(1900, 1, 1)).total_seconds() / 60

        for index, row in stim_data_df.iterrows():
            cluster_size = int(row['Cluster size (num)'])
            stim_duration = row['Stim duration (sec)']
            interstim_interval = row['Interstim interval (sec)']
            stim_onset = row['Stim onset (hh:mm:ss)'].total_seconds() / 60

            stim_onset_relative = stim_onset - start_time

            stim_periods = []
            for stim_number in range(cluster_size):
                stim_start = stim_onset_relative + stim_number * \
                    (stim_duration + interstim_interval) / \
                    60
                stim_end = stim_start + stim_duration / 60
                stim_periods.append((stim_start, stim_end))

            stim_timings.append((cluster_size, stim_periods))

        return stim_timings

    def prepare_figure(self, time_column, show_nighttime=False, show_time_of_day=False):
        """
        Prepare a figure for visualizing optogenetics data with overlays.

        Parameters:
        - time_column (pd.Series): Series containing the time data.
        - show_nighttime (bool, optional): Whether to show nighttime shading. Defaults to False.
        - show_time_of_day (bool, optional): Whether to show time of day on the x-axis. Defaults to False.

        Returns:
        - fig (matplotlib.figure.Figure): The figure object.
        - ax (matplotlib.axes.Axes): The axes object.
        - scaled_time_column (pd.Series): Scaled time column.
        """
        self.delete_current_figure()
        scaled_time_column = self.scale_time_column(time_column)

        fig, ax = plt.subplots(figsize=(6, 4))

        time_unit = self.graph_settings_container_instance.time_unit_menu.get()
        show_time_of_day = (time_unit == 'time of day')

        if show_time_of_day:
            ax.set_xlabel('Time of Day')
        else:
            if time_unit == 'seconds':
                ax.set_xlabel('Time (s)')
            elif time_unit == 'hours':
                ax.set_xlabel('Time (h)')
            elif time_unit == 'minutes':
                ax.set_xlabel('Time (min)')

        if show_time_of_day:
            start_time_str = self.temp_and_act_start_time_var.get()
            if start_time_str:
                start_time = datetime.strptime(start_time_str, '%H:%M:%S')

                interval_hours = 0.5
                interval_minutes = interval_hours * 60

                minutes_since_hour_start = start_time.minute + \
                    start_time.second / 60 + start_time.microsecond / 60000000
                rounding_offset = (
                    interval_minutes - minutes_since_hour_start % interval_minutes) % interval_minutes
                closest_interval = start_time + \
                    timedelta(minutes=rounding_offset)

                time_labels = []
                current_time = closest_interval
                max_time = start_time + timedelta(minutes=time_column.max())

                while current_time <= max_time:
                    time_labels.append(current_time.strftime('%H:%M'))
                    current_time += timedelta(hours=interval_hours)

                ax.set_xticks([round(i) for i in np.linspace(
                    0, max(time_column), len(time_labels))])
                ax.set_xticklabels(
                    time_labels, rotation=45, ha="right", rotation_mode="anchor", va="center")

        if show_nighttime:
            self.add_nighttime_shading_to_plot(ax, time_column)

        ax.set_xlim(scaled_time_column.iloc[0], scaled_time_column.iloc[-1])

        return fig, ax, scaled_time_column

    def overlay_data(self, ax, temp_data=None, act_data=None, ymin=None, ymax=None):
        """
        Overlay temperature and activity data on the plot.

        Parameters:
        - ax (matplotlib.axes.Axes): The axes on which to overlay the data.
        - temp_data (pd.DataFrame, optional): DataFrame containing the temperature data. Defaults to None.
        - act_data (pd.DataFrame, optional): DataFrame containing the activity data. Defaults to None.
        - ymin (float, optional): Minimum y-axis value. Defaults to None.
        - ymax (float, optional): Maximum y-axis value. Defaults to None.

        Returns:
        - ax_act (matplotlib.axes.Axes): The axes with the activity data overlayed.
        """
        temp_present = temp_data is not None and self.graph_settings_container_instance.temperature_data_var.get()
        act_present = act_data is not None and self.graph_settings_container_instance.activity_data_var.get()

        if temp_present and act_present:
            ax.yaxis.set_visible(False)
            self.overlay_temp_on_figure(ax, temp_data, left_axis=True)
            ax_act = self.overlay_act_on_figure(ax, act_data, ymin, ymax)
        elif temp_present:
            self.overlay_temp_on_figure(ax, temp_data, left_axis=False)
        elif act_present:
            ax_act = self.overlay_act_on_figure(ax, act_data, ymin, ymax)
        else:
            ax_act = ax

        return ax_act

    def overlay_opto_stimulations(self, ax):
        """
        Overlay optogenetic stimulations on the plot.

        Parameters:
        - ax (matplotlib.axes.Axes): The axes on which to overlay the stimulations.
        """
        if self.stim_timings is None:
            return

        ymin, ymax = ax.get_ylim()

        for cluster_size, timings in self.stim_timings:
            for stim_start, stim_end in timings:
                time_unit = self.graph_settings_container_instance.time_unit_menu.get()
                time_factor = self.get_time_scale(time_unit)

                scaled_stim_start = stim_start * time_factor
                scaled_stim_end = stim_end * time_factor

                rect = plt.Rectangle(
                    (scaled_stim_start, ymin), scaled_stim_end - scaled_stim_start, ymax - ymin, color='blue', alpha=0.3)
                ax.add_patch(rect)

        ax.set_ylim(ymin, ymax)

    def save_static_inputs(self, df):
        """
        Save the static inputs to a JSON file, handling both cluster and stimulation data.

        Parameters:
        - df (pd.DataFrame): DataFrame containing the data.
        """
        data = {
            'clusters': {},
            'stimulations': {}
        }

        for _, row in df.iterrows():
            cluster_name = row['Cluster Name']
            base_cluster_name = cluster_name.rsplit(
                '_', 1)[0]

            pre_time = row['pre_stim_time'] if 'stim' in cluster_name else row['pre_cluster_time']
            post_time = row['post_stim_time'] if 'stim' in cluster_name else row['post_cluster_time']
            bin_size = row['bin_size']

            if 'stim' in cluster_name:
                data['stimulations'][base_cluster_name] = (
                    pre_time, post_time, bin_size)
            else:
                data['clusters'][base_cluster_name] = (
                    pre_time, post_time, bin_size)

        with open('cluster_static_settings.json', 'w') as f:
            json.dump(data['clusters'], f)

        with open('stim_static_settings.json', 'w') as f:
            json.dump(data['stimulations'], f)

    def load_static_inputs(self):
        """
        Load the static inputs from JSON files for both cluster and stimulation settings.

        Returns:
        - settings (dict): Dictionary containing the cluster and stimulation settings.
        """
        settings = {
            'clusters': {},
            'stimulations': {}
        }

        def load_data_from_json(file_path, data_key):
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    for name, settings_data in data.items():
                        settings[data_key][name] = {
                            'pre_time': settings_data[0],
                            'post_time': settings_data[1],
                            'bin_size': settings_data[2]
                        }
                except Exception as e:
                    print(f"Error reading JSON file {file_path}: {e}")
            else:
                with open(file_path, 'w') as f:
                    json.dump({}, f)

        load_data_from_json('cluster_static_settings.json', 'clusters')
        load_data_from_json('stim_static_settings.json', 'stimulations')

        return settings

    def populate_table(self):
        """Populate the table with cluster and stimulation data."""
        file_path_str = os.path.basename(self.file_path.get())

        for index, (cluster_name, cluster_data) in enumerate(self.data_dict[file_path_str].items()):
            # Check if the entry is for a stimulation based on naming convention
            if 'stim' in cluster_name:
                pre_time = cluster_data.get('pre_stim_time', 'N/A')
                post_time = cluster_data.get('post_stim_time', 'N/A')
                # Assumed keys for stim data
                start_time = format(cluster_data.get('stim_start', 0), '.1f')
                end_time = format(cluster_data.get('stim_end', 0), '.1f')
            else:
                pre_time = cluster_data.get('pre_cluster_time', 'N/A')
                post_time = cluster_data.get('post_cluster_time', 'N/A')
                start_time = format(cluster_data.get('start_time', 0), '.1f')
                end_time = format(cluster_data.get('end_time', 0), '.1f')

            bin_size = cluster_data.get('bin_size', 'N/A')

            # Determine the tag based on the index
            tag = "Even" if index % 2 == 0 else "Odd"

            self.table_treeview.insert('', 'end', values=(
                file_path_str, cluster_name, pre_time, post_time, bin_size, start_time, end_time), tags=(tag,))

        self.table_treeview.update_idletasks()

    def populate_data_dict(self):
        """Populate the data dictionary with cluster data and settings."""
        file_path_str = os.path.basename(self.file_path.get())

        if file_path_str not in self.data_dict:
            self.data_dict[file_path_str] = {}

        if self.data_type == 'photometry':
            self.populate_photometry_data_dict(file_path_str)
        elif self.data_type == 'optogenetics':
            self.populate_opto_data_dict(file_path_str)

        if self.data_type == 'photometry' or self.data_type == 'optogenetics':
            if self.used_default_values:
                print('Using default values for cluster/stim settings.')
                df = self.data_dict_to_df(self.data_dict)
                self.save_static_inputs(df)

    def populate_photometry_data_dict(self, file_path_str):
        """Populate the data dictionary with photometry cluster data and settings."""
        cluster_id = 1

        cluster_settings = self.load_static_inputs()

        clusters_with_inputs = [name for name, settings in cluster_settings.items(
        ) if any(str(value) != "" for value in settings.values())]

        use_stored_inputs = bool(clusters_with_inputs)

        self.used_default_values = False

        for (start_index, end_index, peak_count), cluster_data in self.cluster_dict.items():
            peak_times = cluster_data['peaks']
            alignment_index = cluster_data.get('alignment_index', -1)
            cluster_name = cluster_data['name']

            start_time = self.time_column.iloc[start_index]
            end_time = self.time_column.iloc[end_index]

            cluster_base_name = cluster_name.rsplit('_', 1)[0]
            if use_stored_inputs and cluster_base_name in cluster_settings:
                pre_cluster_time = cluster_settings[cluster_base_name]['pre_cluster_time']
                post_cluster_time = cluster_settings[cluster_base_name]['post_cluster_time']
                bin_size = cluster_settings[cluster_base_name]['bin_size']
            else:
                pre_cluster_time = "60"
                post_cluster_time = "60"
                bin_size = "10"
                self.used_default_values = True

            self.data_dict[file_path_str][cluster_name] = {
                'pre_cluster_time': pre_cluster_time,
                'post_cluster_time': post_cluster_time,
                'bin_size': bin_size,
                'start_time': start_time,
                'end_time': end_time,
                'alignment_index': alignment_index,
                'peaks': peak_times
            }

    def populate_opto_data_dict(self, file_path_str):
        """
        Populate the data dictionary with optogenetic stimulation data and settings.

        Parameters:
        - file_path_str (str): The file path string to use as the key in the data dictionary.
        """
        cluster_count = {}

        stim_settings = self.load_static_inputs()
        # Simplified check for stored inputs
        use_stored_inputs = any(stim_settings)

        self.used_default_values = False

        for cluster_size, timings in self.stim_timings:
            if cluster_size not in cluster_count:
                cluster_count[cluster_size] = 0
            cluster_count[cluster_size] += 1

            # Numbering suffix for clusters of the same size
            cluster_suffix = f"_cluster_{cluster_count[cluster_size]}"
            cluster_name = f"{cluster_size}_stim{cluster_suffix}"

            stim_start = timings[0][0]
            stim_end = timings[-1][1]

            # Use stored inputs if they exist for this cluster
            if use_stored_inputs and cluster_name in stim_settings:
                pre_stim_time = stim_settings[cluster_name]['pre_stim_time']
                post_stim_time = stim_settings[cluster_name]['post_stim_time']
                bin_size = stim_settings[cluster_name]['bin_size']
            else:
                pre_stim_time = "60"
                post_stim_time = "60"
                bin_size = "10"
                self.used_default_values = True

            self.data_dict[file_path_str][cluster_name] = {
                'pre_stim_time': pre_stim_time,
                'post_stim_time': post_stim_time,
                'bin_size': bin_size,
                'stim_start': stim_start,
                'stim_end': stim_end,
                'cluster_size': cluster_size
            }

    def update_cluster_inputs(self):
        """Update the cluster inputs in the data_dict and the table."""
        file_path_str = os.path.basename(self.file_path.get())
        pre_time = self.static_inputs_frame.pre_behaviour_time_entry.get()
        post_time = self.static_inputs_frame.post_behaviour_time_entry.get()
        bin_size = self.static_inputs_frame.bin_size_entry.get()

        selected_cluster_label = self.static_inputs_frame.selected_behaviour.get().strip()

        is_stim_update = 'stim' in selected_cluster_label.lower()

        if is_stim_update:
            stim_counts = self.get_stim_counts()
            selected_stim_label = selected_cluster_label.split()[0]
        else:
            selected_peak_label = selected_cluster_label.split()[0]

        treeview_columns = self.table_treeview.cget("columns")

        if file_path_str in self.data_dict:
            for cluster_name, cluster_data in self.data_dict[file_path_str].items():
                if is_stim_update:
                    if selected_cluster_label == "All Stims" or \
                            (selected_stim_label == "All" and "stim" in cluster_name) or \
                            (f"{selected_stim_label}_stim" in cluster_name):

                        cluster_data['pre_stim_time'] = pre_time
                        cluster_data['post_stim_time'] = post_time
                        cluster_data['bin_size'] = bin_size

                        for item in self.table_treeview.get_children():
                            if self.table_treeview.set(item, 'number_of_peaks') == cluster_name:
                                self.table_treeview.set(
                                    item, 'pre_cluster_time', pre_time)
                                self.table_treeview.set(
                                    item, 'post_cluster_time', post_time)
                                self.table_treeview.set(
                                    item, 'bin_size', bin_size)
                else:
                    if selected_cluster_label == "All Clusters" or \
                            (selected_peak_label == "All" and "Peak" in cluster_name) or \
                            (f"{selected_peak_label} Peak" in cluster_name):

                        cluster_data['pre_cluster_time'] = pre_time
                        cluster_data['post_cluster_time'] = post_time
                        cluster_data['bin_size'] = bin_size

                        for item in self.table_treeview.get_children():
                            if self.table_treeview.set(item, 'number_of_peaks') == cluster_name:
                                self.table_treeview.set(
                                    item, 'pre_cluster_time', pre_time)
                                self.table_treeview.set(
                                    item, 'post_cluster_time', post_time)
                                self.table_treeview.set(
                                    item, 'bin_size', bin_size)

        self.table_treeview.update_idletasks()
        self.annotate_clusters_with_time_period()

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
        """
        Find the offset to the target time string from the 'Date Time' column in the dataframe.

        Parameters:
        - dataframe (pd.DataFrame): DataFrame containing the 'Date Time' column.
        - target_time_str (str): Target time in the format "HH:MM:SS".

        Returns:
        - offset_seconds (float or None): Offset in seconds to the target time, or None if not found.
        - prev_time_from_data (str or None): Previous time from the data closest to the target time, or None if not found.
        """
        dataframe['DateTime'] = pd.to_datetime(dataframe['Date Time'])

        target_time = pd.to_datetime(target_time_str).time()

        # This assumes 'Date Time' is the start of the event
        dataframe['Offset'] = dataframe['DateTime'].apply(
            lambda x: (datetime.combine(x.date(), target_time) - x)
            if x.time() < target_time else pd.Timedelta(days=1)
        )

        before_target = dataframe[dataframe['Offset'] < pd.Timedelta(days=1)]
        if not before_target.empty:
            last_row_before_target = before_target.iloc[-1]
            offset_minutes = (
                last_row_before_target['Offset'].total_seconds()) / 60
            prev_time_from_data = last_row_before_target['DateTime'].strftime(
                '%H:%M:%S')
            return offset_minutes, prev_time_from_data
        else:
            print("No valid previous time found")
            return None, None

    def precalculate_data_versions(self):
        """Precalculate different versions of the data, including full and trimmed datasets."""
        data_column_name = self.data_selection_frame.selected_column_var.get()

        baseline = self.dataframe[data_column_name].median()

        self.full_dataframe = self.dataframe.copy()

        sixty_minute_indices = self.dataframe[self.dataframe.iloc[:, 0] >= 60].index

        if sixty_minute_indices.any():
            sixty_minute_index = sixty_minute_indices[0]
            sliced_dataframe = self.dataframe[sixty_minute_index:]
            below_baseline_indices = sliced_dataframe[sliced_dataframe[data_column_name]
                                                      <= baseline].index

            if below_baseline_indices.any():
                first_idx_below_baseline_after_60_min = below_baseline_indices[0]
                first_idx_to_use = max(
                    sixty_minute_index, first_idx_below_baseline_after_60_min)
            else:
                first_idx_below_baseline_after_60_min = None
                first_idx_to_use = sixty_minute_index
        else:
            sixty_minute_index = None
            first_idx_below_baseline_after_60_min = None
            first_idx_to_use = 0  # default to the start if no sixty minute index found

        if first_idx_to_use is not None and first_idx_to_use > 0:
            self.seconds_removed = self.dataframe.iloc[first_idx_to_use, 0] * 60
            self.trimmed_dataframe = self.dataframe.iloc[first_idx_to_use:].reset_index(
                drop=True)
            self.trimmed_dataframe.iloc[:, 0] = self.trimmed_dataframe.iloc[:,
                                                                            0] - self.trimmed_dataframe.iloc[0, 0]
        else:
            self.seconds_removed = 0
            self.trimmed_dataframe = self.dataframe.copy()

    def get_current_photometry_data(self):
        """
        Get the current photometry data based on the selected options.

        Returns:
        - pd.Series: Time column of the current photometry data.
        - pd.Series: Data column of the current photometry data.
        - list: List of detected peaks in the data.
        - list: List of final clusters in the data.
        - dict: Dictionary of grouped clusters by peak count.
        """
        data_column_name = self.data_selection_frame.selected_column_var.get()

        if self.graph_settings_container_instance.remove_first_60_minutes_var.get():
            self.dataframe = self.trimmed_dataframe.copy()
        else:
            self.dataframe = self.full_dataframe.copy()

        detected_peaks = self.detect_peaks_with_optimal_prominence(
            self.dataframe[data_column_name])

        clusters_final, self.cluster_dict = self.identify_clusters(self.dataframe.iloc[:, 0],
                                                                   self.dataframe[data_column_name], detected_peaks)

        grouped_clusters = self.group_clusters_by_peak_count(self.cluster_dict)

        return self.dataframe.iloc[:, 0], self.dataframe[data_column_name], detected_peaks, clusters_final, grouped_clusters

    def get_time_scale(self, time_unit):
        """
        Get the scaling factor for the given time unit.

        Parameters:
        - time_unit (str): The unit of time ('minutes', 'seconds', 'hours', or 'time of day').

        Returns:
        - float or None: Scaling factor for the time unit, or None for 'time of day'.
        """
        if time_unit == 'minutes':
            return 1
        elif time_unit == 'seconds':
            return 60
        elif time_unit == 'hours':
            return 1 / 60
        elif time_unit == 'time of day':
            return None

    def create_photometry_figure(self, ax, time_column, data_column, peak_indices, clusters, show_nighttime=False):
        """
        Create a figure with data, peaks, and clusters.

        Parameters:
        - ax (matplotlib.axes.Axes): The axes on which to plot the data.
        - time_column (pd.Series): Series containing the time data.
        - data_column (pd.Series): Series containing the photometry data.
        - peak_indices (list): List of indices where peaks are detected.
        - clusters (list): List of clusters in the data.
        - show_nighttime (bool, optional): Whether to show nighttime shading. Defaults to False.
        """

        scaled_time_column = self.scale_time_column(time_column)

        ax.plot(scaled_time_column, data_column, label="Data",
                color=self.settings_manager.selected_photometry_line_color,
                linewidth=self.settings_manager.selected_photometry_line_width)

        median_value = data_column.median()
        mean_value = data_column.mean()

        baseline_value = mean_value if median_value == 0 else median_value

        baseline_multiplier = float(
            self.baseline_multiplier.get().strip() or 1) - 1

        baseline = baseline_value + (baseline_multiplier * abs(baseline_value))

        if self.baseline_thickness.get() != '0':
            ax.plot([scaled_time_column.iloc[0], scaled_time_column.iloc[-1]], [baseline, baseline], color=self.baseline_color.get(),
                    linestyle=self.baseline_style.get(), linewidth=int(self.baseline_thickness.get()), label="Baseline")

        if show_nighttime:
            self.add_nighttime_shading_to_plot(ax, scaled_time_column)

        ax.plot(scaled_time_column.iloc[peak_indices], data_column.iloc[peak_indices] + int(self.y_offset_peak_symbol.get()),
                color=self.label_color_var.get(),
                marker=self.label_symbol_var.get(),
                linestyle='',
                label="Peaks",
                markersize=int(self.label_size_var.get()))

        for cluster in clusters:
            start = scaled_time_column.iloc[cluster[0]]
            end = scaled_time_column.iloc[min(
                cluster[1], len(scaled_time_column) - 1)]

            ymin = data_column.min()
            ymax_data = data_column.iloc[cluster[0]:cluster[1]].max()
            ymax = ymax_data * float(self.cluster_box_height_modifier.get())

            cluster_box = plt.Rectangle((start, ymin), end - start, ymax - ymin, color=self.cluster_box_color.get(),
                                        alpha=float(self.cluster_box_alpha.get()))

            burst_count = sum(
                1 for peak in peak_indices if cluster[0] <= peak < cluster[1])

            annotation_x = (start + end) / 2
            annotation_y = ymax
            ax.annotate(str(burst_count), (annotation_x, annotation_y), textcoords="offset points",
                        xytext=(0, float(self.y_for_peak_count.get())), ha='center', fontsize=self.peak_count_size_var.get(), color=self.peak_count_color_var.get())

            cluster_key = self.format_cluster_string(burst_count)
            if cluster_key not in self.cluster_display_status or self.cluster_display_status[cluster_key].get():
                ax.add_patch(cluster_box)
                if cluster_key not in self.cluster_boxes:
                    self.cluster_boxes[cluster_key] = []
                self.cluster_boxes[cluster_key].append(cluster_box)

        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.set_ylim(data_column.min(), (data_column.max() * 1.1))

        return ax

    def is_cluster_in_nighttime(self, cluster_start_minutes):
        """
        Check if a cluster's start time falls within the nighttime periods.

        Parameters:
        - cluster_start_minutes (float): The start time of the cluster in minutes since the start of data collection.

        Returns:
        - bool: True if the cluster start time is within a nighttime period, False otherwise.
        """
        base_date = datetime.strptime(self.date, '%y-%m-%d').date()
        start_time = pd.to_datetime(
            self.temp_and_act_start_time_var.get(), format='%H:%M:%S').time()

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

    def open_label_settings_popup(self):
        """Opens a pop-up window to set the label settings."""
        self.popup = tk.Toplevel(self, bg='snow')
        self.popup.title("Cluster Label Settings")
        bold_large_font = ('Helvetica', 10, 'bold')

        self.peak_label_frame = tk.LabelFrame(
            self.popup, text="Peak Label Settings", bg='snow', font=bold_large_font)
        self.peak_label_frame.grid(
            row=0, column=0, padx=10, pady=10, sticky='nsew')

        self.label_color_var = tk.StringVar(
            value=self.settings_manager.selected_label_color)
        tk.Button(self.peak_label_frame, text="Peak Symbol Colour", command=self.choose_label_color).grid(
            row=0, column=0, columnspan=2, padx=10, pady=5)

        self.symbol_options = ["o", "*", "s", "D", "^", "v", "<", ">"]
        self.label_symbol_var = tk.StringVar(
            value=self.settings_manager.selected_label_symbol)
        tk.Label(self.peak_label_frame, text="Peak Symbol:", bg='snow').grid(
            row=1, column=0, sticky=tk.W, padx=10, pady=5)
        symbol_dropdown = ttk.Combobox(self.peak_label_frame, textvariable=self.label_symbol_var,
                                       values=self.symbol_options, state='readonly', width=4)
        symbol_dropdown.grid(row=1, column=1, padx=10, pady=5)

        self.label_size_var = tk.StringVar(
            value=str(self.settings_manager.selected_label_size))
        tk.Label(self.peak_label_frame, text="Peak Symbol Size:", bg='snow').grid(
            row=2, column=0, sticky=tk.W, padx=10, pady=5)
        tk.Entry(self.peak_label_frame, textvariable=self.label_size_var,
                 width=7).grid(row=2, column=1, padx=10, pady=5)

        self.y_offset_peak_symbol = tk.StringVar(
            value=str(self.settings_manager.selected_y_offset_peak_symbol))
        tk.Label(self.peak_label_frame, text="Peak Symbol Y-Offset:",
                 bg='snow').grid(row=3, column=0, sticky=tk.W, padx=10, pady=5)
        tk.Entry(self.peak_label_frame, textvariable=self.y_offset_peak_symbol,
                 width=7).grid(row=3, column=1, padx=10, pady=5)

        self.peak_count_label_frame = tk.LabelFrame(
            self.popup, text="Peak Count Settings", bg='snow', font=bold_large_font)
        self.peak_count_label_frame.grid(
            row=1, column=0, padx=10, pady=10, sticky='nsew')

        self.peak_count_color_var = tk.StringVar(
            value=self.settings_manager.selected_peak_count_color)
        tk.Button(self.peak_count_label_frame, text="Peak Number Colour",
                  command=self.choose_peak_count_color).grid(row=0, column=0, columnspan=2, padx=10, pady=5)

        self.peak_count_size_var = tk.StringVar(
            value=str(self.settings_manager.selected_peak_count_size))
        tk.Label(self.peak_count_label_frame, text="Peak Number Font Size:",
                 bg='snow').grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        tk.Entry(self.peak_count_label_frame, textvariable=self.peak_count_size_var,
                 width=7).grid(row=1, column=1, padx=10, pady=5)

        self.y_for_peak_count = tk.StringVar(
            value=str(self.settings_manager.selected_y_for_peak_count))
        tk.Label(self.peak_count_label_frame, text="Y Offset:", bg='snow').grid(
            row=2, column=0, sticky=tk.W, padx=10, pady=5)
        tk.Entry(self.peak_count_label_frame, textvariable=self.y_for_peak_count,
                 width=7).grid(row=2, column=1, padx=10, pady=5)

        self.baseline_label_frame = tk.LabelFrame(
            self.popup, text="Baseline Settings", bg='snow', font=bold_large_font)
        self.baseline_label_frame.grid(
            row=0, column=1, padx=10, pady=10, sticky='nsew')

        self.baseline_color = tk.StringVar(
            value=self.settings_manager.selected_baseline_color)
        tk.Button(self.baseline_label_frame, text="Baseline Symbol Colour",
                  command=self.choose_baseline_color).grid(row=0, column=0, columnspan=2, padx=10, pady=5)

        self.baseline_multiplier = tk.StringVar(
            value=self.settings_manager.selected_baseline_multiplier)
        tk.Label(self.baseline_label_frame, text="Cluster End Multiplier (Empty = Median):",
                 bg='snow').grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        tk.Entry(self.baseline_label_frame, textvariable=self.baseline_multiplier,
                 width=7).grid(row=1, column=1, padx=10, pady=5)

        self.baseline_style_options = ['-', '--', '-.', ':']
        self.baseline_style = tk.StringVar(
            value=self.settings_manager.selected_baseline_style)
        tk.Label(self.baseline_label_frame, text="Baseline Symbol Style:",
                 bg='snow').grid(row=2, column=0, sticky=tk.W, padx=10, pady=5)
        baseline_style_dropdown = ttk.Combobox(self.baseline_label_frame, textvariable=self.baseline_style, state='readonly', values=self.baseline_style_options,
                                               width=4)
        baseline_style_dropdown.grid(row=2, column=1, padx=10, pady=5)

        self.baseline_thickness = tk.StringVar(
            value=self.settings_manager.selected_baseline_thickness)
        tk.Label(self.baseline_label_frame, text="Baseline Thickness:",
                 bg='snow').grid(row=3, column=0, sticky=tk.W, padx=10, pady=5)
        tk.Entry(self.baseline_label_frame, textvariable=self.baseline_thickness,
                 width=7).grid(row=3, column=1, padx=10, pady=5)

        self.cluster_box_frame = tk.LabelFrame(
            self.popup, text="Cluster Box Settings", bg='snow', font=bold_large_font)
        self.cluster_box_frame.grid(
            row=1, column=1, padx=10, pady=10, sticky='nsew')

        self.cluster_box_color = tk.StringVar(
            value=self.settings_manager.selected_cluster_box_color)
        tk.Button(self.cluster_box_frame, text="Cluster Box Colour", command=self.choose_cluster_box_color).grid(
            row=0, column=0, columnspan=2, padx=10, pady=5)

        self.cluster_box_alpha = tk.StringVar(
            value=self.settings_manager.selected_cluster_box_alpha)
        tk.Label(self.cluster_box_frame, text="Cluster Box Alpha:", bg='snow').grid(
            row=1, column=0, sticky=tk.W, padx=10, pady=5)
        tk.Entry(self.cluster_box_frame, textvariable=self.cluster_box_alpha,
                 width=7).grid(row=1, column=1, padx=10, pady=5)

        self.cluster_box_height_modifier = tk.StringVar(
            value=self.settings_manager.selected_cluster_box_height_modifier)
        tk.Label(self.cluster_box_frame, text="Cluster Box Height Modifier:",
                 bg='snow').grid(row=2, column=0, sticky=tk.W, padx=10, pady=5)
        tk.Entry(self.cluster_box_frame, textvariable=self.cluster_box_height_modifier,
                 width=7).grid(row=2, column=1, padx=10, pady=5)

        self.peak_label_frame.grid_columnconfigure(0, weight=1)
        self.peak_count_label_frame.grid_columnconfigure(0, weight=1)
        self.baseline_label_frame.grid_columnconfigure(0, weight=1)
        self.cluster_box_frame.grid_columnconfigure(0, weight=1)

        save_and_close_button = tk.Button(self.popup, text="Save & Close",
                                          command=lambda: self.save_and_close_label_settings(self.popup))
        save_and_close_button.grid(row=4, column=0, columnspan=2, pady=10)

        self.popup.update_idletasks()
        center_window_on_screen(self.popup)

    def choose_baseline_color(self):
        """Open a color chooser dialog to select the baseline colour."""
        color = colorchooser.askcolor()
        if color[1]:
            self.baseline_color.set(color[1])
        self.popup.lift()

    def choose_label_color(self):
        """Open a color chooser dialog to select the baseline colour."""
        color = colorchooser.askcolor()
        if color[1]:
            self.label_color_var.set(color[1])
        self.popup.lift()

    def choose_peak_count_color(self):
        """Open a color chooser dialog to select the peak count colour."""
        color = colorchooser.askcolor()
        if color[1]:
            self.peak_count_color_var.set(color[1])
        self.popup.lift()

    def choose_cluster_box_color(self):
        """Open a color chooser dialog to select the cluster box colour."""
        color = colorchooser.askcolor()
        if color[1]:
            self.cluster_box_color.set(color[1])
        self.popup.lift()

    def save_and_close_label_settings(self, popup):
        """
        Handle the save & close button click to save label settings and close the popup.

        Parameters:
        - popup (tk.Toplevel): The popup window to close.
        """
        current_baseline_multiplier = self.settings_manager.selected_baseline_multiplier

        self.settings_manager.selected_label_color = self.label_color_var.get()
        self.settings_manager.selected_label_symbol = self.label_symbol_var.get()
        self.settings_manager.selected_label_size = int(
            self.label_size_var.get())
        self.settings_manager.selected_y_offset_peak_symbol = int(
            self.y_offset_peak_symbol.get())
        self.settings_manager.selected_peak_count_color = self.peak_count_color_var.get()
        self.settings_manager.selected_peak_count_size = int(
            self.peak_count_size_var.get())
        self.settings_manager.selected_y_for_peak_count = int(
            self.y_for_peak_count.get())
        self.settings_manager.selected_baseline_multiplier = self.baseline_multiplier.get()
        self.settings_manager.selected_baseline_color = self.baseline_color.get()
        self.settings_manager.selected_baseline_style = self.baseline_style.get()
        self.settings_manager.selected_baseline_thickness = self.baseline_thickness.get()
        self.settings_manager.selected_cluster_box_color = self.cluster_box_color.get()
        self.settings_manager.selected_cluster_box_alpha = self.cluster_box_alpha.get()
        self.settings_manager.selected_cluster_box_height_modifier = self.cluster_box_height_modifier.get()

        self.settings_manager.save_variables()

        if current_baseline_multiplier != self.settings_manager.selected_baseline_multiplier:
            # If it has changed, recalculate the clusters and related data
            self.reset_clusters_based_on_user_input()
            return

        if hasattr(self, 'figure_canvas'):
            if self.act_data is not None and self.temp_data is not None:
                self.visualize_photometry_data_with_overlays(self.time_column, self.data_column, self.detected_peaks, self.clusters_final, self.graph_canvas, self.temp_data,
                                                             self.act_data, show_nighttime=True)
            else:
                self.visualize_photometry_data_with_overlays(
                    self.time_column, self.data_column, self.detected_peaks, self.clusters_final, self.graph_canvas)

        popup.destroy()

    def extract_date_and_mouse_number(self, file_path_var, mouse_name):
        """
        Extract the date and mouse number from the file path.

        Parameters:
        - file_path_var (tk.StringVar): StringVar containing the file path.
        - mouse_name (str): Name of the mouse.

        Returns:
        - date (str or None): Extracted date in the format "dd-mm-yyyy" if found, otherwise None.
        - mouse_name (str): Name of the mouse.
        """
        # TODO Check this function
        main_file_name = os.path.basename(file_path_var.get())
        date_match = re.search(r"(\d+)-(\d+)-(\d+)", main_file_name)
        date = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}" if date_match else None
        return date, mouse_name

    def retrieve_associated_files(self, date, file_path_var):
        """
        Retrieve the associated temperature and activity files based on the given date.

        Parameters:
        - date (str): The date to filter the telemetry files.
        - file_path_var (tk.StringVar): StringVar containing the file path.

        Returns:
        - act_file_path (str or None): Path to the activity file or None if not found.
        - temp_file_path (str or None): Path to the temperature file or None if not found.
        """
        main_file_directory = os.path.dirname(file_path_var.get())
        if not os.path.exists(main_file_directory):
            return None, None

        date_pattern = re.compile(rf'\b{date}\b')

        all_files = [f for f in os.listdir(
            main_file_directory) if not f.startswith('._')]

        temp_files = [f for f in all_files if 'temp' in f.lower()
                      and date_pattern.search(f)]
        act_files = [f for f in all_files if 'act' in f.lower()
                     and date_pattern.search(f)]

        temp_file_path = os.path.join(
            main_file_directory, temp_files[0]) if temp_files else None
        act_file_path = os.path.join(
            main_file_directory, act_files[0]) if act_files else None

        if (not temp_file_path or not act_file_path) and self.settings_manager.telemetry_folder_path:
            telemetry_directory = self.settings_manager.telemetry_folder_path
            if os.path.exists(telemetry_directory):
                if not temp_file_path:
                    temp_files = [f for f in os.listdir(
                        telemetry_directory) if 'temp' in f.lower() and date in f]
                    temp_file_path = os.path.join(
                        telemetry_directory, temp_files[0]) if temp_files else None
                if not act_file_path:
                    act_files = [f for f in os.listdir(
                        telemetry_directory) if 'act' in f.lower() and date in f]
                    act_file_path = os.path.join(
                        telemetry_directory, act_files[0]) if act_files else None

        self.associated_temp_data_entry.set(
            temp_files[0] if temp_files else "")
        self.associated_act_data_entry.set(act_files[0] if act_files else "")

        self.update_idletasks()

        return act_file_path, temp_file_path

    def refresh_graph_display(self):
        pass

    def update_duration_box(self):
        pass

    def handle_behaviour_change(self, *args, **kwargs):
        pass

    def update_box_colors_and_behaviour_options(self, behaviour, color_rgb):
        pass

    def save_and_close(self, popup=None, close=True):
        pass

    def create_sheets_for_clusters(self, writer):
        """
        Create and populate sheets for clusters in an Excel writer.

        Parameters:
        - writer (pd.ExcelWriter): The Excel writer object to create sheets in.
        """
        unique_cluster_numbers = self.mean_cluster_data.keys()
        sorted_cluster_numbers = sorted(unique_cluster_numbers)

        for cluster_number in sorted_cluster_numbers:
            if cluster_number == 1:
                sheet_name = 'Clusters with 1 Peak'
            else:
                sheet_name = f'Clusters with {cluster_number} peaks'
            self.populate_cluster_sheet(writer, sheet_name, cluster_number)

            self.set_variable_column_widths(writer.sheets[sheet_name])

        for cluster_number in sorted_cluster_numbers:
            if cluster_number == 1:
                sheet_name = 'Raw, Clusters with 1 Peak'
            else:
                sheet_name = f'Raw, Clusters with {cluster_number} Peaks'
            self.populate_raw_data_sheet(writer, sheet_name, cluster_number)

    def calculate_column_widths(self, headers):
        """
        Calculate the optimal column widths based on the headers.

        Parameters:
        - headers (list): List of column headers.

        Returns:
        - list: List of optimal column widths.
        """
        return [max(len(str(header)), 10) for header in headers]

    def populate_raw_data_sheet(self, writer, sheet_name, cluster_number):
        """
        Populate a sheet with raw data for a given cluster number.

        Parameters:
        - writer (pd.ExcelWriter): The Excel writer object to create sheets in.
        - sheet_name (str): Name of the sheet to create.
        - cluster_number (int): The cluster number to get data for.
        """
        file_path_str = os.path.basename(self.file_path.get())
        cluster_data = self.mean_cluster_data.get(cluster_number)
        worksheet = writer.book.add_worksheet(sheet_name)

        self.bold = writer.book.add_format({'bold': True})
        self.all_cell_format = writer.book.add_format(
            {'bold': True, 'bg_color': '#e0eadf'})
        self.day_cell_format = writer.book.add_format(
            {'bold': True, 'bg_color': 'yellow'})
        self.night_cell_format = writer.book.add_format(
            {'bold': True, 'bg_color': '#8f9ed9'})

        full_temp_data = cluster_data["full"]["raw_temp_data"]
        full_act_data = cluster_data["full"]["raw_act_data"]
        if self.data_type == 'photometry':
            full_photometry_data = cluster_data["full"]["photometry_cluster_data"]

        row_idx, col_idx = 0, 0

        next_col_idx, full_row_idx_after_temp = self.write_raw_data_to_sheet(
            worksheet, writer, row_idx, col_idx, 'Full', 'Temp', full_temp_data)
        next_col_idx, full_row_idx_after_act = self.write_raw_data_to_sheet(
            worksheet, writer, row_idx, next_col_idx, 'Full', 'Act', full_act_data)
        if self.data_type == 'photometry':
            next_col_idx, full_row_idx_after_photometry = self.write_raw_data_to_sheet(worksheet, writer, row_idx, next_col_idx, 'Full', 'Photometry',
                                                                                       full_photometry_data)

        col_idx = 0
        row_idx = full_row_idx_after_temp

        if cluster_data["day"].get("mean_temp_data") is not None:
            day_temp_data = cluster_data["day"]["raw_temp_data"]
            day_act_data = cluster_data["day"]["raw_act_data"]
            if self.data_type == 'photometry':
                day_photometry_data = cluster_data["day"]["photometry_cluster_data"]

            next_col_idx, day_row_idx_after_temp = self.write_raw_data_to_sheet(
                worksheet, writer, row_idx, col_idx, 'Day', 'Temp', day_temp_data)
            next_col_idx, day_row_idx_after_act = self.write_raw_data_to_sheet(
                worksheet, writer, row_idx, next_col_idx, 'Day', 'Act', day_act_data)
            if self.data_type == 'photometry':
                next_col_idx, day_row_idx_after_photometry = self.write_raw_data_to_sheet(worksheet, writer, row_idx, next_col_idx, 'Day', 'Photometry',
                                                                                          day_photometry_data)

            row_idx = day_row_idx_after_temp
            col_idx = 0

        if cluster_data["night"].get("mean_temp_data") is not None:
            night_temp_data = cluster_data["night"]["raw_temp_data"]
            night_act_data = cluster_data["night"]["raw_act_data"]
            if self.data_type == 'photometry':
                night_photometry_data = cluster_data["night"]["photometry_cluster_data"]

            next_col_idx, night_row_idx_after_temp = self.write_raw_data_to_sheet(
                worksheet, writer, row_idx, col_idx, 'Night', 'Temp', night_temp_data)
            next_col_idx, night_row_idx_after_act = self.write_raw_data_to_sheet(
                worksheet, writer, row_idx, next_col_idx, 'Night', 'Act', night_act_data)
            if self.data_type == 'photometry':
                next_col_idx, night_row_idx_after_photometry = self.write_raw_data_to_sheet(worksheet, writer, row_idx, next_col_idx, 'Night', 'Photometry',
                                                                                            night_photometry_data)

            row_idx = night_row_idx_after_temp
            col_idx = 1

        if cluster_data["day"].get("mean_temp_data") is not None:
            row_for_night = day_row_idx_after_temp
            night_col_idx = 2
        else:
            row_for_night = full_row_idx_after_temp
            night_col_idx = 1

        # Conditionally add navigation hyperlinks
        if cluster_data["day"].get("mean_temp_data") is not None:
            self.add_navigation_hyperlink(
                worksheet, writer, 'Day', full_row_idx_after_temp + 1, 1)

        if cluster_data["night"].get("mean_temp_data") is not None:
            self.add_navigation_hyperlink(
                worksheet, writer, 'Night', row_for_night + 1, night_col_idx)

        worksheet.set_column(0, 30, 20.5)

    def add_home_hyperlink(self, worksheet, writer, col_idx, row_idx):
        """
        Add a hyperlink that takes the user back to cell A1.

        Parameters:
        - worksheet (xlsxwriter.worksheet.Worksheet): The worksheet object to add the hyperlink to.
        - writer (pd.ExcelWriter): The writer object used for creating Excel files.
        - col_idx (int): The column index where the hyperlink should be placed.
        - row_idx (int): The row index where the hyperlink should be placed.
        """
        hyperlink_format = writer.book.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'underline': True,
            'font_color': 'blue'
        })

        worksheet.write_url(row_idx, col_idx, "internal:'{}'!A1".format(
            worksheet.name), string='Go to Full Data', cell_format=hyperlink_format)

    def write_raw_data_to_sheet(self, worksheet, writer, row_idx, col_idx, period, data_type, data):
        """
        Write data to the worksheet with specified headings and return next column and row indices.

        Parameters:
        - worksheet (xlsxwriter.worksheet.Worksheet): The worksheet object to write data to.
        - writer (pd.ExcelWriter): The writer object used for creating Excel files.
        - row_idx (int): The starting row index to write data.
        - col_idx (int): The starting column index to write data.
        - period (str): The period of the data ('Full', 'Day', 'Night').
        - data_type (str): The type of data ('Temp', 'Act', 'Photometry').
        - data (pd.DataFrame or list): The data to write.

        Returns:
        - next_col_idx (int): The next column index after writing the data.
        - next_row_idx (int): The next row index after writing the data.
        """
        worksheet.write(row_idx, col_idx,
                        f'Raw data: {period} - {data_type}', self.bold)

        if (period == 'Day' or period == 'Night') and data_type == 'Temp':
            self.add_home_hyperlink(worksheet, writer, col_idx + 1, row_idx)

        row_idx += 1

        next_col_idx = col_idx

        if isinstance(data, pd.DataFrame):
            if not data.empty:
                for col_num, header in enumerate(data.columns):
                    worksheet.write(row_idx, col_idx +
                                    col_num, header, self.bold)
                for row_num, row_data in enumerate(data.itertuples(index=False, name=None)):
                    for col_num, value in enumerate(row_data):
                        try:
                            worksheet.write(row_idx + row_num + 1,
                                            col_idx + col_num, value)
                        except:
                            pass
                next_col_idx += len(data.columns)
                next_row_idx = row_idx + len(data) + 1
            else:
                next_row_idx = row_idx
        elif isinstance(data, list):
            for row_num, row_data in enumerate(data):
                for col_num, value in enumerate(row_data):
                    worksheet.write(row_idx + row_num,
                                    col_idx + col_num, value)
            next_col_idx += len(data[0]) if data else 1
            next_row_idx = row_idx + len(data) + 1 if data else row_idx
        else:
            next_row_idx = row_idx

        next_row_idx += 1
        next_col_idx += 1
        return next_col_idx, next_row_idx

    def add_navigation_hyperlink(self, worksheet, writer, period, row_idx, col_idx):
        """
        Add a hyperlink for quick navigation to 'Day' or 'Night' section, with the target cell at the top-left corner.

        Parameters:
        - worksheet (xlsxwriter.worksheet.Worksheet): The worksheet object to add the hyperlink to.
        - writer (pd.ExcelWriter): The writer object used for creating Excel files.
        - period (str): 'Day' or 'Night'.
        - row_idx (int): The row index where the period data starts.
        - col_idx (int): The column index where the period data starts.
        """
        hyperlink_format = writer.book.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'underline': True,
            'font_color': 'blue'
        })

        # Define the target cell
        # Adding 1 to row_idx because Excel is 1-based
        target_cell = f"A{row_idx + 1}"

        worksheet.write_url(
            0, col_idx, f"internal:'{worksheet.name}'!{target_cell}", string=f'Go to {period} Data', cell_format=hyperlink_format)

    def populate_cluster_sheet(self, writer, sheet_name, cluster_number):
        """
        Populate a sheet with cluster data for a given cluster number.

        Parameters:
        - writer (pd.ExcelWriter): The Excel writer object to create sheets in.
        - sheet_name (str): Name of the sheet to create.
        - cluster_number (int): The cluster number to get data for.
        """
        file_path_str = os.path.basename(self.file_path.get())

        worksheet = writer.book.add_worksheet(sheet_name)

        self.bold = writer.book.add_format({'bold': True})
        self.all_cell_format = writer.book.add_format(
            {'bold': True, 'bg_color': '#e0eadf'})
        self.day_cell_format = writer.book.add_format(
            {'bold': True, 'bg_color': 'yellow'})
        self.night_cell_format = writer.book.add_format(
            {'bold': True, 'bg_color': '#8f9ed9'})

        temp_act_headers = ['Time (s)', 'Mean Temp',
                            'SEM Temp', 'Mean Act', 'SEM Act']

        row_idx = 0

        if self.data_type == 'photometry':
            day_clusters = sum(1 for key, info in self.cluster_dict.items(
            ) if info['time_period'] == 'Day' and key[2] == cluster_number)
            night_clusters = sum(1 for key, info in self.cluster_dict.items(
            ) if info['time_period'] == 'Night' and key[2] == cluster_number)
        else:
            file_path_str = os.path.basename(self.file_path.get())
            file_data = self.data_dict[file_path_str]

            day_clusters = sum(1 for key, info in file_data.items(
            ) if info['time_period'] == 'Day' and info['cluster_size'] == cluster_number)
            night_clusters = sum(1 for key, info in file_data.items(
            ) if info['time_period'] == 'Night' and info['cluster_size'] == cluster_number)

        full_clusters = day_clusters + night_clusters

        cluster_counts = {
            'full': full_clusters,
            'day': day_clusters,
            'night': night_clusters
        }

        for period in ['full', 'day', 'night']:
            period_data = self.mean_cluster_data.get(
                cluster_number, {}).get(period)
            if period_data and 'binned_mean_temp_data' in period_data:
                if period == 'full':
                    row_idx = 0
                    peak_or_peaks = "Peak" if cluster_number == 1 else "Peaks"

                    hyperlink_label = f'Go to Clusters with {cluster_number} {peak_or_peaks}: raw data'
                    hyperlink_target = f"internal: 'Raw, Clusters with {cluster_number} {peak_or_peaks}'!A1"
                    hyperlink_format = writer.book.add_format({
                        'align': 'center',
                        'valign': 'vcenter',
                        'underline': True,
                        'font_color': 'blue'
                    })

                    worksheet.write_url(
                        row_idx, 1, hyperlink_target, hyperlink_format, string=hyperlink_label)
                    worksheet.merge_range(
                        row_idx, 1, row_idx, 4, hyperlink_label, hyperlink_format)
                else:
                    row_idx += 1  # Skip a row for spacing

                period_title = f"{period.capitalize()} Clusters({cluster_counts[period]})"
                worksheet.write(row_idx, 0, period_title, self.bold)

                row_idx += 1  # Skip a row for spacing

                for col_num, header in enumerate(temp_act_headers):
                    worksheet.write(row_idx, col_num, header, self.bold)
                row_idx += 1
                for bin_idx, row_temp in period_data['binned_mean_temp_data'].iterrows():
                    if bin_idx not in period_data['binned_mean_act_data'].index:
                        continue  # Skip this iteration if bin_range is not found

                    bin_label = row_temp['Bin Range']

                    worksheet.write(row_idx, 0, bin_label)
                    worksheet.write(row_idx, 1, row_temp['Mean'])
                    worksheet.write(row_idx, 2, row_temp['SEM'])
                    row_act = period_data['binned_mean_act_data'].loc[bin_idx]
                    worksheet.write(row_idx, 3, row_act['Mean'])
                    worksheet.write(row_idx, 4, row_act['SEM'])
                    row_idx += 1
            else:
                row_idx += 1  # Leave a blank row for spacing

        file_data = self.data_dict[file_path_str]

        self.write_cluster_details(
            worksheet, cluster_number, file_data, self.cluster_dict)

    def generate_cluster_headings(self, file_data, cluster_number):
        """
        Generate cluster headings based on the given number of peaks.

        Parameters:
        - file_data (dict): Dictionary containing the file data.
        - cluster_number (int): The number of peaks in the clusters.

        Returns:
        - cluster_headings (list): List of cluster headings.
        """
        cluster_headings = ['Cluster ID']

        if self.data_type == 'photometry':
            # Pattern to match the cluster keys with the given number of peaks, ignoring the cluster ID
            pattern = re.compile(rf'^{cluster_number} Peaks? in Cluster_\d+$')
            def format_key(key): return key
        else:
            # Pattern to match the cluster keys with the given number of stimuli
            pattern = re.compile(rf'^{cluster_number}_stim_cluster_\d+$')
            def format_key(
                key): return f"{cluster_number} cluster in {key.split('_', 1)[1]}"

        for cluster_key in file_data:
            if pattern.match(cluster_key):
                cluster_headings.append(format_key(cluster_key))

        return cluster_headings

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
        """
        Write the details of clusters to the worksheet.

        Parameters:
        - worksheet (xlsxwriter.worksheet.Worksheet): The worksheet object to write data to.
        - cluster_number (int): The number of peaks in the clusters.
        - file_data (dict): Dictionary containing the file data.
        - cluster_dict (dict): Dictionary containing cluster information.
        """
        if self.data_type == 'photometry':
            data_column_name = self.data_selection_frame.selected_column_var.get()
            delta_symbol = '\u0394'
            data_column_name = {'dFoF_465': f' ({delta_symbol}F/F)', '490DF/F': f' ({delta_symbol}F/F)',
                                'Z_465': ' (Z-score)'}.get(data_column_name, '')

            worksheet.write(0, 6, 'Photometry Cluster Parameters', self.bold)
            worksheet.write(0, 7, f'Data Column exported:', self.bold)
            worksheet.write(0, 8, f'{data_column_name}', self.bold)
        else:
            worksheet.write(0, 6, 'Stim Parameters', self.bold)

        row_idx, col_idx = 3, 6
        self.write_cluster_static_inputs(
            worksheet, 1, 7, cluster_number, file_data)

        all_cluster_headings = self.generate_cluster_headings(
            file_data, cluster_number)
        rows_to_skip_all = len(all_cluster_headings)

        cluster_basic_headings = [
            'Cluster Start Time (min)', 'Cluster End Time (min)', 'Cluster Duration (min)', 'Cluster alignment peak time']
        worksheet.write(row_idx, col_idx, 'Full', self.all_cell_format)
        row_idx += 1

        row_idx, col_idx = self.write_headings(
            worksheet, row_idx, all_cluster_headings, cluster_basic_headings, rows_to_skip_all)

        if self.data_type == 'photometry':
            peak_time_headings = [
                f'Peak {i + 1} Time (min)' for i in range(cluster_number)]
            peak_isi_headings = [
                f'Interpeak Interval(min)[{i + 1}] - [{i + 2}]' for i in range(cluster_number - 1)]

            peak_amp_unit = {'dFoF_465': f' ({delta_symbol}F/F)', '490DF/F': f' ({delta_symbol}F/F)',
                             'Z_465': ' (Z-score)'}.get(data_column_name, '')
            peak_amp_headings = [
                f'Peak {i + 1} Amplitude{peak_amp_unit}' for i in range(cluster_number)]

            row_idx, col_idx = self.write_headings(
                worksheet, row_idx, all_cluster_headings, peak_time_headings, rows_to_skip_all)

            row_idx, col_idx = self.write_headings(
                worksheet, row_idx, all_cluster_headings, peak_amp_headings, rows_to_skip_all
            )
            if cluster_number != 1:
                row_idx, col_idx = self.write_headings(
                    worksheet, row_idx, all_cluster_headings, peak_isi_headings, rows_to_skip_all
                )
        if self.data_type == 'photometry':
            full_clusters = [
                details for key, details in cluster_dict.items() if key[2] == cluster_number]
            day_clusters = [details for key, details in cluster_dict.items(
            ) if key[2] == cluster_number and details['time_period'] == 'Day']
            night_clusters = [details for key, details in cluster_dict.items(
            ) if key[2] == cluster_number and details['time_period'] == 'Night']

        else:
            pattern = re.compile(rf'^{cluster_number}_stim_cluster_\d+$')
            def format_key(
                key): return f"{cluster_number} cluster in {key.split('_', 1)[1]}"

            full_clusters = [
                {**details, 'name': format_key(key), 'alignment_peak_time': 0,
                 'cluster_duration': details['stim_end'] - details['stim_start']}
                for key, details in file_data.items() if pattern.match(key)]
            day_clusters = [
                {**details, 'name': format_key(key), 'alignment_peak_time': 0,
                 'cluster_duration': details['stim_end'] - details['stim_start']}
                for key, details in file_data.items() if pattern.match(key) and details['time_period'] == 'Day']
            night_clusters = [
                {**details, 'name': format_key(key), 'alignment_peak_time': 0,
                 'cluster_duration': details['stim_end'] - details['stim_start']}
                for key, details in file_data.items() if pattern.match(key) and details['time_period'] == 'Night']

        day_cluster_headings = self.generate_cluster_headings_from_list(
            day_clusters)
        night_cluster_headings = self.generate_cluster_headings_from_list(
            night_clusters)

        rows_to_skip_day = len(day_cluster_headings)
        rows_to_skip_night = len(night_cluster_headings)

        row_idx_for_basic_data = 5
        initial_row_idx_for_peak_data = None
        row_idx_for_basic_data, row_idx_for_peak_data = self.write_cluster_data_to_worksheet(
            worksheet,
            full_clusters,
            row_idx_for_basic_data,
            col_idx,
            rows_to_skip_all,
            initial_row_idx_for_peak_data,
            cluster_number
        )

        initial_row_idx_for_peak_data = row_idx_for_peak_data - \
            (rows_to_skip_all - 1)

        row_idx_for_day = row_idx_for_night = row_idx_for_basic_data + 3

        if day_clusters:
            worksheet.write(initial_row_idx_for_peak_data, 6,
                            'Day Clusters', self.day_cell_format)

            row_idx = initial_row_idx_for_peak_data + 1

            row_idx, col_idx = self.write_headings(
                worksheet, row_idx, day_cluster_headings, cluster_basic_headings, rows_to_skip_day
            )

            if self.data_type == 'photometry':
                row_idx, col_idx = self.write_headings(
                    worksheet, row_idx, day_cluster_headings, peak_time_headings, rows_to_skip_day
                )

                row_idx, col_idx = self.write_headings(
                    worksheet, row_idx, day_cluster_headings, peak_amp_headings, rows_to_skip_day
                )
                if cluster_number != 1:
                    row_idx, col_idx = self.write_headings(
                        worksheet, row_idx, day_cluster_headings, peak_isi_headings, rows_to_skip_day
                    )

                initial_row_idx_for_peak_data += rows_to_skip_day + 1

            row_idx_for_day, initial_row_idx_for_peak_data = self.write_cluster_data_to_worksheet(
                worksheet,
                day_clusters,
                row_idx_for_day,
                col_idx,
                rows_to_skip_day,
                initial_row_idx_for_peak_data,
                cluster_number
            )

            row_idx_for_night = row_idx_for_day + 3
            initial_row_idx_for_peak_data -= rows_to_skip_day - 1

        if night_clusters:
            worksheet.write(initial_row_idx_for_peak_data, 6,
                            'Night Clusters', self.night_cell_format)
            row_idx = initial_row_idx_for_peak_data + 1

            row_idx, col_idx = self.write_headings(
                worksheet, row_idx, night_cluster_headings, cluster_basic_headings, rows_to_skip_night
            )

            if self.data_type == 'photometry':
                row_idx, col_idx = self.write_headings(
                    worksheet, row_idx, night_cluster_headings, peak_time_headings, rows_to_skip_night
                )
                row_idx, col_idx = self.write_headings(
                    worksheet, row_idx, night_cluster_headings, peak_amp_headings, rows_to_skip_night
                )
                if cluster_number != 1:
                    row_idx, col_idx = self.write_headings(
                        worksheet, row_idx, night_cluster_headings, peak_isi_headings, rows_to_skip_night
                    )
            row_idx_for_night, initial_row_idx_for_peak_data = self.write_cluster_data_to_worksheet(
                worksheet,
                night_clusters,
                row_idx_for_night,
                col_idx,
                rows_to_skip_night,
                initial_row_idx_for_peak_data,
                cluster_number
            )

        self.settings_manager.selected_column_name = self.data_selection_frame.selected_column_var.get()
        self.settings_manager.save_variables()

    def write_cluster_data_to_worksheet(self, worksheet, clusters, row_idx_for_basic_data, col_idx, rows_to_skip, initial_row_idx_for_peak_data, cluster_number):
        """
        Write cluster data to the worksheet.

        Parameters:
        - worksheet (xlsxwriter.worksheet.Worksheet): The worksheet object to write data to.
        - clusters (list): List of cluster details.
        - row_idx_for_basic_data (int): Starting row index for basic data.
        - col_idx (int): Starting column index.
        - rows_to_skip (int): Number of rows to skip.
        - initial_row_idx_for_peak_data (int): Initial row index for peak data.
        - cluster_number (int): Number of peaks in the clusters.

        Returns:
        - next_row_idx_for_basic_data (int): Next row index for basic data.
        - row_idx_for_peak_data (int): Row index for peak data.
        """
        for cluster_details in clusters:
            if self.data_type == 'photometry':
                basic_data = [
                    cluster_details['start_time'],
                    cluster_details['end_time'],
                    cluster_details['cluster_duration'],
                    cluster_details['peaks'][cluster_details['alignment_index']]
                ]
            else:
                basic_data = [
                    cluster_details['stim_start'],
                    cluster_details['stim_end'],
                    cluster_details['cluster_duration'],
                    cluster_details['cluster_size']
                ]

            row_idx_for_basic_data = self.write_cluster_data_in_columns(
                worksheet, row_idx_for_basic_data, col_idx, basic_data)

            row_idx_for_peak_data = row_idx_for_basic_data + rows_to_skip

            if self.data_type == 'photometry':
                row_idx_for_peak_data, next_row_idx_for_basic_data = self.write_peak_data_in_columns(worksheet, row_idx_for_peak_data, col_idx, cluster_details['peaks'],
                                                                                                     row_idx_for_basic_data,
                                                                                                     rows_to_skip)

                row_idx_for_peak_data, next_row_idx_for_basic_data = self.write_peak_data_in_columns(worksheet, row_idx_for_peak_data, col_idx, cluster_details.get('peak_amplitudes', []),
                                                                                                     next_row_idx_for_basic_data, rows_to_skip)

                if cluster_number > 1:
                    row_idx_for_peak_data, next_row_idx_for_basic_data = self.write_peak_data_in_columns(worksheet, row_idx_for_peak_data, col_idx, cluster_details.get('interpeak_intervals', []),
                                                                                                         next_row_idx_for_basic_data, rows_to_skip)
            else:
                next_row_idx_for_basic_data = row_idx_for_basic_data

        return next_row_idx_for_basic_data, row_idx_for_peak_data

    def write_vertical_headings(self, worksheet, row_idx, headings):
        """
        Write vertical headings to the worksheet.

        Parameters:
        - worksheet (xlsxwriter.worksheet.Worksheet): The worksheet object to write data to.
        - row_idx (int): Starting row index.
        - headings (list): List of headings to write.

        Returns:
        - int: Next column index after writing the headings.
        """
        col_idx = 6
        for heading in headings:
            worksheet.write(row_idx, col_idx, heading, self.bold)
            row_idx += 1
        return col_idx + 1  # Reset row index after headings and move to next column

    def write_headings(self, worksheet, row_idx, cluster_headings, headings, rows_to_skip):
        """
        Write cluster and data headings to the worksheet.

        Parameters:
        - worksheet (xlsxwriter.worksheet.Worksheet): The worksheet object to write data to.
        - row_idx (int): Starting row index.
        - cluster_headings (list): List of cluster headings to write vertically.
        - headings (list): List of data headings to write horizontally.
        - rows_to_skip (int): Number of rows to skip after writing the headings.

        Returns:
        - row_idx (int): Next row index after writing the headings.
        - col_idx (int): Column index reset to 7.
        """
        col_idx = self.write_vertical_headings(
            worksheet, row_idx, cluster_headings)
        for heading in headings:
            worksheet.write(row_idx, col_idx, heading, self.bold)
            col_idx += 1
        row_idx = row_idx + rows_to_skip + 1
        return row_idx, 7  # Reset column index after headings and move to next row

    def write_cluster_data_in_columns(self, worksheet, row_idx, col_idx, data_list):
        """
        Write cluster data in columns to the worksheet.

        Parameters:
        - worksheet (xlsxwriter.worksheet.Worksheet): The worksheet object to write data to.
        - row_idx (int): Starting row index.
        - col_idx (int): Starting column index.
        - data_list (list): List of data points to write.

        Returns:
        - int: Next row index after writing the data.
        """
        for data in data_list:
            worksheet.write(row_idx, col_idx, data)
            col_idx += 1  # Move to the next column for the next data point
        return row_idx + 1  # Move to the next row after writing data

    def write_peak_data_in_columns(self, worksheet, row_idx, col_idx, data_list, row_idx_for_basic_data, rows_to_skip):
        """
        Write peak data in columns to the worksheet.

        Parameters:
        - worksheet (xlsxwriter.worksheet.Worksheet): The worksheet object to write data to.
        - row_idx (int): Starting row index.
        - col_idx (int): Starting column index.
        - data_list (list): List of peak data points to write.
        - row_idx_for_basic_data (int): Starting row index for basic data.
        - rows_to_skip (int): Number of rows to skip.

        Returns:
        - row_idx (int): Next row index after writing the peak data.
        - next_row_idx_for_basic_data (int): Next row index for basic data after writing the peak data.
        """
        for data in data_list:
            worksheet.write(row_idx, col_idx, data)
            col_idx += 1  # Move to the next column for the next data point
        row_idx = row_idx + rows_to_skip
        next_row_idx_for_basic_data = row_idx_for_basic_data + rows_to_skip + 1
        # Move to the next row after writing data
        return row_idx + 1, next_row_idx_for_basic_data

    def write_cluster_static_inputs(self, worksheet, row_idx, col_idx, cluster_number, file_data):
        """
        Write static inputs for the cluster to the worksheet.

        Parameters:
        - worksheet (xlsxwriter.worksheet.Worksheet): The worksheet object to write data to.
        - row_idx (int): Starting row index.
        - col_idx (int): Starting column index.
        - cluster_number (int): The number of peaks in the cluster.
        - file_data (dict): Dictionary containing the file data.

        Returns:
        - row_idx (int): Next row index after writing the static inputs.
        """
        if self.data_type == 'photometry':
            static_values_name = 'cluster'
        else:
            static_values_name = 'stim'

        worksheet.write(row_idx, col_idx - 1, 'Static Inputs', self.bold)
        cluster_static_headings = [
            f'Pre {static_values_name} time (s)',
            f'Post {static_values_name} time (s)',
            'Bin size']
        for heading in cluster_static_headings:
            worksheet.write(row_idx, col_idx, heading, self.bold)
            col_idx += 1  # Move to the next column for the next heading

        # Move to the next row to start writing data
        row_idx += 1

        col_idx -= len(cluster_static_headings)
        cluster_pattern_peaks = f"{cluster_number} Peak{'s' if cluster_number > 1 else ''} in Cluster_"
        cluster_pattern_stim = f"{cluster_number}_stim_cluster_"

        for key, value in file_data.items():
            if key.startswith(cluster_pattern_peaks) or key.startswith(cluster_pattern_stim):
                data_keys = [f'pre_{static_values_name}_time',
                             f'post_{static_values_name}_time',
                             'bin_size']
                for data_key in data_keys:
                    # Ensure the value is written as a number, not a string
                    try:
                        static_value = float(value.get(data_key, 0))
                        if static_value.is_integer():
                            static_value = int(static_value)
                    except ValueError:
                        # In case the value is not a number, write it as is (fallback to string)
                        static_value = value.get(data_key, '')

                    worksheet.write(row_idx, col_idx, static_value)
                    col_idx += 1  # Move to the next column for the next piece of data
                break

        # Move to the next row after writing static data
        row_idx += 1

        return row_idx

    def format_bin_label(self, start_time, bin_size_sec):
        """
        Format a bin label based on the start time and bin size.

        Parameters:
        - start_time (int): The start time of the bin in seconds.
        - bin_size_sec (int): The size of the bin in seconds.

        Returns:
        - str: The formatted bin label.
        """
        end_time = start_time + bin_size_sec
        return f"{start_time} - {end_time}"

    def extract_button_click_handler(self):
        """
        Handle the extract button click event, perform data binning, and save the data to an Excel file.

        Parameters:
        - file_path_var (tk.StringVar): StringVar containing the file path.
        """
        if self.export_options_container.use_binned_data_var.get() == 1:
            self.bin_all_cluster_data()
            file_path = self.file_path.get()
            original_file_name = os.path.splitext(
                os.path.basename(file_path))[0]
            folder_path = os.path.join(os.path.dirname(file_path), os.path.splitext(
                os.path.basename(file_path))[0] + "_MRP_Script")
            os.makedirs(folder_path, exist_ok=True)

            selected_column_name = self.data_selection_frame.selected_column_var.get()
            original_file_name += f"_{selected_column_name}"

            output_file_path = os.path.join(
                folder_path, f"{original_file_name}.xlsx")

            with pd.ExcelWriter(output_file_path, engine='xlsxwriter') as writer:
                self.create_sheets_for_clusters(writer)

                print(f"Excel file has been created at: {output_file_path}")

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
        """Bin all the data contained in self.mean_cluster_data based on their respective sample rates."""
        file_data = list(self.data_dict.values())[0]

        # Build a dictionary mapping number of peaks/stim to bin size
        peak_to_bin_size = {}
        for cluster_key, cluster_info in file_data.items():
            match = re.match(r'(\d+) Peaks?', cluster_key)
            if not match:
                match = re.match(r'(\d+)_stim', cluster_key)
            if match:
                num_peaks_or_stim_from_key = int(match.group(1))
                bin_size_sec = int(cluster_info['bin_size'])
                peak_to_bin_size[num_peaks_or_stim_from_key] = bin_size_sec

        for cluster_number, cluster_periods in self.mean_cluster_data.items():
            bin_size_sec = peak_to_bin_size.get(cluster_number)
            if not bin_size_sec:
                continue

            for period in ['full', 'day', 'night']:
                period_data = cluster_periods.get(period)

                if period_data.get("mean_temp_data") is not None and period_data.get("mean_act_data") is not None:
                    binned_temp_data = self.bin_data_dynamic(
                        period_data["mean_temp_data"], bin_size_sec)
                    period_data["binned_mean_temp_data"] = binned_temp_data

                    binned_act_data = self.bin_data_dynamic(
                        period_data["mean_act_data"], bin_size_sec)
                    period_data["binned_mean_act_data"] = binned_act_data

    def compute_photometry_mean(self, photometry_data_list):
        """
        Compute the mean and standard error of the mean (SEM) for the non-time columns in a list of photometry data.

        Parameters:
        - photometry_data_list (list): A list of pandas DataFrames containing photometry data. The first DataFrame should be sorted by the time column.

        Returns:
        - all_photometry_data (pandas DataFrame): A DataFrame containing the merged photometry data with the mean and SEM calculated for the non-time columns.
        """
        all_photometry_data = photometry_data_list[0].copy()

        time_col = all_photometry_data.columns[0]

        all_photometry_data = all_photometry_data.sort_values(by=time_col)

        all_photometry_data.rename(
            columns={all_photometry_data.columns[1]: 'dFoF_465_0'}, inplace=True)

        for i, df in enumerate(photometry_data_list[1:], start=1):
            df = df.sort_values(by=time_col)

            # Use merge_asof to merge with a tolerance
            all_photometry_data = pd.merge_asof(
                all_photometry_data,
                df.rename(columns={df.columns[1]: f'dFoF_465_{i}'}),
                on=time_col,
                tolerance=0.002,
                direction='nearest'
            )

        data_columns = all_photometry_data.columns[1:]
        all_photometry_data['Mean'] = all_photometry_data[data_columns].mean(
            axis=1, skipna=True)

        if len(data_columns) == 1:
            all_photometry_data['SEM'] = 0
        else:
            all_photometry_data['SEM'] = all_photometry_data[data_columns].sem(
                axis=1, skipna=True)

        return all_photometry_data

    def bin_data_dynamic(self, data, bin_size_sec):
        """
        Bins the data based on a dynamic bin size in seconds.

        Parameters:
        - data (DataFrame): The input data to be binned.
        - bin_size_sec (int): The desired bin size in seconds.

        Returns:
        - binned_data (DataFrame): The binned data with the mean values for each bin.
        """
        time_col = data.columns[0]

        bin_edges = list(self.float_range(
            data[time_col].iloc[0], data[time_col].iloc[-1] + bin_size_sec, bin_size_sec))

        # Check if the last bin is smaller than the desired bin size
        if (bin_edges[-1] - bin_edges[-2]) < bin_size_sec:
            bin_edges.pop(-1)

        bins = pd.cut(data[time_col], bins=bin_edges,
                      right=False, include_lowest=True, labels=False)

        binned_data = data.groupby(bins)[['Mean', 'SEM']].mean()

        binned_data.reset_index(inplace=True)

        bin_ranges = [
            f"{int(bin_edges[i])} - {int(bin_edges[i + 1])}" for i in range(len(bin_edges) - 1)]
        binned_data['Bin Range'] = bin_ranges

        binned_data = binned_data[['Bin Range', 'Mean', 'SEM']]

        return binned_data

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

        # Apply user-defined font sizes, preserving existing labels if no new label is specified
        xlabel_fontsize = self.export_options_container.font_settings.get(
            'xlabel_fontsize')
        ylabel_fontsize = self.export_options_container.font_settings.get(
            'ylabel_fontsize')
        xtick_fontsize = self.export_options_container.font_settings.get(
            'xtick_fontsize')
        ytick_fontsize = self.export_options_container.font_settings.get(
            'ytick_fontsize')
        title_fontsize = self.export_options_container.font_settings.get(
            'title_fontsize')
        y_axis_name = self.export_options_container.font_settings.get(
            'y_axis_name', '')
        y_label_to_use = y_axis_name if y_axis_name else current_ylabel

        height_str = self.export_options_container.height_entry.get().strip()
        width_str = self.export_options_container.width_entry.get().strip()
        fig_copy = copy.deepcopy(self.fig)

        if height_str and width_str:
            try:
                # Desired axis width and height in cm
                axis_width_in = float(width_str) / 2.54
                axis_height_in = float(height_str) / 2.54
                
                margin_multiplier = math.sqrt(axis_width_in**2 + axis_height_in**2)
                
                # Set the default font size relative to the diagonal length of the figure
                default_font_size = 1.8 * margin_multiplier
                
                xlabel_font_size = int(xlabel_fontsize) if xlabel_fontsize else default_font_size
                ylabel_font_size = int(ylabel_fontsize) if ylabel_fontsize else default_font_size
                xtick_label_size = int(xtick_fontsize) if xtick_fontsize else default_font_size
                ytick_label_size = int(ytick_fontsize) if ytick_fontsize else default_font_size            
                
                # Determine scaling factors based on the ratio of new font size to the default font size
                xlabel_scale = xlabel_font_size / default_font_size
                ylabel_scale = ylabel_font_size / default_font_size
                xtick_scale = xtick_label_size / default_font_size
                ytick_scale = ytick_label_size / default_font_size

                # Use the maximum scale factor to adjust margins (to account for the largest text size change)
                scale_factor = max(xlabel_scale, ylabel_scale, xtick_scale, ytick_scale)

                # Fixed margins in inches, scaled conservatively to accommodate labels and ticks
                left_margin_in = 0.2 * margin_multiplier * scale_factor
                right_margin_in = 0.3 * scale_factor
                top_margin_in = 0.1 * scale_factor
                bottom_margin_in = 0.15 * margin_multiplier * scale_factor    

                fig_width = left_margin_in + axis_width_in + right_margin_in
                fig_height = bottom_margin_in + axis_height_in + top_margin_in
                fig_copy.set_size_inches(fig_width, fig_height)

                # Calculate margins as fractions of the figure size
                left = left_margin_in / fig_width
                right = 1 - right_margin_in / fig_width
                bottom = bottom_margin_in / fig_height
                top = 1 - top_margin_in / fig_height

                fig_copy.subplots_adjust(
                    left=left, right=right, top=top, bottom=bottom)

                ax = fig_copy.axes[0]

                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)

                ax.set_xlabel(current_xlabel, fontsize=xlabel_font_size)
                ax.set_ylabel(y_label_to_use, fontsize=ylabel_font_size)
                ax.tick_params(axis='x', labelsize=xtick_label_size)
                ax.tick_params(axis='y', labelsize=ytick_label_size)

                ax.set_title(ax.get_title(), fontsize=int(
                    title_fontsize) if title_fontsize else ax.title.get_fontsize())
                
                print(f"font sizes: {xlabel_fontsize}, {ylabel_fontsize}, {xtick_fontsize}, {ytick_fontsize}, {title_fontsize}")
                print(f"default font size: {default_font_size}")

            except ValueError:
                print("Invalid height or width. Using default figure size.")


        selected_format = self.export_options_container.image_format_combobox.get().lower()
        dpi = int(self.export_options_container.dpi_entry.get())
        file_path = self.file_path_var.get()
        figure_display = self.figure_display_dropdown.get()

        if figure_display == "Behaviour Mean and SEM":
            behaviour_choice = self.behaviour_choice_graph.get()
            base_name = f"{self.mouse_name}_{figure_display}_{behaviour_choice}"
        else:
            base_name = f"{self.mouse_name}_{figure_display}"

        if not self.mouse_name:
            base_name, _ = os.path.splitext(os.path.basename(file_path))

        dir_name = os.path.dirname(file_path)
        exported_images_dir = os.path.join(
            dir_name, f"exported_images_{self.mouse_name}")
        os.makedirs(exported_images_dir, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%b%d_%H%M")
        base_name = f"{base_name}_{timestamp}"

        counter = 1
        original_base_name = base_name
        while os.path.isfile(os.path.join(exported_images_dir, f"{base_name}.{selected_format}")):
            base_name = f"{original_base_name}_{counter}"
            counter += 1

        filename = os.path.join(exported_images_dir,
                                f"{base_name}.{selected_format}")

        fig_copy.savefig(filename, transparent=True,
                         format=selected_format, dpi=dpi)

        plt.close(fig_copy)
