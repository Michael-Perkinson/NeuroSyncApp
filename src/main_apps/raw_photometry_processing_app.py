from tkinter import ttk, filedialog
import tkinter as tk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import pandas as pd

from src.processing.raw_photometry_processing import PhotometryRawProcessor
from src.gui.views.data_selection_frame_legacy import DataSelectionFrame
from src.core.app_settings_manager import AppSettingsManager
from src.gui.shared.tk_styles import define_custom_ttk_styles
from src.gui.shared.window_manager import center_window_on_screen


class RawPhotometryProcessingApp(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):
        """
        Initialize the main application frame.

        Parameters:
            parent (tk.Tk|tk.Frame): The parent widget.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        self.settings_manager = AppSettingsManager(
            app_type="raw_photometry_processing")
        self.app_name = "raw_photometry_processing"
        self.settings_manager.load_variables()

        define_custom_ttk_styles()

        super().__init__(parent, style='Bordered.TFrame', **kwargs)

        self.all_graphs_reference = {}
        self.file_path_var = tk.StringVar(value="")
        self.analysis_option_var = tk.IntVar(value=1)
        self.start_time_var = tk.StringVar(value="")
        self.end_time_var = tk.StringVar(value="")
        self.df_columns_var = tk.StringVar(value="")
        self.time_column_var = tk.StringVar(
            value=self.settings_manager.selected_time_column or "")
        self._405nm_column_var = tk.StringVar(
            value=self.settings_manager.selected_405nm_column or "")
        self._465nm_column_var = tk.StringVar(
            value=self.settings_manager.selected_465nm_column or "")

        self.configure_main_frames()
        self.create_widgets()

    def configure_main_frames(self):
        """Configure the main frames within the application."""
        self.top_frame = ttk.Frame(
            self, relief="groove", borderwidth=2, style="CustomFrame.TFrame")
        self.top_frame.grid(row=0, column=0, sticky="nsew")

        self.bottom_frame = ttk.Frame(
            self, relief="groove", borderwidth=2, style="CustomFrame.TFrame")
        self.bottom_frame.grid(row=1, column=0, sticky="nsew")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)

    def create_widgets(self):
        """Creates and configures various widgets for the GUI."""
        self.create_data_selection_widgets()
        self.create_time_selection_widgets()
        self.create_export_option_widgets()

        self.setup_notebooks()

        self.top_frame.grid_columnconfigure(0, weight=0)
        self.top_frame.grid_columnconfigure(1, weight=0)
        self.top_frame.grid_columnconfigure(2, weight=1)

    def create_data_selection_widgets(self):
        """Creates widgets for data selection."""
        self.data_selection_frame = DataSelectionFrame(
            self.top_frame,
            settings_manager=self.settings_manager,
            new_data_file_callback=self.handle_new_data_file,
        )
        self.data_selection_frame.grid(
            row=0, column=0, padx=5, pady=5, sticky=tk.NS)

        self.data_selection_frame.column_label.grid_forget()
        self.data_selection_frame.column_dropdown_frame.grid_forget()
        self.data_selection_frame.baseline_note_frame.grid_forget()
        self.data_selection_frame.baseline_save_button.grid_forget()

        self.time_dropdown_frame = self.create_dropdown(
            parent_frame=self.data_selection_frame,
            label_text="Time column:",
            dropdown_var=self.time_column_var,
            options=[],
            setting_key='selected_time_column'
        )

        self._405nm_dropdown_frame = self.create_dropdown(
            parent_frame=self.data_selection_frame,
            label_text="405nm column:",
            dropdown_var=self._405nm_column_var,
            options=[],
            setting_key='selected_405nm_column'
        )

        self._465nm_dropdown_frame = self.create_dropdown(
            parent_frame=self.data_selection_frame,
            label_text="465nm column:",
            dropdown_var=self._465nm_column_var,
            options=[],
            setting_key='selected_465nm_column'
        )

    def create_dropdown(self, parent_frame, label_text, dropdown_var, options=None, default_option="", setting_key=None):
        """
        Creates and returns a labeled dropdown menu with optional default value and settings persistence.

        Parameters:
            parent_frame (tk.Frame): The parent frame.
            label_text (str): The text for the label.
            dropdown_var (tk.StringVar): The variable for the dropdown.
            options (list): List of dropdown options. Defaults to an empty list.
            default_option (str): The default value to display. Defaults to an empty string.
            setting_key (str): Key for saving/retrieving the dropdown value in settings. Defaults to None.

        Returns:
            ttk.Frame: The frame containing the dropdown.
        """
        # Set initial value to default or saved value
        dropdown_var.set(default_option if not setting_key else getattr(
            self.settings_manager, setting_key, default_option))

        # Create dropdown container
        dropdown_container = ttk.Frame(parent_frame, style='NoBorder.TFrame')
        dropdown_container.grid(pady=(5, 5), padx=10, sticky=tk.EW)

        # Add label
        label = tk.Label(dropdown_container, text=label_text,
                         font=('Helvetica', 10), fg='black', bg='snow', anchor="w", width=12)
        label.grid(row=0, column=0, padx=(55, 0), sticky=tk.W)

        dropdown_frame = ttk.Frame(
            dropdown_container, borderwidth=2, relief="solid")
        dropdown_frame.configure(style='Bordered.TFrame')
        dropdown_frame.grid(
            row=0, column=1, sticky=tk.W)

        # Add empty dropdown, to be populated later
        dropdown = ttk.OptionMenu(
            dropdown_frame,
            dropdown_var,
            dropdown_var.get(),
            *(options or [])
        )
        dropdown.configure(style="Custom.TMenubutton", width=15)
        dropdown.grid(row=0, column=1, sticky=tk.W)

        # Initially disable dropdown
        dropdown['state'] = 'disabled'

        # Save the widget in a way it can be updated later
        dropdown_container.dropdown_widget = dropdown

        return dropdown_container

    def update_dropdown_options(self, dropdown_container, options, default_value=None):
        """
        Update the dropdown options dynamically and set default values.

        Parameters:
        - dropdown_container (ttk.Frame): The container holding the dropdown menu.
        - options (list): The list of new options to populate in the dropdown.
        - default_value (str, optional): The value to set as default if current value is invalid.
        
        Returns:
        - str: The current value in the dropdown.
        """

        dropdown = dropdown_container.dropdown_widget
        menu = dropdown['menu']
        menu.delete(0, 'end')  # Clear existing options

        # Populate new options in the dropdown menu
        for option in options:
            menu.add_command(
                label=option,
                command=lambda value=option: dropdown.setvar(
                    dropdown.cget("textvariable"), value)
            )
        dropdown['state'] = 'normal'

        # Determine the default value
        current_value = dropdown.getvar(dropdown.cget("textvariable"))
        if default_value and default_value in options:
            dropdown.setvar(dropdown.cget("textvariable"), default_value)
        elif current_value not in options and options:
            dropdown.setvar(dropdown.cget("textvariable"), options[0])
        elif not options:
            dropdown['state'] = 'disabled'  # Disable dropdown if no options
            
        return current_value 

    def create_time_selection_widgets(self):
        """Creates widgets for time selection."""
        self.time_selection_frame = ttk.Frame(
            self.top_frame, style='Bordered.TFrame')
        self.time_selection_frame.grid(
            row=0, column=1, padx=5, pady=5, sticky=tk.NSEW)

        self.time_selection_frame_title = tk.Label(
            self.time_selection_frame, text="Time Selection for analysis", font=('Helvetica', 12, 'bold'), fg='black', bg='snow')
        self.time_selection_frame_title.grid(
            row=0, column=0, columnspan=2, padx=10, pady=(5, 15))

        self.start_time_label = tk.Label(
            self.time_selection_frame, text="Start Time (s):", font=('Helvetica', 10), fg='black', bg='snow')
        self.start_time_label.grid(
            row=1, column=0, padx=10, pady=(0, 5), sticky=tk.W)

        self.start_time_entry = tk.Entry(
            self.time_selection_frame, width=10, font=('Helvetica', 10), fg='black', bg='snow', textvariable=self.start_time_var)
        self.start_time_entry.grid(
            row=1, column=1, padx=10, pady=(0, 5), sticky=tk.W)

        self.end_time_label = tk.Label(
            self.time_selection_frame, text="End Time (s):", font=('Helvetica', 10), fg='black', bg='snow')
        self.end_time_label.grid(
            row=2, column=0, padx=10, pady=(0, 5), sticky=tk.W)

        self.end_time_entry = tk.Entry(
            self.time_selection_frame, width=10, font=('Helvetica', 10), fg='black', bg='snow', textvariable=self.end_time_var)
        self.end_time_entry.grid(
            row=2, column=1, padx=10, pady=(0, 5), sticky=tk.W)

        self.total_time_label = tk.Label(
            self.time_selection_frame, text="Total Time (s):", font=('Helvetica', 10), fg='black', bg='snow')
        self.total_time_label.grid(
            row=3, column=0, padx=10, pady=(0, 5), sticky=tk.W)

        self.total_time_display = tk.Label(
            self.time_selection_frame,
            text="0 s",  # Set initial text with maximum possible width
            font=('Helvetica', 10, 'bold'),
            fg='blue',
            bg='snow',
            anchor='w',  # Align text to the left
            width=15  # Set a fixed width (adjust based on your content)
        )
        self.total_time_display.grid(
            row=3, column=1, padx=10, pady=(0, 5), sticky=tk.W
        )

        self.start_time_var.trace_add(
            "write", self.refresh_time_selection_preview
        )
        self.end_time_var.trace_add("write", self.refresh_time_selection_preview)

        self.save_times_button = tk.Button(
            self.time_selection_frame, text="Save Times", bg='lightblue', command=self.save_times)
        self.save_times_button.grid(
            row=4, column=1, padx=10, pady=(5, 5), sticky=tk.W)

    def create_export_option_widgets(self):
        """Creates widgets for export options."""
        self.export_options_frame = ttk.Frame(
            self.top_frame, style='Bordered.TFrame')
        self.export_options_frame.grid(
            row=0, column=2, padx=5, pady=5, sticky=tk.NSEW)

        self.export_options_frame_title = tk.Label(
            self.export_options_frame, text="Export Options", font=('Helvetica', 12, 'bold'), fg='black', bg='snow')
        self.export_options_frame_title.grid(
            row=0, column=0, columnspan=2, padx=10, pady=(5, 15))

        self.time_selection_frame_title = tk.Label(
            self.export_options_frame, text="Choose Noise Correction", font=('Helvetica', 12, 'bold'), fg='black', bg='snow')
        self.time_selection_frame_title.grid(
            row=4, column=0, columnspan=2, padx=10, pady=(5, 5))

        self.analysis_option_label = tk.Label(
            self.export_options_frame, text="Analysis Option Below:", font=('Helvetica', 10), fg='black', bg='snow')
        self.analysis_option_label.grid(
            row=5, column=0, padx=10, pady=(0, 5), sticky=tk.NSEW)

        self.analysis_option_dropdown = ttk.Combobox(
            self.export_options_frame,
            textvariable=self.analysis_option_var,
            values=["1", "2", "3", "4"],
            state="readonly"
        )
        self.analysis_option_dropdown.set("1")
        self.analysis_option_dropdown.grid(
            row=5, column=1, columnspan=1, sticky=tk.NSEW)

        def on_combobox_change(event):
            selected_option = self.analysis_option_var.get()
            # Handle the selection
            print(f"Selected option: {selected_option}")

        self.analysis_option_dropdown.bind(
            "<<ComboboxSelected>>", on_combobox_change)

    def process_dropdown_selection(self, value, setting_key):
        """
        Process the dropdown selection and save it to settings.

        Parameters:
            value (str): The selected value.
            setting_key (str): The key to save the value under.
        """
        if setting_key:
            setattr(self.settings_manager, setting_key, value)
            self.settings_manager.save_variables()  # Save the updated settings
        else:
            print(
                f"Warning: No setting_key provided for dropdown selection: {value}")

    def save_times(self):
        selected_range = self._get_selected_time_range_minutes()
        if selected_range is None:
            self.total_time_display.config(text="Invalid")
            return

        start_time, end_time = selected_range
        self.update_lines(graph_index=0, start_time=start_time, end_time=end_time)

    def _get_primary_graph_x_range(self, graph_index=0):
        """Return the min/max x-range for the requested graph, or None if unavailable."""
        graph = self.all_graphs_reference.get(graph_index)
        if not graph:
            return None

        ax = graph.get("primary_axis")
        if not ax or not ax.lines:
            return None

        x_data = ax.lines[0].get_xdata()
        if len(x_data) == 0:
            return None

        return float(x_data[0]), float(x_data[-1])

    def _get_selected_time_range_minutes(self, graph_index=0):
        """Parse the time-entry widgets and clamp them to the plotted range."""
        x_range = self._get_primary_graph_x_range(graph_index)
        if x_range is None:
            return None

        time_min, time_max = x_range
        try:
            start_time = float(self.start_time_var.get()) / 60 if self.start_time_var.get() else time_min
            end_time = float(self.end_time_var.get()) / 60 if self.end_time_var.get() else time_max
        except ValueError:
            return None

        start_time = min(max(start_time, time_min), time_max)
        end_time = min(max(end_time, time_min), time_max)
        if end_time < start_time:
            end_time = time_max

        return start_time, end_time

    @staticmethod
    def _format_duration_seconds(total_time: int) -> str:
        """Return a compact human-readable duration string."""
        hours = int(total_time // 3600)
        minutes = int((total_time % 3600) // 60)
        seconds = int(total_time % 60)

        time_parts = []
        if hours > 0:
            time_parts.append(f"{hours} h")
        if minutes > 0:
            time_parts.append(f"{minutes} min")
        time_parts.append(f"{seconds} s")
        return " ".join(time_parts)

    def refresh_time_selection_preview(self, *_args):
        """Update the duration label and preview lines for the current time selection."""
        selected_range = self._get_selected_time_range_minutes()
        if selected_range is None:
            self.total_time_display.config(text="Invalid")
            return

        start_time, end_time = selected_range
        total_time = round((end_time - start_time) * 60)
        if total_time <= 0:
            self.total_time_display.config(text="Invalid")
            return

        self.total_time_display.config(text=self._format_duration_seconds(total_time))
        self.update_lines(graph_index=0, start_time=start_time, end_time=end_time)

    def handle_new_data_file(self, file_path, selected_column=None, column_dropdown=None, mouse_name=None, dataframe=None, is_time_based_data=False):
        """
        Handle a new data file and update the relevant settings.

        Parameters:
            file_path (str): The path to the CSV file.
            selected_column (str, optional): Pre-selected column for processing.
            column_dropdown (widget, optional): Dropdown to be updated with column options.
            mouse_name (str, optional): Identifier for the mouse data.
            dataframe (pd.DataFrame, optional): Pre-loaded DataFrame (bypasses file read).
            is_time_based_data (bool, optional): Flag indicating if the data is time-based.
        """      
        
        # Clear all existing graphs
        self.clear_graphs()
        
        # Process the raw data
        self.processor = PhotometryRawProcessor(
            file_path=file_path, dataframe=dataframe)
        self.column_options = list(self.processor.raw_data.columns)

        # Identify relevant columns
        time_column, signal_405_column, signal_465_column = self.identify_columns()

        # Load and slice data
        raw_signals = self.processor.load_data_to_numpy(
            time_column, signal_405_column, signal_465_column)
                
        # Update dropdown options dynamically
        current_value = self.update_dropdown_options(
            self.time_dropdown_frame, self.column_options)
        current_value = self.update_dropdown_options(
            self._405nm_dropdown_frame, self.column_options)
        current_value = self.update_dropdown_options(
            self._465nm_dropdown_frame, self.column_options)

        # Draw the first graph with start and end lines
        self.draw_first_graph(raw_signals)
        self.refresh_time_selection_preview()
            
    def identify_columns(self):
        """
        Identify time, 405nm, and 465nm signal columns in the dataset.
        """
        time_column = next(
            (col for col in self.column_options if self.data_selection_frame.is_time_data(
                self.processor.raw_data[[col]])),
            None
        )
        if not time_column:
            raise ValueError("No suitable time column found in the data.")

        column_candidates = [
            col for col in self.column_options if col != time_column]
        signal_405_column = '405nm' if '405nm' in column_candidates else column_candidates[0]
        signal_465_column = '465nm' if '465nm' in column_candidates else (
            '490nm' if '490nm' in column_candidates else column_candidates[1]
        )

        return time_column, signal_405_column, signal_465_column

    def draw_first_graph(self, raw_signals):
        """
        Draw the first graph with start and end lines, using different y-axes for each signal.
        """
        graph_frame = ttk.Frame(self.raw_data_tab)
        graph_frame.pack(fill="both", expand=True)

        fig = Figure(figsize=(10, 4), dpi=100)
        ax1 = fig.add_subplot(111)  # Primary y-axis for signal_465
        ax2 = ax1.twinx()           # Secondary y-axis for signal_405

        time, signal_405, signal_465 = raw_signals
        
        signal_405_min = min(signal_405)
        signal_405_max = max(signal_405)
        
        _405_y_top = signal_405_max + (1 * signal_405_min)
        _405_y_bot = signal_405_min - (0.01 * signal_405_min)
        _405_range = _405_y_top - _405_y_bot
        
        signal_465_min = min(signal_465)
        signal_465_max = max(signal_465)
        
        # Plot 465nm signal on the primary y-axis
        ax1.plot(time, signal_465, label="465nm Signal", color="green", linewidth=0.8)
        ax1.set_ylabel("465nm Signal", color="green")
        ax1.tick_params(axis='y', labelcolor="green")

        ax1.set_ylim(
            [signal_465_min - (0.5 * _405_range), signal_465_max * 1.02])

        # Plot 405nm signal on the secondary y-axis
        ax2.plot(time, signal_405, label="405nm Signal", color="purple", linewidth=0.5, alpha=0.5)
        ax2.set_ylabel("405nm Signal", color="purple")
        ax2.tick_params(axis='y', labelcolor="purple")

        # Set a smaller range for the secondary y-axis (405nm signal)
        ax2.set_ylim(_405_y_bot, _405_y_top)

        # Add start and end lines to both axes
        start_line = ax1.axvline(
            x=time[0], color="red", linestyle="--", linewidth=1.5, label="Start: 0s")
        end_line = ax1.axvline(
            x=time[-1], color="blue", linestyle="--", linewidth=1.5, label=f"End: {time[-1]:.2f}s")

        # Set shared x-axis title
        ax1.set_title("Raw Data")
        ax1.set_xlabel("Time (min)")
        ax1.set_xlim([time[0] - 1, time[-1] + 1])

        # Add tight layout for the figure
        fig.tight_layout()

        # Save references to the lines for updating
        self.all_graphs_reference[0] = {
            "figure": fig,
            "primary_axis": ax1,
            "secondary_axis": ax2,
            "start_line": start_line,
            "end_line": end_line,
        }

        # Embed the figure in the canvas
        self.add_canvas_to_frame(graph_frame, fig)
        
        processed_signals = self.processor.prepare_filtered_signals(raw_signals)
    
    def add_canvas_to_frame(self, frame, figure):
        """
        Embed a Matplotlib figure in a Tkinter frame.
        """
        canvas = FigureCanvasTkAgg(figure, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

        # Create a subframe for the toolbar
        toolbar_frame = ttk.Frame(frame)
        toolbar_frame.pack(fill="x", side="bottom")

        # Add the toolbar to the toolbar frame
        toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
        toolbar.update()

        # Style the toolbar
        toolbar.config(background="snow")
        toolbar._message_label.config(background="snow")
        toolbar._message_label.config(foreground="black", font=("Arial", 10))
        toolbar.configure(background="snow", bd=0)
        toolbar._message_label.configure(background="snow", bd=0)

    def clear_graphs(self):
        """
        Clear all existing graphs and reset the graph index.
        """
        # List of tabs to clear
        tabs = [self.raw_data_tab, self.noise_correction_tab, self.final_data_tab]

        for tab in tabs:
            for widget in tab.winfo_children():
                widget.destroy()

        # Clear the graph reference dictionary and reset the graph index
        self.all_graphs_reference.clear()
        self.graph_index = 0
    
    def setup_notebooks(self):
        """Setup the main and settings notebooks."""
        self.notebook_graphs = ttk.Notebook(
            self, style="CustomNotebook.TNotebook")
        self.notebook_graphs.grid(
            row=1, column=0, columnspan=3, padx=10, pady=10, sticky=tk.NSEW)

        # Create tabs
        self.raw_data_tab = ttk.Frame(
            self.notebook_graphs, style="CustomNotebook.TFrame")
        self.noise_correction_tab = ttk.Frame(
            self.notebook_graphs, style="CustomNotebook.TFrame")
        self.final_data_tab = ttk.Frame(
            self.notebook_graphs, style="CustomNotebook.TFrame")

        # Add tabs to notebook
        self.notebook_graphs.add(self.raw_data_tab, text="Raw Data")
        self.notebook_graphs.add(
            self.noise_correction_tab, text="Noise Correction Options")
        self.notebook_graphs.add(self.final_data_tab, text="Final Data")

        self.notebook_graphs.configure(height=520)    

    def update_lines(self, graph_index, start_time=None, end_time=None):
        """
        Update the positions of the start and end lines for a specific graph.

        Parameters:
        - graph_index (int): Index of the graph to update.
        - start_time (float): The start time to update the red line.
        - end_time (float): The end time to update the blue line.
        """
        graph = self.all_graphs_reference.get(graph_index)
        if not graph:
            print(f"Graph index {graph_index} does not exist in all_graphs_reference.")
            return

        start_line = graph["start_line"]
        end_line = graph["end_line"]

        # Retrieve the first and last data points in the time column
        x_data = graph.get("primary_axis").lines[0].get_xdata()
        if len(x_data) == 0:
            print(f"Graph {graph_index} has no data.")
            return

        time_min = x_data[0]  # First time point
        time_max = x_data[-1]  # Last time point

        # Validate and adjust start_time and end_time
        start_time = start_time if start_time is not None and time_min <= start_time <= time_max else time_min
        end_time = end_time if end_time is not None and time_min <= end_time <= time_max else time_max

        # Ensure logical range: start_time <= end_time
        if end_time < start_time:
            print("End time cannot be earlier than start time. Resetting end_time to time_max.")
            end_time = time_max

        # Update line positions
        start_line.set_xdata([start_time, start_time])
        end_line.set_xdata([end_time, end_time])

        # Redraw the canvas
        try:
            graph["figure"].canvas.draw()
        except Exception as e:
            print(f"Error updating lines: {e}")


    def show_selected_graph(self, start_index, selected, num_graphs):
        """
        Show the graph corresponding to the dropdown selection.

        Parameters:
        - start_index (int): The starting index for graphs in this tab.
        - selected (str): The selected graph label (e.g., "Graph 2").
        - num_graphs (int): Total number of graphs available in this tab.
        """
        selected_index = start_index + int(selected.split()[-1]) - 1

        for i in range(num_graphs):
            graph = self.all_graphs_reference.get(start_index + i)
            if graph:
                frame = graph["frame"]
                if start_index + i == selected_index:
                    # Show the selected graph
                    frame.pack(fill="both", expand=True)
                else:
                    frame.pack_forget()  # Hide all others
