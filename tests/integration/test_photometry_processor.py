"""
Integration tests for PhotometryRawProcessor.

These tests load the example CSV and verify the processing pipeline produces
the same numeric output as before the refactor. Values were captured from
the v0-pre-refactor tag.
"""
import pytest
import numpy as np
from pathlib import Path

from src.processing.raw_photometry_processing import PhotometryRawProcessor, butter_lowpass_filter

EXAMPLE_CSV = Path(__file__).parent.parent.parent / "example_data" / "photometry_behaviour" / "example_Data ST5435.csv"

TIME_COL = "# t_min"
COL_405 = "405"
COL_465 = "465"


@pytest.fixture(scope="module")
def processor():
    proc = PhotometryRawProcessor(file_path=str(EXAMPLE_CSV))
    t, s405, s465 = proc.load_data_to_numpy(TIME_COL, COL_405, COL_465)
    proc.time_seconds = t
    proc.signal_405 = s405
    proc.signal_465 = s465
    return proc


@pytest.fixture(scope="module")
def filtered_signals(processor):
    return processor.prepare_filtered_signals()


class TestLoadDataToNumpy:
    def test_array_length(self, processor):
        assert len(processor.time_seconds) == 84091

    def test_time_start_end(self, processor):
        assert processor.time_seconds[0] == pytest.approx(0.0)
        assert processor.time_seconds[-1] == pytest.approx(140.15, rel=1e-3)

    def test_signal_405_stats(self, processor):
        assert processor.signal_405.mean() == pytest.approx(0.266622, rel=1e-3)
        assert processor.signal_405.std() == pytest.approx(0.015379, rel=1e-3)

    def test_signal_465_stats(self, processor):
        assert processor.signal_465.mean() == pytest.approx(0.751548, rel=1e-3)
        assert processor.signal_465.std() == pytest.approx(0.279094, rel=1e-3)

    def test_missing_column_raises(self):
        proc = PhotometryRawProcessor(file_path=str(EXAMPLE_CSV))
        with pytest.raises(ValueError, match="missing"):
            proc.load_data_to_numpy("nonexistent", "405", "465")

    def test_returns_numpy_arrays(self, processor):
        assert isinstance(processor.time_seconds, np.ndarray)
        assert isinstance(processor.signal_405, np.ndarray)
        assert isinstance(processor.signal_465, np.ndarray)


class TestPrepareFilteredSignals:
    def test_output_keys(self, filtered_signals):
        expected_keys = {
            "filtered_adjusted_405",
            "smooth_adjusted_405_opt1",
            "smooth_adjusted_405_opt2",
            "smooth_adjusted_405_opt3",
            "smooth_adjusted_405_opt4",
            "smooth_signal_465",
        }
        assert set(filtered_signals.keys()) == expected_keys

    def test_smooth_465_length(self, processor, filtered_signals):
        assert len(filtered_signals["smooth_signal_465"]) == len(processor.time_seconds)

    def test_smooth_465_mean(self, filtered_signals):
        assert filtered_signals["smooth_signal_465"].mean() == pytest.approx(0.75155, rel=1e-3)

    def test_smooth_465_std(self, filtered_signals):
        assert filtered_signals["smooth_signal_465"].std() == pytest.approx(0.278059, rel=1e-3)

    def test_smooth_465_first_value(self, filtered_signals):
        assert filtered_signals["smooth_signal_465"][0] == pytest.approx(1.401032, rel=1e-3)

    def test_smooth_405_opt1_mean(self, filtered_signals):
        assert filtered_signals["smooth_adjusted_405_opt1"].mean() == pytest.approx(0.266623, rel=1e-3)

    def test_all_outputs_finite(self, filtered_signals):
        for key, arr in filtered_signals.items():
            assert np.all(np.isfinite(arr)), f"Non-finite values in {key}"


class TestButterLowpassFilter:
    def test_output_length_preserved(self):
        data = np.random.randn(1000)
        filtered = butter_lowpass_filter(data, cutoff_freq=0.4, sample_rate=10.0)
        assert len(filtered) == len(data)

    def test_attenuates_high_frequency(self):
        """Filter should reduce variance of high-freq noise."""
        t = np.linspace(0, 100, 10000)
        signal = np.sin(2 * np.pi * 0.1 * t)          # 0.1 Hz — passband
        noise = np.sin(2 * np.pi * 5.0 * t) * 0.5    # 5 Hz — stopband
        combined = signal + noise
        filtered = butter_lowpass_filter(combined, cutoff_freq=0.4, sample_rate=10.0)
        # Residual after removing known signal should be much smaller than noise amplitude (0.5)
        residual_std = (filtered - signal).std()
        assert residual_std < 0.25


class TestSliceData:
    def test_slice_reduces_length(self):
        proc = PhotometryRawProcessor(file_path=str(EXAMPLE_CSV))
        t, s405, s465 = proc.load_data_to_numpy(TIME_COL, COL_405, COL_465)
        proc.time_seconds = t.copy()
        proc.signal_405 = s405.copy()
        proc.signal_465 = s465.copy()

        original_len = len(proc.time_seconds)
        proc.slice_data(TIME_COL, COL_405, COL_465, start_time=10.0, end_time=20.0)
        assert len(proc.time_seconds) < original_len

    def test_slice_invalid_range_raises(self):
        proc = PhotometryRawProcessor(file_path=str(EXAMPLE_CSV))
        t, s405, s465 = proc.load_data_to_numpy(TIME_COL, COL_405, COL_465)
        proc.time_seconds = t.copy()
        proc.signal_405 = s405.copy()
        proc.signal_465 = s465.copy()

        with pytest.raises(ValueError, match="End time must be greater"):
            proc.slice_data(TIME_COL, COL_405, COL_465, start_time=50.0, end_time=10.0)
