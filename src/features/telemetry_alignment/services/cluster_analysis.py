"""Controller for telemetry cluster compute orchestration."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)
from src.processing.cluster_detection import (
    find_longest_cluster_times,
    group_clusters_by_time_period,
    select_peak_clusters,
)
from src.processing.telemetry_processing import (
    build_aligned_photometry_cluster_data,
)


class TelemetryClusterService:
    """Owns cluster-level compute and precompute flows for telemetry app."""

    def __init__(self, app):
        self.app = app

    def compute_data_for_cluster(self, selected_peak_count, changed_static_inputs=None):
        cluster_number = selected_peak_count
        longest_pre_peak, longest_post_peak = self.find_longest_times(cluster_number)
        native_longest_pre_peak, native_longest_post_peak = self.find_longest_times()

        photometry_data_list = self.extract_and_prepare_photometry_data(
            longest_pre_peak, longest_post_peak, cluster_number
        )
        processed_data, raw_data, native_data = self.extract_and_prepare_temp_and_act_data(
            longest_pre_peak,
            longest_post_peak,
            cluster_number,
            native_longest_pre_peak,
            native_longest_post_peak,
        )

        if processed_data["full"]["temp"] is None or processed_data["full"]["act"] is None:
            logger.warning(
                "Cluster %s: no temp/act data overlaps the cluster time window — "
                "check that the alignment start time and telemetry files cover the "
                "photometry recording period. Skipping precompute for this cluster.",
                cluster_number,
            )
            return

        self.app.mean_cluster_data[cluster_number] = {
            "full": {
                "mean_temp_data": processed_data["full"]["temp"],
                "mean_act_data": processed_data["full"]["act"],
                "photometry_cluster_data": photometry_data_list["full"]["Clusters"],
                "universal_time_axis_temp": processed_data["full"]["temp"]["Time (s)"].tolist(),
                "universal_time_axis_act": processed_data["full"]["act"]["Time (s)"].tolist(),
                "raw_temp_data": raw_data["full"]["temp"],
                "raw_act_data": raw_data["full"]["act"],
                "native_temp_segments": native_data["full"]["temp"],
                "native_act_segments": native_data["full"]["act"],
            },
            "day": {
                "mean_temp_data": processed_data["day"]["temp"],
                "mean_act_data": processed_data["day"]["act"],
                "photometry_cluster_data": photometry_data_list["day"]["Clusters"],
                "universal_time_axis_temp": processed_data["full"]["temp"]["Time (s)"].tolist(),
                "universal_time_axis_act": processed_data["full"]["act"]["Time (s)"].tolist(),
                "raw_temp_data": raw_data["day"]["temp"],
                "raw_act_data": raw_data["day"]["act"],
                "native_temp_segments": native_data["day"]["temp"],
                "native_act_segments": native_data["day"]["act"],
            },
            "night": {
                "mean_temp_data": processed_data["night"]["temp"],
                "mean_act_data": processed_data["night"]["act"],
                "photometry_cluster_data": photometry_data_list["night"]["Clusters"],
                "universal_time_axis_temp": processed_data["full"]["temp"]["Time (s)"].tolist(),
                "universal_time_axis_act": processed_data["full"]["act"]["Time (s)"].tolist(),
                "raw_temp_data": raw_data["night"]["temp"],
                "raw_act_data": raw_data["night"]["act"],
                "native_temp_segments": native_data["night"]["temp"],
                "native_act_segments": native_data["night"]["act"],
            },
        }

        if changed_static_inputs is not None:
            selected_cluster_string = self.app.selected_cluster.get()
            selected_display_type = self.app.selected_display.get()

            if selected_display_type == "Single Cluster Display":
                self.app.display_presenter.visualize_single_cluster(
                    selected_cluster_string
                )
            elif selected_display_type == "Mean Cluster Display":
                self.app.display_presenter.visualize_mean_cluster(
                    selected_cluster_string
                )

    def precompute_all_clusters(self, updated_clusters=None):
        unique_peak_counts = self.app.get_peak_counts()
        unique_stim_counts = self.app.get_stim_counts()

        if updated_clusters is not None:
            updated_peak_counts = set()
            updated_stim_counts = set()

            for cluster_name in updated_clusters:
                if "Peak" in cluster_name:
                    peak_count = int(re.search(r"(\d+)", cluster_name).group(1))
                    updated_peak_counts.add(peak_count)
                elif "stim" in cluster_name:
                    stim_count = int(re.search(r"(\d+)", cluster_name).group(1))
                    updated_stim_counts.add(stim_count)

            unique_peak_counts = [
                peak_count for peak_count in unique_peak_counts if peak_count in updated_peak_counts
            ]
            unique_stim_counts = [
                stim_count for stim_count in unique_stim_counts if stim_count in updated_stim_counts
            ]

        unique_peak_counts = sorted(unique_peak_counts)
        unique_stim_counts = sorted(unique_stim_counts)

        for peak_count in unique_peak_counts:
            if updated_clusters is not None:
                self.compute_data_for_cluster(peak_count, changed_static_inputs=True)
            else:
                self.compute_data_for_cluster(peak_count)

        for stim_count in unique_stim_counts:
            if updated_clusters is not None:
                self.app.compute_data_for_stim_cluster(stim_count, changed_static_inputs=True)
            else:
                self.app.compute_data_for_stim_cluster(stim_count)

    def find_longest_times(self, cluster_number=None):
        return find_longest_cluster_times(self.app.data_dict, cluster_number)

    def extract_and_prepare_temp_and_act_data(
        self,
        longest_pre_peak,
        longest_post_peak,
        cluster_number,
        native_longest_pre_peak=None,
        native_longest_post_peak=None,
    ):
        all_clusters = select_peak_clusters(self.app.cluster_dict, cluster_number)
        clusters_by_period = group_clusters_by_time_period(all_clusters)

        processed_data = {
            "full": {"temp": None, "act": None},
            "day": {"temp": None, "act": None},
            "night": {"temp": None, "act": None},
        }
        raw_data = {
            "full": {"temp": None, "act": None},
            "day": {"temp": None, "act": None},
            "night": {"temp": None, "act": None},
        }
        native_data = {
            "full": {"temp": [], "act": []},
            "day": {"temp": [], "act": []},
            "night": {"temp": [], "act": []},
        }

        if native_longest_pre_peak is None or native_longest_post_peak is None:
            native_longest_pre_peak, native_longest_post_peak = (
                longest_pre_peak,
                longest_post_peak,
            )

        for period, clusters in clusters_by_period.items():
            if not clusters:
                continue

            native_temp_data, native_act_data = self.app.process_data_for_clusters(
                clusters, native_longest_pre_peak, native_longest_post_peak
            )
            native_data[period]["temp"] = native_temp_data
            native_data[period]["act"] = native_act_data

            all_temp_data, all_act_data = self.app.process_data_for_clusters(
                clusters, longest_pre_peak, longest_post_peak
            )

            if not all_temp_data or all(all_temp.empty for all_temp in all_temp_data):
                ext = self.app.extended_temp_data
                t_min = ext["Time (min)"].min() if ext is not None and not ext.empty else "N/A"
                t_max = ext["Time (min)"].max() if ext is not None and not ext.empty else "N/A"
                logger.warning(
                    "Period '%s': all temp windows are empty. "
                    "Extended temp data spans Time(min) [%s, %s]. "
                    "Check alignment start time and that temp file covers the recording.",
                    period, t_min, t_max,
                )
                continue
            if not all_act_data or all(all_act.empty for all_act in all_act_data):
                ext = self.app.extended_act_data
                t_min = ext["Time (min)"].min() if ext is not None and not ext.empty else "N/A"
                t_max = ext["Time (min)"].max() if ext is not None and not ext.empty else "N/A"
                logger.warning(
                    "Period '%s': all act windows are empty. "
                    "Extended act data spans Time(min) [%s, %s]. "
                    "Check alignment start time and that act file covers the recording.",
                    period, t_min, t_max,
                )
                continue

            axis_time_start = -longest_pre_peak * 60
            axis_time_end = longest_post_peak * 60
            universal_time_axis_temp = self.app.create_universal_time_axis(
                axis_time_start, axis_time_end, self.app.temp_sample_rate
            )
            universal_time_axis_act = self.app.create_universal_time_axis(
                axis_time_start, axis_time_end, self.app.act_sample_rate
            )

            all_temp_data = self.app.trim_data_to_minimum_length(all_temp_data)
            all_act_data = self.app.trim_data_to_minimum_length(all_act_data)

            concatenated_temp_data = self.app.align_and_concatenate_data(
                all_temp_data, universal_time_axis_temp
            )
            concatenated_act_data = self.app.align_and_concatenate_data(
                all_act_data, universal_time_axis_act
            )

            if concatenated_temp_data.empty or concatenated_act_data.empty:
                continue

            concatenated_temp_data = concatenated_temp_data.iloc[::-1].dropna(how="all").iloc[::-1]
            concatenated_act_data = concatenated_act_data.iloc[::-1].dropna(how="all").iloc[::-1]

            final_temp_data = self.app.calculate_mean_and_sem(concatenated_temp_data)
            final_act_data = self.app.calculate_mean_and_sem(concatenated_act_data)

            processed_data[period]["temp"] = final_temp_data
            processed_data[period]["act"] = final_act_data
            raw_data[period]["temp"] = concatenated_temp_data
            raw_data[period]["act"] = concatenated_act_data

        return processed_data, raw_data, native_data

    def extract_and_prepare_photometry_data(self, longest_pre_peak, longest_post_peak, cluster_number):
        data_column = self.app.data_selection_frame.selected_column_var.get()
        clusters_by_period = group_clusters_by_time_period(
            select_peak_clusters(self.app.cluster_dict, cluster_number)
        )
        return build_aligned_photometry_cluster_data(
            self.app.dataframe,
            data_column,
            clusters_by_period,
            longest_pre_peak,
            longest_post_peak,
        )
