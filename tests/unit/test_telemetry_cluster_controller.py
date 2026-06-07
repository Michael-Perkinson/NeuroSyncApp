from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import pytest

from src.features.telemetry_alignment.services.cluster_analysis import (
    TelemetryClusterService,
)


def test_find_longest_times_supports_global_and_per_cluster_windows():
    app = SimpleNamespace(
        data_dict={
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
    )
    controller = TelemetryClusterService(app)

    pre_one, post_one = controller.find_longest_times(1)
    pre_global, post_global = controller.find_longest_times()

    assert pre_one == pytest.approx(1.0)
    assert post_one == pytest.approx(4.0)
    assert pre_global == pytest.approx(6.0)
    assert post_global == pytest.approx(14.0)


def test_extract_and_prepare_temp_and_act_data_uses_global_window_only_for_native_segments():
    cluster_entry = {
        "name": "1 Peak in Cluster_1",
        "time_period": "Day",
        "peaks": [10.0],
        "alignment_index": 0,
        "end_time": 12.0,
    }
    calls: list[tuple[float, float]] = []
    aligned_frame = pd.DataFrame({"Time (s)": [0, 10], "cluster": [1.0, 2.0]})

    app = SimpleNamespace(
        cluster_dict={(0, 1, 1): cluster_entry},
        process_data_for_clusters=lambda clusters, pre, post: (
            calls.append((pre, post))
            or (
                [pd.DataFrame({"Time (min)": [0.0], "Data": [1.0], "Cluster Name": ["1 Peak in Cluster_1"]})],
                [pd.DataFrame({"Time (min)": [0.0], "Data": [2.0], "Cluster Name": ["1 Peak in Cluster_1"]})],
            )
        ),
        create_universal_time_axis=lambda start, end, sample_rate: [start, end],
        temp_sample_rate=10.0,
        act_sample_rate=10.0,
        trim_data_to_minimum_length=lambda data: data,
        align_and_concatenate_data=lambda all_data, universal_time_axis: aligned_frame.copy(),
        calculate_mean_and_sem=lambda dataframe: dataframe.assign(Mean=1.0, SEM=0.0),
    )
    controller = TelemetryClusterService(app)

    processed_data, raw_data, native_data = controller.extract_and_prepare_temp_and_act_data(
        1.0,
        4.0,
        1,
        6.0,
        14.0,
    )

    assert calls == [(6.0, 14.0), (1.0, 4.0), (6.0, 14.0), (1.0, 4.0)]
    assert len(native_data["full"]["temp"]) == 1
    assert len(native_data["day"]["temp"]) == 1
    assert processed_data["full"]["temp"]["Mean"].iloc[0] == pytest.approx(1.0)
    assert raw_data["full"]["temp"].equals(aligned_frame)
