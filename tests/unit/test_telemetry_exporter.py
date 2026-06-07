from __future__ import annotations

import pandas as pd
import pytest

from src.features.telemetry_alignment.exporters.export_frames import (
    build_intercluster_interval_frame,
    build_native_signal_frame,
    get_standardized_native_window_bounds,
)


def test_build_intercluster_interval_frame_orders_photometry_clusters():
    cluster_dict = {
        (10, 20, 2): {
            "name": "2 Peaks in Cluster_2",
            "start_time": 4.0,
            "end_time": 5.0,
            "cluster_duration": 1.0,
            "peaks": [4.2, 4.8],
            "alignment_index": 0,
            "time_period": "Night",
        },
        (0, 5, 1): {
            "name": "1 Peak in Cluster_1",
            "start_time": 1.0,
            "end_time": 1.5,
            "cluster_duration": 0.5,
            "peaks": [1.2],
            "alignment_index": 0,
            "time_period": "Day",
        },
    }

    frame = build_intercluster_interval_frame(cluster_dict, {}, "photometry")

    assert frame["Cluster Name"].tolist() == [
        "1 Peak in Cluster_1",
        "2 Peaks in Cluster_2",
    ]
    assert frame["Cluster Order"].tolist() == [1, 2]
    assert frame.loc[1, "Previous Cluster"] == "1 Peak in Cluster_1"
    assert frame.loc[1, "Interval From Previous End (min)"] == pytest.approx(2.5)
    assert frame.loc[1, "Interval Start-to-Start (min)"] == pytest.approx(3.0)


def test_build_intercluster_interval_frame_uses_stim_timing_metadata():
    file_data = {
        "3_stim_cluster_2": {
            "name": "3_stim_cluster_2",
            "stim_start": 10.0,
            "stim_end": 11.0,
            "cluster_size": 3,
            "time_period": "Night",
        },
        "2_stim_cluster_1": {
            "name": "2_stim_cluster_1",
            "stim_start": 3.0,
            "stim_end": 3.5,
            "cluster_size": 2,
            "time_period": "Day",
        },
    }

    frame = build_intercluster_interval_frame({}, file_data, "stim")

    assert frame["Cluster Name"].tolist() == ["2_stim_cluster_1", "3_stim_cluster_2"]
    assert frame.loc[0, "Alignment Time (min)"] == pytest.approx(3.0)
    assert frame.loc[1, "Interval From Previous End (min)"] == pytest.approx(6.5)


def test_build_native_signal_frame_flattens_native_segments_for_modeling():
    cluster_dict = {
        (0, 5, 1): {
            "name": "1 Peak in Cluster_1",
            "start_time": 1.0,
            "end_time": 1.5,
            "cluster_duration": 0.5,
            "peaks": [1.2],
            "alignment_index": 0,
            "time_period": "Day",
            "pre_cluster_time": "6",
            "post_cluster_time": "12",
        }
    }
    native_segment = pd.DataFrame(
        {
            "Date Time": pd.to_datetime(
                [
                    "2024-01-01 12:00:00",
                    "2024-01-01 12:00:10",
                    "2024-01-01 12:00:20",
                    "2024-01-01 12:00:30",
                ]
            ),
            "Time (min)": [-0.2, -0.1, 0.0, 0.3],
            "Data": [37.1, 37.2, 37.4, 37.7],
            "Cluster Name": [
                "1 Peak in Cluster_1",
                "1 Peak in Cluster_1",
                "1 Peak in Cluster_1",
                "1 Peak in Cluster_1",
            ],
        }
    )
    mean_cluster_data = {
        1: {
            "full": {
                "native_temp_segments": [native_segment],
            }
        }
    }

    frame = build_native_signal_frame(
        mean_cluster_data=mean_cluster_data,
        cluster_dict=cluster_dict,
        file_data={},
        data_type="photometry",
        signal_type="temp",
        window_mode="full_cluster",
    )

    assert frame.columns.tolist() == [
        "Cluster Order",
        "Cluster Name",
        "Cluster Size",
        "Time Period",
        "First Peak Time (min)",
        "Cluster Start Time (min)",
        "Cluster End Time (min)",
        "Window Start (min)",
        "Window End (min)",
        "Sample Index",
        "Relative Time (min)",
        "Absolute Time",
        "Value",
    ]
    assert frame["Cluster Order"].tolist() == [1, 1, 1]
    assert frame["First Peak Time (min)"].tolist() == [pytest.approx(1.2)] * 3
    assert frame["Window Start (min)"].tolist() == [pytest.approx(1.1)] * 3
    assert frame["Window End (min)"].tolist() == [pytest.approx(1.7)] * 3
    assert frame["Sample Index"].tolist() == [1, 2, 3]
    assert frame["Relative Time (min)"].tolist() == [-0.1, 0.0, 0.3]
    assert frame["Value"].tolist() == [37.2, 37.4, 37.7]
    assert list(frame["Absolute Time"]) == list(native_segment["Date Time"].iloc[1:])


