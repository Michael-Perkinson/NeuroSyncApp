import tkinter as tk
from tkinter import ttk


def create_main_frame(parent, container):
    """
    Creates and configures the main frame for an application.

    Parameters:
        parent (tk.Widget): The parent widget (Tk or Frame).
        container (ttk.Frame): The main container frame inside the class.

    Returns:
        ttk.Frame: The created main frame.
    """
    if isinstance(parent, tk.Tk):
        parent.title("Data Processing")

    main_frame = ttk.Frame(container, style="Bordered.TFrame")
    main_frame.grid(row=0, column=0, columnspan=4, padx=10, sticky=tk.NSEW)
    container.grid(row=0, column=0, sticky="nsew")

    return main_frame
