"""Tests for src/processing/behavior_metrics.py — currently 0% covered."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.processing.behavior_metrics import (
    calculate_auc,
    calculate_duration_metrics,
    calculate_max_amp,
    calculate_mean_dff,
    calculate_mean_sem,
    calculate_metrics_for_bins,
    compute_z_score,
    convert_time,
    generate_mean_sem_df,
    get_time_scale,
)


class TestCalculateAuc:
    def test_flat_signal_with_known_area(self):
        result = calculate_auc([2.0, 2.0, 2.0, 2.0, 2.0], dx=0.1)
        assert result == pytest.approx(0.8, rel=1e-3)

    def test_triangular_ramp(self):
        # Simpson's rule on [0, 1, 0] with dx=1: h/3*(f0+4f1+f2) = 1/3*(0+4+0) = 4/3
        result = calculate_auc([0.0, 1.0, 0.0], dx=1.0)
        assert result == pytest.approx(4 / 3, rel=1e-3)

    def test_accepts_numpy_array(self):
        result = calculate_auc(np.array([1.0, 2.0, 1.0]), dx=0.5)
        assert isinstance(result, float)

    def test_negative_signal_gives_negative_area(self):
        result = calculate_auc([-1.0, -1.0, -1.0], dx=1.0)
        assert result < 0


class TestCalculateMaxAmp:
    def test_returns_maximum(self):
        assert calculate_max_amp([1.0, 5.0, 3.0]) == pytest.approx(5.0)

    def test_empty_array_returns_nan(self):
        assert np.isnan(calculate_max_amp([]))

    def test_handles_numpy_input(self):
        assert calculate_max_amp(np.array([2.0, 4.0])) == pytest.approx(4.0)

    def test_ignores_nan_values(self):
        assert calculate_max_amp([float("nan"), 3.0, 1.0]) == pytest.approx(3.0)

    def test_single_element(self):
        assert calculate_max_amp([7.0]) == pytest.approx(7.0)


class TestCalculateMeanDff:
    def test_simple_mean(self):
        assert calculate_mean_dff([1.0, 3.0]) == pytest.approx(2.0)

    def test_skips_nan(self):
        assert calculate_mean_dff([1.0, float("nan"), 3.0]) == pytest.approx(2.0)

    def test_single_value(self):
        assert calculate_mean_dff([5.0]) == pytest.approx(5.0)

    def test_all_zeros(self):
        assert calculate_mean_dff([0.0, 0.0, 0.0]) == pytest.approx(0.0)


class TestCalculateDurationMetrics:
    def test_single_event_zero_sem(self):
        mean, sem = calculate_duration_metrics([0.0], [60.0])
        assert mean == pytest.approx(1.0)
        assert sem == 0.0

    def test_two_events_computes_mean_and_sem(self):
        mean, sem = calculate_duration_metrics([0.0, 0.0], [60.0, 120.0])
        assert mean == pytest.approx(1.5)
        assert sem > 0

    def test_none_end_times_skipped(self):
        mean, sem = calculate_duration_metrics([0.0, 0.0], [60.0, None])
        assert mean == pytest.approx(1.0)

    def test_nan_end_times_skipped(self):
        mean, sem = calculate_duration_metrics([0.0, 0.0], [60.0, np.nan])
        assert mean == pytest.approx(1.0)
        assert sem == 0.0

    def test_all_none_end_times_returns_nan(self):
        mean, sem = calculate_duration_metrics([0.0], [None])
        assert np.isnan(mean) and np.isnan(sem)

    def test_all_nan_end_times_returns_nan(self):
        mean, sem = calculate_duration_metrics([0.0], [np.nan])
        assert np.isnan(mean) and np.isnan(sem)

    def test_three_events_correct_mean(self):
        mean, _ = calculate_duration_metrics([0.0, 0.0, 0.0], [60.0, 120.0, 180.0])
        assert mean == pytest.approx(2.0)


class TestCalculateMeanSem:
    def test_single_column_returns_zero_sem(self):
        df = pd.DataFrame({"Time": [0.0, 1.0], "A": [2.0, 4.0]})
        result = calculate_mean_sem(df, "Time")
        assert result["SEM"].tolist() == [0.0, 0.0]
        assert result["Mean"].tolist() == [2.0, 4.0]

    def test_two_columns_computes_mean_and_sem(self):
        df = pd.DataFrame({"Time": [0.0], "A": [1.0], "B": [3.0]})
        result = calculate_mean_sem(df, "Time")
        assert result["Mean"].tolist() == [pytest.approx(2.0)]
        assert result["SEM"].tolist()[0] > 0

    def test_time_column_preserved_in_output(self):
        df = pd.DataFrame({"Time": [0.0, 0.5], "A": [1.0, 2.0], "B": [3.0, 4.0]})
        result = calculate_mean_sem(df, "Time")
        assert result["Time"].tolist() == [0.0, 0.5]

    def test_result_has_expected_columns(self):
        df = pd.DataFrame({"Time": [0.0], "X": [1.0], "Y": [2.0]})
        result = calculate_mean_sem(df, "Time")
        assert set(result.columns) == {"Time", "Mean", "SEM"}


class TestGenerateMeanSemDf:
    def test_builds_correct_time_axis_length(self):
        data = {"Instance_1": [1.0, 2.0, 3.0], "Instance_2": [3.0, 4.0, 5.0]}
        result = generate_mean_sem_df(data, [0, 1, 2], 0.0, 2.0)
        assert len(result) == 3
        assert result["Time"].tolist() == pytest.approx([0.0, 1.0, 2.0])

    def test_single_instance_zero_sem(self):
        data = {"Instance_1": [1.0, 2.0]}
        result = generate_mean_sem_df(data, [0, 1], 0.0, 1.0)
        assert result["SEM"].tolist() == [0.0, 0.0]

    def test_mean_is_average_across_instances(self):
        data = {"A": [2.0, 4.0], "B": [4.0, 6.0]}
        result = generate_mean_sem_df(data, [0, 1], 0.0, 1.0)
        assert result["Mean"].tolist() == pytest.approx([3.0, 5.0])

    def test_negative_time_range(self):
        data = {"A": [1.0, 2.0, 3.0]}
        result = generate_mean_sem_df(data, [0, 1, 2], -1.0, 1.0)
        assert result["Time"].iloc[0] == pytest.approx(-1.0)
        assert result["Time"].iloc[-1] == pytest.approx(1.0)


class TestCalculateMetricsForBins:
    def test_averages_across_instances_per_bin(self):
        instances = [[[1.0], [3.0]], [[3.0], [5.0]]]
        result = calculate_metrics_for_bins(instances, 2, "mean", np.mean)
        assert result[0] == pytest.approx(2.0)
        assert result[1] == pytest.approx(4.0)

    def test_single_instance_single_bin(self):
        instances = [[[2.0, 4.0]]]
        result = calculate_metrics_for_bins(instances, 1, "mean", np.mean)
        assert result[0] == pytest.approx(3.0)

    def test_auc_metric_name_unwraps_list_results(self):
        def list_metric(d):
            return [float(np.sum(d))]

        instances = [[[1.0, 2.0]]]
        result = calculate_metrics_for_bins(instances, 1, "auc", list_metric)
        assert result[0] == pytest.approx(3.0)

    def test_returns_list_of_expected_length(self):
        instances = [[[1.0], [2.0], [3.0]]]
        result = calculate_metrics_for_bins(instances, 3, "mean", np.mean)
        assert len(result) == 3


class TestComputeZScore:
    def test_baseline_mean_and_std_computed(self):
        df = pd.DataFrame(
            {
                "Time": [0.0, 1.0, 2.0, 3.0, 4.0],
                "Signal": [10.0, 12.0, 20.0, 30.0, 40.0],
            }
        )
        _, _, mean, std = compute_z_score(df, "Signal", 0.0, 2.0)
        assert mean == pytest.approx(11.0)
        assert std == pytest.approx(1.0)

    def test_z_time_starts_at_zero(self):
        df = pd.DataFrame(
            {"Time": [0.0, 1.0, 2.0, 3.0], "Signal": [5.0, 6.0, 5.0, 6.0]}
        )
        _, z_time, _, _ = compute_z_score(df, "Signal", 1.0, 2.0)
        assert z_time.iloc[0] == pytest.approx(0.0)

    def test_output_lengths_match(self):
        df = pd.DataFrame({"Time": [0.0, 1.0, 2.0], "Signal": [1.0, 2.0, 3.0]})
        z_data, z_time, _, _ = compute_z_score(df, "Signal", 0.0, 1.5)
        assert len(z_data) == len(z_time)

    def test_returns_four_values(self):
        df = pd.DataFrame({"Time": [0.0, 1.0, 2.0], "Signal": [1.0, 2.0, 3.0]})
        result = compute_z_score(df, "Signal", 0.0, 1.5)
        assert len(result) == 4


class TestConvertTime:
    def test_seconds_passthrough(self):
        assert convert_time("seconds", 120.0) == pytest.approx(120.0)

    def test_to_minutes(self):
        assert convert_time("minutes", 120.0) == pytest.approx(2.0)

    def test_to_hours(self):
        assert convert_time("hours", 3600.0) == pytest.approx(1.0)

    def test_unknown_unit_returns_seconds_value(self):
        assert convert_time("unknown", 60.0) == pytest.approx(60.0)

    def test_zero_input(self):
        assert convert_time("minutes", 0.0) == pytest.approx(0.0)


class TestGetTimeScale:
    def test_hours(self):
        assert get_time_scale("hours") == pytest.approx(1.0 / 60.0)

    def test_minutes(self):
        assert get_time_scale("minutes") == pytest.approx(1.0)

    def test_seconds(self):
        assert get_time_scale("seconds") == pytest.approx(60.0)

    def test_unknown_defaults_to_minutes(self):
        assert get_time_scale("unknown") == pytest.approx(1.0)
