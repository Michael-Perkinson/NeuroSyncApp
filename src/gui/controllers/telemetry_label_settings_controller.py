"""Controller for telemetry peak/cluster label settings popup."""

from __future__ import annotations

import tkinter as tk
from tkinter import colorchooser, ttk

from src.gui.shared.window_manager import center_window_on_screen


class TelemetryLabelSettingsController:
    """Owns label settings popup construction and save/apply behavior."""

    def __init__(self, app):
        self.app = app

    def open_label_settings_popup(self) -> None:
        self.app.popup = tk.Toplevel(self.app, bg="snow")
        self.app.popup.title("Cluster Label Settings")
        bold_large_font = ("Helvetica", 10, "bold")

        self.app.peak_label_frame = tk.LabelFrame(
            self.app.popup, text="Peak Label Settings", bg="snow", font=bold_large_font
        )
        self.app.peak_label_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self.app.label_color_var = tk.StringVar(
            value=self.app.settings_manager.selected_label_color
        )
        tk.Button(
            self.app.peak_label_frame,
            text="Peak Symbol Colour",
            command=self.choose_label_color,
        ).grid(row=0, column=0, columnspan=2, padx=10, pady=5)

        self.app.symbol_options = ["o", "*", "s", "D", "^", "v", "<", ">"]
        self.app.label_symbol_var = tk.StringVar(
            value=self.app.settings_manager.selected_label_symbol
        )
        tk.Label(self.app.peak_label_frame, text="Peak Symbol:", bg="snow").grid(
            row=1, column=0, sticky=tk.W, padx=10, pady=5
        )
        ttk.Combobox(
            self.app.peak_label_frame,
            textvariable=self.app.label_symbol_var,
            values=self.app.symbol_options,
            state="readonly",
            width=4,
        ).grid(row=1, column=1, padx=10, pady=5)

        self.app.label_size_var = tk.StringVar(
            value=str(self.app.settings_manager.selected_label_size)
        )
        tk.Label(self.app.peak_label_frame, text="Peak Symbol Size:", bg="snow").grid(
            row=2, column=0, sticky=tk.W, padx=10, pady=5
        )
        tk.Entry(self.app.peak_label_frame, textvariable=self.app.label_size_var, width=7).grid(
            row=2, column=1, padx=10, pady=5
        )

        self.app.y_offset_peak_symbol = tk.StringVar(
            value=str(self.app.settings_manager.selected_y_offset_peak_symbol)
        )
        tk.Label(
            self.app.peak_label_frame, text="Peak Symbol Y-Offset:", bg="snow"
        ).grid(row=3, column=0, sticky=tk.W, padx=10, pady=5)
        tk.Entry(
            self.app.peak_label_frame, textvariable=self.app.y_offset_peak_symbol, width=7
        ).grid(row=3, column=1, padx=10, pady=5)

        self.app.peak_count_label_frame = tk.LabelFrame(
            self.app.popup, text="Peak Count Settings", bg="snow", font=bold_large_font
        )
        self.app.peak_count_label_frame.grid(
            row=1, column=0, padx=10, pady=10, sticky="nsew"
        )

        self.app.peak_count_color_var = tk.StringVar(
            value=self.app.settings_manager.selected_peak_count_color
        )
        tk.Button(
            self.app.peak_count_label_frame,
            text="Peak Number Colour",
            command=self.choose_peak_count_color,
        ).grid(row=0, column=0, columnspan=2, padx=10, pady=5)

        self.app.peak_count_size_var = tk.StringVar(
            value=str(self.app.settings_manager.selected_peak_count_size)
        )
        tk.Label(
            self.app.peak_count_label_frame, text="Peak Number Font Size:", bg="snow"
        ).grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        tk.Entry(
            self.app.peak_count_label_frame, textvariable=self.app.peak_count_size_var, width=7
        ).grid(row=1, column=1, padx=10, pady=5)

        self.app.y_for_peak_count = tk.StringVar(
            value=str(self.app.settings_manager.selected_y_for_peak_count)
        )
        tk.Label(self.app.peak_count_label_frame, text="Y Offset:", bg="snow").grid(
            row=2, column=0, sticky=tk.W, padx=10, pady=5
        )
        tk.Entry(
            self.app.peak_count_label_frame, textvariable=self.app.y_for_peak_count, width=7
        ).grid(row=2, column=1, padx=10, pady=5)

        self.app.baseline_label_frame = tk.LabelFrame(
            self.app.popup, text="Baseline Settings", bg="snow", font=bold_large_font
        )
        self.app.baseline_label_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        self.app.baseline_color = tk.StringVar(
            value=self.app.settings_manager.selected_baseline_color
        )
        tk.Button(
            self.app.baseline_label_frame,
            text="Baseline Symbol Colour",
            command=self.choose_baseline_color,
        ).grid(row=0, column=0, columnspan=2, padx=10, pady=5)

        self.app.baseline_multiplier = tk.StringVar(
            value=self.app.settings_manager.selected_baseline_multiplier
        )
        tk.Label(
            self.app.baseline_label_frame,
            text="Cluster End Multiplier (Empty = Median):",
            bg="snow",
        ).grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        tk.Entry(
            self.app.baseline_label_frame,
            textvariable=self.app.baseline_multiplier,
            width=7,
        ).grid(row=1, column=1, padx=10, pady=5)

        self.app.baseline_style_options = ["-", "--", "-.", ":"]
        self.app.baseline_style = tk.StringVar(
            value=self.app.settings_manager.selected_baseline_style
        )
        tk.Label(
            self.app.baseline_label_frame, text="Baseline Symbol Style:", bg="snow"
        ).grid(row=2, column=0, sticky=tk.W, padx=10, pady=5)
        ttk.Combobox(
            self.app.baseline_label_frame,
            textvariable=self.app.baseline_style,
            state="readonly",
            values=self.app.baseline_style_options,
            width=4,
        ).grid(row=2, column=1, padx=10, pady=5)

        self.app.baseline_thickness = tk.StringVar(
            value=self.app.settings_manager.selected_baseline_thickness
        )
        tk.Label(
            self.app.baseline_label_frame, text="Baseline Thickness:", bg="snow"
        ).grid(row=3, column=0, sticky=tk.W, padx=10, pady=5)
        tk.Entry(
            self.app.baseline_label_frame,
            textvariable=self.app.baseline_thickness,
            width=7,
        ).grid(row=3, column=1, padx=10, pady=5)

        self.app.cluster_box_frame = tk.LabelFrame(
            self.app.popup, text="Cluster Box Settings", bg="snow", font=bold_large_font
        )
        self.app.cluster_box_frame.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")

        self.app.cluster_box_color = tk.StringVar(
            value=self.app.settings_manager.selected_cluster_box_color
        )
        tk.Button(
            self.app.cluster_box_frame,
            text="Cluster Box Colour",
            command=self.choose_cluster_box_color,
        ).grid(row=0, column=0, columnspan=2, padx=10, pady=5)

        self.app.cluster_box_alpha = tk.StringVar(
            value=self.app.settings_manager.selected_cluster_box_alpha
        )
        tk.Label(self.app.cluster_box_frame, text="Cluster Box Alpha:", bg="snow").grid(
            row=1, column=0, sticky=tk.W, padx=10, pady=5
        )
        tk.Entry(
            self.app.cluster_box_frame, textvariable=self.app.cluster_box_alpha, width=7
        ).grid(row=1, column=1, padx=10, pady=5)

        self.app.cluster_box_height_modifier = tk.StringVar(
            value=self.app.settings_manager.selected_cluster_box_height_modifier
        )
        tk.Label(
            self.app.cluster_box_frame, text="Cluster Box Height Modifier:", bg="snow"
        ).grid(row=2, column=0, sticky=tk.W, padx=10, pady=5)
        tk.Entry(
            self.app.cluster_box_frame,
            textvariable=self.app.cluster_box_height_modifier,
            width=7,
        ).grid(row=2, column=1, padx=10, pady=5)

        self.app.peak_label_frame.grid_columnconfigure(0, weight=1)
        self.app.peak_count_label_frame.grid_columnconfigure(0, weight=1)
        self.app.baseline_label_frame.grid_columnconfigure(0, weight=1)
        self.app.cluster_box_frame.grid_columnconfigure(0, weight=1)

        tk.Button(
            self.app.popup,
            text="Save & Close",
            command=lambda: self.save_and_close_label_settings(self.app.popup),
        ).grid(row=4, column=0, columnspan=2, pady=10)

        self.app.popup.update_idletasks()
        center_window_on_screen(self.app.popup)

    def choose_baseline_color(self):
        color = colorchooser.askcolor()
        if color[1]:
            self.app.baseline_color.set(color[1])
        self.app.popup.lift()

    def choose_label_color(self):
        color = colorchooser.askcolor()
        if color[1]:
            self.app.label_color_var.set(color[1])
        self.app.popup.lift()

    def choose_peak_count_color(self):
        color = colorchooser.askcolor()
        if color[1]:
            self.app.peak_count_color_var.set(color[1])
        self.app.popup.lift()

    def choose_cluster_box_color(self):
        color = colorchooser.askcolor()
        if color[1]:
            self.app.cluster_box_color.set(color[1])
        self.app.popup.lift()

    def save_and_close_label_settings(self, popup):
        current_baseline_multiplier = self.app.settings_manager.selected_baseline_multiplier

        self.app.settings_manager.selected_label_color = self.app.label_color_var.get()
        self.app.settings_manager.selected_label_symbol = self.app.label_symbol_var.get()
        self.app.settings_manager.selected_label_size = int(self.app.label_size_var.get())
        self.app.settings_manager.selected_y_offset_peak_symbol = int(
            self.app.y_offset_peak_symbol.get()
        )
        self.app.settings_manager.selected_peak_count_color = (
            self.app.peak_count_color_var.get()
        )
        self.app.settings_manager.selected_peak_count_size = int(
            self.app.peak_count_size_var.get()
        )
        self.app.settings_manager.selected_y_for_peak_count = int(
            self.app.y_for_peak_count.get()
        )
        self.app.settings_manager.selected_baseline_multiplier = (
            self.app.baseline_multiplier.get()
        )
        self.app.settings_manager.selected_baseline_color = self.app.baseline_color.get()
        self.app.settings_manager.selected_baseline_style = self.app.baseline_style.get()
        self.app.settings_manager.selected_baseline_thickness = (
            self.app.baseline_thickness.get()
        )
        self.app.settings_manager.selected_cluster_box_color = (
            self.app.cluster_box_color.get()
        )
        self.app.settings_manager.selected_cluster_box_alpha = (
            self.app.cluster_box_alpha.get()
        )
        self.app.settings_manager.selected_cluster_box_height_modifier = (
            self.app.cluster_box_height_modifier.get()
        )
        self.app.settings_manager.save_variables()

        if (
            current_baseline_multiplier
            != self.app.settings_manager.selected_baseline_multiplier
        ):
            self.app.reset_clusters_based_on_user_input()
            return

        if hasattr(self.app, "figure_canvas"):
            if self.app.act_data is not None and self.app.temp_data is not None:
                self.app.telemetry_plot_controller.visualize_photometry_data_with_overlays(
                    self.app.time_column,
                    self.app.data_column,
                    self.app.detected_peaks,
                    self.app.clusters_final,
                    self.app.graph_canvas,
                    self.app.temp_data,
                    self.app.act_data,
                    show_nighttime=True,
                )
            else:
                self.app.telemetry_plot_controller.visualize_photometry_data_with_overlays(
                    self.app.time_column,
                    self.app.data_column,
                    self.app.detected_peaks,
                    self.app.clusters_final,
                    self.app.graph_canvas,
                )

        popup.destroy()
