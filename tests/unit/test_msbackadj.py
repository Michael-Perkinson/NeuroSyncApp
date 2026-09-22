import numpy as np
import pytest

from src.dfer.msbackadj import msbackadj, msbackadj_window_size


def test_msbackadj_window_is_ten_percent_of_recording_span():
    time_values = np.linspace(0.0, 100.0, 101)

    assert msbackadj_window_size(time_values) == pytest.approx(10.0)


def test_msbackadj_removes_slow_baseline_and_preserves_peak_shape():
    time_values = np.linspace(0.0, 100.0, 1001)
    baseline = 20.0 + 0.05 * time_values
    peak = np.exp(-0.5 * ((time_values - 50.0) / 0.5) ** 2)
    signal = baseline + peak

    result = msbackadj(
        time_values,
        signal,
        window_size=10.0,
        step_size=10.0,
    )

    assert result.baseline.shape == signal.shape
    assert result.corrected.shape == signal.shape
    assert np.ptp(result.baseline) > 4.5
    assert np.max(result.corrected) > 0.8
    assert np.mean(np.abs(result.corrected[time_values < 20.0])) < 0.25


def test_msbackadj_rejects_mismatched_input_lengths():
    with pytest.raises(ValueError, match="same number"):
        msbackadj([0.0, 1.0], [1.0], window_size=1.0)
