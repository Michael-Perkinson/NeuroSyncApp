"""Tk-backed state initialization helpers for data-selection widgets."""

from __future__ import annotations

import tkinter as tk


def initialize_attributes(instance):
    """Initialize instance variables."""
    init_file_vars(instance)
    init_time_vars(instance)
    init_display_vars(instance)
    init_graph_settings(instance)
    init_behaviour_vars(instance)
    init_analysis_state(instance)


def init_file_vars(instance):
    """File-related variables."""
    instance.file_path = ""
    instance.file_path_var = tk.StringVar()
    instance.is_file_parsed = False


def init_time_vars(instance):
    """Time-related variables."""
    instance.start_time = 0.0
    instance.end_time = 0.0
    instance.time_settings = {
        "pre_behaviour": tk.StringVar(),
        "post_behaviour": tk.StringVar(),
        "sync_start": tk.StringVar(),
        "duration_box": tk.StringVar(value="1"),
    }


def init_display_vars(instance):
    """UI display-related variables."""
    instance.selected_column = tk.StringVar()
    instance.column_titles = []
    instance.table_treeview = None
    instance.figure_canvas = None
    instance.figure_display_dropdown = None
    instance.figure_display_choices = None
    instance.checkbox_state = False
    instance.warning_shown = False


def init_graph_settings(instance):
    """Graph-related variables (grouped in a dict)."""
    instance.graph_settings = {
        "x_axis_min": tk.StringVar(),
        "x_axis_max": tk.StringVar(),
        "y_axis_min": tk.StringVar(),
        "y_axis_max": tk.StringVar(),
        "x_gridlines": tk.StringVar(),
        "y_gridlines": tk.StringVar(),
    }
    instance.xlim_max = None
    instance.xlim_min = None


def init_behaviour_vars(instance):
    """Behaviour-related variables (grouped in a dict)."""
    instance.behaviour_data = {
        "no_behaviours": [],
        "colours": {},
        "boxes": {},
        "adjusted_dataframes": {},
        "display_status": {},
        "already_adjusted": False,
        "auc_binned": [],
        "max_amp_binned": [],
        "mean_dff_binned": [],
    }
    instance.default_column_names = {
        "Behaviours/events": "",
        "Start Time": "",
        "End Time": "",
    }
    instance.display_duration_box_var = tk.BooleanVar(value=True)
    instance.num_instances_box_var = tk.BooleanVar(value=True)
    instance.time_unit_var = tk.StringVar(value="minutes")
    instance.time_input_unit_var = tk.StringVar(value="seconds")
    instance.behaviour_coding_file_var = tk.StringVar()
    instance.tables = {}


def init_analysis_state(instance):
    """Analysis & processing state variables."""
    instance.analysis_state = {
        "current_table_key": None,
        "first_offset_time": None,
        "baseline_pressed": False,
        "mouse_name": None,
        "column_dropdown": None,
        "dataframe": None,
        "z_score_computed": False,
        "previous_baseline_start": None,
        "previous_baseline_end": None,
    }
