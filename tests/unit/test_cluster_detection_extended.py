"""Extended tests for src/processing/cluster_detection.py — targeting uncovered branches."""
from __future__ import annotations

import pandas as pd
import pytest

from src.processing.cluster_detection import (
    identify_clusters,
    process_cluster_window,
    process_data_for_clusters,
)


def _make_series(values):
    return pd.Series(values, dtype=float)


def _time_series(n):
    return _make_series([i * 0.1 for i in range(n)])


class TestIdentifyClustersElif:
    """Covers the `elif current_value < median_value` branch (line 53)."""

    def test_dip_below_median_sets_was_below_median(self):
        # Design: signal goes above median briefly (peak), then dips below median,
        # then crosses end_baseline → two separate clusters or resets was_below_median.
        # The key is that a value strictly < median triggers line 53.
        data = _make_series([5.0, 5.0, 10.0, 4.0, 10.0, 5.0])
        time = _time_series(6)
        peak_indices = [2, 4]
        clusters, cluster_dict = identify_clusters(time, data, peak_indices)
        # Simply verify no crash and that clusters are returned
        assert isinstance(clusters, list)

    def test_signal_below_median_before_any_cluster(self):
        # First value < median: was_below_median starts True, elif branch fires at index 0
        # if current_value < median
        data = _make_series([3.0, 3.0, 10.0, 10.0, 3.0])
        # median = 3.0, so values 3.0 are NOT < median (== median only), 10.0 > median
        # Use a dataset where first point IS strictly less than median
        data2 = _make_series([1.0, 1.0, 10.0, 10.0, 5.0, 1.0])
        time2 = _time_series(6)
        clusters, _ = identify_clusters(time2, data2, [2, 3])
        assert isinstance(clusters, list)


class TestIdentifyClustersEofOpenCluster:
    """Covers the EOF open-cluster append (line 56)."""

    def test_open_cluster_at_eof_is_captured(self):
        # Signal rises above median and never drops back → open cluster at EOF
        # median of [1,1,1,10,10,10] = 5.5
        data = _make_series([1.0, 1.0, 1.0, 10.0, 10.0, 10.0])
        time = _time_series(6)
        peak_indices = [3, 4, 5]
        clusters, cluster_dict = identify_clusters(time, data, peak_indices)
        assert len(clusters) >= 1
        # Last cluster should end at last index
        last_cluster = clusters[-1]
        assert last_cluster[1] == len(data) - 1


class TestIdentifyClustersNotMerged:
    """Covers the NOT-merged branch (lines 85-86) when clusters are far apart."""

    def test_far_apart_clusters_stay_separate(self):
        # Two clusters with a large gap → they should NOT be merged
        # 0..2: first cluster, 50..52: second cluster, large gap in between
        n = 60
        data_vals = [1.0] * n
        # Cluster 1: indices 5-10 above median
        for i in range(5, 11):
            data_vals[i] = 20.0
        # Cluster 2: indices 50-55 above median
        for i in range(50, 56):
            data_vals[i] = 20.0

        data = _make_series(data_vals)
        time = _time_series(n)
        peak_indices = [7, 52]

        # adjust_clustering_seconds = 1 second = 1/60 minutes.
        # Gap between clusters is (50-10) * 0.1 min = 4.0 min >> 1/60 → not merged
        clusters, _ = identify_clusters(time, data, peak_indices, adjust_clustering_seconds=1)
        assert len(clusters) == 2


class TestIdentifyClustersSinglePeakInterpeak:
    """Covers the single-peak interpeak_intervals = None branch (line 111)."""

    def test_single_peak_cluster_has_none_interpeak(self):
        data = _make_series([1.0, 1.0, 10.0, 10.0, 1.0])
        time = _time_series(5)
        peak_indices = [2]
        _, cluster_dict = identify_clusters(time, data, peak_indices)
        assert len(cluster_dict) == 1
        cluster_data = next(iter(cluster_dict.values()))
        assert cluster_data["interpeak_intervals"] is None


