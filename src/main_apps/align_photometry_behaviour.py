import tkinter as tk
from tkinter import ttk
from src.core.app_state import BehaviourViewState
from src.gui.views.behaviour_event_input_frame import BehaviourInputFrame
from src.gui.views.data_selection_frame import DataSelectionFrame
from src.gui.views.static_inputs_frame import StaticInputsFrame
from src.gui.shared.tk_styles import define_custom_ttk_styles
from src.core.app_settings_manager import AppSettingsManager
from src.gui.controllers.behaviour_plot_controller import BehaviourPlotController
from src.gui.controllers.behaviour_export_controller import BehaviourExportController
from src.gui.controllers.behaviour_manual_controller import BehaviourManualController
from src.gui.controllers.behaviour_settings_controller import BehaviourSettingsController
from src.gui.controllers.behaviour_column_settings_controller import (
    BehaviourColumnSettingsController,
)
from src.gui.controllers.behaviour_options_controller import BehaviourOptionsController
from src.gui.controllers.behaviour_data_controller import BehaviourDataController
from src.gui.controllers.behaviour_table_controller import BehaviourTableController
from src.gui.controllers.behaviour_graph_helpers_controller import (
    BehaviourGraphHelpersController,
)
from src.gui.controllers.behaviour_file_controller import BehaviourFileController
from src.gui.controllers.behaviour_ui_controller import BehaviourUIController


