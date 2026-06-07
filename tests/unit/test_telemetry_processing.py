from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from src.processing.telemetry_processing import (
    apply_cluster_binning,
    build_aligned_photometry_cluster_data,
    calculate_mean_and_sem,
    calculate_nighttime_periods,
    calculate_stim_timings,
    create_universal_time_axis,
    extract_and_trim_data,
    extract_data_with_buffer,
    process_photometry_data,
    trim_data_to_minimum_length,
    upsample_telemetry_data,
)


def test_calculate_nighttime_periods_caps_to_recording_end():
    periods = calculate_nighttime_periods(
        date(2024, 1, 1),
        "18:00:00",
        "19:00:00",
        duration_minutes=120,
    )

    assert periods == [(pd.to_datetime("19:00:00").time(), pd.to_datetime("20:00:00").time())]


def test_calculate_stim_timings_uses_recording_start():
    stim_df = pd.DataFrame(
        {
            "Cluster size (num)": [3],
            "Stim duration (sec)": [10],
            "Interstim interval (sec)": [20],
            "Stim onset (hh:mm:ss)": [pd.to_timedelta("00:02:00")],
        }
    )

    stim_timings = calculate_stim_timings(stim_df, "00:01:00")

    assert stim_timings == [
        (
            3,
            [
                pytest.approx((1.0, 1.1666666667)),
                pytest.approx((1.5, 1.6666666667)),
                pytest.approx((2.0, 2.1666666667)),
            ],
        )
    ]


def test_extract_and_trim_data_builds_relative_time_axis():
    dataframe = pd.DataFrame(
        {
            "Date Time": [
                "2024-01-01 12:00:00",
                "2024-01-01 12:00:10",
                "2024-01-01 12:00:20",
                "2024-01-01 12:00:30",
                "2024-01-01 12:00:40",
            ],
            "Data": [1, 2, 3, 4, 5],
        }
    )

    trimmed = extract_and_trim_data(
        dataframe,
        previous_time="12:00:00",
        offset=1 / 6,
        duration=0.5,
        sample_rate=10,
    )

    assert trimmed["Data"].tolist() == [2, 3, 4]
    assert trimmed["Time (min)"].tolist() == [0.0, pytest.approx(1 / 6), pytest.approx(2 / 6)]


def test_extract_data_with_buffer_uses_existing_offset_column():
    dataframe = pd.DataFrame(
        {
            "Offset": [pd.Timedelta(minutes=2), pd.Timedelta(minutes=2)],
            "Data": [1, 2],
        }
    )

    buffered = extract_data_with_buffer(dataframe, offset=2, sample_rate=30)

    assert buffered["Time (min)"].tolist() == [-2.0, -1.5]


def test_extract_data_with_buffer_falls_back_to_previous_time_and_duration():
    dataframe = pd.DataFrame(
        {
            "Date Time": [
                "2024-01-01 12:00:00",
                "2024-01-01 12:00:10",
                "2024-01-01 12:00:20",
                "2024-01-01 12:00:30",
                "2024-01-01 12:00:40",
            ],
            "Data": [1, 2, 3, 4, 5],
        }
    )

    buffered = extract_data_with_buffer(
        dataframe,
        offset=1 / 6,
        sample_rate=10,
        previous_time="12:00:00",
        duration=0.5,
    )

    assert buffered["Data"].tolist() == [1, 2, 3, 4]
    assert buffered["Time (min)"].tolist() == [
        pytest.approx(-1 / 6),
        0.0,
        pytest.approx(1 / 6),
        pytest.approx(2 / 6),
    ]


def test_upsample_telemetry_data_accepts_date_time_column_only():
    dataframe = pd.DataFrame(
        {
            "Date Time": [
                "2024-01-01 12:00:00.000",
                "2024-01-01 12:00:01.000",
            ],
            "Data": [1.0, 3.0],
        }
    )

    upsampled = upsample_telemetry_data(dataframe)

    assert "DateTime" in upsampled.columns
    assert "Offset" in upsampled.columns
    assert upsampled.iloc[0]["Data"] == pytest.approx(1.0)


def test_calculate_mean_and_sem_and_trim_helpers_are_pure_dataframe_ops():
    aligned = pd.DataFrame(
        {
            "Time (s)": [0, 1],
            "Cluster A": [1.0, 3.0],
            "Cluster B": [3.0, 5.0],
        }
    )

    result = calculate_mean_and_sem(aligned)
    trimmed = trim_data_to_minimum_length(
        [
            pd.DataFrame({"x": [1, 2, 3]}),
            pd.DataFrame({"x": [1, 2]}),
        ]
    )

    assert result["Mean"].tolist() == [2.0, 4.0]
    assert result["SEM"].tolist()[0] == pytest.approx(1.0)
    assert len(trimmed[0]) == 2
    assert len(trimmed[1]) == 2
    assert create_universal_time_axis(-10, 10, 10).tolist() == [-10, 0, 10]


def test_process_photometry_data_and_alignment_builder_create_common_axis():
    dataframe = pd.DataFrame(
        {
            "Time (min)": [0.0, 0.00167, 0.00334, 0.00501],
            "Signal": [1.0, 2.0, 3.0, 4.0],
        }
    )

    processed = process_photometry_data(dataframe.copy())
    aligned = build_aligned_photometry_cluster_data(
        dataframe=dataframe,
        data_column="Signal",
        clusters_by_period={
            "full": [
                {
                    "name": "1 Peak in Cluster_1",
                    "peaks": [0.00167],
                    "alignment_index": 0,
                }
            ],
            "day": [],
            "night": [],
        },
        longest_pre_peak=0.00167,
        longest_post_peak=0.00167,
        extra_buffer=0.0,
        step_size=0.00167,
    )

    assert not processed.empty
    assert aligned["full"]["Clusters"] is not None
    assert aligned["full"]["Clusters"].columns.tolist() == [
        "Time (min)",
        "1 Peak in Cluster_1",
    ]


def test_apply_cluster_binning_uses_saved_bin_sizes():
    mean_cluster_data = {
        1: {
            "full": {
                "mean_temp_data": pd.DataFrame(
                    {
                        "Time (s)": [0, 10, 20],
                        "Mean": [1.0, 2.0, 3.0],
                        "SEM": [0.1, 0.2, 0.3],
                    }
                ),
                "mean_act_data": pd.DataFrame(
                    {
                        "Time (s)": [0, 10, 20],
                        "Mean": [4.0, 5.0, 6.0],
                        "SEM": [0.4, 0.5, 0.6],
                    }
                ),
            },
            "day": {},
            "night": {},
        }
    }

    apply_cluster_binning(
        mean_cluster_data,
        {"1 Peak in Cluster_1": {"bin_size": "10"}},
    )

    assert "binned_mean_temp_data" in mean_cluster_data[1]["full"]
    assert "binned_mean_act_data" in mean_cluster_data[1]["full"]
