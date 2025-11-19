import os
import re
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
from tkinter import simpledialog
from tkinter import ttk
import pandas as pd

from src.window_utils import center_window_on_screen
from src.app_settings_manager import AppSettingsManager


class DataSelectionFrame(ttk.Frame):
    def __init__(self, parent, settings_manager,
                 width=None,
                 figure_display_callback=None,
                 new_data_file_callback=None,
                 figure_display_dropdown=None,
                 figure_display_choices=None,
                 baseline_button_pressed=False,
                 update_table_from_frame_callback=None, **kwargs):
        """
        Initialize the DataSelectionFrame.

        Parameters:
        - parent (tk.Tk|tk.Frame): The parent widget.
        - settings_manager (AppSettingsManager): The settings manager for the application.
        - width (int): The width of the frame.
        - figure_display_callback (function): The callback for handling figure display selection.
        - new_data_file_callback (function): The callback for handling new data file selection.
        - figure_display_dropdown (function): The callback for handling figure display dropdown.
        - figure_display_choices (list): The choices for the figure display dropdown.
        - baseline_button_pressed (bool): Whether the baseline button has been pressed.
        - update_table_from_frame_callback (function): The callback for updating the table from the frame.
        - **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(parent, style='Bordered.TFrame', **kwargs)

        self.handle_figure_display_selection = figure_display_callback
        self.new_data_file_callback = new_data_file_callback
        self.figure_display_dropdown = figure_display_dropdown
        self.figure_display_choices = figure_display_choices
        self.baseline_button_pressed = baseline_button_pressed
        self.update_table_from_frame = update_table_from_frame_callback
        self.settings_manager = settings_manager

        self.file_path_var = tk.StringVar()
        self.selected_column_var = tk.StringVar()
        self.use_baseline_var = tk.BooleanVar(value=False)
        self.use_baseline_var.trace_add(
            'write', lambda *args: self.toggle_baseline_entries())

        self.column_dropdown = None
        self.dataframe = None
        self.mouse_name = None
        self.width = width

        self.create_frame_widgets()

    def create_frame_widgets(self):
        """Create and layout the widgets for the frame."""
        self.configure(style='Bordered.TFrame')
        if self.width is not None:
            self.grid_columnconfigure(0, minsize=self.width)

        self._create_data_selection_title()
        self._create_file_row_frame()
        self._create_baseline_note_frame()
        self._create_baseline_save_button()

    def _create_data_selection_title(self):
        """Create the title label for the data selection section."""
        data_selection_title_label = tk.Label(self, text="Data Selection", font=('Helvetica', 12, 'bold'),
                                              fg='black', bg='snow')
        data_selection_title_label.grid(row=0, column=0, padx=10, pady=(10, 5))

    def _create_file_row_frame(self):
        """Create the file row frame with buttons and entry for file selection."""
        file_row_frame = ttk.Frame(self, style="Custom.TFrame")
        file_row_frame.grid(row=1, column=0, padx=10,
                            pady=(10, 5), sticky=tk.NSEW)

        select_data_folder_button = tk.Button(file_row_frame, text="Select Folder", font=('Helvetica', 10), bg='lightblue',
                                              command=self.select_default_data_folder)
        select_data_folder_button.grid(row=0, column=0, padx=10, sticky=tk.W)

        select_button = tk.Button(file_row_frame, text="Select File:", font=('Helvetica', 10), bg='lightblue',
                                  command=lambda: self.select_main_data_file(self.file_path_var, self.selected_column_var, self.column_dropdown, self.dataframe))
        select_button.grid(row=0, column=1, padx=10, sticky=tk.W)

        self._create_file_name_entry(file_row_frame)
        self._create_column_title_selector(file_row_frame)

    def _create_file_name_entry(self, parent_frame):
        """
        Create the entry widget for displaying the selected file name.

        Parameters:
        - parent_frame (tk.Frame): The parent frame for the entry widget.
        """
        file_name_entry_frame = ttk.Frame(parent_frame)
        file_name_entry_frame.grid(row=0, column=2, padx=10, sticky=tk.W)

        file_name_entry_scrollbar = tk.Scrollbar(
            file_name_entry_frame, orient=tk.HORIZONTAL)
        file_name_entry_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        file_name_entry = tk.Entry(file_name_entry_frame, width=15, font=('Helvetica', 10), fg='black', bg='snow',
                                   state='readonly', textvariable=self.file_path_var, xscrollcommand=file_name_entry_scrollbar.set)
        file_name_entry.pack(side=tk.LEFT, fill=tk.X)
        file_name_entry_scrollbar.config(command=file_name_entry.xview)

    def on_column_selection_changed(self, *args):
        """
        Callback for when the column selection is changed.

        Parameters:
        - *args: Variable arguments.
        """
        self.settings_manager.selected_column_name = self.selected_column_var.get()
        self.handle_figure_display_selection(None)

    def _create_column_title_selector(self, parent_frame):
        """
        Create the combobox for selecting the data column title.

        Parameters:
        - parent_frame (tk.Frame): The parent frame for the combobox.
        """
        column_label = tk.Label(parent_frame, text="Column Title:", font=(
            'Helvetica', 10), fg='black', bg='snow')
        column_label.grid(row=0, column=3, sticky=tk.W)

        self.column_dropdown_frame = ttk.Frame(
            parent_frame, borderwidth=2, relief="solid")
        self.column_dropdown_frame.configure(style='Bordered.TFrame')
        self.column_dropdown_frame.grid(
            row=0, column=4, pady=(0, 5), sticky=tk.E)

        self.column_dropdown = ttk.OptionMenu(
            self.column_dropdown_frame, self.selected_column_var, '', "")
        self.column_dropdown.configure(style="Custom.TMenubutton")
        self.column_dropdown.grid(row=0, column=4, sticky=tk.W)
        self.column_dropdown['state'] = 'disabled'

        self.selected_column_var.set(" " * 1)
        self.column_dropdown["menu"].delete(0, "end")

    def _create_baseline_note_frame(self):
        """Create the baseline note frame with checkbox and time entries."""
        baseline_note_frame = ttk.Frame(self, style="Custom.TFrame")
        baseline_note_frame.grid(
            row=2, column=0, padx=10, pady=(10, 5), sticky=tk.NSEW)

        baseline_checkbox = ttk.Checkbutton(baseline_note_frame, text="Baselined z-score", variable=self.use_baseline_var,
                                            style='Custom.TCheckbutton', command=self.toggle_baseline_entries)
        baseline_checkbox.grid(
            row=0, column=0, padx=(0, 20), pady=10, sticky=tk.W)

        baseline_start_label = tk.Label(baseline_note_frame, text="Start Time (s):", font=('Helvetica', 10),
                                        fg='black', bg='snow')
        baseline_start_label.grid(row=0, column=1, sticky=tk.W)

        self.baseline_start_entry = tk.Entry(baseline_note_frame, width=10, font=('Helvetica', 10), fg='black', bg='snow',
                                             state=tk.DISABLED)
        self.baseline_start_entry.bind(
            "<KeyRelease>", self.reset_baseline_button_state)
        self.baseline_start_entry.grid(row=0, column=2, sticky=tk.W)

        baseline_end_label = tk.Label(baseline_note_frame, text="End Time (s):", font=('Helvetica', 10),
                                      fg='black', bg='snow')
        baseline_end_label.grid(row=0, column=3, padx=(10, 0), sticky=tk.W)

        self.baseline_end_entry = tk.Entry(baseline_note_frame, width=10, font=('Helvetica', 10), fg='black', bg='snow',
                                           state=tk.DISABLED)
        self.baseline_end_entry.bind(
            "<KeyRelease>", self.reset_baseline_button_state)
        self.baseline_end_entry.grid(row=0, column=4, sticky=tk.W)

    def _create_baseline_save_button(self):
        """Create the save button for baseline values."""
        baseline_save_button = tk.Button(self, text="Save Baseline", font=('Helvetica', 10), bg='lightblue',
                                         command=lambda: self.save_baseline_values(self.figure_display_dropdown))
        baseline_save_button.grid(row=3, column=0, padx=10, pady=(10, 5))

    def get_column_titles(self, dataframe):
        """
        Returns a list of column titles from a pandas DataFrame.

        Parameters:
        - dataframe (pd.DataFrame): The pandas DataFrame.
        """
        return dataframe.columns.tolist()

    def check_and_convert_time_column(self, dataframe):
        """
        Checks the first column of the given DataFrame for time units and converts them to minutes if found.

        Parameters:
        - dataframe (pd.DataFrame): The pandas DataFrame.

        Returns:
        - pd.DataFrame: The possibly modified DataFrame.
        """
        first_column_title = dataframe.columns[0].lower()

        time_units = {
            'seconds': 1 / 60,
            'sec': 1 / 60,  # This will handle 'sec' and 'secs'
            'minutes': 1,
            'min': 1
        }

        conversion_performed = False

        for unit, factor in time_units.items():
            # Use regular expression to find the unit surrounded by non-alphanumeric characters
            # or at the start/end of the string, including inside parentheses
            pattern = re.compile(
                r'\b' + re.escape(unit) + r's?\b', re.IGNORECASE)
            if pattern.search(first_column_title):
                dataframe.iloc[:, 0] = dataframe.iloc[:, 0] * factor
                # Rename the column to indicate minutes
                dataframe.columns = [
                    'Time (min)'] + dataframe.columns.tolist()[1:]
                conversion_performed = True
                break

        if conversion_performed:
            print("Time unit found and converted.")
        else:
            print("No time unit found. Assuming values are in minutes.")

        return dataframe

    def populate_dropdown(self, choices):
        """
        Populates the dropdown with the given choices.

        Parameters:
        - choices (list): The choices to populate the dropdown with.
        """
        menu = self.column_dropdown['menu']
        menu.delete(0, 'end')
        for choice in choices:
            menu.add_command(
                label=choice, command=lambda value=choice: self.selected_column_var.set(value))

    def select_main_data_file(self, file_path_var, selected_column_var, column_dropdown, dataframe, callback=None):
        """
        Opens a file chooser dialog and loads the selected file into a pandas DataFrame.

        Parameters:
        - file_path_var (tk.StringVar): The variable to store the selected file path.
        - selected_column_var (tk.StringVar): The variable to store the selected column name.
        - column_dropdown (ttk.OptionMenu): The dropdown for selecting the column name.
        - dataframe (pd.DataFrame): The DataFrame to store the loaded data.
        - callback (function): The callback to execute after loading the data.
        """
        initial_dir = self.settings_manager.default_data_folder_path if hasattr(
            self.settings_manager, 'default_data_folder_path') else None

        file_path = filedialog.askopenfilename(
            initialdir=initial_dir,
            filetypes=[("All supported files", "*.csv;*.xlsx"), ("CSV Files", "*.csv"), ("Excel Files", "*.xlsx")])

        # Return early if the file chooser is cancelled
        if not file_path:
            return

        if file_path:
            self.file_path_var.set(file_path)

            if file_path.endswith('.csv'):
                dataframe = pd.read_csv(file_path)
            elif file_path.endswith('.xlsx'):
                try:
                    dataframe = pd.read_excel(file_path)
                except:
                    dataframe = pd.read_excel(file_path, skiprows=1)

            dataframe = self.check_and_convert_time_column(dataframe)
            column_titles = self.get_column_titles(dataframe)
            selected_column_var.set(column_titles[0])

            self.populate_dropdown(column_titles)

            self.column_dropdown['state'] = 'normal'

            if self.settings_manager.selected_column_name in dataframe.columns:
                selected_column_var.set(
                    self.settings_manager.selected_column_name)
            elif 'dFoF_465' in dataframe.columns:
                selected_column_var.set('dFoF_465')
            elif '490DF/F' in dataframe.columns:
                selected_column_var.set('490DF/F')
            else:
                selected_column_var.set(dataframe.columns[1])

            is_time_based_data = self.is_time_data(dataframe)

            if not self.is_time_data(dataframe):
                print("Proceeding despite suspected non-time data.")

        mouse_name = self.extract_mouse_name(file_path)

        self.baseline_button_pressed = False
        if self.new_data_file_callback:
            self.new_data_file_callback(
                file_path_var, selected_column_var, column_dropdown, mouse_name, dataframe, is_time_based_data)

    def select_default_data_folder(self):
        """Opens a folder chooser dialog to select the default data folder."""
        root = tk.Tk()
        root.withdraw()
        folder_path = filedialog.askdirectory(
            title="Select Default Data Folder")
        root.destroy()

        if folder_path:
            self.settings_manager.default_data_folder_path = folder_path
            self.settings_manager.save_variables()

    def extract_mouse_name(self, file_path):
        """
        Extracts the mouse name from the given file path, using the first pattern
        of letters followed by numbers (e.g., ABC123).

        If none is found, prompts the user for manual entry.
        """
        base_name, _ = os.path.splitext(os.path.basename(file_path))

        # Regex: letters followed by digits
        pattern = r"[A-Za-z]+\d+"
        matches = re.findall(pattern, base_name)

        if matches:
            mouse_name = matches[0]   # Just take the first match
        else:
            # No matches found → ask user
            mouse_name = simpledialog.askstring(
                "Input",
                "No mouse number found in the filename. Please enter the mouse name or identifying code:",
                parent=self
            )

        # If user cancels or enters nothing, fallback
        if not mouse_name:
            mouse_name = os.path.basename(self.file_path_var.get())[:12]

        return mouse_name


    def is_time_data(self, dataframe, subset_size=20, tolerance_ratio=0.9):
        """
        Checks if the first column of the given DataFrame is consistent time data.

        Parameters:
        - dataframe (pd.DataFrame): The DataFrame to check.
        - subset_size (int): The size of the subset to check for time data consistency.
        - tolerance_ratio (float): The ratio of consistent differences to the subset size.

        Returns:
        - bool: Whether the first column is consistent time data.
        """
        first_column = dataframe.iloc[:, 0]
        if pd.api.types.is_numeric_dtype(first_column):
            diffs = first_column.diff().dropna()

            actual_subset_size = min(subset_size, len(diffs))

            mode_diff = pd.Series(diffs).mode()[0]

            # Count how many differences are close to the mode (within a small tolerance)
            tolerance = mode_diff * 0.05 
            consistent_diffs_count = sum(abs(diffs - mode_diff) < tolerance)

            # Check if the majority of differences are close to the mode
            return consistent_diffs_count / actual_subset_size >= tolerance_ratio

        else:
            return False

    def toggle_baseline_entries(self):
        """Toggles the state of the baseline start and end entries based on the state of the baseline checkbox."""
        if self.use_baseline_var.get() == 1:
            self.baseline_start_entry.config(state=tk.NORMAL)
            self.baseline_end_entry.config(state=tk.NORMAL)

            if "Z-scored data" not in self.figure_display_dropdown['values']:
                self.figure_display_dropdown['values'] = self.figure_display_choices + [
                    "Z-scored data"]
        else:
            self.baseline_start_entry.config(state=tk.DISABLED)
            self.baseline_end_entry.config(state=tk.DISABLED)

            if "Z-scored data" in self.figure_display_dropdown['values']:
                self.figure_display_dropdown['values'] = self.figure_display_choices

        self.master.master.checkbox_state = self.use_baseline_var.get()

    def save_baseline_values(self, figure_display_dropdown):
        """
        Saves the baseline start and end values and updates the table.

        Parameters:
        - figure_display_dropdown (tk.OptionMenu): The figure display dropdown from the main app.
        """
        figure_display_dropdown.set("Z-scored data")
        self.baseline_button_pressed = True

        self.handle_figure_display_selection(None)

        self.update_table_from_frame()

    def set_figure_display_dropdown(self, dropdown):
        """ 
        Sets the figure display dropdown from the main app.

        Parameters:
        - dropdown (tk.OptionMenu): The figure display dropdown from the main app.
        """
        self.figure_display_dropdown = dropdown

    def set_figure_display_choices(self, choices):
        """
        Sets the choices for the figure display dropdown.

        Parameters:
        - choices (list): The choices for the figure display.
        """
        self.figure_display_choices = choices

    def reset_baseline_button_state(self, event=None):
        """ 
        Resets the baseline button state to False.

        Parameters:
        - event (tk.Event): The event that triggered the reset.
        """
        self.baseline_button_pressed = False
