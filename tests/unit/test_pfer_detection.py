import pandas as pd

from src.dfer.pfer_detection import signal_specs


def test_option_five_single_output_uses_signal_as_pfer_baseline():
    frame = pd.DataFrame(
        {
            "dFoF_465": [0.1, 0.2],
            "dFoF_405": [float("nan"), float("nan")],
        }
    )
    frame.attrs["dfer_option"] = 5

    dataset_kind, specs = signal_specs(frame)

    assert dataset_kind == "single"
    assert specs[0]["signal_col"] == "dFoF_465"
    assert specs[0]["baseline_col"] == "dFoF_465"


def test_control_based_single_output_keeps_405_pfer_baseline():
    frame = pd.DataFrame(
        {
            "dFoF_465": [0.1, 0.2],
            "dFoF_405": [0.0, 0.1],
            "dfer_option": [1, 1],
        }
    )

    _, specs = signal_specs(frame)

    assert specs[0]["baseline_col"] == "dFoF_405"
