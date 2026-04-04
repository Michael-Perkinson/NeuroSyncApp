from typing import List, Optional, Callable
from pathlib import Path
import logging
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from tkinter import ttk
import pandas as pd
from src.gui.shared.data_selection_state import (
    init_analysis_state,
    init_display_vars,
    init_file_vars,
)
from src.processing.data_utils import extract_mouse_name
from src.file_management.file_loader import load_data_file, process_loaded_data
from src.gui.shared.ui_elements import populate_dropdown
from src.gui.shared.tk_state import bind_tk_var
from src.gui.shared.view_state_models import DataSelectionViewState
from src.core.app_settings_manager import AppSettingsManager

logger = logging.getLogger(__name__)


class DataSelectionFrame(ttk.Frame):
    def __init__(self,
                parent: tk.Widget,
                settings_manager: AppSettingsManager,
                width: Optional[int] = None,
                figure_display_callback: Optional[Callable] = None,
                new_data_file_callback: Optional[Callable] = None,
                figure_display_dropdown: Optional[ttk.OptionMenu] = None,
                figure_display_choices: Optional[list[str]] = None,
                baseline_button_pressed: bool = False,
                update_table_from_frame_callback: Optional[Callable] = None,
                **kwargs) -> None:
        """
        Initialize the DataSelectionFrame.

        Parameters:
        - parent (tk.Widget): The parent widget.
        - settings_manager (AppSettingsManager): The settings manager for the application.
        - width (Optional[int]): The width of the frame.
        - figure_display_callback (Optional[Callable]): Callback for handling figure display selection.
        - new_data_file_callback (Optional[Callable]): Callback for handling new data file selection.
        - figure_display_dropdown (Optional[ttk.OptionMenu]): The dropdown menu for figure display.
        - figure_display_choices (Optional[list[str]]): Choices for figure display dropdown.
        - baseline_button_pressed (bool): Whether the baseline button has been pressed.
        - update_table_from_frame_callback (Optional[Callable]): Callback for updating the table from the frame.
        - **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(parent, style='Bordered.TFrame', **kwargs)

        self.settings_manager = settings_manager
        self.width= width

        self.handle_figure_display_selection = figure_display_callback
        self.new_data_file_callback = new_data_file_callback
        self.figure_display_dropdown = figure_display_dropdown
        self.figure_display_choices = figure_display_choices
        self.baseline_button_pressed = baseline_button_pressed
        self.update_table_from_frame = update_table_from_frame_callback

        self.setup_variables()
        self.create_frame_widgets()


    def setup_variables(self) -> None:
        """Initialize instance variables & UI state variables."""
        init_file_vars(self)
        init_display_vars(self)
        init_analysis_state(self)
        self.view_state = DataSelectionViewState()

        self.use_baseline_var = tk.BooleanVar(value=False)
        self.use_baseline_var.trace_add(
            'write', lambda *_: self.toggle_baseline_entries())
        bind_tk_var(self.file_path_var, self.view_state, "file_path")
        bind_tk_var(self.selected_column, self.view_state, "selected_column")
        bind_tk_var(self.use_baseline_var, self.view_state, "use_baseline")

    def create_frame_widgets(self) -> None:
        """Create and layout the widgets for the frame."""
        self.configure(style='Bordered.TFrame')

        if self.width is not None:
            self.grid_columnconfigure(0, minsize=self.width)

        self._create_headers()
        self._create_file_selection()
        self._create_baseline_settings()
        self._create_save_button()

    def _create_headers(self) -> None:
        """Create the title label for the data selection section."""
        data_selection_title_label = tk.Label(
            self, text="Data Selection", font=('Helvetica', 12, 'bold'),
            fg='black', bg='snow'
        )
        data_selection_title_label.grid(row=0, column=0, padx=10, pady=(10, 5))

    def _create_file_selection(self) -> None:
        """Create the file selection area with buttons and entry field."""
        file_row_frame = ttk.Frame(self, style="Custom.TFrame")
        file_row_frame.grid(row=1, column=0, padx=10,
                            pady=(10, 5), sticky=tk.NSEW)

        select_data_folder_button = tk.Button(
            file_row_frame, text="Select Folder", font=('Helvetica', 10),
            bg='lightblue', command=self.select_default_data_folder
        )
        select_data_folder_button.grid(row=0, column=0, padx=10, sticky=tk.W)

        select_button = tk.Button(
            file_row_frame, text="Select File:", font=('Helvetica', 10),
            bg='lightblue', command=lambda: self._on_select_file(self.file_path_var)
        )
        select_button.grid(row=0, column=1, padx=10, sticky=tk.W)

        self._create_file_name_entry(file_row_frame)
        self._create_column_title_selector(file_row_frame)

    def _on_select_file(self, file_path_var: tk.StringVar) -> None:
        """
        Handles file selection via GUI and loads data.

        Parameters:
        - file_path_var (tk.StringVar): The variable for the selected file path.
        """
        file_path = self._prompt_file_selection()

        if not file_path:
            return

        try:
            file_path_var.set(file_path)
            dataframe = load_data_file(file_path)
            if dataframe is None or getattr(dataframe, "empty", False):
                raise ValueError("The selected file did not contain usable tabular data.")

            processed_data = process_loaded_data(dataframe)

            dataframe = processed_data["dataframe"]
            column_titles = processed_data["column_titles"]
            self.selected_column.set(processed_data["selected_column"])
            is_time_based = processed_data["is_time_based"]
        except Exception as exc:
            logger.warning("Failed to load data file %s: %s", file_path, exc)
            file_path_var.set("")
            messagebox.showerror(
                "File Load Error",
                f"Could not load that file.\n\n{exc}",
                parent=self,
            )
            return

        if not is_time_based:
            logger.debug("Proceeding despite suspected non-time data in %s.", file_path)

        self._update_ui_after_file_selection(
            file_path, dataframe, column_titles, self.selected_column, is_time_based
        )

        mouse_name = self._get_mouse_name(file_path)

        if self.new_data_file_callback:
            self.new_data_file_callback(
                self.file_path_var,
                self.selected_column,
                self.column_dropdown,
                mouse_name,
                dataframe,
                is_time_based,
            )

    def _prompt_file_selection(self) -> str:
        """
        Prompt user for file selection.

        Returns:
        - str: The selected file path.
        """
        initial_dir = getattr(self.settings_manager,
                              'default_data_folder_path', None)

        return filedialog.askopenfilename(
            initialdir=initial_dir,
            filetypes=[("All supported files", "*.csv;*.xlsx"),
                       ("CSV Files", "*.csv"),
                       ("Excel Files", "*.xlsx")]
        )

    def _update_ui_after_file_selection(
        self,
        file_path: str,
        dataframe: pd.DataFrame,
        column_titles: List[str],
        selected_column: tk.StringVar,
        is_time_based: bool
        ) -> None:
        """Update UI after loading a file.

        Parameters:
        - file_path (str): The selected file path.
        - dataframe (pd.DataFrame): The loaded DataFrame.
        - column_titles (List[str]): The column names.
        - selected_column (tk.StringVar): The selected column variable.
        - is_time_based (bool): Whether the data is time-based.
        """
        populate_dropdown(self.column_dropdown,
                          selected_column, column_titles)
        self.column_dropdown['state'] = 'normal'
        preferred_columns = ['dFoF_465', '490DF/F']
        selected_column = next(
            (col for col in preferred_columns if col in dataframe.columns), dataframe.columns[1])
        self.selected_column.set(selected_column)

        self.baseline_button_pressed = False

    def _get_mouse_name(self, file_path):
        """
        Gets the mouse name, prompting the user only if necessary.

        Parameters:
        - file_path (str): The file path from which to extract the mouse name.

        Returns:
        - str: The mouse name.
        """
        mouse_name = extract_mouse_name(file_path)

        if not mouse_name:
            mouse_name = simpledialog.askstring(
                "Input",
                "No mouse number found in the filename. Please enter the mouse name or identifying code:",
                parent=self
            )

        return mouse_name if mouse_name else Path(file_path).name[:12]

    def select_default_data_folder(self):
        """Opens a folder chooser dialog to select the default data folder."""
        root = tk.Tk()
        root.withdraw()
        folder_path = filedialog.askdirectory(
            title="Select Default Data Folder"
        )
        root.destroy()

        if folder_path:
            self.settings_manager.default_data_folder_path = folder_path
            self.settings_manager.save_variables()

    def _create_file_name_entry(self, parent_frame):
        """
        Create the entry widget for displaying the selected file name.

        Parameters:
        - parent_frame (tk.Frame): The parent frame for the entry widget.
        """
        self.file_name_entry_frame = ttk.Frame(parent_frame)
        self.file_name_entry_frame.grid(row=0, column=2, padx=10, sticky=tk.W)

        self.file_name_entry_scrollbar = tk.Scrollbar(
            self.file_name_entry_frame, orient=tk.HORIZONTAL
        )
        self.file_name_entry_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.file_name_entry = tk.Entry(
            self.file_name_entry_frame, width=15, font=('Helvetica', 10),
            fg='black', bg='snow', state='readonly',
            textvariable=self.file_path_var, xscrollcommand=self.file_name_entry_scrollbar.set
        )
        self.file_name_entry.pack(side=tk.LEFT, fill=tk.X)

        self.file_name_entry_scrollbar.config(
            command=self.file_name_entry.xview)

    def on_column_selection_changed(self):
        """
        Callback for when the column selection is changed.

        """
        self.settings_manager.selected_column_name = self.selected_column.get()
        self.handle_figure_display_selection(None)

    def _create_column_title_selector(self, parent_frame):
        """Create a dropdown selector for choosing the data column."""
        self.column_label = tk.Label(
            parent_frame, text="Column Title:", font=('Helvetica', 10),
            fg='black', bg='snow'
        )
        self.column_label.grid(row=0, column=3, sticky=tk.W)

        self.column_dropdown_frame = ttk.Frame(
            parent_frame, borderwidth=2, relief="solid", style='Bordered.TFrame'
        )
        self.column_dropdown_frame.grid(
            row=0, column=4, pady=(0, 5), sticky=tk.E)

        self.column_dropdown = ttk.OptionMenu(
            self.column_dropdown_frame, self.selected_column, '', ""
        )
        self.column_dropdown.configure(style="Custom.TMenubutton")
        self.column_dropdown.grid(row=0, column=4, sticky=tk.W)
        self.column_dropdown['state'] = 'disabled'

    def _create_baseline_settings(self):
        """Create the baseline settings UI."""
        self.baseline_note_frame = ttk.Frame(self, style="Custom.TFrame")
        self.baseline_note_frame.grid(
            row=2, column=0, padx=10, pady=(10, 5), sticky=tk.NSEW)

        baseline_checkbox = ttk.Checkbutton(
            self.baseline_note_frame, text="Baselined z-score",
            variable=self.use_baseline_var, style='Custom.TCheckbutton',
            command=self.toggle_baseline_entries
        )
        baseline_checkbox.grid(
            row=0, column=0, padx=(0, 20), pady=10, sticky=tk.W)

        baseline_start_label = tk.Label(
            self.baseline_note_frame, text="Start Time (s):", font=('Helvetica', 10),
            fg='black', bg='snow'
        )
        baseline_start_label.grid(row=0, column=1, sticky=tk.W)

        self.baseline_start_entry = tk.Entry(
            self.baseline_note_frame, width=10, font=('Helvetica', 10),
            fg='black', bg='snow', state=tk.DISABLED
        )
        self.baseline_start_entry.bind(
            "<KeyRelease>", self.reset_baseline_button_state)
        self.baseline_start_entry.grid(row=0, column=2, sticky=tk.W)

        baseline_end_label = tk.Label(
            self.baseline_note_frame, text="End Time (s):", font=('Helvetica', 10),
            fg='black', bg='snow'
        )
        baseline_end_label.grid(row=0, column=3, padx=(10, 0), sticky=tk.W)

        self.baseline_end_entry = tk.Entry(
            self.baseline_note_frame, width=10, font=('Helvetica', 10),
            fg='black', bg='snow', state=tk.DISABLED
        )
        self.baseline_end_entry.bind(
            "<KeyRelease>", self.reset_baseline_button_state)
        self.baseline_end_entry.grid(row=0, column=4, sticky=tk.W)

    def _create_save_button(self):
        """Create the save button for baseline values."""
        self.baseline_save_button = tk.Button(
            self, text="Save Baseline", font=('Helvetica', 10),
            bg='lightblue', command=self._on_save_baseline
        )
        self.baseline_save_button.grid(row=3, column=0, padx=10, pady=(10, 5))

    def _on_save_baseline(self):
        """Wraps the baseline save callback to remove UI logic."""
        self.save_baseline_values(self.figure_display_dropdown)

    def toggle_baseline_entries(self):
        """Toggle baseline entry states based on checkbox selection."""
        is_checked = self.use_baseline_var.get()
        if not hasattr(self, "baseline_start_entry") or not hasattr(self, "baseline_end_entry"):
            return
        self._set_baseline_entry_state(is_checked)
        self._update_figure_display_dropdown(is_checked)

        if hasattr(self.master.master, "checkbox_state"):
            self.master.master.checkbox_state = is_checked

    def _set_baseline_entry_state(self, enabled):
        """Enable or disable baseline start/end entry fields."""
        state = tk.NORMAL if enabled else tk.DISABLED
        self.baseline_start_entry.config(state=state)
        self.baseline_end_entry.config(state=state)

    def _update_figure_display_dropdown(self, enabled):
        """Update figure display dropdown options based on baseline toggle."""
        if self.figure_display_dropdown is None:
            return
        if enabled and "Z-scored data" not in self.figure_display_dropdown['values']:
            self.figure_display_dropdown['values'] += ["Z-scored data"]
        elif not enabled and "Z-scored data" in self.figure_display_dropdown['values']:
            self.figure_display_dropdown['values'].remove("Z-scored data")

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
