import tkinter as tk
from tkinter import ttk


class BehaviourInputFrame(ttk.Frame):
    def __init__(self, parent, width=None, select_column_names_callback=None, select_event_file_callback=None, figure_display_dropdown=None, *args, **kwargs):
        """
        Initialize the BehaviourInputFrame.
        
        Parameters:
        - parent (tk.Tk|tk.Frame): The parent widget.
        - width (int): The width of the frame.
        - select_column_names_callback (function): The callback for selecting column names.
        - select_event_file_callback (function): The callback for selecting an event file.
        - figure_display_dropdown (function): The callback for selecting an event file.
        - *args: Variable length argument list.
        - **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(parent, style='Bordered.TFrame', *args, **kwargs)
        self.width = width

        self.behaviour_name_var = tk.StringVar()
        self.behaviour_type_var = tk.StringVar(value="Point")
        self.start_time_var = tk.StringVar()
        self.end_time_var = tk.StringVar()
        self.select_column_names_callback = select_column_names_callback
        self.select_event_file_callback = select_event_file_callback
        self.figure_display_dropdown_callback = figure_display_dropdown

        self.configure(style='Bordered.TFrame')
        if self.width is not None:
            self.grid_columnconfigure(0, minsize=self.width)

        self._create_widgets()

    def _create_widgets(self):
        """Call functions to create and layout the widgets in the frame."""
        self._create_title_label()
        self._create_coding_frame()

    def _create_title_label(self):
        """Create the title label for the frame."""
        self.behaviour_input_label = tk.Label(self, text="Behaviour Input", font=('Helvetica', 12, 'bold'),
                                              fg='black', bg='snow')
        self.behaviour_input_label.grid(
            row=0, column=0, columnspan=2, padx=10, pady=(10, 5))

    def _create_coding_frame(self):
        """Create the frame for the behaviour coding widgets."""
        self.behaviour_coding_frame = ttk.Frame(self, style='Custom.TFrame')
        self.behaviour_coding_frame.grid(
            row=2, column=0, columnspan=2, padx=10, pady=(10, 5))
        self._create_sync_start_time_widgets()
        self._create_import_buttons()

    def _create_sync_start_time_widgets(self):
        """Create the widgets for synchronizing the start time of the video and behaviour data."""
        self.synchronize_start_time_label = tk.Label(self.behaviour_coding_frame, text="Video Coding Start Time (s):",
                                                     font=('Helvetica', 10), fg='black', bg='snow')
        self.synchronize_start_time_label.grid(
            row=0, column=0, padx=(10, 0), pady=(10, 5))

        self.synchronize_start_time_entry = tk.Entry(self.behaviour_coding_frame, width=10, font=('Helvetica', 10),
                                                     fg='black', bg='snow', state='normal')
        self.synchronize_start_time_entry.grid(
            row=0, column=1, padx=(10, 10), pady=(10, 5))
        self.synchronize_start_time_entry.insert(tk.END, "0")

    def _create_import_buttons(self):
        """Create the buttons for importing behaviour coding and selecting column names."""
        self.import_behaviour_button = tk.Button(self.behaviour_coding_frame, text="Import Behaviour Coding", font=('Helvetica', 10), bg='lightblue',
                                                 command=self.select_event_file, state=tk.NORMAL)
        self.import_behaviour_button.grid(
            row=1, column=0, padx=10, pady=(10, 5))

        self.column_names_button = tk.Button(self.behaviour_coding_frame, text="Column Names", font=(
            'Helvetica', 10), bg='lightblue', command=self.select_column_names)
        self.column_names_button.grid(row=1, column=1, padx=10, pady=(10, 5))

    def select_column_names(self):
        """Trigger the callback for selecting column names."""
        if self.select_column_names_callback:
            self.select_column_names_callback()

    def select_event_file(self):
        """Trigger the callback for selecting an event file."""
        if self.select_event_file_callback:
            self.select_event_file_callback()

    def figure_display_dropdown_callback(self):
        """Trigger the callback for selecting an event file."""
        if self.figure_display_dropdown_callback:
            self.figure_display_dropdown_callback()

    @staticmethod
    def convert_time_units(time_data, time_unit):
        """
        Convert time data to the desired time unit.

        Parameters:
        - time_data (float): The time data to convert.
        - time_unit (str): The desired time unit to convert to.

        Returns:
        - time_data (float): The time data converted to the desired time unit.
        """
        if time_unit == 'seconds':
            return time_data * 60
        elif time_unit == 'hours':
            return time_data / 60
        else:
            return time_data
