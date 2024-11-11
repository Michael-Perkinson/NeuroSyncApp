import tkinter as tk
from tkinter import ttk

class StaticInputsFrame(ttk.Frame):
    def __init__(self, parent, width=None, save_inputs_callback=None, **kwargs):
        """
        Initialize the StaticInputsFrame.
        
        Parameters:
        - parent (tk.Tk|tk.Frame): The parent widget.
        - width (int): The width of the frame.
        - save_inputs_callback (function): The callback for saving the inputs.
        - **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(parent, style='Bordered.TFrame', **kwargs)

        #Initializing the necessary instance variables
        self.pre_behaviour_time_var = tk.StringVar()
        self.post_behaviour_time_var = tk.StringVar()
        self.bin_size_var = tk.StringVar()
        self.save_inputs_callback = save_inputs_callback
        self.width = width

        # Create widgets
        self.create_frame_widgets()

    def create_frame_widgets(self):
        """Create the widgets for the frame."""
        self.configure(style='Bordered.TFrame')
        # Set the width if specified
        if self.width is not None:
            self.grid_columnconfigure(0, minsize=self.width)

        # Static Inputs - Title
        self.static_inputs_title_label = tk.Label(self, text="Static Inputs", font=('Helvetica', 12, 'bold'),
                                                  fg='black', bg='snow')
        self.static_inputs_title_label.grid(row=0, column=0, columnspan=2, padx=10, pady=(5, 0))

        # Static Inputs - Title
        static_inputs_title_label = tk.Label(self, text="Static Inputs", font=('Helvetica', 12, 'bold'),
                                             fg='black', bg='snow')
        static_inputs_title_label.grid(row=0, column=0, columnspan=2, padx=10, pady=(5, 0))

        # Static Inputs - Pre-behaviour Time
        self.pre_behaviour_time_label = tk.Label(self, text="Pre-behaviour Time (s):", font=('Helvetica', 10),
                                                 fg='black', bg='snow')
        self.pre_behaviour_time_label.grid(row=1, column=0, padx=10, pady=(0, 5), sticky=tk.W)

        self.pre_behaviour_time_entry = tk.Entry(self, width=10, font=('Helvetica', 10), fg='black',
                                                 bg='snow', textvariable=self.pre_behaviour_time_var)
        self.pre_behaviour_time_entry.grid(row=1, column=1, padx=10, pady=(0, 5), sticky=tk.E)

        # Static Inputs - Post-behaviour Time
        self.post_behaviour_time_label = tk.Label(self, text="Post-behaviour Time (s):", font=('Helvetica', 10),
                                                  fg='black', bg='snow')
        self.post_behaviour_time_label.grid(row=2, column=0, padx=10, pady=(0, 5), sticky=tk.W)

        self.post_behaviour_time_entry = tk.Entry(self, width=10, font=('Helvetica', 10), fg='black',
                                                  bg='snow', textvariable=self.post_behaviour_time_var)
        self.post_behaviour_time_entry.grid(row=2, column=1, padx=10, pady=(0, 5), sticky=tk.E)

        # Static Inputs - Bin Size
        self.bin_size_label = tk.Label(self, text="Bin Size (s):", font=('Helvetica', 10), fg='black',
                                       bg='snow')
        self.bin_size_label.grid(row=3, column=0, padx=10, pady=(0, 5), sticky=tk.W)

        self.bin_size_entry = tk.Entry(self, width=10, font=('Helvetica', 10), fg='black', bg='snow',
                                       textvariable=self.bin_size_var)
        self.bin_size_entry.grid(row=3, column=1, padx=10, pady=(0, 5), sticky=tk.E)

        self.selected_behaviour = tk.StringVar(value='Select Behaviour')

        # Create a ttk.Frame to hold the OptionMenu
        self.dropdown_frame = ttk.Frame(self, borderwidth=2, relief="solid")
        self.dropdown_frame.configure(style='Bordered.TFrame')
        self.dropdown_frame.grid(row=4, column=0, columnspan=2, padx=10, pady=(0, 5), sticky=tk.E)

        # Use ttk.OptionMenu instead of tk.OptionMenu
        self.behaviour_dropdown = ttk.OptionMenu(self.dropdown_frame, self.selected_behaviour, '', "")
        self.behaviour_dropdown.configure(style="Custom.TMenubutton")
        # Set the state of the dropdown to disabled initially
        self.behaviour_dropdown['state'] = 'disabled'

        # Rest of your configuration
        self.behaviour_dropdown.grid(row=4, column=0, columnspan=2, sticky=tk.NSEW)
        self.selected_behaviour.set(" " * 15)
        self.behaviour_dropdown["menu"].delete(0, "end")

        # Static Inputs - Save Inputs Button
        save_inputs_button = tk.Button(self, text="Insert Times", font=('Helvetica', 10), bg='lightblue',
                                       command=self.save_inputs_callback if self.save_inputs_callback else self.default_save)
        save_inputs_button.grid(row=4, column=0, padx=10, pady=(0, 5), sticky=tk.W)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)
        self.rowconfigure(3, weight=1)