def test_build_native_signal_frame_uses_saved_photometry_pre_post_settings():
    cluster_dict = {
        (0, 5, 1): {
            "name": "1 Peak in Cluster_1",
            "start_time": 165.026667,
            "end_time": 169.746663,
            "cluster_duration": 4.719996,
            "peaks": [166.408333],
            "alignment_index": 0,
            "time_period": "Day",
        }
    }
    file_data = {
        "1 Peak in Cluster_1": {
            "pre_cluster_time": "600",
            "post_cluster_time": "1200",
        }
    }
    native_segment = pd.DataFrame(
        {
            "Date Time": pd.to_datetime(
                [
                    "2024-01-01 12:00:00",
                    "2024-01-01 12:00:10",
                ]
            ),
            "Time (min)": [0.0, 0.1666667],
            "Data": [37.1, 37.2],
            "Cluster Name": [
                "1 Peak in Cluster_1",
                "1 Peak in Cluster_1",
            ],
        }
    )
    mean_cluster_data = {
        1: {
            "full": {
                "native_temp_segments": [native_segment],
            }
        }
    }

    frame = build_native_signal_frame(
        mean_cluster_data=mean_cluster_data,
        cluster_dict=cluster_dict,
        file_data=file_data,
        data_type="photometry",
        signal_type="temp",
        window_mode="full_cluster",
    )

    assert frame["Window Start (min)"].tolist() == [pytest.approx(156.408333)] * 2
    assert frame["Window End (min)"].tolist() == [pytest.approx(189.746663)] * 2


