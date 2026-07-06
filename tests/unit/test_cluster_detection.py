from __future__ import annotations

import pandas as pd
import pytest

from src.processing.cluster_detection import (
    find_longest_cluster_times,
    group_clusters_by_time_period,
    identify_clusters,
    process_cluster_window,
    select_peak_clusters,
    select_stim_clusters,
)


def test_identify_clusters_merges_nearby_clusters_when_requested():
    time_column = pd.Series([0.0, 0.5, 1.0, 1.5, 2.0, 2.5])
    data_column = pd.Series([0.0, 5.0, 0.0, 5.0, 0.0, 0.0])

    clusters, cluster_dict = identify_clusters(
        time_column,
        data_column,
        peak_indices=[1, 3],
        baseline_multiplier="1",
        adjust_clustering_seconds="45",
    )

    assert clusters == [(1, 4)]
    assert list(cluster_dict) == [(1, 4, 2)]
    assert cluster_dict[(1, 4, 2)]["name"] == "2 Peaks in Cluster_1"


def test_identify_clusters_can_use_full_trace_baseline_reference():
    time_column = pd.Series(range(7), dtype=float)
    trimmed_data = pd.Series([0.0, 0.0, 5.0, 4.0, 5.0, 0.0, 0.0])
    full_trace_reference = pd.Series([4.0, 4.0, 4.0, 4.0, 4.0, 5.0, 5.0])

    _, current_baseline_clusters = identify_clusters(
        time_column,
        trimmed_data,
        peak_indices=[2, 4],
    )
    _, full_baseline_clusters = identify_clusters(
        time_column,
        trimmed_data,
        peak_indices=[2, 4],
        baseline_reference_column=full_trace_reference,
    )

    assert list(current_baseline_clusters) == [(2, 5, 2)]
    assert list(full_baseline_clusters) == [(2, 3, 1), (4, 5, 1)]


def test_process_cluster_window_aligns_temp_and_act_to_peak_time():
    cluster_data = {
        "name": "1 Peak in Cluster_1",
        "peaks": [10.0],
        "alignment_index": 0,
    }
    temp_data = pd.DataFrame({"Time (min)": [9.0, 10.0, 11.0], "Data": [1.0, 2.0, 3.0]})
    act_data = pd.DataFrame({"Time (min)": [9.0, 10.0, 11.0], "Data": [4.0, 5.0, 6.0]})

    truncated_temp, truncated_act = process_cluster_window(
        cluster_data,
        1.0,
        1.0,
        temp_data,
        act_data,
    )

    assert truncated_temp["Time (min)"].tolist() == [-1.0, 0.0, 1.0]
    assert truncated_act["Time (min)"].tolist() == [-1.0, 0.0, 1.0]
    assert truncated_temp["Cluster Name"].tolist() == ["1 Peak in Cluster_1"] * 3


def test_cluster_selection_helpers_cover_peak_stim_and_period_filters():
    peak_cluster = {"name": "1 Peak in Cluster_1", "time_period": "Day"}
    stim_cluster = {"name": "2_stim_cluster_1", "time_period": "Night"}

    peak_clusters = select_peak_clusters({(0, 1, 1): peak_cluster}, 1)
    stim_clusters = select_stim_clusters(
        {"file.csv": {"2_stim_cluster_1": stim_cluster, "3_stim_cluster_1": {}}},
        2,
    )
    grouped = group_clusters_by_time_period([peak_cluster, stim_cluster])

    assert peak_clusters == [peak_cluster]
    assert stim_clusters == [stim_cluster]
    assert grouped["day"] == [peak_cluster]
    assert grouped["night"] == [stim_cluster]


def test_find_longest_cluster_times_matches_existing_window_logic():
    data_dict = {
        "file.csv": {
            "1 Peak in Cluster_1": {
                "peaks": [10.0],
                "alignment_index": 0,
                "end_time": 12.0,
                "pre_cluster_time": "60",
                "post_cluster_time": "120",
            },
            "3 Peaks in Cluster_1": {
                "peaks": [20.0, 21.0, 22.0],
                "alignment_index": 1,
                "end_time": 25.0,
                "pre_cluster_time": "300",
                "post_cluster_time": "600",
            },
        }
    }

    pre_one, post_one = find_longest_cluster_times(data_dict, 1)
    pre_global, post_global = find_longest_cluster_times(data_dict)

    assert pre_one == pytest.approx(1.0)
    assert post_one == pytest.approx(4.0)
    assert pre_global == pytest.approx(6.0)
    assert post_global == pytest.approx(14.0)