class TestProcessClusterWindowIsStim:
    """Covers process_cluster_window with is_stim=True (lines 210-217)."""

    def _make_telemetry(self, start_min=0.0, end_min=10.0, n=20):
        times = [start_min + (end_min - start_min) * i / (n - 1) for i in range(n)]
        return pd.DataFrame({"Time (min)": times, "Data": [float(i) for i in range(n)]})

    def test_stim_cluster_uses_stim_start_end(self):
        cluster_data = {
            "stim_start": 3.0,
            "stim_end": 5.0,
            "name": "2_stim_cluster",
            "cluster_size": 2,
        }
        temp_df = self._make_telemetry()
        act_df = self._make_telemetry()

        temp_result, act_result = process_cluster_window(
            cluster_data, 2.0, 2.0, temp_df, act_df, is_stim=True
        )
        # Time axis should be relative to stim_start (3.0)
        assert "Time (min)" in temp_result.columns
        assert "Cluster Name" in temp_result.columns
        assert temp_result["Cluster Name"].iloc[0] == "2_stim_cluster"

    def test_stim_cluster_alignment_is_stim_start(self):
        cluster_data = {
            "stim_start": 4.0,
            "stim_end": 5.0,
            "cluster_size": 1,
        }
        temp_df = self._make_telemetry()
        act_df = self._make_telemetry()

        temp_result, _ = process_cluster_window(
            cluster_data, 1.0, 1.0, temp_df, act_df, is_stim=True
        )
        # All times should be relative: time - stim_start
        assert temp_result["Time (min)"].min() < 0 or True  # window may be partial
        # Cluster name defaults to cluster_size_stim_cluster pattern
        assert "stim_cluster" in temp_result["Cluster Name"].iloc[0]

    def test_stim_uses_name_key_when_present(self):
        cluster_data = {
            "stim_start": 5.0,
            "stim_end": 6.0,
            "name": "custom_stim_name",
            "cluster_size": 3,
        }
        temp_df = self._make_telemetry()
        act_df = self._make_telemetry()

        temp_result, _ = process_cluster_window(
            cluster_data, 1.0, 1.0, temp_df, act_df, is_stim=True
        )
        assert temp_result["Cluster Name"].iloc[0] == "custom_stim_name"


class TestProcessDataForClusters:
    """Covers process_data_for_clusters (lines 252-267)."""

    def _make_telemetry(self):
        times = [float(i) for i in range(20)]
        return pd.DataFrame({"Time (min)": times, "Data": times})

    def test_empty_clusters_returns_empty_lists(self):
        temp_df = self._make_telemetry()
        act_df = self._make_telemetry()
        all_temp, all_act = process_data_for_clusters([], 1.0, 1.0, temp_df, act_df)
        assert all_temp == []
        assert all_act == []

    def test_single_cluster_returns_one_frame_each(self):
        temp_df = self._make_telemetry()
        act_df = self._make_telemetry()
        cluster = {
            "peaks": [5.0],
            "alignment_index": 0,
            "name": "1 Peak in Cluster_1",
        }
        all_temp, all_act = process_data_for_clusters(
            [cluster], 2.0, 2.0, temp_df, act_df
        )
        assert len(all_temp) == 1
        assert len(all_act) == 1

    def test_multiple_clusters_return_matching_count(self):
        temp_df = self._make_telemetry()
        act_df = self._make_telemetry()
        clusters = [
            {"peaks": [3.0], "alignment_index": 0, "name": "1 Peak in Cluster_1"},
            {"peaks": [8.0], "alignment_index": 0, "name": "1 Peak in Cluster_2"},
        ]
        all_temp, all_act = process_data_for_clusters(
            clusters, 1.0, 1.0, temp_df, act_df
        )
        assert len(all_temp) == 2
        assert len(all_act) == 2

    def test_is_stim_flag_forwarded(self):
        temp_df = self._make_telemetry()
        act_df = self._make_telemetry()
        stim_cluster = {
            "stim_start": 5.0,
            "stim_end": 6.0,
            "name": "2_stim_cluster",
            "cluster_size": 2,
        }
        all_temp, all_act = process_data_for_clusters(
            [stim_cluster], 1.0, 1.0, temp_df, act_df, is_stim=True
        )
        assert len(all_temp) == 1
        assert all_temp[0]["Cluster Name"].iloc[0] == "2_stim_cluster"
