import json
import tkinter as tk


class AppSettingsManager:
    def __init__(self, app_type="default"):
        """
        Initialize the settings manager with default settings.

        Parameters:
        - app_type (str): The type of app to initialize the settings for.
        """
        self.app_type = app_type
        self.initialize_default_settings()
        self.unique_behaviours = []
        self.selected_column_name = None

        self.display_duration_box_var = tk.BooleanVar(value=True)
        self.num_instances_box_var = tk.BooleanVar(value=True)

    def initialize_default_settings(self):
        """Initialize the settings with default values."""

        self.behaviour_colors = {} 
        self.default_settings = {
            'selected_trace_color': 'green',
            'selected_sem_color': 'grey',
            'selected_bar_sem_color': "grey",
            'selected_bar_fill_color': "blue",
            'selected_bar_border_color': "black",
            'selected_line_color': 'red',
            'selected_temp_line_color': 'red',
            'selected_activity_bar_color': 'blue',
            'selected_cluster_box_color': 'orange',
            'default_onset_line_color': 'red',
            'default_sem_color': 'grey',
            'default_line_color': 'red',
            'default_bar_sem_color': 'grey',
            'default_bar_fill_color': 'blue',
            'default_bar_border_color': 'black',
            'default_trace_color': 'green',
            'default_temp_line_color': 'red',
            'default_activity_bar_color': 'blue',
            'default_temp_sem_color': 'orange',
            'default_photometry_line_color': 'green',
            'default_cluster_box_color': 'orange',
            'default_cluster_box_alpha': '0.2',
            'default_cluster_box_height_modifier': '1',
            'selected_label_color': 'red',
            'selected_label_symbol': '*',
            'selected_label_size': '12',
            'selected_y_offset_peak_symbol': '0',
            'selected_peak_count_color': 'red',
            'selected_peak_count_size': '12',
            'selected_y_for_peak_count': '10',
            'selected_baseline_multiplier': '',
            'selected_baseline_color': 'green',
            'selected_baseline_style': '--',
            'selected_baseline_thickness': '1',
            'selected_photometry_line_color': 'black',
            'selected_photometry_line_alpha': '1.0',
            'selected_cluster_box_alpha': '0.2',
            'selected_cluster_box_height_modifier': '1',
            'light_off_time_var': '19:00:00',
            'selected_photometry_line_width': '0.5',
            'selected_horizontal_scale_bar_offset': '10',
            'selected_vertical_scale_bar_offset': '10',
            'selected_scale_bar_color': 'black',
            'selected_scale_bar_width': '2',
            'selected_scale_bar_size': '5',
            'selected_temp_mean_line_width': '1',
            'selected_temp_mean_line_color': 'red',
            'selected_temp_sem_color': 'red',
            'selected_temp_mean_line_alpha': '1.0',
            'selected_temp_sem_line_alpha': '0.1',
            'selected_temp_desired_offset': '0.5',
            'selected_temp_desired_scale': '0.4',
            'selected_temp_y_axis_color': 'red',
            'selected_temp_num_ticks': '10',
            'selected_activity_mean_bar_color': 'green',
            'selected_activity_mean_bar_alpha': '0.5',
            'selected_activity_desired_offset': '0',
            'selected_activity_desired_scale': '0.3',
            'selected_activity_y_axis_color': 'green',
            'selected_activity_num_bins': '',
            'selected_activity_num_ticks': '10',
            'telemetry_folder_path': '',
            'default_data_folder_path': '',
            'number_of_minor_ticks': '0',
            'onset_line_color': 'red',
            'onset_line_thickness': '1',
            'onset_line_style': '--',
            'duration_box_placement': '1.0',
            'box_height_factor': '0.2',
            'alpha': '0.2',
            'bar_graph_size': '0.2',
            'selected_column_name': '',
        }
        # Initialize settings with default values
        for key, value in self.default_settings.items():
            setattr(self, key, value)

    def update_unique_behaviours(self, unique_behaviours):
        """
        Update the unique behaviours in the settings.

        Parameters:
        - unique_behaviours (list): The list of unique behaviours.
        """
        self.unique_behaviours = unique_behaviours

    def update_behaviour_colors(self, behaviour_colors):
        """
        Update the behaviour colors in the settings.

        Parameters:
        - behaviour_colors (dict): The dictionary of behaviour colors.
        """
        self.behaviour_colors = behaviour_colors

    def save_variables(self):
        """Save the current settings to a file."""
        existing_config = self.load_existing_config()
        config = self.construct_config(existing_config)
        self.save_config_to_file(config)

    def load_existing_config(self):
        """
        Load the existing settings from a file.

        Returns:
        - dict: The existing settings loaded from the file.

        Raises:
        - FileNotFoundError: If the file does not exist        
        """
        try:
            with open(f"{self.app_type}_settings.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            print("No existing settings found. Creating new settings file.")
            return {}

    def save_values_from_gui(self):
        """Save the values from the GUI to the settings."""
        # Save values from GUI to settings
        self.selected_photometry_line_width = self.graph_settings_container_instance.selected_photometry_line_width.get()
        self.box_height_factor = self.graph_settings_container_instance.box_height_entry.get()
        self.alpha = self.graph_settings_container_instance.alpha_entry.get()
        self.bar_graph_size = self.graph_settings_container_instance.bar_graph_size_entry.get()
        self.onset_line_thickness = self.graph_settings_container_instance.onset_line_thickness_entry.get()
        self.onset_line_style = self.graph_settings_container_instance.onset_line_style_combobox.get()
        self.duration_box_placement = self.graph_settings_container_instance.duration_box_placement.get()
        # self.number_of_minor_ticks = self.graph_settings_container_instance.number_of_minor_ticks.get()

    def construct_config(self, existing_config):
        """
        Construct the configuration dictionary depending on the app used.

        Parameters:
        - existing_config (dict): The existing configuration dictionary.

        Returns:
        - config (dict): The configuration dictionary for the app opened.
        """
        config = existing_config.copy()
        config.update(self.shared_config())
        if self.app_type == "align_photometry_and_behaviour_app":
            self.save_values_from_gui()
            config.update(self.align_specific_config())
        elif self.app_type == "Menopause_app":
            config.update(self.menopause_specific_config())
        return config

    def shared_config(self):
        """Return the shared configuration for all apps."""
        return {
            'selected_photometry_line_width': self.selected_photometry_line_width,
            'selected_bar_fill_color': self.selected_bar_fill_color,
            'selected_bar_border_color': self.selected_bar_border_color,
            'selected_line_color': self.selected_line_color,
            'selected_bar_sem_color': self.selected_bar_sem_color,
            'selected_trace_color': self.selected_trace_color,
            'selected_sem_color': self.selected_sem_color,
            'default_data_folder_path': self.default_data_folder_path,
            'selected_column_name': self.selected_column_name,
            'number_of_minor_ticks': self.number_of_minor_ticks,
        }

    def align_specific_config(self):
        """
        Return the configuration specific to align_photometry_and_behaviour_app.

        Returns:
        - config (dict): The configuration dictionary for the align_photometry_and_behaviour.
        """
        config = {
            'box_height_factor': self.box_height_factor,
            'alpha': self.alpha,
            'bar_graph_size': self.bar_graph_size,
            'onset_line_color': self.onset_line_color,
            'onset_line_thickness': self.onset_line_thickness,
            'onset_line_style': self.onset_line_style,
            'duration_box_placement': self.duration_box_placement,
            'display_duration_box_var': self.display_duration_box_var.get(),
            'num_instances_box_var': self.num_instances_box_var.get(),
            'behaviour_colors': {}  # Initialize this key to avoid KeyError
        }
        behaviour_colors = getattr(self, 'behaviour_colors', {})

        for behaviour, actual_color in behaviour_colors.items():
            behaviour_color = actual_color

            if isinstance(behaviour_color, (tuple, list)):
                config['behaviour_colors'][behaviour] = behaviour_color

        return config

    def menopause_specific_config(self):
        """
        Return the configuration specific to Menopause_app.

        Returns:
        - config (dict): The configuration dictionary for the Menopause_app.        
        """
        return {
            'selected_cluster_box_color': self.selected_cluster_box_color,
            'selected_label_color': self.selected_label_color,
            'selected_label_symbol': self.selected_label_symbol,
            'selected_label_size': self.selected_label_size,
            'selected_y_offset_peak_symbol': self.selected_y_offset_peak_symbol,
            'selected_peak_count_color': self.selected_peak_count_color,
            'selected_peak_count_size': self.selected_peak_count_size,
            'selected_y_for_peak_count': self.selected_y_for_peak_count,
            'selected_baseline_multiplier': self.selected_baseline_multiplier,
            'selected_baseline_color': self.selected_baseline_color,
            'selected_baseline_style': self.selected_baseline_style,
            'selected_baseline_thickness': self.selected_baseline_thickness,
            'selected_cluster_box_alpha': self.selected_cluster_box_alpha,
            'selected_cluster_box_height_modifier': self.selected_cluster_box_height_modifier,
            'selected_column_name': self.selected_column_name,
            'light_off_time_var': self.light_off_time_var,
            'selected_photometry_line_color': self.selected_photometry_line_color,
            'selected_photometry_line_alpha': self.selected_photometry_line_alpha,
            'selected_temp_mean_line_width': self.selected_temp_mean_line_width,
            'selected_temp_mean_line_color': self.selected_temp_mean_line_color,
            'selected_temp_sem_color': self.selected_temp_sem_color,
            'selected_temp_mean_line_alpha': self.selected_temp_mean_line_alpha,
            'selected_temp_sem_line_alpha': self.selected_temp_sem_line_alpha,
            'selected_temp_desired_offset': self.selected_temp_desired_offset,
            'selected_temp_desired_scale': self.selected_temp_desired_scale,
            'selected_temp_y_axis_color': self.selected_temp_y_axis_color,
            'selected_temp_num_ticks': self.selected_temp_num_ticks,
            'selected_activity_mean_bar_color': self.selected_activity_mean_bar_color,
            'selected_activity_mean_bar_alpha': self.selected_activity_mean_bar_alpha,
            'selected_activity_desired_offset': self.selected_activity_desired_offset,
            'selected_activity_desired_scale': self.selected_activity_desired_scale,
            'selected_activity_y_axis_color': self.selected_activity_y_axis_color,
            'selected_activity_num_bins': self.selected_activity_num_bins,
            'selected_activity_num_ticks': self.selected_activity_num_ticks,
            'telemetry_folder_path': self.telemetry_folder_path,
        }

    def save_config_to_file(self, config):
        """
        Save the configuration to a file.

        Parameters:
        - config (dict): The configuration dictionary to save.

        Raises:
        - Exception: If there is an error saving the settings.        
        """
        try:
            with open(f"{self.app_type}_settings.json", "w") as f:
                json.dump(config, f)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def load_variables(self):
        """
        Load the settings from the file.

        Raises:
        - FileNotFoundError: If the file does not exist.
        - Exception: If there is an error loading the settings.        
        """
        try:
            with open(f"{self.app_type}_settings.json", "r") as f:
                settings = json.load(f)
            self.apply_settings(settings)
        except FileNotFoundError:
            print("No existing settings file found. Using default settings.")
        except Exception as e:
            print(f"Error loading settings: {e}")

    def apply_settings(self, settings):
        """
        Apply the settings to the current instance.

        Parameters:
        - settings (dict): The settings to apply.

        Raises:
        - AttributeError: If the attribute does not exist in the instance.
        """
        for key, value in settings.items():
            if hasattr(self, key):
                current_attribute = getattr(self, key)
                if isinstance(current_attribute, tk.BooleanVar):
                    # Update the BooleanVar with the value from settings
                    current_attribute.set(value)
                elif key == 'behaviour_colors':
                    # Special handling for 'behaviour_colors'
                    setattr(self, key, value)
                else:
                    # For all other settings that don't require special handling
                    setattr(self, key, value)

    def update_graph_settings_container(self, graph_settings_container_instance):
        """
        Update the graph settings container instance.

        Parameters:
        - graph_settings_container_instance: The graph settings container instance.
        """
        self.graph_settings_container_instance = graph_settings_container_instance

    def update_export_options_container(self, export_options_container):
        """
        Update the export options container instance.

        Parameters:
        - export_options_container: The export options container instance.
        """
        self.export_options_container = export_options_container
