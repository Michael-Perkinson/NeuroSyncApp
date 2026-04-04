"""
This module defines the BehaviourInputFrame class, a custom ttk.Frame for
handling behaviour input and synchronization in a tkinter-based GUI.

Features:
- Inputting behaviour coding information.
- Synchronizing start times between video and behaviour data.
- Selecting event files and column names using callbacks.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from src.gui.shared.tkinter_widgets import create_label, create_entry, create_button


class BehaviourInputFrame(ttk.Frame):
    """
    A custom ttk.Frame for behaviour input and synchronization in a tkinter GUI.

    This frame contains:
    - Input fields for behaviour name, type, and timing.
    - Buttons to import behaviour coding and select column names.
    - Callbacks for handling user interactions with the frame.

    Attributes:
        behaviour_name_var (tk.StringVar): Stores the behaviour name.
        behaviour_type_var (tk.StringVar): Stores the behaviour type ("Point" or other).
        start_time_var (tk.StringVar): Stores the start time of behaviour.
        end_time_var (tk.StringVar): Stores the end time of behaviour.
        select_column_names_callback (Optional[Callable]): Callback for selecting column names.
        import_behaviour_callback (Optional[Callable]): Callback for importing behaviour coding.
    """

    def __init__(
        self,
        parent: tk.Widget,
        width: Optional[int] = None,
        select_column_names_callback: Optional[Callable[[], None]] = None,
        select_event_file_callback: Optional[Callable[[], None]] = None,
        **kwargs,
    ) -> None:
        """
        Initialize the BehaviourInputFrame.

        Parameters:
        - parent (tk.Widget): The parent widget.
        - width (Optional[int]): The width of the frame.
        - select_column_names_callback (Optional[Callable]): Callback for selecting column names.
        - select_event_file_callback (Optional[Callable]): Callback for selecting an event file.
        - **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(parent, style="Bordered.TFrame", **kwargs)
        self.width = width

        # Variables
        self.behaviour_name_var = tk.StringVar()
        self.behaviour_type_var = tk.StringVar(value="Point")
        self.start_time_var = tk.StringVar()
        self.end_time_var = tk.StringVar()
        self.select_column_names_callback = select_column_names_callback
        self.import_behaviour_callback = select_event_file_callback

        # Widget placeholders
        self.behaviour_input_label: Optional[tk.Label] = None
        self.behaviour_coding_frame: Optional[ttk.Frame] = None
        self.synchronize_start_time_label: Optional[tk.Label] = None
        self.synchronize_start_time_entry: Optional[tk.Entry] = None
        self.import_behaviour_button: Optional[tk.Button] = None
        self.column_names_button: Optional[tk.Button] = None

        # Configure layout
        self.configure(style="Bordered.TFrame")
        if self.width:
            self.grid_columnconfigure(0, minsize=self.width)

        # Create widgets
        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create and layout widgets in the frame."""
        self._create_title_label("Behaviour Input")
        self._create_coding_frame()

    def _create_title_label(self, text: str) -> None:
        """Create the title label for the frame."""
        self.behaviour_input_label = create_label(
            self, text, font=("Helvetica", 12, "bold")
        )
        self.behaviour_input_label.grid(
            row=0, column=0, columnspan=2, padx=10, pady=(10, 5)
        )

    def _create_coding_frame(self) -> None:
        """Create the frame for behaviour coding widgets."""
        self.behaviour_coding_frame = ttk.Frame(self, style="Custom.TFrame")
        self.behaviour_coding_frame.grid(
            row=1, column=0, columnspan=2, padx=10, pady=(10, 5)
        )

        # Synchronization Widgets
        self._create_sync_start_time_widgets(self.behaviour_coding_frame)

        # Import Buttons
        self._create_import_buttons(self.behaviour_coding_frame)

    def _create_sync_start_time_widgets(self, parent: ttk.Frame) -> None:
        """
        Create widgets for synchronizing start times.

        Parameters:
        - parent (ttk.Frame): The parent frame for the widgets.
        """
        self.synchronize_start_time_label = create_label(
            parent, "Video Coding Start Time (s):", font=("Helvetica", 10)
        )
        self.synchronize_start_time_label.grid(
            row=0, column=0, padx=(10, 0), pady=(10, 5))

        self.synchronize_start_time_entry = create_entry(
            parent, self.start_time_var, width=10)
        self.synchronize_start_time_entry.grid(
            row=0, column=1, padx=(10, 10), pady=(10, 5))
        self.synchronize_start_time_entry.insert(tk.END, "0")

    def _create_import_buttons(self, parent: ttk.Frame) -> None:
        """Create buttons for importing behaviour coding and selecting column names."""
        self.import_behaviour_button = create_button(
            parent,
            "Import Behaviour Coding",
            self.on_import_behaviour_click,
        )
        self.import_behaviour_button.grid(row=1, column=0, padx=10, pady=(10, 5))

        self.column_names_button = create_button(
            parent,
            "Column Names",
            self.select_column_names,
        )
        self.column_names_button.grid(row=1, column=1, padx=10, pady=(10, 5))

    def select_column_names(self) -> None:
        """Trigger the callback for selecting column names."""
        if self.select_column_names_callback:
            self.select_column_names_callback()

    def on_import_behaviour_click(self) -> None:
        """Trigger the callback for importing behaviour coding."""
        if self.import_behaviour_callback:
            self.import_behaviour_callback()
