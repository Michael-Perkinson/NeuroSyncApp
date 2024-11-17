import tkinter as tk
from tkinter import ttk

from src.window_utils import center_window_on_screen


class ExportOptionsContainer(ttk.Frame):
    def __init__(self, parent,
                 file_path_var,
                 settings_manager,
                 extract_button_click_handler,
                 save_image,
                 **kwargs):
        """
        Initialize the ExportOptionsContainer.

        Parameters:
        - parent (tk.Tk|tk.Frame): The parent widget.
        - file_path_var (tk.StringVar): The variable to store the file path.
        - settings_manager (SettingsManager): The settings manager.
        - extract_button_click_handler (function): The callback for the extract button click.
        - save_image (function): The callback for saving the image.
        - **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(parent, style='NoBorder.TFrame',
                         borderwidth=2, relief='solid', **kwargs)

        self.settings_manager = settings_manager
        self.file_path_var = file_path_var
        self.extract_button_click_handler = extract_button_click_handler
        self.save_image = save_image
        self.use_auc_var = tk.BooleanVar(value=True)
        self.use_max_amp_var = tk.BooleanVar(value=True)
        self.use_mean_dff_var = tk.BooleanVar(value=True)
        self.use_binned_data_var = tk.BooleanVar(value=True)
        self.combine_csv_var = tk.BooleanVar(value=True)
        self.font_settings = {
            'xlabel_fontsize': '',
            'ylabel_fontsize': '',
            'xtick_fontsize': '',
            'ytick_fontsize': '',
            'y_axis_name': '',
        }

        self.grid(row=0, column=0, padx=10, pady=10, sticky=tk.NSEW)
        self._create_widgets()

    def _create_widgets(self):
        """Create and layout the widgets in the frame."""
        export_options_current_frame = ttk.Frame(self, style='Bordered.TFrame')
        export_options_current_frame.grid(
            row=0, column=0, padx=10, pady=10, sticky=tk.NSEW)

        auc_checkbox = ttk.Checkbutton(export_options_current_frame, text="AUC", variable=self.use_auc_var,
                                       style='Custom.TCheckbutton')
        auc_checkbox.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)

        max_amp_checkbox = ttk.Checkbutton(export_options_current_frame, text="Max AMP", variable=self.use_max_amp_var,
                                           style='Custom.TCheckbutton')
        max_amp_checkbox.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        mean_dff_checkbox = ttk.Checkbutton(export_options_current_frame, text="Mean dF/F", variable=self.use_mean_dff_var,
                                            style='Custom.TCheckbutton')
        mean_dff_checkbox.grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)

        binned_data_checkbox = ttk.Checkbutton(export_options_current_frame, text="Binned Data",
                                               variable=self.use_binned_data_var, style='Custom.TCheckbutton')
        binned_data_checkbox.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)

        combine_csv_checkbutton = ttk.Checkbutton(export_options_current_frame, text="One excel workbook?", variable=self.combine_csv_var,
                                                  style='Custom.TCheckbutton')
        combine_csv_checkbutton.grid(
            row=1, column=0, columnspan=2, padx=5, pady=5, sticky=tk.W)

        extract_data_button = tk.Button(export_options_current_frame, text="Extract Data", font=('Helvetica', 10),
                                        bg='lightblue', command=lambda: self.extract_button_click_handler())
        extract_data_button.grid(
            row=1, column=3, padx=10, pady=(10, 5), sticky=tk.W)

        export_options_all_frame = ttk.Frame(self, style='Bordered.TFrame')
        export_options_all_frame.grid(
            row=1, column=0, padx=10, pady=10, sticky=tk.NSEW)

        self.image_format_label = tk.Label(
            export_options_all_frame, text="Image Format:", bg='snow')
        self.image_format_label.grid(row=0, column=0, padx=5, pady=5)

        self.image_format_combobox = ttk.Combobox(export_options_all_frame, values=[
                                                  "EPS", "SVG", "TIFF", "PNG", "JPG"], state="readonly", width=5)
        self.image_format_combobox.set("PNG")
        self.image_format_combobox.grid(row=0, column=1, padx=5, pady=5)

        dpi_label = tk.Label(export_options_all_frame, text="DPI:", bg='snow')
        dpi_label.grid(row=0, column=2, padx=5, pady=5)

        self.dpi_entry = ttk.Entry(export_options_all_frame, width=5)
        self.dpi_entry.insert(tk.END, "600")
        self.dpi_entry.grid(row=0, column=3, padx=5, pady=5)

        width_label = tk.Label(export_options_all_frame,
                               text="Width (cm):", bg='snow')
        width_label.grid(row=1, column=0, padx=5, pady=5)

        self.width_entry = ttk.Entry(export_options_all_frame, width=5)
        self.width_entry.insert(tk.END, "")
        self.width_entry.grid(row=1, column=1, padx=5, pady=5)

        height_label = tk.Label(export_options_all_frame,
                                text="Height (cm):", bg='snow')
        height_label.grid(row=1, column=2, padx=5, pady=5)

        self.height_entry = ttk.Entry(export_options_all_frame, width=5)
        self.height_entry.insert(tk.END, "")
        self.height_entry.grid(row=1, column=3, padx=5, pady=5)

        font_settings_button = tk.Button(
            export_options_all_frame, text="Font Settings", command=self.open_font_settings_popup, bg='lightblue')
        font_settings_button.grid(row=0, column=4, padx=5, pady=5)

        save_button = tk.Button(
            export_options_all_frame, text="Save Image", command=self.save_image, bg='lightblue')
        save_button.grid(row=1, column=4, padx=5, pady=5)

    def open_font_settings_popup(self):
        """Opens a pop-up window to set the font settings for matplotlib graphs."""
        font_popup = tk.Toplevel(self, bg='white')
        font_popup.title("Font Settings")
        font_options_font = ('Helvetica', 10, 'bold')

        font_settings_frame = tk.LabelFrame(
            font_popup, text="Font Settings", bg='white', font=font_options_font)
        font_settings_frame.grid(
            row=0, column=0, padx=10, pady=10, sticky='nsew')

        def apply_font_sizes_and_close():
            """Apply the font sizes and close the popup."""
            self.font_settings['xlabel_fontsize'] = self.xlabel_font_size_var.get(
            ).strip()
            self.font_settings['ylabel_fontsize'] = self.ylabel_font_size_var.get(
            ).strip()
            self.font_settings['xtick_fontsize'] = self.xticks_font_size_var.get(
            ).strip()
            self.font_settings['ytick_fontsize'] = self.yticks_font_size_var.get(
            ).strip()
            self.font_settings['y_axis_name'] = self.y_axis_name_var.get(
            ).strip()
            font_popup.destroy()

        self.xlabel_font_size_var = tk.StringVar()
        self.xticks_font_size_var = tk.StringVar()
        self.ylabel_font_size_var = tk.StringVar()
        self.yticks_font_size_var = tk.StringVar()
        self.y_axis_name_var = tk.StringVar()

        tk.Label(font_settings_frame, text="Overwrite Y-axis Name:",
                 bg='white').grid(row=0, column=0, padx=5, pady=5, columnspan=2)
        tk.Entry(font_settings_frame, textvariable=self.y_axis_name_var,
                 width=15).grid(row=0, column=2, padx=5, pady=5, columnspan=2)

        y_settings = [
            ("Y-label Font Size:", self.ylabel_font_size_var),
            ("Y-ticks Font Size:", self.yticks_font_size_var),
        ]
        x_settings = [
            ("X-label Font Size:", self.xlabel_font_size_var),
            ("X-ticks Font Size:", self.xticks_font_size_var),
        ]

        for i, (label_text, var) in enumerate(y_settings, start=1):
            tk.Label(font_settings_frame, text=label_text, bg='white').grid(
                row=i, column=0, padx=5, pady=5)
            tk.Entry(font_settings_frame, textvariable=var, width=7).grid(
                row=i, column=1, padx=5, pady=5)

        for i, (label_text, var) in enumerate(x_settings, start=1):
            tk.Label(font_settings_frame, text=label_text, bg='white').grid(
                row=i, column=2, padx=5, pady=5)
            tk.Entry(font_settings_frame, textvariable=var, width=7).grid(
                row=i, column=3, padx=5, pady=5)

        save_and_close_button = tk.Button(
            font_popup, text="Apply & Close", command=apply_font_sizes_and_close)
        save_and_close_button.grid(row=4, column=0, columnspan=2, pady=10)

        font_popup.update_idletasks()  # Update "idle" tasks to get updated dimensions
        center_window_on_screen(font_popup)
