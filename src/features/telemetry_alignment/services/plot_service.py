"""Controller for telemetry plotting, overlays, and aligned temp/act extraction."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
import math
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PySide6.QtWidgets import QInputDialog, QMessageBox

from src.processing.telemetry_processing import (
    AmbiguousTelemetryAlignmentError,
    calculate_nighttime_periods,
    calculate_stim_timings as _calculate_stim_timings,
    extract_and_trim_data as _extract_and_trim_data,
    extract_data_for_date_and_offset as _extract_data_for_date_and_offset,
    extract_data_with_buffer as _extract_data_with_buffer,
    find_offset_for_previous_time as _find_offset_for_previous_time,
    parse_recording_date,
    upsample_telemetry_data,
)


logger = logging.getLogger(__name__)


class TelemetryPlotService:
    """Owns telemetry plotting and telemetry-file alignment visualization helpers."""

    def __init__(self, app):
        self.app = app

    def custom_date_parser(self, date_str):
        return parse_recording_date(date_str)

    def calculate_nighttime_period(self):
        start_time_str = self._get_recording_start_time_str()

        lights_off_time_str = (self.app.light_off_time_var.get() or "").strip()
        if not getattr(self.app, "date", None):
            self.app.nighttime_periods = []
            return

        recording_date = parse_recording_date(self.app.date).date()
        self.app.nighttime_periods = calculate_nighttime_periods(
            recording_date,
            start_time_str,
            lights_off_time_str,
            self.app.duration_main_data + self._get_display_time_offset_minutes(),
        )
        self.app.settings_manager.light_off_time_var = lights_off_time_str
        self.app.settings_manager.save_variables()

    def add_nighttime_shading_to_plot(self, ax, time_column):
        if not getattr(self.app, "nighttime_periods", None):
            return

        start_time_value = self._get_recording_start_time_str()
        parsed_start_time = pd.to_datetime(
            start_time_value, format="%H:%M:%S", errors="coerce"
        )
        if pd.isna(parsed_start_time):
            return

        start_time = parsed_start_time.time()
        recording_date = datetime.strptime(self.app.date, "%y-%m-%d").date()
        display_offset_minutes = self._get_display_time_offset_minutes()

        for night_start_time, night_end_time in self.app.nighttime_periods:
            night_start_datetime = datetime.combine(recording_date, night_start_time)
            night_end_datetime = datetime.combine(recording_date, night_end_time)

            if night_end_time < start_time:
                night_end_datetime += timedelta(days=1)

            night_start_minutes = (
                night_start_datetime - datetime.combine(recording_date, start_time)
            ).total_seconds() / 60 - display_offset_minutes
            night_end_minutes = (
                night_end_datetime - datetime.combine(recording_date, start_time)
            ).total_seconds() / 60 - display_offset_minutes

            if night_end_minutes < time_column.iloc[0]:
                continue
            night_start_minutes = max(night_start_minutes, time_column.iloc[0])
            night_end_minutes = min(night_end_minutes, time_column.iloc[-1])
            if night_start_minutes <= time_column.iloc[-1]:
                ax.axvspan(
                    night_start_minutes,
                    night_end_minutes,
                    color="gray",
                    alpha=0.3,
                    label="Nighttime",
                )

    def _get_recording_start_time_str(self) -> str:
        start_time_str = (self.app.temp_and_act_start_time_var.get() or "").strip()
        if start_time_str:
            return start_time_str
        return str(self.app.start_time_timedelta or "").strip()

    @staticmethod
    def _format_alignment_candidate(candidate: dict) -> str:
        target_datetime = pd.Timestamp(candidate["target_datetime"])
        previous_timestamp = pd.Timestamp(candidate["previous_timestamp"])
        available_minutes = float(candidate.get("available_minutes", 0) or 0)
        offset_minutes = float(candidate.get("offset", 0) or 0)
        return (
            f"{target_datetime:%Y-%m-%d %H:%M:%S} "
            f"(covers {available_minutes:.1f} min; "
            f"sample {previous_timestamp:%Y-%m-%d %H:%M:%S}, "
            f"offset {offset_minutes:.2f} min)"
        )

    def _prompt_for_alignment_candidate(
        self,
        candidates: list[dict],
    ) -> pd.Timestamp | None:
        choices = [
            self._format_alignment_candidate(candidate)
            for candidate in candidates
        ]
        selected_label, accepted = QInputDialog.getItem(
            self.app,
            "Select Telemetry Alignment Date",
            (
                "More than one telemetry date can cover this recording.\n"
                "Choose the actual plug-in/alignment date and time:"
            ),
            choices,
            0,
            False,
        )
        if not accepted:
            return None

        selected_index = choices.index(selected_label)
        return pd.Timestamp(candidates[selected_index]["target_datetime"])

    def _extract_data_with_alignment_choice(
        self,
        file_path,
        sheet_name,
        target_date,
        target_time,
        duration,
        selected_alignment_datetime=None,
    ):
        try:
            return (
                self.extract_data_for_date_and_offset(
                    file_path,
                    sheet_name,
                    target_date,
                    target_time,
                    duration,
                    selected_alignment_datetime,
                ),
                selected_alignment_datetime,
            )
        except AmbiguousTelemetryAlignmentError as exc:
            selected_alignment_datetime = self._prompt_for_alignment_candidate(
                exc.candidates
            )
            if selected_alignment_datetime is None:
                return None, None
            return (
                self.extract_data_for_date_and_offset(
                    file_path,
                    sheet_name,
                    target_date,
                    target_time,
                    duration,
                    selected_alignment_datetime,
                ),
                selected_alignment_datetime,
            )

    def _extract_overlay_dataframe(
        self,
        file_path,
        sheet_name,
        target_date,
        target_time,
        extraction_duration,
        extended_duration,
        selected_alignment_datetime,
        label,
        data_type,
    ):
        result, selected_alignment_datetime = self._extract_data_with_alignment_choice(
            file_path,
            sheet_name,
            target_date,
            target_time,
            extraction_duration,
            selected_alignment_datetime,
        )
        if result is None:
            return None, selected_alignment_datetime

        telemetry_data, offset, previous_time = result
        logger.info(
            "%s telemetry selected anchor %s with %.3f minute offset.",
            label,
            previous_time,
            offset,
        )
        timestamps_5_to_10 = telemetry_data["Date Time"].iloc[4:10].tolist()
        sample_rate = self.app.calculate_sample_rate(timestamps_5_to_10)
        trimmed_df = self.extract_and_trim_data(
            telemetry_data,
            previous_time,
            offset,
            extraction_duration,
            sample_rate,
            data_type,
        )
        extended_df = self.extract_data_with_buffer(
            telemetry_data,
            previous_time,
            offset,
            extended_duration,
            sample_rate,
        )
        return (
            {
                "source_data": telemetry_data,
                "sample_rate": sample_rate,
                "trimmed": trimmed_df,
                "extended": extended_df,
            },
            selected_alignment_datetime,
        )

    def _get_display_time_offset_minutes(self) -> float:
        if getattr(self.app, "data_type", None) != "photometry":
            return 0.0
        if not self.app.graph_settings_container_instance.remove_first_60_minutes_var.get():
            return 0.0
        return float(getattr(self.app, "seconds_removed", 0) or 0) / 60.0

    def _get_full_photometry_duration_minutes(self) -> float:
        full_dataframe = getattr(self.app, "full_dataframe", None)
        if full_dataframe is None or full_dataframe.empty:
            return float(getattr(self.app, "duration_main_data", 0) or 0)
        time_column = pd.to_numeric(full_dataframe.iloc[:, 0], errors="coerce").dropna()
        if time_column.empty:
            return float(getattr(self.app, "duration_main_data", 0) or 0)
        return float(time_column.iloc[-1] - time_column.iloc[0])

    def _get_full_baseline_reference_column(self, data_column_name: str | None):
        full_dataframe = getattr(self.app, "full_dataframe", None)
        if (
            full_dataframe is None
            or full_dataframe.empty
            or data_column_name not in full_dataframe.columns
        ):
            return None
        return full_dataframe[data_column_name]

    def _get_selected_baseline_reference_column(self):
        data_selection_frame = getattr(self.app, "data_selection_frame", None)
        selected_column_var = getattr(data_selection_frame, "selected_column_var", None)
        if selected_column_var is None:
            return None
        return self._get_full_baseline_reference_column(selected_column_var.get())

    def _shift_overlay_time_axis(
        self, dataframe: pd.DataFrame | None, minutes: float
    ) -> pd.DataFrame | None:
        if dataframe is None:
            return None
        if dataframe.empty or minutes == 0:
            return dataframe.copy()

        time_column_name = self.find_time_column(dataframe)
        if time_column_name is None:
            return dataframe.copy()

        shifted = dataframe.copy()
        shifted[time_column_name] = (
            pd.to_numeric(shifted[time_column_name], errors="coerce") - minutes
        )
        return shifted

    def _has_cached_raw_telemetry(self) -> bool:
        return (
            getattr(self.app, "raw_aligned_temp_data", None) is not None
            or getattr(self.app, "raw_aligned_act_data", None) is not None
        )

    def apply_cached_telemetry_for_current_display(self) -> None:
        display_offset_minutes = self._get_display_time_offset_minutes()
        self.app.temp_data = self._shift_overlay_time_axis(
            getattr(self.app, "raw_aligned_temp_data", None),
            display_offset_minutes,
        )
        self.app.act_data = self._shift_overlay_time_axis(
            getattr(self.app, "raw_aligned_act_data", None),
            display_offset_minutes,
        )
        self.app.extended_temp_data = self._shift_overlay_time_axis(
            getattr(self.app, "raw_extended_temp_data", None),
            display_offset_minutes,
        )
        self.app.extended_act_data = self._shift_overlay_time_axis(
            getattr(self.app, "raw_extended_act_data", None),
            display_offset_minutes,
        )

    def _update_current_photometry_state(self) -> None:
        (
            self.app.time_column,
            self.app.data_column,
            self.app.detected_peaks,
            self.app.clusters_final,
            self.app.grouped_clusters,
        ) = self.get_current_photometry_data()

        time_values = pd.to_numeric(self.app.time_column, errors="coerce").dropna()
        if not time_values.empty:
            self.app.duration_main_data = float(time_values.iloc[-1] - time_values.iloc[0])

    def _refresh_cluster_static_data(self) -> None:
        static_settings_store = getattr(self.app, "static_settings_store", None)
        if static_settings_store is not None:
            static_settings_store.populate_data_dict(replace_existing=True)

        cluster_table_panel = getattr(self.app, "cluster_table_panel", None)
        if cluster_table_panel is not None:
            cluster_table_panel.populate_table()

        populate_dropdown = getattr(self.app, "populate_static_input_dropdown", None)
        if callable(populate_dropdown):
            populate_dropdown()

    def _invalidate_cluster_precompute(self) -> None:
        self.app.mean_cluster_data = {}

    def refresh_after_trim_toggle(self) -> None:
        if self.app.data_type != "photometry":
            self.redraw_graph()
            return

        self._update_current_photometry_state()
        if self._has_cached_raw_telemetry():
            self.apply_cached_telemetry_for_current_display()

        self.calculate_nighttime_period()
        self._refresh_cluster_static_data()
        self.app.annotate_clusters_with_time_period()
        self._invalidate_cluster_precompute()
        self.visualize_photometry_data_with_overlays(
            self.app.time_column,
            self.app.data_column,
            self.app.detected_peaks,
            self.app.clusters_final,
            self.app.graph_canvas,
            self.app.temp_data,
            self.app.act_data,
            show_nighttime=True,
        )
        self.app.settings_manager.save_variables()

    @staticmethod
    def _time_of_day_interval_minutes(span_minutes: float) -> int:
        if span_minutes <= 120:
            return 15
        if span_minutes <= 360:
            return 30
        if span_minutes <= 720:
            return 60
        return 120

    @staticmethod
    def _round_up_datetime(dt: datetime, interval_minutes: int) -> datetime:
        total_minutes = dt.hour * 60 + dt.minute + dt.second / 60
        rounded_minutes = math.ceil(total_minutes / interval_minutes) * interval_minutes
        rounded_base = datetime.combine(dt.date(), datetime.min.time())
        rounded = rounded_base + timedelta(minutes=rounded_minutes)
        if rounded < dt:
            rounded += timedelta(minutes=interval_minutes)
        return rounded

    def _apply_time_of_day_axis(self, ax, time_column) -> bool:
        start_time_str = self._get_recording_start_time_str()
        if not start_time_str or not getattr(self.app, "date", None):
            return False

        parsed_start_time = pd.to_datetime(
            start_time_str, format="%H:%M:%S", errors="coerce"
        )
        if pd.isna(parsed_start_time):
            return False

        recording_date = parse_recording_date(self.app.date).date()
        recording_start = datetime.combine(recording_date, parsed_start_time.time())
        display_offset_minutes = self._get_display_time_offset_minutes()
        absolute_window_start = display_offset_minutes + float(time_column.iloc[0])
        absolute_window_end = display_offset_minutes + float(time_column.iloc[-1])
        window_start = recording_start + timedelta(minutes=absolute_window_start)
        window_end = recording_start + timedelta(minutes=absolute_window_end)
        span_minutes = max(
            1.0, float(time_column.iloc[-1]) - float(time_column.iloc[0])
        )
        interval_minutes = self._time_of_day_interval_minutes(span_minutes)
        tick_time = self._round_up_datetime(window_start, interval_minutes)

        tick_positions = []
        tick_labels = []
        while tick_time <= window_end:
            tick_positions.append(
                (tick_time - recording_start).total_seconds() / 60
                - display_offset_minutes
            )
            tick_labels.append(tick_time.strftime("%H:%M"))
            tick_time += timedelta(minutes=interval_minutes)

        if not tick_positions:
            tick_positions = [
                float(time_column.iloc[0]),
                float(time_column.iloc[-1]),
            ]
            tick_labels = [
                window_start.strftime("%H:%M"),
                window_end.strftime("%H:%M"),
            ]

        ax.set_xticks(tick_positions)
        ax.set_xticklabels(
            tick_labels,
            rotation=45,
            ha="right",
            rotation_mode="anchor",
            va="center",
        )
        return True

    def find_time_column(self, dataframe):
        for col in dataframe.columns:
            if re.match(r"^Time\s", col):
                return col
        return None

    def mean_of_top_five(self, data_column):
        numeric_column = pd.to_numeric(data_column, errors="coerce").dropna()
        if len(numeric_column) >= 5:
            return numeric_column.nlargest(5).mean()
        return numeric_column.mean()

    @staticmethod
    def _finite_series(values) -> pd.Series:
        numeric_values = pd.to_numeric(values, errors="coerce")
        return numeric_values[np.isfinite(numeric_values)]

    def _overlay_columns_are_usable(
        self, dataframe: pd.DataFrame | None, value_column: str, label: str
    ) -> bool:
        if dataframe is None or dataframe.empty:
            logger.warning("%s overlay skipped because no rows were available.", label)
            return False

        time_column_name = self.find_time_column(dataframe)
        if time_column_name is None:
            logger.warning("%s overlay skipped because no time column was found.", label)
            return False
        if value_column not in dataframe.columns:
            logger.warning(
                "%s overlay skipped because column '%s' was not found.",
                label,
                value_column,
            )
            return False

        time_values = self._finite_series(dataframe[time_column_name])
        data_values = self._finite_series(dataframe[value_column])
        if time_values.empty or data_values.empty:
            logger.warning(
                "%s overlay skipped because the selected telemetry window has no finite values.",
                label,
            )
            return False
        return True

    @staticmethod
    def _positive_float(value, fallback: float) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return fallback
        return number if np.isfinite(number) and number > 0 else fallback

    def calculate_dynamic_bins(self, n, b_ref=600, t_ref=1200, k=5):
        bins = int(b_ref * math.log(1 + (n * k / t_ref)))
        return min(n, bins)

    def find_offset_for_previous_time(self, dataframe, target_time_str):
        return _find_offset_for_previous_time(dataframe, target_time_str)

    def extract_data_for_date_and_offset(
        self,
        file_path,
        sheet_name,
        target_date,
        target_time,
        duration=None,
        selected_alignment_datetime=None,
    ):
        return _extract_data_for_date_and_offset(
            file_path,
            sheet_name,
            target_date,
            target_time,
            duration,
            selected_alignment_datetime,
        )

    def extract_and_trim_data(self, dataframe, previous_time, offset, duration, sample_rate, data_type):
        return _extract_and_trim_data(
            dataframe, previous_time, offset, duration, sample_rate
        )

    def extract_data_with_buffer(self, dataframe, previous_time, offset, duration, sample_rate):
        return _extract_data_with_buffer(
            dataframe,
            offset,
            sample_rate,
            previous_time=previous_time,
            duration=duration,
        )

    def upsample_data(self, dataframe):
        return upsample_telemetry_data(dataframe)

    def calculate_stim_timings(self, stim_data_df):
        return _calculate_stim_timings(
            stim_data_df, self.app.temp_and_act_start_time_var.get()
        )

    def prepare_figure(self, time_column, show_nighttime=False, show_time_of_day=False):
        self.app.delete_current_figure()
        scaled_time_column = self.app.scale_time_column(time_column)
        fig, ax = plt.subplots(figsize=(6, 4))

        time_unit = self.app.graph_settings_container_instance.time_unit_menu.get()
        selected_display = getattr(self.app.selected_display, "get", lambda: "Full Trace Display")()
        show_time_of_day = (
            time_unit == "time of day" and selected_display != "Mean Cluster Display"
        )

        if show_time_of_day:
            ax.set_xlabel("Time of Day")
        else:
            if time_unit == "seconds":
                ax.set_xlabel("Time (s)")
            elif time_unit == "hours":
                ax.set_xlabel("Time (h)")
            elif time_unit == "minutes":
                ax.set_xlabel("Time (min)")
            elif time_unit == "time of day":
                ax.set_xlabel("Time (min)")

        if show_time_of_day and not self._apply_time_of_day_axis(ax, time_column):
            ax.set_xlabel("Time (min)")

        if show_nighttime:
            self.add_nighttime_shading_to_plot(ax, time_column)

        ax.set_xlim(scaled_time_column.iloc[0], scaled_time_column.iloc[-1])
        return fig, ax, scaled_time_column

    def create_photometry_figure(self, ax, time_column, data_column, peak_indices, clusters, show_nighttime=False):
        scaled_time_column = self.app.scale_time_column(time_column)
        ax.plot(
            scaled_time_column,
            data_column,
            label="Data",
            color=self.app.settings_manager.selected_photometry_line_color,
            linewidth=self.app.settings_manager.selected_photometry_line_width,
        )

        baseline_reference_column = self._get_selected_baseline_reference_column()
        if baseline_reference_column is None:
            baseline_reference_column = data_column
        median_value = baseline_reference_column.median()
        mean_value = baseline_reference_column.mean()
        baseline_value = mean_value if median_value == 0 else median_value
        baseline_multiplier = float(self.app.baseline_multiplier.get().strip() or 1) - 1
        baseline = baseline_value + (baseline_multiplier * abs(baseline_value))

        if self.app.baseline_thickness.get() != "0":
            ax.plot(
                [scaled_time_column.iloc[0], scaled_time_column.iloc[-1]],
                [baseline, baseline],
                color=self.app.baseline_color.get(),
                linestyle=self.app.baseline_style.get(),
                linewidth=int(self.app.baseline_thickness.get()),
                label="Baseline",
            )

        if show_nighttime:
            self.add_nighttime_shading_to_plot(ax, scaled_time_column)

        ax.plot(
            scaled_time_column.iloc[peak_indices],
            data_column.iloc[peak_indices] + int(self.app.y_offset_peak_symbol.get()),
            color=self.app.label_color_var.get(),
            marker=self.app.label_symbol_var.get(),
            linestyle="",
            label="Peaks",
            markersize=int(self.app.label_size_var.get()),
        )

        for cluster in clusters:
            start = scaled_time_column.iloc[cluster[0]]
            end = scaled_time_column.iloc[min(cluster[1], len(scaled_time_column) - 1)]
            ymin = data_column.min()
            ymax_data = data_column.iloc[cluster[0] : cluster[1]].max()
            ymax = ymax_data * float(self.app.cluster_box_height_modifier.get())

            cluster_box = plt.Rectangle(
                (start, ymin),
                end - start,
                ymax - ymin,
                color=self.app.cluster_box_color.get(),
                alpha=float(self.app.cluster_box_alpha.get()),
            )

            burst_count = sum(1 for peak in peak_indices if cluster[0] <= peak < cluster[1])
            annotation_x = (start + end) / 2
            annotation_y = ymax
            ax.annotate(
                str(burst_count),
                (annotation_x, annotation_y),
                textcoords="offset points",
                xytext=(0, float(self.app.y_for_peak_count.get())),
                ha="center",
                fontsize=self.app.peak_count_size_var.get(),
                color=self.app.peak_count_color_var.get(),
            )

            cluster_key = self.app.format_cluster_string(burst_count)
            if cluster_key not in self.app.cluster_display_status or self.app.cluster_display_status[cluster_key].get():
                ax.add_patch(cluster_box)
                if cluster_key not in self.app.cluster_boxes:
                    self.app.cluster_boxes[cluster_key] = []
                self.app.cluster_boxes[cluster_key].append(cluster_box)

        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.set_ylim(data_column.min(), (data_column.max() * 1.1))
        return ax

    def overlay_temp_on_figure(self, ax, trimmed_temp_df, sem_temp_data=None, left_axis=True):
        value_column = "Mean" if sem_temp_data is not None else "Data"
        if not self._overlay_columns_are_usable(trimmed_temp_df, value_column, "Temperature"):
            return None

        time_column_name = self.find_time_column(trimmed_temp_df)
        time_data = pd.to_numeric(trimmed_temp_df[time_column_name], errors="coerce")
        if "s" in time_column_name.lower():
            time_data = time_data / 60

        time_column = self.app.scale_time_column(time_data).reset_index(drop=True)
        temp_values = pd.to_numeric(
            trimmed_temp_df[value_column], errors="coerce"
        ).reset_index(drop=True)
        finite_mask = np.isfinite(time_column) & np.isfinite(temp_values)
        time_column = time_column[finite_mask]
        temp_values = temp_values[finite_mask]
        if time_column.empty or temp_values.empty:
            logger.warning(
                "Temperature overlay skipped because the selected telemetry window has no finite values."
            )
            return None

        if left_axis:
            ax_temp = ax.twinx()
            ax_temp.spines["right"].set_visible(False)
            ax_temp.spines["left"].set_position(("outward", 0))
            ax_temp.yaxis.set_ticks_position("left")
            ax_temp.yaxis.set_label_position("left")
        else:
            ax_temp = ax.twinx()
            ax_temp.spines["right"].set_position(("outward", 0))

        ax_temp.plot(
            time_column,
            temp_values,
            color=self.app.settings_manager.selected_temp_mean_line_color,
            label="Temperature",
            linewidth=self.app.settings_manager.selected_temp_mean_line_width,
            alpha=float(self.app.settings_manager.selected_temp_mean_line_alpha),
        )

        if sem_temp_data is not None:
            sem_series = (
                sem_temp_data.iloc[:, 0]
                if isinstance(sem_temp_data, pd.DataFrame)
                else sem_temp_data
            )
            sem_values = pd.to_numeric(sem_series, errors="coerce")
            sem_values = sem_values.reset_index(drop=True)[finite_mask]
            sem_mask = np.isfinite(sem_values)
            if sem_mask.any():
                temp_array = np.array(temp_values[sem_mask], dtype=float)
                sem_array = np.array(sem_values[sem_mask], dtype=float)
                lower_bound = temp_array - sem_array
                upper_bound = temp_array + sem_array
                ax_temp.fill_between(
                    time_column[sem_mask],
                    lower_bound,
                    upper_bound,
                    color=self.app.settings_manager.selected_temp_sem_color,
                    alpha=float(self.app.settings_manager.selected_temp_sem_line_alpha),
                )

        ax_temp.set_ylabel(
            "Temperature (\N{DEGREE SIGN}C)",
            color=self.app.settings_manager.selected_temp_sem_color,
        )
        ax_temp.tick_params(axis="y", labelcolor=self.app.settings_manager.selected_temp_sem_color)

        if sem_temp_data is not None:
            sem_series = (
                sem_temp_data.iloc[:, 0]
                if isinstance(sem_temp_data, pd.DataFrame)
                else sem_temp_data
            )
            sem_values_for_limits = pd.to_numeric(
                sem_series, errors="coerce"
            ).reset_index(drop=True)[finite_mask]
            sem_values_for_limits = sem_values_for_limits[np.isfinite(sem_values_for_limits)]
            if sem_values_for_limits.empty:
                actual_temp_min = temp_values.min()
                actual_temp_max = temp_values.max()
            else:
                aligned_temp_values = temp_values.loc[sem_values_for_limits.index]
                actual_temp_min = min(
                    (aligned_temp_values - sem_values_for_limits).min(),
                    aligned_temp_values.min(),
                )
                actual_temp_max = max(
                    (aligned_temp_values + sem_values_for_limits).max(),
                    aligned_temp_values.max(),
                )
        else:
            actual_temp_min = temp_values.min()
            actual_temp_max = temp_values.max()

        if not np.isfinite(actual_temp_min) or not np.isfinite(actual_temp_max):
            logger.warning("Temperature overlay skipped because axis limits were not finite.")
            ax_temp.remove()
            return None

        if actual_temp_min == actual_temp_max:
            padding = max(abs(float(actual_temp_min)) * 0.01, 0.5)
            actual_temp_min -= padding
            actual_temp_max += padding

        temp_difference = actual_temp_max - actual_temp_min
        temp_desired_scale = self._positive_float(
            self.app.settings_manager.selected_temp_desired_scale,
            1.0,
        )
        try:
            temp_position_factor = float(self.app.settings_manager.selected_temp_desired_offset)
        except (TypeError, ValueError):
            temp_position_factor = 0.5
        if not np.isfinite(temp_position_factor):
            temp_position_factor = 0.5
        scaled_temp_difference = temp_difference / temp_desired_scale
        total_padding = scaled_temp_difference - temp_difference
        bottom_padding = total_padding * temp_position_factor
        top_padding = total_padding - bottom_padding
        temp_desired_range_min = actual_temp_min - bottom_padding
        temp_desired_range_max = actual_temp_max + top_padding

        ax_temp.set_ylim(temp_desired_range_min, temp_desired_range_max)
        ax_temp.spines["top"].set_visible(False)
        return ax_temp

    def overlay_act_on_figure(self, ax, act_data, ymin_photometry, ymax_photometry, sem_act_data=None):
        value_column = "Mean" if sem_act_data is not None else "Data"
        if not self._overlay_columns_are_usable(act_data, value_column, "Activity"):
            return None

        time_column_name = self.find_time_column(act_data)
        time_data = pd.to_numeric(act_data[time_column_name], errors="coerce")
        if "s" in time_column_name.lower():
            time_data = time_data / 60

        time_column = self.app.scale_time_column(time_data).reset_index(drop=True)
        act_values = pd.to_numeric(
            act_data[value_column], errors="coerce"
        ).reset_index(drop=True)
        finite_mask = np.isfinite(time_column) & np.isfinite(act_values)
        time_column = time_column[finite_mask]
        act_values = act_values[finite_mask]
        if time_column.empty or act_values.empty:
            logger.warning(
                "Activity overlay skipped because the selected telemetry window has no finite values."
            )
            return None

        ax_act = ax.twinx()

        max_act_modifier = self._positive_float(
            self.app.settings_manager.selected_activity_desired_scale,
            1.0,
        )
        baseline_modifier = max_act_modifier * 0
        desired_baseline = ymin_photometry - baseline_modifier

        if sem_act_data is not None:
            histogram_height = self.mean_of_top_five(act_values) / max_act_modifier
        else:
            histogram_height = self.mean_of_top_five(act_values) / max_act_modifier
        if not np.isfinite(histogram_height):
            histogram_height = 1.0

        act_ymax_with_offset = desired_baseline + histogram_height
        ax.set_ylim((ymin_photometry - baseline_modifier), ymax_photometry + (0.05 * ymax_photometry))

        ax_act.spines["right"].set_position(("outward", 0))
        ax_act.spines["right"].set_visible(True)

        num_bins = self.app.settings_manager.selected_activity_num_bins
        if self.app.selected_display.get() == "Mean Cluster Display":
            num_bins = int((time_data.iloc[-1] - time_data.iloc[0]) / self.app.act_sample_rate * 60)
        elif num_bins == "":
            num_bins = self.calculate_dynamic_bins(len(time_column))
        else:
            num_bins = int(num_bins)
        num_bins = max(1, int(num_bins))

        ax_act.hist(
            time_column,
            weights=act_values,
            bins=num_bins,
            align="mid",
            color=self.app.settings_manager.selected_activity_mean_bar_color,
            label="Activity",
            alpha=float(self.app.settings_manager.selected_activity_mean_bar_alpha),
        )

        ax_act.set_ylabel("Activity (counts)", color=self.app.settings_manager.selected_activity_mean_bar_color)
        ax_act.tick_params(axis="y", labelcolor=self.app.settings_manager.selected_activity_mean_bar_color, labelright=True)
        ax_act.spines["left"].set_visible(False)
        ax_act.spines["top"].set_visible(False)
        if not np.isfinite(act_ymax_with_offset) or act_ymax_with_offset <= 0:
            act_ymax_with_offset = max(1.0, float(np.nanmax(act_values)) if len(act_values) else 1.0)
        ax_act.set_ylim(0, act_ymax_with_offset)
        return ax_act

    def overlay_data(self, ax, temp_data=None, act_data=None, ymin=None, ymax=None):
        temp_present = temp_data is not None and self.app.graph_settings_container_instance.temperature_data_var.get()
        act_present = act_data is not None and self.app.graph_settings_container_instance.activity_data_var.get()

        if temp_present and act_present:
            ax_temp = self.overlay_temp_on_figure(ax, temp_data, left_axis=True)
            if ax_temp is not None:
                ax.yaxis.set_visible(False)
            ax_act = self.overlay_act_on_figure(ax, act_data, ymin, ymax)
            if ax_act is None:
                ax_act = ax
        elif temp_present:
            self.overlay_temp_on_figure(ax, temp_data, left_axis=False)
            ax_act = ax
        elif act_present:
            ax_act = self.overlay_act_on_figure(ax, act_data, ymin, ymax)
            if ax_act is None:
                ax_act = ax
        else:
            ax_act = ax

        return ax_act

    def overlay_opto_stimulations(self, ax):
        if self.app.stim_timings is None:
            return

        ymin, ymax = ax.get_ylim()
        for _, timings in self.app.stim_timings:
            for stim_start, stim_end in timings:
                time_unit = self.app.graph_settings_container_instance.time_unit_menu.get()
                time_factor = self.app.get_time_scale(time_unit)
                if time_factor is None:
                    time_factor = self.app.get_time_scale("minutes")
                scaled_stim_start = stim_start * time_factor
                scaled_stim_end = stim_end * time_factor
                rect = plt.Rectangle(
                    (scaled_stim_start, ymin),
                    scaled_stim_end - scaled_stim_start,
                    ymax - ymin,
                    color="blue",
                    alpha=0.3,
                )
                ax.add_patch(rect)

        ax.set_ylim(ymin, ymax)

    def get_single_cluster_data(self, cluster_dropdown_value, pre_time=0.0, post_time=0.0):
        cluster_number = int(cluster_dropdown_value.split()[-1])
        cluster_indices = list(self.app.cluster_dict.keys())[cluster_number - 1]
        start_index, end_index, _ = cluster_indices

        original_start_time = self.app.time_column[start_index]
        original_end_time = self.app.time_column[end_index]

        adjusted_start_time = max(0, original_start_time - pre_time)
        adjusted_end_time = min(self.app.time_column.iloc[-1], original_end_time + post_time)
        adjusted_start_index = (self.app.time_column - adjusted_start_time).abs().idxmin()
        adjusted_end_index = (self.app.time_column - adjusted_end_time).abs().idxmin()

        time_column = self.app.time_column.iloc[adjusted_start_index:adjusted_end_index]
        data_column = self.app.data_column.iloc[adjusted_start_index:adjusted_end_index]
        return time_column, data_column

    def visualize_photometry_data_with_overlays(
        self,
        time_column,
        data_column,
        detected_peaks,
        clusters,
        graph_canvas,
        temp_data=None,
        act_data=None,
        show_nighttime=False,
    ):
        fig, ax, _ = self.prepare_figure(time_column, show_nighttime)
        ax = self.create_photometry_figure(ax, time_column, data_column, detected_peaks, clusters, show_nighttime)
        ymin_photometry, ymax_photometry = ax.get_ylim()
        self.overlay_data(ax, temp_data, act_data, ymin_photometry, ymax_photometry)
        self.app.embed_figure_in_canvas(fig, graph_canvas)

    def visualize_opto_data_with_overlays(self, show_nighttime=False):
        temp_data = self.app.temp_data
        act_data = self.app.act_data
        time_column = temp_data["Time (min)"]
        self.app.display_dropdown.configure(state="normal")

        fig, ax, _ = self.prepare_figure(time_column, show_nighttime, show_time_of_day=False)
        ymin_photometry, ymax_photometry = ax.get_ylim()
        ax_act = self.overlay_data(ax, temp_data, act_data, ymin_photometry, ymax_photometry)
        self.overlay_opto_stimulations(ax_act)
        self.app.embed_figure_in_canvas(fig, self.app.graph_canvas)

    def precalculate_data_versions(self):
        data_column_name = self.app.data_selection_frame.selected_column_var.get()
        baseline = self.app.dataframe[data_column_name].median()
        self.app.full_dataframe = self.app.dataframe.copy()

        sixty_minute_indices = self.app.dataframe[self.app.dataframe.iloc[:, 0] >= 60].index
        if sixty_minute_indices.any():
            sixty_minute_index = sixty_minute_indices[0]
            sliced_dataframe = self.app.dataframe[sixty_minute_index:]
            below_baseline_indices = sliced_dataframe[sliced_dataframe[data_column_name] <= baseline].index

            if below_baseline_indices.any():
                first_idx_to_use = max(sixty_minute_index, below_baseline_indices[0])
            else:
                first_idx_to_use = sixty_minute_index
        else:
            first_idx_to_use = 0

        if first_idx_to_use is not None and first_idx_to_use > 0:
            self.app.seconds_removed = self.app.dataframe.iloc[first_idx_to_use, 0] * 60
            self.app.trimmed_dataframe = self.app.dataframe.iloc[first_idx_to_use:].reset_index(drop=True)
            self.app.trimmed_dataframe.iloc[:, 0] = (
                self.app.trimmed_dataframe.iloc[:, 0] - self.app.trimmed_dataframe.iloc[0, 0]
            )
        else:
            self.app.seconds_removed = 0
            self.app.trimmed_dataframe = self.app.dataframe.copy()

    def get_current_photometry_data(self):
        data_column_name = self.app.data_selection_frame.selected_column_var.get()
        if self.app.graph_settings_container_instance.remove_first_60_minutes_var.get():
            self.app.dataframe = self.app.trimmed_dataframe.copy()
        else:
            self.app.dataframe = self.app.full_dataframe.copy()

        detected_peaks = self.app.detect_peaks_with_optimal_prominence(self.app.dataframe[data_column_name])
        baseline_reference_column = self._get_full_baseline_reference_column(
            data_column_name
        )
        clusters_final, self.app.cluster_dict = self.app.identify_clusters(
            self.app.dataframe.iloc[:, 0],
            self.app.dataframe[data_column_name],
            detected_peaks,
            baseline_reference_column=baseline_reference_column,
        )
        grouped_clusters = self.app.group_clusters_by_peak_count(self.app.cluster_dict)
        return (
            self.app.dataframe.iloc[:, 0],
            self.app.dataframe[data_column_name],
            detected_peaks,
            clusters_final,
            grouped_clusters,
        )

    def overlay_temp_and_act(self):
        target_date = self.app.date
        act_file_path = self.app.act_file_path
        temp_file_path = self.app.temp_file_path
        full_duration = self._get_full_photometry_duration_minutes()
        display_offset_minutes = self._get_display_time_offset_minutes()
        extraction_duration = full_duration
        extended_duration = full_duration + 60
        act_data = None
        temp_data = None
        self.app.raw_aligned_act_data = None
        self.app.raw_extended_act_data = None
        self.app.raw_aligned_temp_data = None
        self.app.raw_extended_temp_data = None
        self.app.display_dropdown.configure(state="normal")

        parsed_date = self.custom_date_parser(target_date)
        formatted_date = parsed_date.strftime("%m/%d/%Y")
        if not self.app.temp_and_act_start_time_var.get().strip():
            if self.app.start_time_timedelta is not None:
                target_time = self.app.start_time_timedelta
            else:
                QMessageBox.critical(
                    self.app,
                    "Input Error",
                    "Please enter a valid file alignment time.",
                )
                return None, None
        else:
            target_time = self.app.temp_and_act_start_time_var.get().strip()

        logger.info(
            "Telemetry extraction requested for %s %s over %.3f raw minutes; "
            "display offset is %.3f minutes.",
            formatted_date,
            target_time,
            extraction_duration,
            display_offset_minutes,
        )

        selected_alignment_datetime = None
        act_overlay = None
        temp_overlay = None
        if act_file_path is not None:
            act_overlay, selected_alignment_datetime = self._extract_overlay_dataframe(
                act_file_path,
                self.app.mouse_name,
                formatted_date,
                target_time,
                extraction_duration,
                extended_duration,
                selected_alignment_datetime,
                "Activity",
                "act",
            )
            if act_overlay is None:
                return None, None

        if temp_file_path is not None:
            selected_before_temp = selected_alignment_datetime
            temp_overlay, selected_alignment_datetime = self._extract_overlay_dataframe(
                temp_file_path,
                self.app.mouse_name,
                formatted_date,
                target_time,
                extraction_duration,
                extended_duration,
                selected_alignment_datetime,
                "Temperature",
                "temp",
            )
            if temp_overlay is None:
                return None, None

            if (
                selected_before_temp is None
                and selected_alignment_datetime is not None
                and act_file_path is not None
            ):
                act_overlay, _ = self._extract_overlay_dataframe(
                    act_file_path,
                    self.app.mouse_name,
                    formatted_date,
                    target_time,
                    extraction_duration,
                    extended_duration,
                    selected_alignment_datetime,
                    "Activity",
                    "act",
                )
                if act_overlay is None:
                    return None, None

        if act_overlay is not None:
            act_data = act_overlay["source_data"]
            self.app.act_sample_rate = act_overlay["sample_rate"]
            self.app.raw_extended_act_data = act_overlay["extended"]
            self.app.raw_aligned_act_data = act_overlay["trimmed"]

        if temp_overlay is not None:
            temp_data = temp_overlay["source_data"]
            self.app.temp_sample_rate = temp_overlay["sample_rate"]
            self.app.raw_extended_temp_data = temp_overlay["extended"]
            self.app.raw_aligned_temp_data = temp_overlay["trimmed"]

        if self.app.data_type == "photometry" and temp_data is not None:
            temp_data = self.upsample_data(temp_data)
            temp_sample_rate = 0.1

        self.apply_cached_telemetry_for_current_display()
        trimmed_temp_df = self.app.temp_data
        trimmed_act_df = self.app.act_data

        if self.app.data_type == "photometry":
            self._update_current_photometry_state()
            self.calculate_nighttime_period()
            self._refresh_cluster_static_data()
            self.app.annotate_clusters_with_time_period()
            self._invalidate_cluster_precompute()
            self.visualize_photometry_data_with_overlays(
                self.app.time_column,
                self.app.data_column,
                self.app.detected_peaks,
                self.app.clusters_final,
                self.app.graph_canvas,
                trimmed_temp_df,
                trimmed_act_df,
                show_nighttime=True,
            )
        elif self.app.data_type == "optogenetics":
            self.app.update_column_headings()
            self.app.static_settings_store.populate_data_dict()
            self.app.cluster_table_panel.populate_table()
            self.app.populate_static_input_dropdown()
            self.calculate_nighttime_period()
            self.app.annotate_clusters_with_time_period()
            self.app.precompute_all_clusters()
            self.visualize_opto_data_with_overlays(show_nighttime=True)

    def redraw_graph(self):
        if self.app.data_type == "photometry":
            self._update_current_photometry_state()
            if self._has_cached_raw_telemetry():
                self.apply_cached_telemetry_for_current_display()
            self.calculate_nighttime_period()

            if self.app.act_data is not None or self.app.temp_data is not None:
                self.visualize_photometry_data_with_overlays(
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
                self.visualize_photometry_data_with_overlays(
                    self.app.time_column,
                    self.app.data_column,
                    self.app.detected_peaks,
                    self.app.clusters_final,
                    self.app.graph_canvas,
                )
        elif self.app.data_type == "optogenetics":
            self.visualize_opto_data_with_overlays(show_nighttime=True)

        self.app.settings_manager.save_variables()
