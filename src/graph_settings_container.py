import hashlib
import tkinter as tk
import tkinter.colorchooser as colorchooser
from tkinter import messagebox, colorchooser, Frame, Canvas
from tkinter import ttk
from window_utils import center_window_on_screen


class GraphSettingsContainer(ttk.Frame):
    def __init__(self, parent, widgets_to_include=None,
                 app_name=None,
                 settings_manager=None,
                 refresh_graph_display_callback=None,
                 update_duration_box_callback=None,
                 handle_behaviour_change_callback=None,
                 load_variables_callback=None,
                 save_variables_callback=None,
                 create_behaviour_options_callback=None,
                 update_box_colors_callback=None,
                 save_and_close_axis_callback=None,
                 redraw_graph_callback=None,
                 **kwargs):
        """
        Initialize the GraphSettingsContainer.

        Parameters:
        - parent (tk.Tk|tk.Frame): The parent widget.
        - widgets_to_include (list): The list of widgets to include.
        - app_name (str): The name of the app.
        - settings_manager (SettingsManager): The settings manager.
        - refresh_graph_display_callback (function): The callback for refreshing the graph display.
        - update_duration_box_callback (function): The callback for updating the duration box.
        - handle_behaviour_change_callback (function): The callback for handling behaviour change.
        - load_variables_callback (function): The callback for loading variables.
        - save_variables_callback (function): The callback for saving variables.
        - create_behaviour_options_callback (function): The callback for creating behaviour options.
        - update_box_colors_callback (function): The callback for updating box colors.
        - save_and_close_axis_callback (function): The callback for saving and closing the axis.
        - redraw_graph_callback (function): The callback for redrawing the graph.
        - **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(parent, style='Bordered.TFrame', **kwargs)

        self.settings_manager = settings_manager
        self.app_name = app_name

        self.row = 0
        self.column = 0
        self.widgets = {}
        self.settings_vars = {
            "Temperature": {},
            "Activity": {}
        }

        # Store the callback functions
        self.refresh_graph_display_callback = refresh_graph_display_callback
        self.update_duration_box_callback = update_duration_box_callback
        self.handle_behaviour_change_callback = handle_behaviour_change_callback
        self.load_variables_callback = load_variables_callback
        self.save_variables_callback = save_variables_callback
        self.create_behaviour_options_callback = create_behaviour_options_callback
        self.update_box_colors_callback = update_box_colors_callback
        self.save_and_close_axis_callback = save_and_close_axis_callback
        self.redraw_graph_callback = redraw_graph_callback

        # Initialize variables
        self.file_path_var = tk.StringVar()
        self.pre_behaviour_time_var = tk.StringVar()
        self.post_behaviour_time_var = tk.StringVar()
        self.bin_size_var = tk.StringVar()
        self.column_titles = []
        self.duration_data_cache = {}
        self.selected_column_var = tk.StringVar()
        self.synchronize_start_time_var = tk.StringVar()
        self.default_duration_box_placement = tk.StringVar(value=1.0)
        self.duration_box_placement = tk.StringVar(
            value=(self.default_duration_box_placement))
        self.table_treeview = None
        self.activity_data_var = tk.StringVar()
        self.temperature_data_var = tk.StringVar()
        self.activity_data_var = tk.BooleanVar(value=True)
        self.temperature_data_var = tk.BooleanVar(value=True)
        self.selected_photometry_line_color = 'black'
        self.selected_sem_color = 'grey'
        self.selected_bar_sem_color = "grey"
        self.selected_bar_fill_color = "blue"
        self.selected_bar_border_color = "black"
        self.selected_line_color = 'red'
        self.selected_temp_line_color = 'red'
        self.selected_temp_sem_color = 'orange'
        self.selected_activity_bar_color = 'blue'
        self.selected_cluster_box_color = 'orange'
        self.unique_behaviours = []
        self.behaviour_colors = {}
        self.behaviour_boxes = {}
        self.adjusted_behaviour_dataframes = {}
        self.behaviour_display_status = {}
        self.figure_canvas = None
        self.default_photometry_line_color = 'green'
        self.default_sem_color = 'grey'
        self.default_line_color = 'red'
        self.default_bar_sem_color = 'grey'
        self.default_bar_fill_color = 'blue'
        self.default_bar_border_color = 'black'
        self.default_temp_line_color = 'red'
        self.default_temp_sem_color = 'orange'
        self.default_activity_bar_color = 'blue'
        self.default_cluster_box_color = 'orange'
        self.bar_fill_color_name = self.default_bar_fill_color.capitalize()
        self.bar_border_color_name = self.default_bar_border_color.capitalize()
        self.line_color_name = self.default_line_color.capitalize()
        self.bar_sem_color_name = self.default_sem_color.capitalize()
        self.photometry_line_color_name = self.default_photometry_line_color.capitalize()
        self.temp_line_color_name = self.default_temp_line_color.capitalize()
        self.temp_line_sem_color_name = self.default_temp_sem_color.capitalize()
        self.activity_bar_color_name = self.default_activity_bar_color.capitalize()
        self.cluster_box_color_name = self.default_cluster_box_color.capitalize()
        self.temp_line_color_name = self.default_temp_line_color.capitalize()
        self.behaviours_results_auc_binned = []
        self.behaviours_results_max_amp_binned = []
        self.behaviours_results_mean_dff_binned = []
        self.default_column_names = {'Behaviours/events': '',
                                     'Start Time': '',
                                     'End Time': ''}
        self.display_duration_box_var = tk.BooleanVar(value=True)
        self.num_instances_box_var = tk.BooleanVar(value=True)
        self.time_unit_var = tk.StringVar(value="minutes")  # default value
        self.time_input_unit_var = tk.StringVar(
            value="seconds")  # default value
        self.x_gridlines_var = tk.StringVar()  # no default value
        self.y_gridlines_var = tk.StringVar()  # no default value
        self.current_table_key = None
        # Variable to keep track of the baseline button state
        self.baseline_button_pressed = False
        self.mouse_name = None
        self.column_dropdown = None  # or some default value
        self.dataframe = None
        self.figure_display_dropdown = None
        self.figure_display_choices = None
        self.checkbox_state = True
        self.z_score_computed = False
        self.previous_baseline_start = None
        self.previous_baseline_end = None
        self.x_axis_min_var = tk.StringVar()
        self.x_axis_max_var = tk.StringVar()
        self.y_axis_min_var = tk.StringVar()
        self.y_axis_max_var = tk.StringVar()
        self.selected_behaviour_to_zero = tk.StringVar()
        self.selected_photometry_line_width = tk.StringVar(
            value=self.settings_manager.selected_photometry_line_width)

        if self.app_name == "Menopause_app":
            self.photometry_line_color_var = tk.StringVar(
                value=self.settings_manager.selected_photometry_line_color)
            self.photometry_line_alpha_var = tk.StringVar(
                value=self.settings_manager.selected_photometry_line_alpha)
            self.horizontal_scale_bar_offset_var = tk.StringVar(
                value=self.settings_manager.selected_horizontal_scale_bar_offset)
            self.vertical_scale_bar_offset_var = tk.StringVar(
                value=self.settings_manager.selected_vertical_scale_bar_offset)
            self.scale_bar_color_var = tk.StringVar(
                value=self.settings_manager.selected_scale_bar_color)
            self.scale_bar_width_var = tk.StringVar(
                value=self.settings_manager.selected_scale_bar_width)
            self.scale_bar_size_var = tk.StringVar(
                value=self.settings_manager.selected_scale_bar_size)

            self.temp_mean_line_width_var = tk.StringVar(
                value=self.settings_manager.selected_temp_mean_line_width)
            self.temp_mean_line_color_var = tk.StringVar(
                value=self.settings_manager.selected_temp_mean_line_color)
            self.temp_sem_color_var = tk.StringVar(
                value=self.settings_manager.selected_temp_sem_color)
            self.temp_mean_line_alpha_var = tk.StringVar(
                value=self.settings_manager.selected_temp_mean_line_alpha)
            self.temp_sem_line_alpha_var = tk.StringVar(
                value=self.settings_manager.selected_temp_sem_line_alpha)
            self.temp_desired_offset_var = tk.StringVar(
                value=self.settings_manager.selected_temp_desired_offset)
            self.temp_desired_scale_var = tk.StringVar(
                value=self.settings_manager.selected_temp_desired_scale)
            self.temp_y_axis_color_var = tk.StringVar(
                value=self.settings_manager.selected_temp_y_axis_color)
            self.temp_num_ticks_var = tk.StringVar(
                value=self.settings_manager.selected_temp_num_ticks)

            self.activity_mean_bar_color_var = tk.StringVar(
                value=self.settings_manager.selected_activity_mean_bar_color)
            self.activity_mean_bar_alpha_var = tk.StringVar(
                value=self.settings_manager.selected_activity_mean_bar_alpha)
            self.activity_desired_offset_var = tk.StringVar(
                value=self.settings_manager.selected_activity_desired_offset)
            self.activity_desired_scale_var = tk.StringVar(
                value=self.settings_manager.selected_activity_desired_scale)
            self.activity_y_axis_color_var = tk.StringVar(
                value=self.settings_manager.selected_activity_y_axis_color)
            self.activity_num_bins_var = tk.StringVar(
                value=self.settings_manager.selected_activity_num_bins)
            self.activity_num_ticks_var = tk.StringVar(
                value=self.settings_manager.selected_activity_num_ticks)

        if self.app_name == "align_photometry_and_behaviour_app":
            self.box_height_factor = tk.StringVar(
                value=self.settings_manager.box_height_factor)
            self.alpha = tk.StringVar(value=self.settings_manager.alpha)
            self.bar_graph_size = tk.StringVar(
                value=self.settings_manager.bar_graph_size)
            self.onset_line_thickness = tk.StringVar(
                value=self.settings_manager.onset_line_thickness)
            self.onset_line_style = tk.StringVar(
                value=self.settings_manager.onset_line_style)
            self.duration_box_placement = tk.StringVar(
                value=self.settings_manager.duration_box_placement)

        self.ax = None
        self.default_x_limits = None
        self.default_y_limits = None
        self.mean_sem_df = None
        self.mean_duration = None
        self.sem_duration = None
        self.popup = None

        self.widgets_to_include = widgets_to_include or []
        self.create_graph_settings_container(parent)

    def create_graph_settings_container(self, parent):
        """Create and initialize graph settings container."""
        self.settings_container_frame = ttk.Frame(
            parent, style='NoBorder.TFrame', borderwidth=2, relief='solid')
        self.settings_container_frame.grid(
            row=0, column=0, padx=5, pady=10, sticky=tk.NSEW)
        self.settings_container_frame.columnconfigure(0, weight=1)
        self.settings_container_frame.rowconfigure(0, weight=1)

        # Call the canvas setup function
        self.setup_canvas()

        # Settings frame for changing graph
        self.graph_settings_frame = ttk.Frame(
            self.settings_container_frame, style='Bordered.TFrame')
        self.graph_settings_frame.grid(
            row=1, column=0, columnspan=3, padx=10, pady=(10, 5), sticky=tk.NSEW)

        # Create a dictionary that maps the widget name to its corresponding creation function
        widget_creation_map = {
            'line_width': self.create_line_width_widget,
            'box_height': self.create_box_height_widget,
            'alpha': self.create_alpha_widget,
            'bar_graph_size': self.create_bar_graph_size_widget,
            'onset_line_thickness': self.create_onset_line_thickness_widget,
            'onset_line_style': self.create_onset_line_style_widget,
            'activity_line_width': self.create_activity_line_width_widget,
            'temperature_line_width': self.create_temperature_line_width_widget,
            'color_buttons': self.create_color_buttons_widget,
            'activity_bars_color': self.create_activity_bars_color_widget,
            'temp_trace_color': self.create_temp_trace_color_widget,
            'temp_trace_sem_color': self.create_temp_trace_sem_color_widget,
            'photometry_trace_color': self.create_photometry_trace_color_widget,
            'checkboxes': self.create_display_options_widgets,
            'axis_range': self.create_axis_range_widget,
            'zero_x_axis_to_behaviour': self.create_zero_x_axis_widget,
            'graph_time_labels': self.create_graph_time_label_widgets,
            'photometry_settings': self.create_photometry_settings_button,
            'temperature_settings': self.create_temperature_settings_button,
            'activity_settings': self.create_activity_settings_button,
            'number_of_minor_ticks': self.create_number_of_minor_ticks_widget,
            'remove_first_60_minutes': self.create_remove_first_60_minutes_widget
        }

        # Loop through the widgets_to_include list and call the corresponding widget creation function
        for widget_name in self.widgets_to_include:
            creation_func = widget_creation_map.get(widget_name)
            if creation_func:
                creation_func()

    def create_line_width_widget(self):
        """Create the line width widget."""
        line_width_label = tk.Label(self.graph_settings_frame, text="Photometry Line Width:", font=('Helvetica', 8), fg='black',
                                    bg='snow', wraplength=120)
        line_width_label.grid(
            row=self.row, column=self.column, padx=5, pady=5, sticky=tk.W)
        self.column += 1

        self.line_width_entry = tk.Entry(self.graph_settings_frame, textvariable=self.selected_photometry_line_width, width=10, font=('Helvetica', 8), fg='black',
                                         bg='snow', state='normal')
        self.line_width_entry.grid(
            row=self.row, column=self.column, padx=5, pady=5, sticky=tk.W)

        self.column += 1
        if self.column >= 3:
            self.column = 0
            self.row += 1

    def create_box_height_widget(self):
        """Create the box height widget."""
        if self.column >= 3:
            self.column = 0
            self.row += 1

        box_height_label = tk.Label(self.graph_settings_frame, text="Transparent Box Height Factor:", font=('Helvetica', 8),
                                    fg='black', bg='snow', wraplength=120)
        box_height_label.grid(
            row=self.row, column=self.column, padx=5, pady=5, sticky=tk.W)

        self.column += 1

        self.box_height_entry = tk.Entry(self.graph_settings_frame, textvariable=self.box_height_factor, width=10, font=('Helvetica', 8), fg='black',
                                         bg='snow', state='normal')
        self.box_height_entry.grid(
            row=self.row, column=self.column, padx=5, pady=5, sticky=tk.W)

        self.column += 1
        if self.column >= 3:
            self.column = 0
            self.row += 1

    def create_number_of_minor_ticks_widget(self):
        """Create the number of minor ticks widget."""
        number_of_minor_ticks_label = tk.Label(self.graph_settings_frame, text="Number of Minor Ticks:", font=('Helvetica', 8),
                                               fg='black', bg='snow', wraplength=120)
        number_of_minor_ticks_label.grid(
            row=self.row, column=self.column, padx=5, pady=5, sticky=tk.W)

        self.column += 1

        self.number_of_minor_ticks_entry = tk.Entry(self.graph_settings_frame, width=10, font=('Helvetica', 8), fg='black',
                                                    bg='snow', state='normal')
        self.number_of_minor_ticks_entry.insert(tk.END, "0")
        self.number_of_minor_ticks_entry.grid(
            row=self.row, column=self.column, padx=5, pady=5, sticky=tk.W)

        self.column += 1
        if self.column >= 3:
            self.column = 0
            self.row += 1

    def create_remove_first_60_minutes_widget(self):
        """Create the remove first 60 minutes widget."""
        self.remove_first_60_minutes_var = tk.BooleanVar(
            value=True)  # Defaulted to True (checked)

        remove_first_60_minutes_label = tk.Label(self.graph_settings_frame, text="Remove First 60 Minutes:", font=('Helvetica', 8),
                                                 fg='black', bg='snow', wraplength=120)
        remove_first_60_minutes_label.grid(
            row=self.row, column=self.column, padx=5, pady=5, sticky=tk.NSEW)

        self.remove_first_60_minutes_checkbox = tk.Checkbutton(self.graph_settings_frame, bg='snow',
                                                               variable=self.remove_first_60_minutes_var,
                                                               command=self.redraw_graph)
        self.remove_first_60_minutes_checkbox.grid(
            row=self.row, column=self.column, padx=5, pady=5, sticky=tk.E)

        self.column += 1

        if self.column >= 3:
            self.column = 0
            self.row += 1

    def create_alpha_widget(self):
        """Create the alpha widget."""
        alpha_label = tk.Label(self.graph_settings_frame, text="Transparent Boxes (Alpha):", font=('Helvetica', 8),
                               fg='black', bg='snow', wraplength=120)
        alpha_label.grid(row=self.row, column=self.column,
                         padx=5, pady=5, sticky=tk.W)

        self.column += 1

        self.alpha_entry = tk.Entry(self.graph_settings_frame, textvariable=self.alpha, width=10, font=('Helvetica', 8), fg='black', bg='snow',
                                    state='normal')
        self.alpha_entry.grid(
            row=self.row, column=self.column, padx=5, pady=5, sticky=tk.W)

        self.column += 1
        if self.column >= 3:
            self.column = 0
            self.row += 1

    def create_bar_graph_size_widget(self):
        """Create the bar graph size widget."""
        bar_graph_size_label = tk.Label(self.graph_settings_frame, text="Duration Box Height:", font=('Helvetica', 8),
                                        fg='black', bg='snow')
        bar_graph_size_label.grid(
            row=self.row, column=self.column, padx=5, pady=5, sticky=tk.W)

        self.column += 1

        self.bar_graph_size_entry = tk.Entry(self.graph_settings_frame, textvariable=self.bar_graph_size, width=10, font=('Helvetica', 8), fg='black',
                                             bg='snow', state='normal')
        self.bar_graph_size_entry.grid(
            row=self.row, column=self.column, padx=5, pady=5, sticky=tk.W)

        self.column += 1
        if self.column >= 3:
            self.column = 0
            self.row += 1

    def create_onset_line_thickness_widget(self):
        """Create the onset line thickness widget."""
        onset_line_thickness_label = tk.Label(self.graph_settings_frame, text="Onset Line Thickness:",
                                              font=('Helvetica', 8), fg='black', bg='snow', wraplength=120)
        onset_line_thickness_label.grid(
            row=self.row, column=self.column, padx=5, pady=5, sticky=tk.W)

        self.column += 1

        self.onset_line_thickness_entry = tk.Entry(self.graph_settings_frame, textvariable=self.onset_line_thickness, width=10, font=('Helvetica', 8), fg='black',
                                                   bg='snow', state='normal')
        self.onset_line_thickness_entry.grid(
            row=self.row, column=self.column, padx=5, pady=5, sticky=tk.W)

        self.column += 1
        if self.column >= 3:
            self.column = 0
            self.row += 1

    def create_onset_line_style_widget(self):
        """Create the onset line style widget."""
        onset_line_style_label = tk.Label(self.graph_settings_frame, text="Onset Line Style:", font=('Helvetica', 8),
                                          fg='black', bg='snow')
        onset_line_style_label.grid(
            row=self.row, column=self.column, padx=5, pady=5, sticky=tk.W)

        self.column += 1

        # List of available line styles
        onset_line_styles = ['-', '--', '-.', ':']
        self.onset_line_style_combobox = ttk.Combobox(self.graph_settings_frame, width=7, values=onset_line_styles,
                                                      state='readonly')
        self.onset_line_style_combobox.grid(
            row=self.row, column=self.column, padx=5, pady=5, sticky=tk.W)
        self.onset_line_style_combobox.set(self.onset_line_style.get())

        self.column += 1
        if self.column >= 3:
            self.column = 0
            self.row += 1

    def create_activity_line_width_widget(self):
        """Create the activity line width widget."""
        activity_line_width_label = tk.Label(self.graph_settings_frame, text="Activity Line Width:",
                                             font=('Helvetica', 8), fg='black', bg='snow')
        activity_line_width_label.grid(
            row=self.row, column=self.column, padx=5, pady=5, sticky=tk.W)

        self.column += 1

        self.activity_line_width_entry = tk.Entry(self.graph_settings_frame, width=10, font=('Helvetica', 8),
                                                  fg='black', bg='snow', state='normal')
        self.activity_line_width_entry.insert(tk.END, "1.0")
        self.activity_line_width_entry.grid(
            row=self.row, column=self.column, padx=5, pady=5, sticky=tk.W)

        self.column += 1
        if self.column >= 3:
            self.column = 0
            self.row += 1

    def create_temperature_line_width_widget(self):
        """Create the temperature line width widget."""
        temperature_line_width_label = tk.Label(self.graph_settings_frame, text="Temperature Line Width:",
                                                font=('Helvetica', 8), fg='black', bg='snow')
        temperature_line_width_label.grid(
            row=self.row, column=self.column, padx=5, pady=5, sticky=tk.W)

        self.column += 1

        self.temperature_line_width_entry = tk.Entry(self.graph_settings_frame, width=10, font=('Helvetica', 8),
                                                     fg='black', bg='snow', state='normal')
        self.temperature_line_width_entry.insert(tk.END, "1.0")
        self.temperature_line_width_entry.grid(
            row=self.row, column=self.column, padx=5, pady=5, sticky=tk.W)

        self.column += 1
        if self.column >= 3:
            self.column = 0
            self.row += 1

    def create_color_buttons_widget(self):
        """Create the color buttons widget."""
        # Bar Graph Fill color
        self.bar_fill_color_button = tk.Button(self.graph_settings_frame, text="Bar Fill colour", font=('Helvetica', 8),
                                               command=self.select_bar_fill_color)
        self.bar_fill_color_button.grid(
            row=self.row, column=self.column, padx=5, pady=10, sticky=tk.NSEW)

        self.column += 1

        # Bar Graph Border color
        self.bar_border_color_button = tk.Button(self.graph_settings_frame, text="Bar Border colour", font=('Helvetica', 8),
                                                 command=self.select_bar_border_color)
        self.bar_border_color_button.grid(
            row=self.row, column=self.column, padx=5, pady=10, sticky=tk.NSEW)

        self.column += 1

        # SEM color
        self.sem_color_button = tk.Button(self.graph_settings_frame, text="Bar SEM colour", font=('Helvetica', 8),
                                          command=self.select_bar_sem_color)
        self.sem_color_button.grid(
            row=self.row, column=self.column, padx=5, pady=10, sticky=tk.NSEW)

        self.column += 1

        # Line color
        self.line_color_button = tk.Button(self.graph_settings_frame, text="Onset Line colour", font=('Helvetica', 8),
                                           command=self.select_line_color)
        self.line_color_button.grid(
            row=self.row, column=self.column, padx=(5, 10), pady=10, sticky=tk.NSEW)

        self.column += 1
        if self.column >= 3:
            self.column = 0
            self.row += 1

    def create_temp_trace_color_widget(self):
        """Create the temperature trace color widget."""
        self.temp_line_color_button = tk.Button(self.graph_settings_frame, text="Temp Line Colour", font=('Helvetica', 8),
                                                command=self.select_temp_line_color)
        self.temp_line_color_button.grid(
            row=self.row, column=self.column, padx=(5, 10), pady=10, sticky=tk.NSEW)

        self.column += 1
        if self.column >= 3:
            self.column = 0
            self.row += 1

    def create_temp_trace_sem_color_widget(self):
        """Create the temperature trace SEM color widget."""
        self.temp_sem_color_button = tk.Button(self.graph_settings_frame, text="Temp SEM Colour", font=('Helvetica', 8),
                                               command=self.select_temp_sem_color)
        self.temp_sem_color_button.grid(
            row=self.row, column=self.column, padx=(5, 10), pady=10, sticky=tk.NSEW)

        self.column += 1
        if self.column >= 3:
            self.column = 0
            self.row += 1

    def create_photometry_trace_color_widget(self):
        """Create the photometry trace color widget."""
        self.photometry_line_color_button = tk.Button(self.graph_settings_frame, text="Photometry Line Colour", font=('Helvetica', 8),
                                                      command=self.select_photometry_line_color)
        self.photometry_line_color_button.grid(
            row=self.row, column=self.column, padx=(5, 10), pady=10, sticky=tk.NSEW)

        self.column += 1
        if self.column >= 3:
            self.column = 0
            self.row += 1

    def create_activity_bars_color_widget(self):
        """Create the activity bars color widget."""
        self.activity_bar_color_button = tk.Button(self.graph_settings_frame, text="Activity Bar Fill Colour", font=('Helvetica', 8),
                                                   command=self.select_activity_bar_color)
        self.activity_bar_color_button.grid(
            row=self.row, column=self.column, padx=5, pady=10, sticky=tk.NSEW)

        self.column += 1
        if self.column >= 3:
            self.column = 0
            self.row += 1

    def create_display_options_widgets(self):
        """Create the display options widgets."""
        duration_box_checkbox = tk.Checkbutton(self.graph_settings_frame, text='Display Duration',
                                               font=('Helvetica', 8),
                                               variable=self.settings_manager.display_duration_box_var, bg='snow',
                                               command=self.refresh_graph_display)
        duration_box_checkbox.grid(
            row=self.row, column=self.column, padx=(5, 10), pady=5, sticky=tk.W)

        self.column += 1

        instances_box_checkbox = tk.Checkbutton(self.graph_settings_frame, text='Display Number of Instances',
                                                wraplength=120,
                                                font=('Helvetica', 8),
                                                variable=self.settings_manager.num_instances_box_var, bg='snow',
                                                command=self.refresh_graph_display)
        instances_box_checkbox.grid(
            row=self.row, column=self.column, padx=(5, 10), pady=5, sticky=tk.W)

        self.column += 1

        # Create the label and entry widgets for the height modifier
        box_placement_label = tk.Label(self.graph_settings_frame, text='Duration Box Placement Modifier (+/-):',
                                       font=('Helvetica', 8),
                                       bg='snow', wraplength=120)
        box_placement_label.grid(
            row=self.row, column=self.column, padx=(5, 10), pady=5, sticky=tk.W)

        self.column += 1

        box_placement_spinbox = tk.Spinbox(self.graph_settings_frame, from_=-5, to=5, increment=0.2,
                                           textvariable=self.duration_box_placement,
                                           font=('Helvetica', 8), bg='snow', width=7, command=self.update_duration_box)
        box_placement_spinbox.grid(
            row=self.row, column=self.column, padx=(0, 10), pady=5, sticky=tk.W)

        self.column += 1
        if self.column >= 3:
            self.column = 0
            self.row += 1

    def create_axis_range_widget(self):
        """Create the axis range widget."""
        if self.column >= 3:
            self.column = 0
            self.row += 1

        # Create the variable to hold the state
        self.limit_axis_range_var = tk.BooleanVar()
        self.limit_axis_range_checkbox = tk.Checkbutton(self.graph_settings_frame, text='Limit Axis Range', bg='snow',
                                                        variable=self.limit_axis_range_var)
        self.limit_axis_range_checkbox.config(
            command=lambda: self.save_and_close_axis(close=False))
        self.limit_axis_range_checkbox.grid(
            row=self.row, column=self.column, padx=(5, 10), pady=5, sticky=tk.W)

        self.column += 1

        # Button to open the axis range setting pop-up
        self.axis_range_button = tk.Button(self.graph_settings_frame, text="Set Axis Range",
                                           command=self.open_axis_range_popup, bg='lightblue')
        self.axis_range_button.grid(
            row=self.row, column=self.column, padx=(5, 10), pady=5)

        self.column += 1
        if self.column >= 3:
            self.column = 0
            self.row += 1

    def create_acivity_data_checkbox(self):
        """Create the activity data checkbox."""
        self.activity_data_var = tk.BooleanVar()  # Variable to hold the state
        self.activity_data_checkbox = tk.Checkbutton(self.graph_settings_frame, text='Activity Data', bg='snow',
                                                     variable=self.activity_data_var)
        self.activity_data_checkbox.config(
            command=lambda: self.save_and_close(close=False))
        self.activity_data_checkbox.grid(
            row=self.row, column=self.column, padx=(5, 10), pady=5, sticky=tk.W)

        self.column += 1
        if self.column >= 3:
            self.column = 0
            self.row += 1

    def create_temperature_data_checkbox(self):
        """Create the temperature data checkbox."""
        self.temperature_data_var = tk.BooleanVar()  # Variable to hold the state
        self.temperature_data_checkbox = tk.Checkbutton(self.graph_settings_frame, text='Temperature Data', bg='snow',
                                                        variable=self.temperature_data_var)
        self.temperature_data_checkbox.config(
            command=lambda: self.save_and_close(close=False))
        self.temperature_data_checkbox.grid(
            row=self.row, column=self.column, padx=(5, 10), pady=5, sticky=tk.W)

        self.column += 1
        if self.column >= 3:
            self.column = 0
            self.row += 1

    def create_zero_x_axis_widget(self):
        """Create the zero x-axis widget."""
        self.zero_x_axis_checkbox_var = tk.IntVar()  # Create the variable to hold the state
        self.zero_x_axis_checkbox = tk.Checkbutton(self.graph_settings_frame, text='Zero X-axis with behavior', bg='snow',
                                                   wraplength=120,
                                                   variable=self.zero_x_axis_checkbox_var,
                                                   command=self.handle_behaviour_change)
        self.zero_x_axis_checkbox.grid(
            row=self.row, column=self.column, padx=(5, 10), pady=5, sticky=tk.W)

        self.selected_behaviour_to_zero = tk.StringVar(value=" " * 15)

        self.column += 1

        # Create a ttk.Frame to hold the OptionMenu
        self.behaviour_dropdown_frame = ttk.Frame(
            self.graph_settings_frame, borderwidth=2, relief="solid")
        self.behaviour_dropdown_frame.configure(style='Bordered.TFrame')
        self.behaviour_dropdown_frame.grid(
            row=self.row, column=self.column, padx=10, pady=(0, 5), sticky=tk.W)

        self.column += 1

        self.behaviour_to_zero_dropdown = ttk.OptionMenu(self.behaviour_dropdown_frame, self.selected_behaviour_to_zero, '',
                                                         "")
        self.behaviour_to_zero_dropdown.config(
            width=7, style="Custom.TMenubutton")

        # Set the state of the dropdown to disabled initially
        self.behaviour_to_zero_dropdown['state'] = 'disabled'
        self.behaviour_to_zero_dropdown.grid(
            row=self.row, column=self.column, sticky=tk.NSEW)
        self.behaviour_to_zero_dropdown["menu"].delete(0, "end")

        self.column += 1
        if self.column >= 3:
            self.column = 0
            self.row += 1

    def create_graph_time_label_widgets(self):
        """Create the graph time label widgets and update button."""
        self.column = 0
        self.row += 1

        self.time_unit_var = tk.StringVar(value="minutes")  # default value
        self.time_unit_menu = ttk.Combobox(self.graph_settings_frame, textvariable=self.time_unit_var,
                                           values=["seconds", "minutes", "hours", "time of day"], state='readonly')
        self.time_unit_menu.grid(
            row=self.row, column=self.column, padx=(5, 10), sticky=tk.EW)
        self.time_unit_menu.bind(
            "<<ComboboxSelected>>", lambda event: self.refresh_graph_display())

        self.column += 1

        # Add label and Entry for x ticks
        label_text = "X Ticks:" if self.app_name == "Menopause_app" else "X Ticks:"
        self.x_gridlines_label = tk.Label(
            self.graph_settings_frame, text=label_text, bg='snow')
        # adjust the row and column as needed
        self.x_gridlines_label.grid(
            row=self.row, column=self.column, sticky=tk.W)
        self.x_gridlines_var = tk.StringVar()  # user can enter a value here
        self.x_gridlines_entry = tk.Entry(
            self.graph_settings_frame, width=7, textvariable=self.x_gridlines_var)
        self.x_gridlines_entry.grid(
            row=self.row, column=self.column, padx=10, sticky=tk.E)

        self.column += 1

        # Add label and Entry for y ticks
        self.y_gridlines_label = tk.Label(
            self.graph_settings_frame, text="Y Ticks:", bg='snow')
        # adjust the row and column as needed
        self.y_gridlines_label.grid(
            row=self.row, column=self.column, sticky=tk.W)
        self.y_gridlines_var = tk.StringVar()  # user can enter a value here
        self.y_gridlines_entry = tk.Entry(
            self.graph_settings_frame, width=7, textvariable=self.y_gridlines_var)
        self.y_gridlines_entry.grid(
            row=self.row, column=self.column, padx=(50, 10), sticky=tk.E)

        self.column += 1

        # Update Button
        self.update_button = tk.Button(self.graph_settings_frame, text='Update Settings', font=('Helvetica', 8),
                                       command=self.refresh_graph_display, bg='lightblue')
        self.update_button.grid(row=self.row, column=self.column, padx=(
            5, 10), pady=5, sticky=tk.NSEW)

        self.column += 1
        if self.column >= 3:
            self.column = 0
            self.row += 1

    def save_variables(self):
        """Save the variables to the settings manager."""
        if self.save_variables_callback:
            self.save_variables_callback()

    def load_variables(self):
        """Load the variables from the settings manager."""
        if self.load_variables_callback:
            self.load_variables_callback()

    def complete_initialization(self):
        """Complete the initialization of the graph settings container."""
        self.load_variables()
        self.update_button_colors()

    def open_axis_range_popup(self):
        """Opens a pop-up window to set the axis range"""
        self.popup = tk.Toplevel(self.graph_settings_frame, bg='snow')
        self.popup.title("Set Axis Range")

        # You can adjust the width (300) and height (200) as needed
        self.popup.geometry('260x120')

        # Initialize the variables if they don't already exist
        if not hasattr(self, 'x_axis_min_var'):
            self.x_axis_min_var = tk.StringVar()
        if not hasattr(self, 'x_axis_max_var'):
            self.x_axis_max_var = tk.StringVar()
        if not hasattr(self, 'y_axis_min_var'):
            self.y_axis_min_var = tk.StringVar()
        if not hasattr(self, 'y_axis_max_var'):
            self.y_axis_max_var = tk.StringVar()

        # Add label and Entries for limiting x axis min and max
        tk.Label(self.popup, text="X Axis Min:", bg='snow').grid(
            row=0, column=0, sticky=tk.NSEW)
        tk.Entry(self.popup, width=7, textvariable=self.x_axis_min_var).grid(row=0, column=1, padx=(5, 10), pady=(10, 5),
                                                                             sticky=tk.NSEW)

        tk.Label(self.popup, text="X Axis Max:", bg='snow').grid(
            row=0, column=2, sticky=tk.NSEW)
        tk.Entry(self.popup, width=7, textvariable=self.x_axis_max_var).grid(row=0, column=3, padx=(5, 10), pady=(10, 5),
                                                                             sticky=tk.NSEW)

        # Add label and Entries for limiting y axis min and max
        tk.Label(self.popup, text="Y Axis Min:", bg='snow').grid(
            row=2, column=0, sticky=tk.NSEW)
        tk.Entry(self.popup, width=7, textvariable=self.y_axis_min_var).grid(row=2, column=1, padx=(5, 10), pady=(10, 5),
                                                                             sticky=tk.NSEW)

        tk.Label(self.popup, text="Y Axis Max:", bg='snow').grid(
            row=2, column=2, sticky=tk.NSEW)
        tk.Entry(self.popup, width=7, textvariable=self.y_axis_max_var).grid(row=2, column=3, padx=(5, 10), pady=(10, 5),
                                                                             sticky=tk.NSEW)

        # Save and Close button
        save_and_close_axis_button = tk.Button(
            self.popup, text="Save & Close", command=lambda: self.save_and_close_axis(self.popup))
        save_and_close_axis_button.grid(row=3, column=0, columnspan=4, pady=10)

        self.popup.update_idletasks()  # Update "idle" tasks to get updated dimensions
        center_window_on_screen(self.popup)  # Center the popup window

    def setup_canvas(self):
        """Create and initialize canvas for behaviour names."""
        self.canvas = Canvas(self.settings_container_frame, bg='snow')
        self.canvas.grid(row=0, column=0, padx=10,
                         pady=(10, 5), sticky=tk.NSEW)

        # Add behaviour options inside the scrollable frame
        self.behaviour_frame = Frame(self.canvas, bg='snow')
        self.behaviour_frame.grid(row=0, column=1, pady=(5, 2), sticky=tk.NW)

        scrollbar = ttk.Scrollbar(
            self.settings_container_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        scrollbar.grid(row=0, column=2, sticky=tk.NS)

        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.create_window(
            (0, 0), window=self.behaviour_frame, anchor=tk.NW)

        def configure_canvas(event):
            """Configure the canvas to allow scrolling."""
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        self.canvas.bind("<Configure>", configure_canvas)

        self.behaviour_frame.bind("<Configure>", lambda event: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))

        # Allow behaviour_frame to expand horizontally
        self.behaviour_frame.grid_columnconfigure(0, weight=1)
        scrollbar.grid_columnconfigure(0, weight=0)

    # class colorManipulation:

    def select_color(self, attribute_name, default_color):
        """
        Open a color picker dialog and set the given attribute to the selected color.

        Parameters:
        - attribute_name (str): The name of the attribute to set.
        - default_color (str): The default color to use if the user cancels the color picker dialog.
        """
        color = colorchooser.askcolor()
        setattr(self, attribute_name,
                color[1] if color[1] is not None else default_color)
        self.update_button_colors()

    def select_temp_line_color(self):
        """Open a color picker dialog and set the temperature line color."""
        self.select_color("selected_temp_line_color",
                          self.default_temp_line_color)

    def select_activity_bar_color(self):
        """Open a color picker dialog and set the activity bar color."""
        self.select_color("selected_activity_bar_color",
                          self.default_activity_bar_color)

    def select_bar_fill_color(self):
        """Open a color picker dialog and set the bar fill color."""
        self.select_color("selected_bar_fill_color",
                          self.default_bar_fill_color)

    def select_temp_sem_color(self):
        """Open a color picker dialog and set the temperature SEM color."""
        self.select_color("selected_temp_sem_color",
                          self.default_temp_sem_color)

    def select_photometry_line_color(self):
        """Open a color picker dialog and set the photometry line color."""
        self.select_color("selected_photometry_line_color",
                          self.default_photometry_line_color)

    def select_bar_border_color(self):
        """Open a color picker dialog and set the bar border color."""
        self.select_color("selected_bar_border_color",
                          self.default_bar_border_color)

    def select_line_color(self):
        """Open a color picker dialog and set the line color."""
        self.select_color("selected_line_color", self.default_line_color)

    def select_bar_sem_color(self):
        """Open a color picker dialog and set the bar SEM color."""
        self.select_color("selected_bar_sem_color", self.default_sem_color)

    def update_button_colors(self):
        """Update the colors of the color buttons."""
        button_color_map = {
            "selected_bar_fill_color": "bar_fill_color_button",
            "selected_bar_border_color": "bar_border_color_button",
            "selected_line_color": "line_color_button",
            "selected_bar_sem_color": "sem_color_button",
            "selected_activity_bar_color": "activity_bar_color_button",
            "selected_cluster_box_color": "cluster_box_color_button",
            "selected_temp_line_color": "temp_line_color_button",
            "selected_temp_sem_color": "temp_sem_color_button",
            "selected_photometry_line_color": "photometry_line_color_button"
        }

        for color_attr, button_attr in button_color_map.items():
            color_value = getattr(self, color_attr, None)
            button = getattr(self, button_attr, None)

            if button and color_value:  # Check if both the button and color attributes exist
                button.config(bg=color_value)
                color_object = self.string_to_color(color_value)
                button.config(fg='white' if self.brightness(
                    color_object) > 0.65 else 'black')

        self.save_variables()

    def string_to_color(self, input_string):
        """
        Converts an arbitrary string into a color.

        Returns:
        - tuple: A tuple of RGB values in the [0, 1] range.
        """
        # Compute the hash of the input string
        hashcode = hashlib.md5(input_string.encode()).hexdigest()

        # Convert the hashcode into an RGB value.
        r = int(hashcode[0:2], 16)
        g = int(hashcode[2:4], 16)
        b = int(hashcode[4:6], 16)

        # Normalize the RGB value into the [0, 1] range expected by matplotlib
        return r / 255.0, g / 255.0, b / 255.0

    def brightness(self, color):
        """
        Calculate the brightness of the color for the contrast.

        Returns:
        - float: The brightness of the color.
        """
        return (color[0] * 299 + color[1] * 587 + color[2] * 114) / 1000.0

    def choose_color(self, behaviour, color_button):
        """
        Let the user choose a color for the behaviour.

        Parameters:
        - behaviour (str): The behaviour to choose a color for.
        - color_button (str): The button to update with the new color.
        """
        color_code = colorchooser.askcolor()[1]
        if color_code is not None:
            # Convert the color code from a hex string to a tuple of RGB values
            color_rgb = tuple(
                int(color_code[i:i + 2], 16) / 255 for i in (1, 3, 5))

            # Update the behaviour color in the dictionary
            self.behaviour_colors[behaviour] = color_rgb

            if self.update_box_colors_callback:
                self.update_box_colors_callback(behaviour, color_rgb)

            # Save the new color selection
            self.save_variables()

    def refresh_graph_display(self):
        """Refresh the graph display."""
        if self.refresh_graph_display_callback:
            self.refresh_graph_display_callback()
            self.settings_manager.save_variables()

    def update_duration_box(self):
        """Update the duration box."""
        if self.update_duration_box_callback:
            self.update_duration_box_callback()

    def handle_behaviour_change(self, *args, **kwargs):
        """
        Handle the behaviour change event.

        Parameters:
        - *args: The arguments passed to the callback.
        - **kwargs: The keyword arguments passed to the callback.
        """
        if self.handle_behaviour_change_callback:
            self.handle_behaviour_change_callback()

    def save_and_close_axis(self, close=True):
        """
        Save the axis range settings and close the pop-up window.

        Parameters:
        - close (bool): Whether to close the pop-up window.
        """
        if self.save_and_close_axis_callback:

            # Pass the popup instance to the callback
            self.save_and_close_axis_callback(popup=self.popup, close=close)

    def create_behaviour_options(self, destroy_frame=True):
        """
        Create the behaviour options.

        Parameters:
        - destroy_frame (bool): Whether to destroy the frame.
        """
        if self.create_behaviour_options_callback:
            self.create_behaviour_options_callback(destroy_frame=destroy_frame)

    def get_setting(self, setting_type, setting_name):
        """
        Get the setting value based on the setting type and name.

        Parameters:
        - setting_type (str): The type of setting to get.
        - setting_name (str): The name of the setting to get.

        Returns:
        - str: The value of the setting.
        """
        # Fetch settings from settings_manager based on setting_type
        if setting_type == "Temperature":
            return getattr(self.settings_manager, f"selected_temp_{setting_name}")
        elif setting_type == "Activity":
            return getattr(self.settings_manager, f"selected_activity_{setting_name}")

    def set_setting(self, setting_type, setting_name, value):
        """
        Set the setting value based on the setting type and name.

        Parameters:
        - setting_type (str): The type of setting to set.
        - setting_name (str): The name of the setting to set.
        - value (str): The value to set the setting to.

        Returns:
        - str: The value of the setting.
        """
        if setting_type == "Temperature":
            setattr(self, f"selected_temp_{setting_name}", value)
        elif setting_type == "Activity":
            setattr(self, f"selected_activity_{setting_name}", value)

    def create_photometry_settings_button(self):
        """Create the Photometry settings button."""
        self.photometry_settings_button = tk.Button(self.graph_settings_frame, text="Photometry Settings",
                                                    command=self.open_photometry_settings_popup, bg='lightblue')
        self.photometry_settings_button.grid(
            row=self.row, column=self.column, padx=5, pady=20)

        self.column += 1

    def create_temperature_settings_button(self):
        """Create the Temperature settings button."""
        self.temperature_settings_button = tk.Button(self.graph_settings_frame, text="Temperature Settings",
                                                     command=self.open_temperature_settings_popup, bg='lightblue')
        self.temperature_settings_button.grid(
            row=self.row, column=self.column, padx=5, pady=20)

        self.column += 1

    def create_activity_settings_button(self):
        """Create the Activity settings button."""
        self.activity_settings_button = tk.Button(self.graph_settings_frame, text="Activity Settings",
                                                  command=self.open_activity_settings_popup, bg='lightblue')
        self.activity_settings_button.grid(
            row=self.row, column=self.column, padx=5, pady=20)

        self.column = 0
        self.row += 1

    def open_photometry_settings_popup(self):
        """Opens a pop-up window to set the Photometry settings."""
        self.photometry_popup = tk.Toplevel(self, bg='snow')
        self.photometry_popup.title("Photometry Settings")
        bold_large_font = ('Helvetica', 10, 'bold')
        popup = self.photometry_popup

        # Photometry Frame
        self.photometry_frame = tk.LabelFrame(
            popup, text="Photometry Settings", bg='snow', font=bold_large_font)
        self.photometry_frame.grid(
            row=0, column=0, padx=10, pady=10, sticky='nsew')

        # Line Color Chooser
        self.line_color_var = tk.StringVar(
            value=self.settings_manager.selected_photometry_line_color)
        tk.Button(self.photometry_frame, text="Choose Line Colour", bg='snow',
                  command=lambda: self.choose_photometry_line_color(popup)).grid(row=0, column=0, padx=10, pady=5)

        # Photometry Line Width
        self.selected_photometry_line_width = tk.StringVar(
            value=str(self.settings_manager.selected_photometry_line_width))
        tk.Label(self.photometry_frame, text="Photometry Line Width:",
                 bg='snow').grid(row=1, column=0, padx=10, pady=5)
        tk.Entry(self.photometry_frame, textvariable=self.selected_photometry_line_width,
                 width=7).grid(row=1, column=1, padx=10, pady=5)

        # Photometry Line Alpha (Transparency)
        self.photometry_line_alpha_var = tk.StringVar(
            value=str(self.settings_manager.selected_photometry_line_alpha))
        tk.Label(self.photometry_frame, text="Photometry Line Alpha:",
                 bg='snow').grid(row=2, column=0, padx=10, pady=5)
        tk.Entry(self.photometry_frame, textvariable=self.photometry_line_alpha_var,
                 width=7).grid(row=2, column=1, padx=10, pady=5)

        # Save and Close button
        save_and_close_button = tk.Button(
            popup, text="Save & Close", command=lambda: self.save_and_close_photometry_settings(popup))
        save_and_close_button.grid(row=8, column=0, columnspan=2, pady=10)

        popup.update_idletasks()  # Update "idle" tasks to get updated dimensions
        center_window_on_screen(popup)  # Center the popup window

    def open_temperature_settings_popup(self):
        """Opens a pop-up window to set the Temperature settings."""
        self.temperature_popup = tk.Toplevel(self, bg='snow')
        self.temperature_popup.title("Temperature Settings")
        bold_large_font = ('Helvetica', 10, 'bold')

        self.temperature_frame = tk.LabelFrame(
            self.temperature_popup, text="Temperature Settings", bg='snow', font=bold_large_font)
        self.temperature_frame.grid(
            row=0, column=0, padx=10, pady=10, sticky='nsew')

        self.create_common_settings_section(
            self.temperature_frame, "Temperature", self.temperature_popup)

        save_and_close_button = tk.Button(self.temperature_popup, text="Save & Close",
                                          command=lambda: self.save_and_close_temperature_settings(self.temperature_popup))
        save_and_close_button.grid(row=1, column=0, pady=10)

        self.temperature_popup.update_idletasks()
        center_window_on_screen(self.temperature_popup)

    def open_activity_settings_popup(self):
        """Opens a pop-up window to set the Activity settings."""
        self.activity_popup = tk.Toplevel(self, bg='snow')
        self.activity_popup.title("Activity Settings")
        bold_large_font = ('Helvetica', 10, 'bold')

        self.activity_frame = tk.LabelFrame(
            self.activity_popup, text="Activity Settings", bg='snow', font=bold_large_font)
        self.activity_frame.grid(
            row=0, column=0, padx=10, pady=10, sticky='nsew')

        self.create_common_settings_section(
            self.activity_frame, "Activity", self.activity_popup)

        self.activity_num_bins_var = tk.StringVar(
            value=str(self.settings_manager.selected_activity_num_bins))
        tk.Label(self.activity_frame, text="Number of Bins (if empty use default):",
                 bg='snow').grid(row=7, column=0, sticky=tk.W, padx=10, pady=5)
        tk.Entry(self.activity_frame, textvariable=self.activity_num_bins_var,
                 width=7).grid(row=7, column=1, padx=10, pady=5)

        save_and_close_button = tk.Button(self.activity_popup, text="Save & Close",
                                          command=lambda: self.save_and_close_activity_settings(self.activity_popup))
        save_and_close_button.grid(row=1, column=0, pady=10)

        self.activity_popup.update_idletasks()
        center_window_on_screen(self.activity_popup)

    def create_common_settings_section(self, parent_frame, setting_type, popup):
        """
        Create the common settings section for the given setting type.

        Parameters:
        - parent_frame (tk.Frame): The parent frame to add the settings to.
        - setting_type (str): The type of setting to create.
        - popup (tk.Toplevel): The pop-up window to add the settings to.
        """
        # Only add line width for Temperature
        if setting_type == "Temperature":
            self.settings_vars[setting_type]['mean_line_width'] = tk.StringVar(
                value=self.get_setting(setting_type, 'mean_line_width'))
            tk.Label(parent_frame, text=f"{setting_type} Line Width:", bg='snow').grid(
                row=0, column=0, sticky=tk.W, padx=10, pady=5)
            tk.Entry(parent_frame, textvariable=self.settings_vars[setting_type]['mean_line_width'], width=7).grid(
                row=0, column=1, padx=10, pady=5)
            row_offset = 1
        else:
            row_offset = 0

        # Mean Line or Bar Color
        color_label_text = "Mean Line Colour" if setting_type == "Temperature" else "Mean Bar Colour"
        color_setting_name = 'mean_line_color' if setting_type == "Temperature" else 'mean_bar_color'
        self.settings_vars[setting_type][color_setting_name] = tk.StringVar(
            value=self.get_setting(setting_type, color_setting_name))
        tk.Label(parent_frame, text=f"{setting_type} {color_label_text}:", bg='snow').grid(
            row=row_offset, column=0, sticky=tk.W, padx=10, pady=5)
        tk.Button(parent_frame, text="Choose Colour",
                  command=lambda: self.choose_setting_color(setting_type, color_setting_name, self.settings_vars[setting_type][color_setting_name], popup)).grid(
            row=row_offset, column=1, padx=10, pady=5)

        row_offset += 1

        # Alpha (Transparency) for both Line and SEM Line (for Temperature) or Bar (for Activity)
        alpha_setting_name = 'mean_line_alpha' if setting_type == "Temperature" else 'mean_bar_alpha'
        self.settings_vars[setting_type][alpha_setting_name] = tk.StringVar(
            value=self.get_setting(setting_type, alpha_setting_name))
        alpha_label_text = "Line Alpha" if setting_type == "Temperature" else "Bar Alpha"
        tk.Label(parent_frame, text=f"{setting_type} {alpha_label_text}:", bg='snow').grid(
            row=row_offset, column=0, sticky=tk.W, padx=10, pady=5)
        tk.Entry(parent_frame, textvariable=self.settings_vars[setting_type][alpha_setting_name], width=7).grid(
            row=row_offset, column=1, padx=10, pady=5)

        row_offset += 1

        # Only add SEM for Temperature
        if setting_type == "Temperature":
            self.settings_vars[setting_type]['sem_color'] = tk.StringVar(
                value=self.get_setting(setting_type, 'sem_color'))
            tk.Label(parent_frame, text=f"{setting_type} SEM Colour:", bg='snow').grid(
                row=row_offset, column=0, sticky=tk.W, padx=10, pady=5)
            tk.Button(parent_frame, text="Choose Colour",
                      command=lambda: self.choose_setting_color(setting_type, 'sem_color', self.settings_vars[setting_type]['sem_color'], popup)).grid(
                row=row_offset, column=1, padx=10, pady=5)

            row_offset += 1

            self.settings_vars[setting_type]['sem_line_alpha'] = tk.StringVar(
                value=self.get_setting(setting_type, 'sem_line_alpha'))
            tk.Label(parent_frame, text="SEM Line Alpha:", bg='snow').grid(
                row=row_offset, column=0, sticky=tk.W, padx=10, pady=5)
            tk.Entry(parent_frame, textvariable=self.settings_vars[setting_type]['sem_line_alpha'], width=7).grid(
                row=row_offset, column=1, padx=10, pady=5)
            row_offset += 1

        # Desired Offset and Scale
        self.settings_vars[setting_type]['desired_offset'] = tk.StringVar(
            value=self.get_setting(setting_type, 'desired_offset'))
        tk.Label(parent_frame, text=f"{setting_type} Desired Offset:", bg='snow').grid(
            row=row_offset, column=0, sticky=tk.W, padx=10, pady=5)
        tk.Entry(parent_frame, textvariable=self.settings_vars[setting_type]['desired_offset'], width=7).grid(
            row=row_offset, column=1, padx=10, pady=5)

        row_offset += 1

        self.settings_vars[setting_type]['desired_scale'] = tk.StringVar(
            value=self.get_setting(setting_type, 'desired_scale'))
        tk.Label(parent_frame, text=f"{setting_type} Desired Scale:", bg='snow').grid(
            row=row_offset, column=0, sticky=tk.W, padx=10, pady=5)
        tk.Entry(parent_frame, textvariable=self.settings_vars[setting_type]['desired_scale'], width=7).grid(
            row=row_offset, column=1, padx=10, pady=5)

        row_offset += 1

        # Y Axis Color and Number of Ticks
        self.settings_vars[setting_type]['y_axis_color'] = tk.StringVar(
            value=self.get_setting(setting_type, 'y_axis_color'))
        tk.Label(parent_frame, text=f"{setting_type} Y Axis Colour:", bg='snow').grid(
            row=row_offset, column=0, sticky=tk.W, padx=10, pady=5)
        tk.Button(parent_frame, text="Choose Colour", command=lambda: self.choose_y_axis_color(
            setting_type, popup)).grid(row=row_offset, column=1, padx=10, pady=5)

        row_offset += 1

        self.settings_vars[setting_type]['num_ticks'] = tk.StringVar(
            value=self.get_setting(setting_type, 'num_ticks'))
        tk.Label(parent_frame, text=f"{setting_type} Number of Ticks:", bg='snow').grid(
            row=row_offset, column=0, sticky=tk.W, padx=10, pady=5)
        tk.Entry(parent_frame, textvariable=self.settings_vars[setting_type]['num_ticks'], width=7).grid(
            row=row_offset, column=1, padx=10, pady=5)

    def choose_setting_color(self, setting_type, setting_name, color_var, popup):
        """
        Opens a color chooser dialog and sets the selected color for a given setting.

        Parameters:
        - setting_type (str): The type of setting to set.
        - setting_name (str): The name of the setting to set.
        - color_var (tk.StringVar): The variable to hold the selected color.
        - popup (tk.Toplevel): The pop-up window to bring to the front.
        """
        color = colorchooser.askcolor()
        if color[1]:  # If a color is chosen (color[1] is the hex color code)
            # Update the StringVar with the selected color
            color_var.set(color[1])
            # Update the setting in the manager
            self.set_setting(setting_type, setting_name, color[1])

        popup.lift()  # Bring the settings popup to the front

    def choose_photometry_line_color(self, popup):
        """
        Open a color picker dialog and set the photometry line color.

        Parameters:
        - popup (tk.Toplevel): The pop-up window to bring to the front.
        """
        color = colorchooser.askcolor()
        if color[1]:
            self.photometry_line_color_var.set(color[1])
        popup.lift()  # Bring the settings popup to the front

    def choose_scale_bar_color(self, popup):
        """
        Open a color picker dialog and set the scale bar color.

        Parameters:
        - popup (tk.Toplevel): The pop-up window to bring to the front.
        """
        color = colorchooser.askcolor()
        if color[1]:
            self.scale_bar_color_var.set(color[1])
        popup.lift()  # Bring the settings popup to the front

    def choose_y_axis_color(self, setting_type, popup):
        """
        Open a color picker dialog and set the y-axis color.

        Parameters:
        - setting_type (str): The type of setting to set.
        - popup (tk.Toplevel): The pop-up window to bring to the front.
        """
        color = colorchooser.askcolor()
        if color[1]:
            self.settings_manager.set_selected_y_axis_color(
                setting_type, color[1])
        popup.lift()  # Bring the settings popup to the front

    def save_and_close_photometry_settings(self, popup):
        """
        Save the Photometry settings and close the popup window.

        Parameters:
        - popup (tk.Toplevel): The pop-up window to close.
        """
        # Save the Photometry settings
        self.settings_manager.selected_photometry_line_color = self.photometry_line_color_var.get()
        self.settings_manager.selected_photometry_line_width = self.selected_photometry_line_width.get()
        self.settings_manager.selected_photometry_line_alpha = self.photometry_line_alpha_var.get()
        self.settings_manager.selected_horizontal_scale_bar_offset = self.horizontal_scale_bar_offset_var.get()
        self.settings_manager.selected_vertical_scale_bar_offset = self.vertical_scale_bar_offset_var.get()
        self.settings_manager.selected_scale_bar_color = self.scale_bar_color_var.get()
        self.settings_manager.selected_scale_bar_width = self.scale_bar_width_var.get()
        self.settings_manager.selected_scale_bar_size = self.scale_bar_size_var.get()

        # Save to file and redraw the graph as needed
        self.settings_manager.save_variables()
        self.redraw_graph()  # todo add callback to redraw graph

        popup.destroy()

    def save_and_close_temperature_settings(self, popup):
        """
        Save the Temperature settings and close the popup window.

        Parameters:
        - popup (tk.Toplevel): The pop-up window to close.
        """
        # Save the Temperature settings using the settings_vars dictionary
        self.settings_manager.selected_temp_line_width = self.settings_vars['Temperature']['mean_line_width'].get(
        )
        self.settings_manager.selected_temp_mean_line_color = self.settings_vars['Temperature']['mean_line_color'].get(
        )
        self.settings_manager.selected_temp_sem_color = self.settings_vars['Temperature']['sem_color'].get(
        )
        self.settings_manager.selected_temp_mean_line_alpha = self.settings_vars['Temperature']['mean_line_alpha'].get(
        )
        self.settings_manager.selected_temp_sem_line_alpha = self.settings_vars['Temperature']['sem_line_alpha'].get(
        )
        self.settings_manager.selected_temp_desired_offset = self.settings_vars['Temperature']['desired_offset'].get(
        )
        self.settings_manager.selected_temp_desired_scale = self.settings_vars['Temperature']['desired_scale'].get(
        )
        self.settings_manager.selected_temp_y_axis_color = self.settings_vars['Temperature']['y_axis_color'].get(
        )
        self.settings_manager.selected_temp_num_ticks = self.settings_vars['Temperature']['num_ticks'].get(
        )

        # Save to file and redraw the graph as needed
        self.settings_manager.save_variables()
        self.redraw_graph()

        popup.destroy()

    def save_and_close_activity_settings(self, popup):
        """
        Save the Activity settings and close the popup window.

        Parameters:
        - popup (tk.Toplevel): The pop-up window to close.
        """
        # Save the Activity settings using the settings_vars dictionary
        self.settings_manager.selected_activity_mean_bar_color = self.settings_vars['Activity']['mean_bar_color'].get(
        )
        self.settings_manager.selected_activity_mean_bar_alpha = self.settings_vars['Activity']['mean_bar_alpha'].get(
        )
        self.settings_manager.selected_activity_desired_offset = self.settings_vars['Activity']['desired_offset'].get(
        )
        self.settings_manager.selected_activity_desired_scale = self.settings_vars['Activity']['desired_scale'].get(
        )
        self.settings_manager.selected_activity_y_axis_color = self.settings_vars['Activity']['y_axis_color'].get(
        )
        self.settings_manager.selected_activity_num_bins = self.activity_num_bins_var.get()
        self.settings_manager.selected_activity_num_ticks = self.settings_vars['Activity']['num_ticks'].get(
        )

        # Save to file and redraw the graph as needed
        self.settings_manager.save_variables()
        self.redraw_graph()

        popup.destroy()

    def redraw_graph(self):
        """Redraw the graph."""
        if self.redraw_graph_callback:
            self.redraw_graph_callback()
