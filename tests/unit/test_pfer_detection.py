from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.dfer import run_pfer
from src.dfer.df_plots import mpl_pfer_figure
from src.dfer.pfer_detection import analyze_signal, baseline_mask, _waveforms_for_peaks


def test_retained_peak_uses_valley_before_rejected_shoulder():
    y = np.interp(np.arange(301), [0, 10, 30, 50, 65, 70, 100, 130, 300],
                  [0, -.1, .3, -.2, -.195, -.198, .4, -.1, 0])
    t = np.arange(len(y)) / 600
    result = analyze_signal(t, y, np.zeros_like(y), .003, 10)
    np.testing.assert_allclose(result['peak_min'], t[[30, 100]])
    np.testing.assert_allclose(result['trough_min'], t[[10, 50]])
    np.testing.assert_allclose(result['amplitudes'], [.4, .6])


def test_end_only_baseline_honours_end():
    t = np.arange(601) / 60
    np.testing.assert_array_equal(baseline_mask(t, '', '300'), t <= 5)


@pytest.mark.parametrize('dt', [.1, .2])
def test_waveform_time_matches_sample_interval(dt):
    t = np.arange(1000) * dt / 60
    _, axis, _ = _waveforms_for_peaks(np.sin(t), t, t[[500]])
    np.testing.assert_allclose(axis, np.arange(-50, 100) * dt)


def test_dual_export_and_plot_share_original_signal_coordinates(tmp_path):
    t = np.arange(0, 120, .1)
    y = -.3 + .1 * np.sin(t)
    path = tmp_path / 'dual.csv'
    pd.DataFrame({'t_min': t / 60, 'dFoF_470': y, 'dFoF_560': y * 2}).to_csv(path, index=False)
    outputs = run_pfer(path)
    figure = mpl_pfer_figure(str(path), outputs)
    assert len(figure.axes) == 2
    for ax, output in zip(figure.axes, outputs.splitlines()):
        stats = pd.read_csv(output)
        stats.columns = [c.lstrip('# ').strip() for c in stats.columns]
        assert len(stats) > 0
        for collection, prefix in zip(ax.collections, ['peak', 'trough']):
            xy = np.asarray(collection.get_offsets())
            line = ax.lines[0]
            np.testing.assert_allclose(xy[:, 1], np.interp(xy[:, 0], line.get_xdata(), line.get_ydata()), atol=1e-5)


def test_pfer_plot_uses_channel_order_when_stats_files_are_renamed(tmp_path):
    t = np.arange(0, 120, .1)
    path = tmp_path / 'dual.csv'
    frame = pd.DataFrame({'t_min': t / 60, 'dFoF_470': np.sin(t), 'dFoF_560': np.cos(t)})
    frame.to_csv(path, index=False)
    outputs = run_pfer(path).splitlines()
    renamed = []
    for index, output in enumerate(outputs):
        destination = tmp_path / f'renamed_stats_{index}.csv'
        Path(output).rename(destination)
        renamed.append(str(destination))

    figure = mpl_pfer_figure(str(path), '\n'.join(renamed))

    np.testing.assert_allclose(figure.axes[0].lines[0].get_ydata(), frame['dFoF_470'])
    np.testing.assert_allclose(figure.axes[1].lines[0].get_ydata(), frame['dFoF_560'])


@pytest.mark.parametrize('y', [np.zeros(300), np.r_[np.arange(150), np.arange(150)[::-1]]])
def test_unpaired_extrema_produce_empty_results(y):
    result = analyze_signal(np.arange(len(y)) / 600, y, np.zeros_like(y), .003, 10)
    assert result['peak_count'] == 0
