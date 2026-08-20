"""Figure sizing and filesystem export helpers."""

from __future__ import annotations

import datetime
import math
from pathlib import Path


def apply_figure_size_and_fonts(
    fig,
    axis_width_cm: float,
    axis_height_cm: float,
    font_settings: dict,
    current_xlabel: str,
    current_ylabel: str,
) -> None:
    """Resize a figure and apply its export font settings in place."""
    axis_width_in = axis_width_cm / 2.54
    axis_height_in = axis_height_cm / 2.54
    diagonal = math.sqrt(axis_width_in**2 + axis_height_in**2)
    default_font_size = 1.8 * diagonal

    def font_size(key: str) -> float:
        value = font_settings.get(key, "")
        return int(value) if value else default_font_size

    xlabel_size = font_size("xlabel_fontsize")
    ylabel_size = font_size("ylabel_fontsize")
    xtick_size = font_size("xtick_fontsize")
    ytick_size = font_size("ytick_fontsize")
    title_size = font_size("title_fontsize")
    scale = max(xlabel_size, ylabel_size, xtick_size, ytick_size) / default_font_size

    left_margin = 0.20 * diagonal * scale
    right_margin = 0.30 * scale
    top_margin = 0.10 * scale
    bottom_margin = 0.15 * diagonal * scale
    figure_width = left_margin + axis_width_in + right_margin
    figure_height = bottom_margin + axis_height_in + top_margin
    fig.set_size_inches(figure_width, figure_height)
    fig.subplots_adjust(
        left=left_margin / figure_width,
        right=1 - right_margin / figure_width,
        top=1 - top_margin / figure_height,
        bottom=bottom_margin / figure_height,
    )

    axis = fig.axes[0]
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    y_label = font_settings.get("y_axis_name", "") or current_ylabel
    axis.set_xlabel(current_xlabel, fontsize=xlabel_size)
    axis.set_ylabel(y_label, fontsize=ylabel_size)
    axis.tick_params(axis="x", labelsize=xtick_size)
    axis.tick_params(axis="y", labelsize=ytick_size)
    axis.set_title(axis.get_title(), fontsize=title_size)


def build_save_path(
    file_path: str,
    mouse_name: str,
    figure_display: str,
    behaviour_choice: str,
    fmt: str,
    recording_date: str | None = "",
) -> Path:
    """Build a collision-free image path and create its output directory."""
    source_path = Path(file_path)
    directory_suffix = (
        f"{mouse_name}_{recording_date}" if recording_date else mouse_name
    )
    output_directory = source_path.parent / f"exported_images_{directory_suffix}"
    output_directory.mkdir(parents=True, exist_ok=True)

    if figure_display == "Behaviour Mean and SEM" and behaviour_choice:
        base_name = f"{mouse_name}_{figure_display}_{behaviour_choice}"
    else:
        base_name = f"{mouse_name}_{figure_display}"
    if not mouse_name:
        base_name = source_path.stem

    date_suffix = (
        recording_date
        if recording_date
        else datetime.datetime.now().strftime("%b%d_%H%M")
    )
    candidate = output_directory / f"{base_name}_{date_suffix}.{fmt}"
    counter = 1
    while candidate.exists():
        candidate = output_directory / f"{base_name}_{date_suffix}_{counter}.{fmt}"
        counter += 1
    return candidate


def save_figure(fig, output_path: str | Path, fmt: str, dpi: int) -> None:
    """Save a figure on an opaque white canvas and close it."""
    import matplotlib.pyplot as plt

    try:
        fig.patch.set_facecolor("white")
        fig.patch.set_alpha(1.0)
        for axis in fig.axes:
            axis.set_facecolor("white")
            axis.patch.set_alpha(1.0)
        fig.savefig(
            str(output_path),
            transparent=False,
            facecolor="white",
            edgecolor="white",
            format=fmt,
            dpi=dpi,
        )
    finally:
        plt.close(fig)
