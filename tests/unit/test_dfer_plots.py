import numpy as np

from src.dfer.df_plots import mpl_options_figure, mpl_results_figure


def test_mpl_single_options_figure_renders_all_five_rows():
    trace = np.arange(4, dtype=float)
    data = {
        "file_type": "single",
        "t_min": trace,
        "smooth_465": trace,
        **{f"smooth_adj_{index}": trace for index in range(1, 6)},
    }

    figure = mpl_options_figure(data)

    assert len(figure.axes) == 5
    assert figure.axes[-1].get_xlabel() == "Time (min)"


def test_mpl_results_figure_hides_control_for_option_five(tmp_path):
    output_path = tmp_path / "option-five.csv"
    output_path.write_text(
        "t_min,dFoF_405,dFoF_465,Z_405,Z_465,# option used=5\n"
        "0.0,nan,0.1,nan,1.0,\n"
        "1.0,nan,0.2,nan,1.1,\n",
        encoding="utf-8",
    )

    figure = mpl_results_figure(str(output_path))

    assert [line.get_label() for line in figure.axes[0].lines] == ["465nm dF/F"]
    assert [line.get_label() for line in figure.axes[1].lines] == ["465nm Z"]


def test_mpl_dual_options_figure_renders_all_five_rows():
    trace = np.arange(4, dtype=float)
    data = {
        "file_type": "dual",
        "t_min": trace,
        "p470": {
            "target_smooth": trace,
            **{f"adj{index}": trace for index in range(1, 6)},
        },
        "p560": {
            "target_smooth": trace,
            **{f"adj{index}": trace for index in range(1, 6)},
        },
    }

    figure = mpl_options_figure(data)

    assert len(figure.axes) == 5
    assert figure.axes[-1].get_xlabel() == "Time (min)"
    assert "no 405/410 control" in figure.axes[-1].get_title()
