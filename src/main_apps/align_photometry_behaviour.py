from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QSizePolicy, QTabWidget, QVBoxLayout, QWidget

from src.core.app_settings_manager import AppSettingsManager
from src.core.app_state import BehaviourViewState
from src.gui.controllers.behaviour_column_settings_controller import (
    BehaviourColumnSettingsController,
)
from src.gui.controllers.behaviour_data_controller import BehaviourDataController
from src.gui.controllers.behaviour_export_controller import BehaviourExportController
from src.gui.controllers.behaviour_file_controller import BehaviourFileController
from src.gui.controllers.behaviour_graph_helpers_controller import (
    BehaviourGraphHelpersController,
)
from src.gui.controllers.behaviour_manual_controller import BehaviourManualController
from src.gui.controllers.behaviour_options_controller import BehaviourOptionsController
from src.gui.controllers.behaviour_plot_controller import BehaviourPlotController
from src.gui.controllers.behaviour_settings_controller import BehaviourSettingsController
from src.gui.controllers.behaviour_table_controller import BehaviourTableController
from src.gui.controllers.behaviour_ui_controller import BehaviourUIController
from src.gui.shared.qt_bindings import ObservableValue
from src.gui.shared.qt_view_styles import APP_TABS_STYLESHEET, PALETTE
from src.gui.views.behaviour_event_input_frame import BehaviourInputFrame
from src.gui.views.data_selection_panel import DataSelectionPanel
from src.gui.views.static_inputs_frame import StaticInputsFrame


