from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.excel_ops.behaviour_exporter import (
    create_df_for_behaviours,
    process_and_bin_data,
)
from src.processing.behaviour_parser import extract_behaviour_results


def _build_photometry_frame(time_seconds: np.ndarray) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Time (min)": time_seconds / 60.0,
            "Signal": np.arange(len(time_seconds), dtype=float),
        }
    )


def _extract_single_behaviour(
    dataframe: pd.DataFrame,
    behaviour_name: str,
    behaviour_start_time: float,
    pre_time: float,
    post_time: float,
):
    params = {
        behaviour_name: [
            {
                "pre_behaviour_time": str(pre_time),
                "post_behaviour_time": str(post_time),
                "bin_size": "5",
                "behaviour_start_time": behaviour_start_time,
            }
        ],
        "behaviours_to_export": {behaviour_name},
        "params_to_extract": [],
    }
    return extract_behaviour_results(
        {behaviour_name},
        params,
        dataframe,
        checkbox_state=False,
        selected_column="Signal",
    )


def _exported_behaviour_frame(
    behaviours_results: dict,
    time_ranges: dict,
    behaviour_name: str,
) -> pd.DataFrame:
    df_list = create_df_for_behaviours(
        behaviours_results,
        [behaviour_name],
        time_ranges,
        combine_csv=True,
        selected_column="Signal",
        checkbox_state=False,
        folder_path="",
    )
    return df_list[0][0]


def test_export_time_axis_uses_actual_3_33hz_sample_rate():
    behaviour_name = "Explore"
    time_seconds = np.round(np.arange(0.0, 30.0, 0.3), 3)
    dataframe = _build_photometry_frame(time_seconds)

    behaviours_results, time_ranges = _extract_single_behaviour(
        dataframe,
        behaviour_name,
        behaviour_start_time=9.0,
        pre_time=3.0,
        post_time=3.0,
    )
    exported = _exported_behaviour_frame(behaviours_results, time_ranges, behaviour_name)

    expected_time = np.round(np.arange(-3.0, 3.0, 0.3), 3)
    np.testing.assert_allclose(exported["Time (s)"].to_numpy(), expected_time)
    assert np.median(np.diff(exported["Time (s)"])) == pytest.approx(0.3)


@pytest.mark.parametrize("sample_interval", [0.1, 0.3])
def test_export_time_axis_preserves_5s_on_15s_off_scheduled_jumps(
    sample_interval,
):
    behaviour_name = "Stim"
    on_blocks = [
        np.round(np.arange(block_start, block_start + 5.0, sample_interval), 3)
        for block_start in (0.0, 20.0, 40.0)
    ]
    dataframe = _build_photometry_frame(np.concatenate(on_blocks))

    behaviours_results, time_ranges = _extract_single_behaviour(
        dataframe,
        behaviour_name,
        behaviour_start_time=20.0,
        pre_time=20.0,
        post_time=5.0,
    )
    exported = _exported_behaviour_frame(behaviours_results, time_ranges, behaviour_name)

    times = exported["Time (s)"].to_numpy()
    zero_index = int(np.flatnonzero(np.isclose(times, 0.0))[0])

    assert times[0] == pytest.approx(-20.0)
    assert times[zero_index] == pytest.approx(0.0)
    assert not np.any((times > -15.0) & (times < 0.0))
    assert times[zero_index] - times[zero_index - 1] > 10.0

    _, _, binned_data = process_and_bin_data(
        behaviours_results[behaviour_name],
        pre_behaviour_time=20,
        post_behaviour_time=5,
        bin_size=5,
        time_ranges=time_ranges[behaviour_name],
    )
    assert [len(bin_values) for bin_values in binned_data] == [
        len(on_blocks[0]),
        0,
        0,
        0,
        len(on_blocks[1]),
    ]