def test_build_native_signal_frame_supports_fixed_window_trimming():
    cluster_dict = {
        (0, 5, 1): {
            "name": "1 Peak in Cluster_1",
            "start_time": 1.0,
            "end_time": 1.5,
            "cluster_duration": 0.5,
            "peaks": [1.2],
            "alignment_index": 0,
            "time_period": "Day",
            "pre_cluster_time": "6",
            "post_cluster_time": "12",
        },
        (10, 18, 2): {
            "name": "2 Peaks in Cluster_1",
            "start_time": 2.0,
            "end_time": 2.8,
            "cluster_duration": 0.8,
            "peaks": [2.1, 2.4],
            "alignment_index": 1,
            "time_period": "Day",
            "pre_cluster_time": "6",
            "post_cluster_time": "12",
        },
    }
    native_segment = pd.DataFrame(
        {
            "Date Time": pd.to_datetime(
                [
                    "2024-01-01 12:00:00",
                    "2024-01-01 12:00:10",
                    "2024-01-01 12:00:20",
                    "2024-01-01 12:00:30",
                ]
            ),
            "Time (min)": [-0.2, -0.1, 0.0, 0.3],
            "Data": [10, 20, 30, 40],
            "Cluster Name": [
                "1 Peak in Cluster_1",
                "1 Peak in Cluster_1",
                "1 Peak in Cluster_1",
                "1 Peak in Cluster_1",
            ],
        }
    )
    longer_segment = pd.DataFrame(
        {
            "Date Time": pd.to_datetime(
                [
                    "2024-01-01 13:00:00",
                    "2024-01-01 13:00:06",
                    "2024-01-01 13:00:12",
                    "2024-01-01 13:00:18",
                    "2024-01-01 13:00:24",
                    "2024-01-01 13:00:30",
                    "2024-01-01 13:00:36",
                    "2024-01-01 13:00:42",
                ]
            ),
            "Time (min)": [-0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3, 0.4],
            "Data": [5, 10, 15, 20, 25, 30, 35, 40],
            "Cluster Name": [
                "2 Peaks in Cluster_1",
                "2 Peaks in Cluster_1",
                "2 Peaks in Cluster_1",
                "2 Peaks in Cluster_1",
                "2 Peaks in Cluster_1",
                "2 Peaks in Cluster_1",
                "2 Peaks in Cluster_1",
                "2 Peaks in Cluster_1",
            ],
        }
    )
    mean_cluster_data = {
        1: {"full": {"native_act_segments": [native_segment]}},
        2: {"full": {"native_act_segments": [longer_segment]}},
    }

    frame = build_native_signal_frame(
        mean_cluster_data=mean_cluster_data,
        cluster_dict=cluster_dict,
        file_data={},
        data_type="photometry",
        signal_type="act",
        window_mode="fixed_window",
    )

    cluster_one = frame[frame["Cluster Name"] == "1 Peak in Cluster_1"].reset_index(drop=True)
    cluster_two = frame[frame["Cluster Name"] == "2 Peaks in Cluster_1"].reset_index(drop=True)

    assert "Padded" not in frame.columns
    assert cluster_one["First Peak Time (min)"].tolist() == [pytest.approx(1.2)] * len(cluster_one)
    assert cluster_two["First Peak Time (min)"].tolist() == [pytest.approx(2.1)] * len(cluster_two)
    assert cluster_one["Relative Time (min)"].tolist() == [
        pytest.approx(-0.1),
        pytest.approx(0.0),
        pytest.approx(0.1),
        pytest.approx(0.2),
        pytest.approx(0.3),
        pytest.approx(0.4),
        pytest.approx(0.5),
        pytest.approx(0.6),
        pytest.approx(0.7),
        pytest.approx(0.8),
        pytest.approx(0.9),
    ]
    assert cluster_one["Window Start (min)"].tolist() == [pytest.approx(1.1)] * len(cluster_one)
    assert cluster_one["Window End (min)"].tolist() == [pytest.approx(1.7)] * len(cluster_one)
    assert cluster_two["Window Start (min)"].tolist() == [pytest.approx(2.0)] * len(cluster_two)
    assert cluster_two["Window End (min)"].tolist() == [pytest.approx(3.0)] * len(cluster_two)
    assert cluster_one["Value"].iloc[0] == 20.0
    assert cluster_one["Value"].iloc[1] == 30.0
    assert cluster_one["Absolute Time"].iloc[0] == pd.Timestamp("2024-01-01 12:00:10")
    assert cluster_one["Absolute Time"].iloc[1] == pd.Timestamp("2024-01-01 12:00:20")
    assert pd.isna(cluster_one["Value"].iloc[2])
    assert pd.isna(cluster_one["Value"].iloc[3])
    assert cluster_one["Value"].iloc[4] == 40.0
    assert cluster_one["Value"].notna().sum() == 3
    assert cluster_one["Value"].isna().sum() == 8
    assert cluster_two["Value"].notna().sum() >= 1


def test_get_standardized_native_window_bounds_uses_longest_cluster_duration():
    cluster_dict = {
        (0, 5, 1): {
            "name": "1 Peak in Cluster_1",
            "start_time": 1.0,
            "end_time": 1.5,
            "cluster_duration": 0.5,
            "peaks": [1.2],
            "alignment_index": 0,
            "time_period": "Day",
            "pre_cluster_time": "6",
            "post_cluster_time": "12",
        },
        (10, 18, 2): {
            "name": "2 Peaks in Cluster_1",
            "start_time": 2.0,
            "end_time": 2.8,
            "cluster_duration": 0.8,
            "peaks": [2.1, 2.4],
            "alignment_index": 1,
            "time_period": "Day",
            "pre_cluster_time": "6",
            "post_cluster_time": "12",
        },
    }

    window_start, window_end = get_standardized_native_window_bounds(
        cluster_dict=cluster_dict,
        file_data={},
        data_type="photometry",
        window_mode="fixed_window",
    )

    assert window_start == pytest.approx(-0.1)
    assert window_end == pytest.approx(0.9)
