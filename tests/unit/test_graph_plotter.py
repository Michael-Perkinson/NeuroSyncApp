from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import matplotlib.image as mpimg
import numpy as np
import pandas as pd
import pytest
from matplotlib.figure import Figure

from src.features.behaviour_alignment.services.plot_service import save_image
from src.gui.framework.graph_plotter import build_save_path, draw_behaviour_boxes


@pytest.mark.parametrize("values", [[-2.0, 0.0, 4.0], [2.0, 3.0, 4.0]])
def test_behaviour_box_starts_at_signal_minimum(values):
    figure = Figure()
    axis = figure.add_subplot(111)
    data = pd.Series(values)
    time_data = pd.Series([0.0, 1.0, 2.0])

    boxes = draw_behaviour_boxes(
        axis,
        data,
        time_data,
        ["Approach"],
        [0.5],
        [1.5],
        {"Approach": "#123456"},
        {"Approach": True},
        1.0,
        0.5,
        0.5,
    )

    assert boxes["Approach"][0].get_y() == min(values)


class TestBuildSavePath:
    """Tests for build_save_path function with recording date support."""

    @pytest.fixture
    def temp_file_path(self, tmp_path):
        """Create a temporary file path for testing."""
        file_path = tmp_path / "mouse_26-07-21_photometry.csv"
        file_path.write_text("dummy data")
        return str(file_path)

    def test_directory_includes_recording_date_when_provided(self, temp_file_path, tmp_path):
        """Directory should NOT include recording date; filename should."""
        output_path = build_save_path(
            temp_file_path,
            mouse_name="mouse_A",
            figure_display="Mean Cluster",
            behaviour_choice="",
            fmt="png",
            recording_date="26-07-21",
        )

        # Directory should be just the mouse name, without the date
        assert "exported_images_mouse_A" in str(output_path)
        assert "exported_images_mouse_A_26-07-21" not in str(output_path)
        # But the filename should still contain the date
        assert "26-07-21" in Path(output_path).name
        assert str(output_path).endswith(".png")

    def test_directory_excludes_date_when_not_provided(self, temp_file_path, tmp_path):
        """Directory should exclude date when recording_date is empty."""
        output_path = build_save_path(
            temp_file_path,
            mouse_name="mouse_A",
            figure_display="Mean Cluster",
            behaviour_choice="",
            fmt="png",
            recording_date="",
        )

        output_str = str(output_path)
        assert "exported_images_mouse_A" in output_str
        assert "_" not in output_str.split("exported_images_")[-1].split(os.sep)[0][len("mouse_A"):]
        assert output_str.endswith(".png")

    def test_directory_is_reused_across_different_recording_dates(self, temp_file_path, tmp_path):
        """Same mouse's export directory should be identical across different recording dates."""
        path1 = build_save_path(
            temp_file_path,
            mouse_name="mouse_A",
            figure_display="Full Trace",
            behaviour_choice="",
            fmt="png",
            recording_date="25-12-08",
        )
        path2 = build_save_path(
            temp_file_path,
            mouse_name="mouse_A",
            figure_display="Full Trace",
            behaviour_choice="",
            fmt="png",
            recording_date="26-01-09",
        )

        # Same directory for the same mouse across different dates
        assert path1.parent == path2.parent
        # Different filenames due to different dates
        assert path1.name != path2.name
        # Each filename contains its respective date
        assert "25-12-08" in path1.name
        assert "26-01-09" in path2.name

    def test_filename_includes_recording_date(self, temp_file_path, tmp_path):
        """Filename should include recording date when provided."""
        output_path = build_save_path(
            temp_file_path,
            mouse_name="mouse_A",
            figure_display="Mean_Cluster",
            behaviour_choice="",
            fmt="png",
            recording_date="26-07-21",
        )

        filename = Path(output_path).name
        assert "26-07-21" in filename
        assert filename.startswith("mouse_A")
        assert filename.endswith(".png")

    def test_filename_uses_timestamp_fallback_when_no_date(self, temp_file_path, tmp_path):
        """Filename should use timestamp when recording_date is empty."""
        output_path = build_save_path(
            temp_file_path,
            mouse_name="mouse_A",
            figure_display="Mean_Cluster",
            behaviour_choice="",
            fmt="png",
            recording_date="",
        )

        filename = Path(output_path).name
        assert filename.startswith("mouse_A")
        assert filename.endswith(".png")
        assert "_" in filename
        assert any(c.isalpha() for c in filename.split("_")[-1])

    def test_filename_format_with_date_prefix(self, temp_file_path, tmp_path):
        """Filename format should be {mouse}_{figure}_{date}.{fmt}."""
        output_path = build_save_path(
            temp_file_path,
            mouse_name="M001",
            figure_display="Full_Trace",
            behaviour_choice="",
            fmt="png",
            recording_date="25-12-08",
        )

        filename = Path(output_path).name
        assert filename == "M001_Full_Trace_25-12-08.png"

    def test_filename_with_behaviour_choice(self, temp_file_path, tmp_path):
        """Filename should include behaviour choice when provided."""
        output_path = build_save_path(
            temp_file_path,
            mouse_name="M001",
            figure_display="Behaviour Mean and SEM",
            behaviour_choice="walking",
            fmt="png",
            recording_date="25-12-08",
        )

        filename = Path(output_path).name
        assert "walking" in filename
        assert "25-12-08" in filename
        assert filename.endswith(".png")

    def test_collision_handling_creates_counter(self, temp_file_path, tmp_path):
        """Should append counter when file already exists."""
        output_path1 = build_save_path(
            temp_file_path,
            mouse_name="M001",
            figure_display="Plot",
            behaviour_choice="",
            fmt="png",
            recording_date="25-12-08",
        )

        Path(output_path1).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path1).write_text("dummy")

        output_path2 = build_save_path(
            temp_file_path,
            mouse_name="M001",
            figure_display="Plot",
            behaviour_choice="",
            fmt="png",
            recording_date="25-12-08",
        )

        assert output_path1 != output_path2
        output_path2_str = str(output_path2)
        assert "_1.png" in output_path2_str or "_2.png" in output_path2_str

    def test_different_image_formats(self, temp_file_path, tmp_path):
        """Should respect different image format extensions."""
        for fmt_ext in ["png", "pdf", "jpg"]:
            output_path = build_save_path(
                temp_file_path,
                mouse_name="M001",
                figure_display="Plot",
                behaviour_choice="",
                fmt=fmt_ext,
                recording_date="25-12-08",
            )

            assert str(output_path).endswith(f".{fmt_ext}")

    def test_mouse_name_with_special_characters(self, temp_file_path, tmp_path):
        """Should handle mouse names with underscores and numbers."""
        output_path = build_save_path(
            temp_file_path,
            mouse_name="M_001_special",
            figure_display="Plot",
            behaviour_choice="",
            fmt="png",
            recording_date="25-12-08",
        )

        filename = Path(output_path).name
        assert filename.startswith("M_001_special")

    def test_recording_date_format_preservation(self, temp_file_path, tmp_path):
        """Recording date format should be preserved in output."""
        test_dates = ["25-12-08", "26-07-21", "24-01-15"]

        for date_str in test_dates:
            output_path = build_save_path(
                temp_file_path,
                mouse_name="M001",
                figure_display="Plot",
                behaviour_choice="",
                fmt="png",
                recording_date=date_str,
            )

            assert date_str in str(output_path)

    def test_backward_compatibility_empty_string_date(self, temp_file_path, tmp_path):
        """Empty string date should trigger timestamp fallback."""
        output_path = build_save_path(
            temp_file_path,
            mouse_name="M001",
            figure_display="Plot",
            behaviour_choice="",
            fmt="png",
            recording_date="",
        )

        filename = Path(output_path).name
        # Check that the filename contains a timestamp (abbreviated month name) instead of a date
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        assert any(month in filename for month in months)

    def test_backward_compatibility_none_date(self, temp_file_path, tmp_path):
        """None date should trigger timestamp fallback."""
        output_path = build_save_path(
            temp_file_path,
            mouse_name="M001",
            figure_display="Plot",
            behaviour_choice="",
            fmt="png",
            recording_date=None,
        )

        filename = Path(output_path).name
        assert filename.startswith("M001_Plot")
        assert filename.endswith(".png")


def test_behaviour_save_image_can_save_the_same_live_plot_twice(tmp_path):
    class Value:
        def __init__(self, value):
            self.value = value

        def get(self):
            return self.value

    figure = Figure()
    axis = figure.add_subplot(111)
    axis.plot([0, 1], [0, 1])
    app = SimpleNamespace(
        fig=figure,
        file_path_var=Value(str(tmp_path / "mouse.csv")),
        mouse_name="mouse_A",
        date="26-08-20",
        figure_display_dropdown=Value("Full Trace Display"),
        behaviour_choice_graph=Value(""),
        export_options_container=SimpleNamespace(
            height_entry=Value(""),
            width_entry=Value(""),
            image_format_combobox=Value("PNG"),
            dpi_entry=Value("300"),
            font_settings={},
        ),
    )

    save_image(app)
    save_image(app)

    output_directory = tmp_path / "exported_images_mouse_A"
    outputs = sorted(output_directory.glob("*.png"))
    assert len(outputs) == 2
    assert all(path.stat().st_size > 0 for path in outputs)

    image = mpimg.imread(outputs[0])
    assert image.shape[-1] == 4
    assert np.allclose(image[..., 3], 1.0)
    assert np.allclose(image[0, 0, :3], 1.0)
