"""Controller for telemetry graph display widget setup and mode switching."""

from __future__ import annotations

import logging
import re
from pathlib import Path
import matplotlib.cm as cm
import matplotlib.pyplot as plt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from src.gui.shared.qt_bindings import ComboBoxControl, ObservableValue
from src.gui.shared.qt_view_styles import apply_button_role, panel_stylesheet


logger = logging.getLogger(__name__)


class TelemetryDisplayPresenter:
    """Owns telemetry display dropdowns and cluster-display mode behavior."""

    def __init__(self, app):
        self.app = app

    def create_graphs_container(self, frame) -> None:
        graphs_container_frame = QFrame(frame)
        graphs_container_frame.setObjectName("telemetryGraphsContainer")
        graphs_container_frame.setStyleSheet(
            panel_stylesheet("telemetryGraphsContainer")
        )
        frame.layout().addWidget(graphs_container_frame)

        container_layout = QVBoxLayout(graphs_container_frame)
        container_layout.setContentsMargins(10, 10, 10, 10)
        container_layout.setSpacing(10)

        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(8)
        container_layout.addLayout(controls_layout)

        self.app.display_choices = [
            "Full Trace Display",
            "Single Cluster Display",
            "Mean Cluster Display",
        ]
        self.app.selected_display = ObservableValue(self.app.display_choices[0])
        self.app.display_dropdown = ComboBoxControl(
            self.app.selected_display,
            graphs_container_frame,
        )
        self.app.display_dropdown.set_options(self.app.display_choices)
        self.app.display_dropdown.currentTextChanged.connect(
            lambda *_args: self.on_cluster_display_selection_changed(None)
        )
        self.app.display_dropdown.configure(state="disabled")

        self.app.selected_period = ObservableValue("Full")
        self.app.period_dropdown = ComboBoxControl(
            self.app.selected_period,
            graphs_container_frame,
        )
        self.app.period_dropdown.set_options(["Full", "Day", "Night"])
        self.app.period_dropdown.currentTextChanged.connect(
            lambda *_args: self.on_cluster_selection_changed(None)
        )
        self.app.period_dropdown.configure(state="disabled")

        self.app.selected_cluster = ObservableValue("")
        self.app.cluster_dropdown = ComboBoxControl(
            self.app.selected_cluster,
            graphs_container_frame,
        )
        self.app.cluster_dropdown.setMinimumWidth(150)
        self.app.cluster_dropdown.currentTextChanged.connect(
            lambda *_args: self.on_cluster_selection_changed(None)
        )
        self.app.cluster_dropdown.configure(state="disabled")

        self.app.label_settings_button = QPushButton(
            graphs_container_frame,
            text="Peak & Cluster Settings",
        )
        apply_button_role(self.app.label_settings_button, "primary")
        self.app.label_settings_button.clicked.connect(
            self.app.label_settings_dialog.open_label_settings_popup
        )

        controls_layout.addWidget(self.app.label_settings_button)
        controls_layout.addWidget(self.app.display_dropdown)
        controls_layout.addWidget(self.app.period_dropdown)
        controls_layout.addWidget(self.app.cluster_dropdown)
        controls_layout.addStretch(1)

        self.app.graph_canvas = QWidget(graphs_container_frame)
        canvas_layout = QVBoxLayout(self.app.graph_canvas)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        canvas_layout.setSpacing(0)
        container_layout.addWidget(self.app.graph_canvas, 1)

    def on_cluster_display_selection_changed(self, event):
        choice = self.app.display_dropdown.currentText()
        self.app.selected_display.set(choice)

        if choice == "Full Trace Display":
            self.app.cluster_dropdown["values"] = []
            self.app.selected_cluster.set("")
            self.app.selected_period.set("Full")
            self.app.cluster_dropdown.configure(state="disabled")
            self.app.period_dropdown.configure(state="disabled")
            if self.app.act_data is not None and self.app.temp_data is not None:
                self.app.plot_service.visualize_photometry_data_with_overlays(
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
                self.app.plot_service.visualize_photometry_data_with_overlays(
                    self.app.time_column,
                    self.app.data_column,
                    self.app.detected_peaks,
                    self.app.clusters_final,
                    self.app.graph_canvas,
                )

        elif choice == "Single Cluster Display":
            cluster_ids = [
                f"Cluster {index + 1}" for index in range(len(self.app.cluster_dict))
            ]
            self.app.cluster_dropdown["values"] = cluster_ids
            self.app.selected_cluster.set(cluster_ids[0])
            self.app.cluster_dropdown.configure(state="normal")
            self.app.period_dropdown.configure(state="disabled")
            self.on_cluster_selection_changed()

        elif choice == "Mean Cluster Display":
            if self.app.data_type == "photometry":
                peak_counts = self.app.get_peak_counts()
                cluster_values = [
                    f"{count} Peak" if count == 1 else f"{count} Peaks"
                    for count in peak_counts
                ]
            elif self.app.data_type == "optogenetics":
                stim_counts = self.app.get_stim_counts()
                cluster_values = [f"{count} stim" for count in stim_counts]
            else:
                cluster_values = []

            self.app.cluster_dropdown["values"] = cluster_values
            if cluster_values and self.app.selected_cluster.get() not in cluster_values:
                self.app.selected_cluster.set(cluster_values[0])
            self.app.cluster_dropdown.configure(state="normal")
            self.app.period_dropdown.configure(state="normal")
            self.on_cluster_selection_changed()

    def on_cluster_selection_changed(self, event=None) -> None:
        selected_display_type = self.app.display_dropdown.currentText()
        selected_cluster_string = self.app.cluster_dropdown.currentText()
        self.app.selected_display.set(selected_display_type)
        self.app.selected_cluster.set(selected_cluster_string)
        self.app.selected_period.set(self.app.period_dropdown.currentText())

        if selected_display_type == "Single Cluster Display":
            if not selected_cluster_string:
                return
            self.visualize_single_cluster(selected_cluster_string)
        elif selected_display_type == "Mean Cluster Display":
            if not selected_cluster_string:
                return
            self.visualize_mean_cluster(selected_cluster_string)

    def visualize_mean_cluster(self, selected_cluster_string):
        period = self.app.selected_period.get().lower()

        cluster_count = int(re.search(r"(\d+)", selected_cluster_string).group(1))
        is_peak = "peak" in selected_cluster_string.lower()

        cluster_data_by_period = self.app.mean_cluster_data.get(cluster_count)
        if cluster_data_by_period is None:
            if is_peak:
                self.app.compute_data_for_cluster(cluster_count)
            else:
                self.app.compute_data_for_stim_cluster(cluster_count)
            cluster_data_by_period = self.app.mean_cluster_data.get(cluster_count)

        if cluster_data_by_period is None or period not in cluster_data_by_period:
            self.display_no_data_figure()
            return

        cluster_data = cluster_data_by_period[period]
        photometry_data = cluster_data.get("photometry_cluster_data")

        if is_peak and photometry_data is None:
            self.display_no_data_figure()
            return

        if is_peak:
            self.plot_mean_cluster(
                cluster_data["mean_temp_data"],
                cluster_data["mean_act_data"],
                photometry_data,
            )
        else:
            self.plot_mean_cluster(
                cluster_data["mean_temp_data"],
                cluster_data["mean_act_data"],
                photometry_data,
                cluster_count,
            )

    def display_no_data_figure(self):
        self.app.delete_current_figure()

        fig, ax = plt.subplots(figsize=(6, 4))
        ax.text(
            0.5,
            0.5,
            "No clusters in time period",
            horizontalalignment="center",
            verticalalignment="center",
            transform=ax.transAxes,
            fontsize=12,
        )

        ax.set_xticks([])
        ax.set_yticks([])
        self.app.embed_figure_in_canvas(fig, self.app.graph_canvas)

    def plot_mean_cluster(
        self, mean_temp_data, mean_act_data, photometry_cluster_data_df, cluster_count=None
    ):
        self.app.delete_current_figure()
        fig, ax = plt.subplots(figsize=(6, 4))

        color_palette = cm.get_cmap("Set1")

        if self.app.data_type == "photometry":
            scaled_time_column = self.app.scale_time_column(
                photometry_cluster_data_df["Time (min)"]
            )

            for i, cluster_name in enumerate(photometry_cluster_data_df.columns[1:]):
                color = color_palette(i % 10)
                ax.plot(
                    scaled_time_column,
                    photometry_cluster_data_df[cluster_name],
                    label=cluster_name,
                    color=color,
                    alpha=0.5,
                )
        elif self.app.data_type == "optogenetics":
            scaled_time_column = self.app.scale_time_column(
                self.app.mean_cluster_data[cluster_count]["full"][
                    "universal_time_axis_temp_min"
                ]
            )

        ax.set_xlim(scaled_time_column.iloc[0], scaled_time_column.iloc[-1])
        ax.set_xlabel("Time")

        temp_present = (
            mean_temp_data is not None
            and self.app.graph_settings_container_instance.temperature_data_var.get()
        )
        act_present = (
            mean_act_data is not None
            and self.app.graph_settings_container_instance.activity_data_var.get()
        )

        if temp_present and act_present:
            sem_temp_data = mean_temp_data["SEM"]
            sem_act_data = mean_act_data["SEM"]

            ax.yaxis.set_visible(False)
            self.app.plot_service.overlay_temp_on_figure(
                ax, mean_temp_data, sem_temp_data, left_axis=True
            )
            self.app.plot_service.overlay_act_on_figure(
                ax, mean_act_data, ax.get_ylim()[0], ax.get_ylim()[1], sem_act_data
            )
        elif temp_present:
            sem_temp_data = mean_temp_data["SEM"]
            self.app.plot_service.overlay_temp_on_figure(
                ax, mean_temp_data, sem_temp_data, left_axis=False
            )
        elif act_present:
            sem_act_data = mean_act_data["SEM"]
            self.app.plot_service.overlay_act_on_figure(
                ax, mean_act_data, ax.get_ylim()[0], ax.get_ylim()[1], sem_act_data
            )

        if self.app.data_type == "optogenetics":
            self.add_stims_to_plot(ax, cluster_count)

        self.app.embed_figure_in_canvas(fig, self.app.graph_canvas)

    def add_stims_to_plot(self, ax, cluster_count):
        if self.app.stim_timings is None:
            return

        ymin, ymax = ax.get_ylim()
        stim_cluster = next(
            (timings for size, timings in self.app.stim_timings if size == cluster_count),
            None,
        )
        if not stim_cluster:
            return

        cluster_start_time = stim_cluster[0][0]

        for stim_start, stim_end in stim_cluster:
            time_unit = self.app.graph_settings_container_instance.time_unit_menu.get()
            time_factor = self.app.get_time_scale(time_unit)

            adjusted_stim_start = (stim_start - cluster_start_time) * time_factor
            adjusted_stim_end = (stim_end - cluster_start_time) * time_factor

            rect = plt.Rectangle(
                (adjusted_stim_start, ymin),
                adjusted_stim_end - adjusted_stim_start,
                ymax - ymin,
                color="blue",
                alpha=0.3,
            )
            ax.add_patch(rect)

        ax.set_ylim(ymin, ymax)

    def visualize_single_cluster(self, cluster_dropdown_value):
        self.app.delete_current_figure()

        file_path_str = Path(self.app.file_path_var.get()).name
        cluster_number = cluster_dropdown_value.split()[-1]

        matching_key = next(
            (
                key
                for key in self.app.data_dict[file_path_str].keys()
                if f"Cluster_{cluster_number}" in key
            ),
            None,
        )

        if matching_key is None:
            logger.warning("No display key matched %s.", cluster_dropdown_value)
            return

        cluster_data = self.app.data_dict[file_path_str][matching_key]

        original_start_time = float(cluster_data["start_time"])
        original_end_time = float(cluster_data["end_time"])
        pre_time = float(cluster_data["pre_cluster_time"]) / 60
        post_time = float(cluster_data["post_cluster_time"]) / 60

        adjusted_start_time = max(0, original_start_time - pre_time)
        adjusted_end_time = min(
            self.app.temp_data["Time (min)"].max(), original_end_time + post_time
        )

        time_column, data_column = self.app.plot_service.get_single_cluster_data(
            cluster_dropdown_value, pre_time, post_time
        )

        truncated_temp_data = (
            self.app.temp_data[
                (self.app.temp_data["Time (min)"] >= adjusted_start_time)
                & (self.app.temp_data["Time (min)"] <= adjusted_end_time)
            ]
            if self.app.temp_data is not None
            else None
        )
        truncated_act_data = (
            self.app.act_data[
                (self.app.act_data["Time (min)"] >= adjusted_start_time)
                & (self.app.act_data["Time (min)"] <= adjusted_end_time)
            ]
            if self.app.act_data is not None
            else None
        )

        fig, ax, scaled_time_column = self.app.plot_service.prepare_figure(
            time_column, show_nighttime=True
        )

        self.app.plot_service.create_photometry_figure(
            ax, time_column, data_column, [], [], []
        )
        ax.set_xlim(scaled_time_column.iloc[0], scaled_time_column.iloc[-1])

        ymin_photometry, ymax_photometry = ax.get_ylim()
        temp_present = (
            truncated_temp_data is not None
            and self.app.graph_settings_container_instance.temperature_data_var.get()
        )
        act_present = (
            truncated_act_data is not None
            and self.app.graph_settings_container_instance.activity_data_var.get()
        )

        if temp_present and act_present:
            ax.yaxis.set_visible(False)
            self.app.plot_service.overlay_temp_on_figure(
                ax, truncated_temp_data, left_axis=True
            )
            self.app.plot_service.overlay_act_on_figure(
                ax, truncated_act_data, ymin_photometry, ymax_photometry
            )
        elif temp_present:
            self.app.plot_service.overlay_temp_on_figure(
                ax, truncated_temp_data, left_axis=False
            )
        elif act_present:
            self.app.plot_service.overlay_act_on_figure(
                ax, truncated_act_data, ymin_photometry, ymax_photometry
            )

        self.app.embed_figure_in_canvas(fig, self.app.graph_canvas)