class DataProcessingSingleInstance(QWidget):
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

    def __init__(self, parent: QWidget | None = None, *args, **kwargs):
        self.settings_manager = AppSettingsManager(
            app_type="align_photometry_and_behaviour_app"
        )
        self.app_name = "align_photometry_and_behaviour_app"
        super().__init__(parent, *args, **kwargs)

        self.initialize_attributes()
        self.create_widgets()

        notebook_graphs, notebook_settings = self.setup_notebooks()
        graph_settings_tab, export_options_tab = self.create_tabs(notebook_settings)
        graph_tab, table_tab = self.behaviour_ui_controller.initialize_graph_settings(
            graph_settings_tab, export_options_tab, notebook_graphs
        )

        self.behaviour_ui_controller.create_graphs_container(graph_tab)
        self.behaviour_table_controller.create_table_container(table_tab)

    def initialize_attributes(self):
        """Initialize state, controllers, and root layout."""
        self._initialize_state()
        self._initialize_controllers()
        self._configure_root_layout()

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

    def _bind_state_var(self, value_var, state_field):
        value_var.set(getattr(self.view_state, state_field))
        value_var.trace_add(
            "write", lambda: setattr(self.view_state, state_field, value_var.get())
        )

    def _initialize_controllers(self):
        for attribute, controller_type in self.CONTROLLER_TYPES.items():
            setattr(self, attribute, controller_type(self))

        self.extract_data_from_photometry = (
            self.export_controller.extract_data_from_photometry
        )

    def _configure_root_layout(self):
        self.setWindowTitle("Data Processing")
        self.setObjectName("behaviourAppRoot")
        self.setStyleSheet(
            f"#behaviourAppRoot {{ background: {PALETTE['app_bg']}; }}"
        )
        self._root_layout = QVBoxLayout(self)
        self._root_layout.setContentsMargins(6, 6, 6, 6)
        self._root_layout.setSpacing(6)

        self.main_frame = QWidget(self)
        self.main_frame.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.main_frame_layout = QGridLayout(self.main_frame)
        self.main_frame_layout.setContentsMargins(0, 0, 0, 0)
        self.main_frame_layout.setHorizontalSpacing(10)
        self.main_frame_layout.setVerticalSpacing(6)
        self.main_frame_layout.setColumnStretch(0, 1)
        self.main_frame_layout.setColumnStretch(1, 1)
        self.main_frame_layout.setColumnStretch(2, 1)
        self._root_layout.addWidget(self.main_frame)

        self.bottom_frame = QWidget(self)
        self.bottom_frame_layout = QGridLayout(self.bottom_frame)
        self.bottom_frame_layout.setContentsMargins(0, 0, 0, 0)
        self.bottom_frame_layout.setHorizontalSpacing(10)
        self.bottom_frame_layout.setVerticalSpacing(0)
        self._root_layout.addWidget(self.bottom_frame, 1)

    def init_file_vars(self):
        """Initialize file-related variables."""
        self._assign_defaults(
            self,
            {
                "file_path": "",
                "is_file_parsed": False,
            },
        )
        self.file_path_var = ObservableValue("")
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
        self.pre_behaviour_time_var = ObservableValue("")
        self.post_behaviour_time_var = ObservableValue("")
        self.synchronize_start_time_var = ObservableValue("")
        self.duration_box_placement_var = ObservableValue("1")
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
        self.selected_column_var = ObservableValue("")
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
                "duration_data_cache": {},
                "original_table": None,
                "original_start_times_min": [],
                "original_end_times_min": [],
                "bar_items": [],
                "toolbar": None,
                "ax": None,
                "fig": None,
                "default_y_limits": None,
                "current_cache_key": None,
            },
        )
        self.display_duration_box_var = ObservableValue(True)
        self.num_instances_box_var = ObservableValue(True)
        self.time_unit_var = ObservableValue("minutes")
        self.time_input_unit_var = ObservableValue("seconds")
        self.x_gridlines_var = ObservableValue("")
        self.y_gridlines_var = ObservableValue("")
        self.x_axis_min_var = ObservableValue("")
        self.x_axis_max_var = ObservableValue("")
        self.y_axis_min_var = ObservableValue("")
        self.y_axis_max_var = ObservableValue("")
        self.behaviour_coding_file_var = ObservableValue("")
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

    def create_data_selection_frame(self):
        """Create and configure the data selection panel."""
        self.data_selection_frame = DataSelectionPanel(
            self.main_frame,
            width=500,
            settings_manager=self.settings_manager,
            figure_display_callback=self.plot_controller.handle_figure_display_selection,
            new_data_file_callback=self.manual_controller.handle_new_data_file,
            update_table_from_frame_callback=self.behaviour_table_controller.update_table_from_frame,
        )
        self.main_frame_layout.addWidget(self.data_selection_frame, 0, 0)
        self.file_path_var = self.data_selection_frame.file_path_var
        self.selected_column_var = self.data_selection_frame.selected_column_var
        self.data_selection_frame.use_baseline_var.trace_add(
            "write",
            lambda: setattr(
                self,
                "checkbox_state",
                bool(self.data_selection_frame.use_baseline_var.get()),
            ),
        )

    def create_behaviour_event_input_frame(self):
        """Create and configure the behaviour input panel."""
        self.behaviour_event_input_frame = BehaviourInputFrame(
            self.main_frame,
            width=450,
            select_event_file_callback=self.behaviour_file_controller.handle_behaviour_file_selection,
            save_column_names_callback=self.behaviour_column_settings_controller.save_from_frame,
        )
        self.main_frame_layout.addWidget(self.behaviour_event_input_frame, 0, 1)

    def create_static_inputs_frame(self):
        """Create and configure the static inputs panel."""
        self.static_inputs_frame = StaticInputsFrame(
            self.main_frame,
            width=230,
            save_inputs_callback=self.behaviour_settings_controller.save_inputs,
        )
        self.main_frame_layout.addWidget(self.static_inputs_frame, 0, 2)

    def setup_notebooks(self):
        """
        Setup the main and settings notebooks.

        Returns:
        - notebook_graphs: The main notebook for displaying graphs.
        - notebook_settings: The settings notebook for configuring graph settings.
        """
        notebook_graphs = QTabWidget(self)
        notebook_settings = QTabWidget(self)
        notebook_graphs.setStyleSheet(APP_TABS_STYLESHEET)
        notebook_settings.setStyleSheet(APP_TABS_STYLESHEET)
        self.bottom_frame_layout.addWidget(notebook_graphs, 0, 0)
        self.bottom_frame_layout.addWidget(notebook_settings, 0, 1)
        self.bottom_frame_layout.setColumnStretch(0, 3)
        self.bottom_frame_layout.setColumnStretch(1, 2)

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
        graph_settings_tab = QWidget(notebook_settings)
        export_options_tab = QWidget(notebook_settings)

        notebook_settings.addTab(graph_settings_tab, "Graph Settings")
        notebook_settings.addTab(export_options_tab, "Export Options")

        return graph_settings_tab, export_options_tab