class DataProcessingSingleInstance(ttk.Frame):
    CONTROLLER_TYPES = {
        "plot_controller": BehaviourPlotController,
        "export_controller": BehaviourExportController,
        "manual_controller": BehaviourManualController,
        "behaviour_settings_controller": BehaviourSettingsController,
        "behaviour_column_settings_controller": BehaviourColumnSettingsController,
        "behaviour_options_controller": BehaviourOptionsController,
        "behaviour_data_controller": BehaviourDataController,
        "behaviour_table_controller": BehaviourTableController,
        "behaviour_graph_helpers_controller": BehaviourGraphHelpersController,
        "behaviour_file_controller": BehaviourFileController,
        "behaviour_ui_controller": BehaviourUIController,
    }

    def __init__(self, parent, *args, **kwargs):
        """
        Initialize the main application frame.

        Parameters:
            parent (tk.Tk|tk.Frame): The parent widget.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        self.settings_manager = AppSettingsManager(
            app_type="align_photometry_and_behaviour_app"
        )
        self.app_name = "align_photometry_and_behaviour_app"

        super().__init__(parent, *args, **kwargs)

        self.initialize_attributes(parent)
        self.create_widgets()

        notebook_graphs, notebook_settings = self.setup_notebooks()
        graph_settings_tab, export_options_tab = self.create_tabs(notebook_settings)
        graph_tab, table_tab = self.behaviour_ui_controller.initialize_graph_settings(
            graph_settings_tab, export_options_tab, notebook_graphs
        )

        self.behaviour_ui_controller.create_graphs_container(graph_tab)
        self.behaviour_table_controller.create_table_container(table_tab)

    def initialize_attributes(self, parent):
        """Initialize state, controllers, and root layout."""
        self._initialize_state()
        self._initialize_controllers()
        self._configure_root_layout(parent)

    @staticmethod
    def _assign_defaults(target, values):
        for attribute, value in values.items():
            setattr(target, attribute, value)

    def _initialize_state(self):
        self.view_state = BehaviourViewState()
        self.init_file_vars()
        self.init_time_vars()
        self.init_display_vars()
        self.init_behaviour_vars()

    def _bind_state_var(self, tk_var, state_field):
        tk_var.set(getattr(self.view_state, state_field))
        tk_var.trace_add(
            "write", lambda *_: setattr(self.view_state, state_field, tk_var.get())
        )

    def _initialize_controllers(self):
        for attribute, controller_type in self.CONTROLLER_TYPES.items():
            setattr(self, attribute, controller_type(self))

        self.extract_data_from_photometry = (
            self.export_controller.extract_data_from_photometry
        )

    def _configure_root_layout(self, parent):
        if isinstance(parent, tk.Tk):
            parent.title("Data Processing")

        self.main_frame = ttk.Frame(self, style="Bordered.TFrame")
        self.main_frame.grid(row=0, column=0, columnspan=4, padx=10, sticky=tk.NSEW)
        self.grid(row=0, column=0, sticky="nsew")

    def init_file_vars(self):
        """Initialize file-related variables."""
        self._assign_defaults(
            self,
            {
                "file_path": "",
                "is_file_parsed": False,
            },
        )
        self.file_path_var = tk.StringVar()
        self._bind_state_var(self.file_path_var, "file_path")

    def init_time_vars(self):
        """Initialize time-related variables."""
        self._assign_defaults(
            self,
            {
                "start_time": 0.0,
                "end_time": 0.0,
            },
        )
        self.pre_behaviour_time_var = tk.StringVar()
        self.post_behaviour_time_var = tk.StringVar()
        self.synchronize_start_time_var = tk.StringVar()
        self.duration_box_placement_var = tk.StringVar(value="1")
        self._bind_state_var(self.pre_behaviour_time_var, "pre_behaviour_time")
        self._bind_state_var(self.post_behaviour_time_var, "post_behaviour_time")
        self._bind_state_var(
            self.synchronize_start_time_var, "synchronize_start_time"
        )
        self._bind_state_var(self.duration_box_placement_var, "duration_box_placement")

    def init_display_vars(self):
        """Initialize display-related variables."""
        self._assign_defaults(
            self,
            {
                "selected_column": "",
                "column_titles": [],
                "table_treeview": None,
                "figure_canvas": None,
                "figure_display_dropdown": None,
                "figure_display_choices": None,
                "checkbox_state": False,
                "warning_shown": False,
            },
        )
        self.selected_column_var = tk.StringVar()
        self._bind_state_var(self.selected_column_var, "selected_column")

    def init_behaviour_vars(self):
        """Initialize behaviour-related variables."""
        self._assign_defaults(
            self,
            {
                "no_behaviours": [],
                "behaviour_colors": {},
                "behaviour_boxes": {},
                "adjusted_behaviour_dataframes": {},
                "behaviour_display_status": {},
                "data_already_adjusted": False,
                "behaviours_results_auc_binned": [],
                "behaviours_results_max_amp_binned": [],
                "behaviours_results_mean_dff_binned": [],
                "default_column_names": {
                    "Behaviours/events": "",
                    "Start Time": "",
                    "End Time": "",
                },
                "current_table_key": None,
                "first_offset_time": None,
                "baseline_button_pressed": False,
                "mouse_name": None,
                "column_dropdown": None,
                "dataframe": None,
                "z_score_computed": False,
                "previous_baseline_start": None,
                "previous_baseline_end": None,
                "xlim_max": None,
                "xlim_min": None,
                "tables": {},
            },
        )
        self.display_duration_box_var = tk.BooleanVar(value=True)
        self.num_instances_box_var = tk.BooleanVar(value=True)
        self.time_unit_var = tk.StringVar(value="minutes")
        self.time_input_unit_var = tk.StringVar(value="seconds")
        self.x_gridlines_var = tk.StringVar()
        self.y_gridlines_var = tk.StringVar()
        self.x_axis_min_var = tk.StringVar()
        self.x_axis_max_var = tk.StringVar()
        self.y_axis_min_var = tk.StringVar()
        self.y_axis_max_var = tk.StringVar()
        self.behaviour_coding_file_var = tk.StringVar()
        self._bind_state_var(self.display_duration_box_var, "display_duration_box")
        self._bind_state_var(self.num_instances_box_var, "num_instances_box")
        self._bind_state_var(self.time_unit_var, "time_unit")
        self._bind_state_var(self.time_input_unit_var, "time_input_unit")
        self._bind_state_var(self.x_gridlines_var, "x_gridlines")
        self._bind_state_var(self.y_gridlines_var, "y_gridlines")
        self._bind_state_var(self.x_axis_min_var, "x_axis_min")
        self._bind_state_var(self.x_axis_max_var, "x_axis_max")
        self._bind_state_var(self.y_axis_min_var, "y_axis_min")
        self._bind_state_var(self.y_axis_max_var, "y_axis_max")
        self._bind_state_var(self.behaviour_coding_file_var, "behaviour_coding_file")
        self.settings_manager.load_variables()

    def create_widgets(self):
        self.create_data_selection_frame()
        self.create_behaviour_event_input_frame()
        self.create_static_inputs_frame()
        define_custom_ttk_styles()

    def create_data_selection_frame(self):
        """Create and configure the DataSelectionFrame."""
        self.data_selection_frame = DataSelectionFrame(
            self.main_frame,
            width=500,
            settings_manager=self.settings_manager,
            figure_display_callback=self.plot_controller.handle_figure_display_selection,
            new_data_file_callback=self.manual_controller.handle_new_data_file,
            update_table_from_frame_callback=self.behaviour_table_controller.update_table_from_frame,
        )
        self.data_selection_frame.grid(
            row=0, column=0, padx=10, pady=10, sticky=tk.NSEW
        )

    def create_behaviour_event_input_frame(self):
        """Create and configure the BehaviourInputFrame."""
        self.behaviour_event_input_frame = BehaviourInputFrame(
            self.main_frame,
            width=450,
            select_column_names_callback=self.behaviour_column_settings_controller.select_column_names,
            select_event_file_callback=self.behaviour_file_controller.handle_behaviour_file_selection,
        )
        self.behaviour_event_input_frame.grid(
            row=0, column=2, padx=10, pady=10, sticky=tk.NSEW
        )
        self.behaviour_event_input_frame.columnconfigure(0, weight=0)
        self.behaviour_event_input_frame.columnconfigure(1, weight=1)

    def create_static_inputs_frame(self):
        """Create and configure the StaticInputsFrame."""
        self.static_inputs_frame = StaticInputsFrame(
            self.main_frame,
            width=230,
            save_inputs_callback=self.behaviour_settings_controller.save_inputs,
        )
        self.static_inputs_frame.grid(row=0, column=3, padx=10, pady=10, sticky=tk.NSEW)

    def setup_notebooks(self):
        """
        Setup the main and settings notebooks.

        Returns:
        - notebook_graphs: The main notebook for displaying graphs.
        - notebook_settings: The settings notebook for configuring graph settings.
        """
        notebook_graphs = ttk.Notebook(self, style="CustomNotebook.TNotebook")
        notebook_graphs.grid(row=1, column=0, columnspan=3, padx=10, sticky=tk.NSEW)

        notebook_settings = ttk.Notebook(
            self, style="CustomNotebook.TNotebook", height=520, width=300
        )
        notebook_settings.grid(row=1, column=3, padx=10, sticky=tk.NSEW)

        return notebook_graphs, notebook_settings

    def create_tabs(self, notebook_settings):
        """
        Create and add tabs to the notebooks.

        Parameters:
        - notebook_settings: The settings notebook to add tabs to.

        Returns:
        - graph_settings_tab: The tab for configuring graph settings.
        - export_options_tab: The tab for configuring export options.
        """
        graph_settings_tab = ttk.Frame(notebook_settings)
        export_options_tab = ttk.Frame(notebook_settings)

        notebook_settings.add(graph_settings_tab, text="Graph Settings")
        notebook_settings.add(export_options_tab, text="Export Options")

        return graph_settings_tab, export_options_tab


