"""Pure telemetry cluster detection and window extraction helpers."""

from __future__ import annotations

import re

import pandas as pd

from src.processing.telemetry_processing import get_universal_times


def _parse_optional_float(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        return float(stripped)
    return float(value)


def identify_clusters(
    time_column: pd.Series,
    data_column: pd.Series,
    peak_indices,
    baseline_multiplier=1,
    adjust_clustering_seconds=None,
    baseline_reference_column=None,
) -> tuple[list[tuple[int, int]], dict]:
    """Identify valid clusters and return both spans and cluster metadata."""
    reference_column = (
        data_column
        if baseline_reference_column is None
        else pd.Series(baseline_reference_column)
    )
    median_value = reference_column.median()
    mean_value = reference_column.mean()
    baseline_value = mean_value if median_value == 0 else median_value

    resolved_baseline_multiplier = (_parse_optional_float(baseline_multiplier) or 1.0) - 1.0
    end_baseline = baseline_value + (resolved_baseline_multiplier * abs(baseline_value))

    clusters: list[tuple[int, int]] = []
    start = None
    was_below_median = True

    for index in range(len(data_column)):
        current_value = data_column.iloc[index]
        if was_below_median and current_value > median_value:
            start = index
            was_below_median = False
        elif not was_below_median and current_value <= end_baseline:
            if start is not None:
                clusters.append((start, index))
                start = None
            was_below_median = True
        elif current_value < median_value:
            was_below_median = True

    if start is not None:
        clusters.append((start, len(data_column) - 1))

    peak_indices = list(peak_indices)
    valid_clusters = [
        cluster
        for cluster in clusters
        if any(peak in range(cluster[0], cluster[1]) for peak in peak_indices)
    ]

    resolved_adjust_clustering = _parse_optional_float(adjust_clustering_seconds)
    if resolved_adjust_clustering is not None:
        adjust_clustering_minutes = resolved_adjust_clustering / 60.0
        merged_clusters: list[tuple[int, int]] = []
        previous_cluster: tuple[int, int] | None = None

        for cluster in valid_clusters:
            if previous_cluster is None:
                merged_clusters.append(cluster)
                previous_cluster = cluster
                continue

            time_between_clusters = (
                time_column.iloc[cluster[0]] - time_column.iloc[previous_cluster[1]]
            )
            if time_between_clusters < adjust_clustering_minutes:
                merged_cluster = (previous_cluster[0], cluster[1])
                merged_clusters[-1] = merged_cluster
                previous_cluster = merged_cluster
            else:
                merged_clusters.append(cluster)
                previous_cluster = cluster

        valid_clusters = merged_clusters

    cluster_dict = {}
    cluster_id = 1

    for cluster in valid_clusters:
        peak_times_within_cluster = [
            time_column.iloc[peak]
            for peak in peak_indices
            if cluster[0] <= peak < cluster[1]
        ]
        peak_amplitudes_within_cluster = [
            data_column.iloc[peak] - median_value
            for peak in peak_indices
            if cluster[0] <= peak < cluster[1]
        ]

        if len(peak_times_within_cluster) > 1:
            interpeak_intervals = [
                peak_times_within_cluster[i + 1] - peak_times_within_cluster[i]
                for i in range(len(peak_times_within_cluster) - 1)
            ]
        else:
            interpeak_intervals = None

        cluster_duration = time_column.iloc[cluster[1]] - time_column.iloc[cluster[0]]
        peak_count = len(peak_times_within_cluster)
        cluster_name = (
            f"1 Peak in Cluster_{cluster_id}"
            if peak_count == 1
            else f"{peak_count} Peaks in Cluster_{cluster_id}"
        )
        key = (cluster[0], cluster[1], peak_count)
        cluster_dict[key] = {
            "name": cluster_name,
            "start_time": time_column.iloc[cluster[0]],
            "end_time": time_column.iloc[cluster[1]],
            "peaks": peak_times_within_cluster,
            "peak_amplitudes": peak_amplitudes_within_cluster,
            "alignment_index": 0,
            "interpeak_intervals": interpeak_intervals,
            "cluster_duration": cluster_duration,
        }
        cluster_id += 1

    return valid_clusters, cluster_dict


def select_peak_clusters(cluster_dict: dict, cluster_number: int) -> list[dict]:
    """Return peak clusters matching *cluster_number* and already tagged by time period."""
    return [
        cluster_data
        for cluster_key, cluster_data in cluster_dict.items()
        if cluster_key[2] == cluster_number and "time_period" in cluster_data
    ]


def select_stim_clusters(data_dict: dict, stim_number: int) -> list[dict]:
    """Return stimulation clusters matching *stim_number* and already tagged by time period."""
    clusters: list[dict] = []
    for cluster_group in data_dict.values():
        for cluster_key, cluster_data in cluster_group.items():
            match = re.search(r"(\d+)_stim", cluster_key)
            if (
                "stim" in cluster_key
                and match
                and int(match.group(1)) == stim_number
                and "time_period" in cluster_data
            ):
                clusters.append(cluster_data)
    return clusters


def group_clusters_by_time_period(clusters: list[dict]) -> dict[str, list[dict]]:
    """Group clusters into `full`, `day`, and `night` period buckets."""
    return {
        "full": list(clusters),
        "day": [cluster for cluster in clusters if cluster.get("time_period") == "Day"],
        "night": [cluster for cluster in clusters if cluster.get("time_period") == "Night"],
    }


def find_longest_cluster_times(data_dict: dict, cluster_number=None) -> tuple[float, float]:
    """Return the longest pre/post windows across the requested peak clusters."""
    longest_pre_peak = 0.0
    longest_post_peak = 0.0

    for cluster_group in data_dict.values():
        for cluster_name, cluster_data in cluster_group.items():
            if "Peak" not in cluster_name:
                continue
            if cluster_number is not None and (
                f"{cluster_number} Peak" not in cluster_name
                and f"{cluster_number} Peaks" not in cluster_name
            ):
                continue

            peak_time = cluster_data["peaks"][cluster_data["alignment_index"]]
            end_time = float(
                cluster_data["end_time"] + (float(cluster_data["post_cluster_time"]) / 60.0)
            )
            start_time = max(
                0.0,
                float(cluster_data["peaks"][0]) - (float(cluster_data["pre_cluster_time"]) / 60.0),
            )

            longest_pre_peak = max(longest_pre_peak, peak_time - start_time)
            longest_post_peak = max(longest_post_peak, end_time - peak_time)

    return longest_pre_peak, longest_post_peak


def process_cluster_window(
    cluster_data: dict,
    longest_pre_peak: float,
    longest_post_peak: float,
    extended_temp_data: pd.DataFrame,
    extended_act_data: pd.DataFrame,
    is_stim: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Extract aligned temp/activity windows for a single cluster."""
    if is_stim:
        stim_start = cluster_data["stim_start"]
        stim_end = cluster_data["stim_end"]
        universal_start_time = stim_start - longest_pre_peak
        universal_end_time = stim_end + longest_post_peak
        cluster_name = cluster_data.get(
            "name", f"{cluster_data['cluster_size']}_stim_cluster"
        )
        alignment_time = stim_start
    else:
        alignment_time = cluster_data["peaks"][cluster_data["alignment_index"]]
        universal_start_time, universal_end_time = get_universal_times(
            alignment_time, longest_pre_peak, longest_post_peak
        )
        cluster_name = cluster_data["name"]

    truncated_temp_data = extended_temp_data[
        (extended_temp_data["Time (min)"] >= universal_start_time)
        & (extended_temp_data["Time (min)"] <= universal_end_time)
    ].copy()
    truncated_act_data = extended_act_data[
        (extended_act_data["Time (min)"] >= universal_start_time)
        & (extended_act_data["Time (min)"] <= universal_end_time)
    ].copy()

    truncated_temp_data["Time (min)"] -= alignment_time
    truncated_act_data["Time (min)"] -= alignment_time
    truncated_temp_data.reset_index(drop=True, inplace=True)
    truncated_act_data.reset_index(drop=True, inplace=True)
    truncated_temp_data["Cluster Name"] = cluster_name
    truncated_act_data["Cluster Name"] = cluster_name
    return truncated_temp_data, truncated_act_data


def process_data_for_clusters(
    clusters: list[dict],
    longest_pre_peak: float,
    longest_post_peak: float,
    extended_temp_data: pd.DataFrame,
    extended_act_data: pd.DataFrame,
    is_stim: bool = False,
) -> tuple[list[pd.DataFrame], list[pd.DataFrame]]:
    """Extract aligned temp/activity windows for many clusters."""
    all_temp_data = []
    all_act_data = []

    for cluster_data in clusters:
        temp_data, act_data = process_cluster_window(
            cluster_data,
            longest_pre_peak,
            longest_post_peak,
            extended_temp_data,
            extended_act_data,
            is_stim=is_stim,
        )
        all_temp_data.append(temp_data)
        all_act_data.append(act_data)

    return all_temp_data, all_act_data
