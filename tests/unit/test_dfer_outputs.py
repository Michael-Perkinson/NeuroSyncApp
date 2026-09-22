import numpy as np
import pandas as pd
import pytest

from src.dfer import df_dual, df_single, run_analysis
from src.dfer.df_common import read_analysis_output, save_analysis_output


def test_save_analysis_output_records_selected_option(tmp_path):
    output_path = tmp_path / "recording_Data.csv"

    save_analysis_output(
        output_path,
        np.array([[1.25, 2.5], [3.75, 4.0]]),
        "t_min,signal",
        "5",
    )

    frame = read_analysis_output(output_path)

    assert (
        output_path.read_text(encoding="utf-8").splitlines()[0]
        == "t_min,signal,# option used=5"
    )
    raw_frame = pd.read_csv(output_path)
    assert raw_frame.columns[-1] == "# option used=5"
    assert raw_frame["t_min"].tolist() == [1.25, 3.75]
    assert list(frame.columns) == ["t_min", "signal"]
    assert frame.attrs["dfer_option"] == 5
    assert frame["t_min"].tolist() == [1.25, 3.75]
    assert frame["signal"].tolist() == [2.5, 4.0]


@pytest.mark.parametrize(
    "invalid_option", ["not-an-option", "0", "-1", 1.5, float("inf")]
)
def test_save_analysis_output_rejects_invalid_option(tmp_path, invalid_option):
    with pytest.raises(ValueError, match="positive integer"):
        save_analysis_output(
            tmp_path / "recording_Data.csv",
            np.ones((2, 1)),
            "signal",
            invalid_option,
        )


def test_save_analysis_output_rejects_non_matrix_data(tmp_path):
    with pytest.raises(ValueError, match="two-dimensional"):
        save_analysis_output(
            tmp_path / "recording_Data.csv",
            np.ones(2),
            "signal",
            "1",
        )


def test_single_analysis_records_selected_option(tmp_path, monkeypatch):
    raw_file = tmp_path / "recording.csv"
    time_values = np.arange(123, dtype=float)
    pd.DataFrame(
        {
            "#time(seconds)": time_values,
            "405nm": 10.0 + 0.01 * time_values,
            "465nm": 20.0 + 0.02 * time_values,
        }
    ).to_csv(raw_file, index=False)
    monkeypatch.setattr(df_single.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        df_single,
        "compute_adjusted_baselines",
        lambda *_args: pytest.fail("option 5 must not use the 405 nm control"),
    )

    output_path = run_analysis(raw_file, analysis_path="5", plot_stage="none")

    output = read_analysis_output(output_path)
    assert output.attrs["dfer_option"] == 5
    assert output["fitted_405"].isna().all()
    assert output["dFoF_405"].isna().all()
    assert output["Z_405"].isna().all()
    assert output["dFoF_465"].notna().all()


def test_dual_analysis_records_selected_option(tmp_path, monkeypatch):
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    raw_file = session_dir / "Fluorescence.csv"
    time_values = np.arange(123, dtype=float) * 1000.0
    pd.DataFrame(
        {
            "TimeStamp": time_values,
            "CH1-410": 10.0 + 0.01 * time_values,
            "CH1-470": 20.0 + 0.02 * time_values,
            "CH1-560": 30.0 + 0.03 * time_values,
        }
    ).to_csv(raw_file, index=False)
    monkeypatch.setattr(df_dual.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        df_dual,
        "compute_adjusted_baselines",
        lambda *_args: pytest.fail("option 5 must not use the 410 nm control"),
    )

    output_path = run_analysis(raw_file, analysis_path="5", plot_stage="none")

    output = read_analysis_output(output_path)
    assert output.attrs["dfer_option"] == 5
