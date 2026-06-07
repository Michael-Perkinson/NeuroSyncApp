"""Pure helpers for figure export request normalization."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ImageExportRequest:
    """Resolved image export settings from controller-provided strings."""

    axis_width_cm: float | None
    axis_height_cm: float | None
    image_format: str
    dpi: int
    figure_display: str
    behaviour_choice: str


def _parse_optional_float(value: str | None) -> float | None:
    text = (value or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def build_image_export_request(
    height_str: str,
    width_str: str,
    selected_format: str,
    dpi_str: str,
    figure_display: str,
    selected_behaviour: str,
) -> ImageExportRequest:
    """Build a normalized image export request."""
    axis_height_cm = _parse_optional_float(height_str)
    axis_width_cm = _parse_optional_float(width_str)
    if axis_height_cm is None or axis_width_cm is None:
        axis_height_cm = None
        axis_width_cm = None

    try:
        dpi = int(dpi_str)
        if dpi <= 0:
            raise ValueError
    except (TypeError, ValueError):
        dpi = 300

    image_format = (selected_format or "png").strip().lower() or "png"
    behaviour_choice = (
        selected_behaviour if figure_display == "Behaviour Mean and SEM" else ""
    )

    return ImageExportRequest(
        axis_width_cm=axis_width_cm,
        axis_height_cm=axis_height_cm,
        image_format=image_format,
        dpi=dpi,
        figure_display=figure_display,
        behaviour_choice=behaviour_choice,
    )
