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
    height_text = (height_str or "").strip()
    width_text = (width_str or "").strip()
    if bool(height_text) != bool(width_text):
        raise ValueError("Enter both image width and height, or leave both fields blank.")

    axis_height_cm = _parse_optional_float(height_str)
    axis_width_cm = _parse_optional_float(width_str)
    if height_text and (axis_height_cm is None or axis_width_cm is None):
        raise ValueError("Image width and height must be valid numbers in centimetres.")
    if axis_height_cm is not None and axis_width_cm is not None:
        if axis_height_cm <= 0 or axis_width_cm <= 0:
            raise ValueError("Image width and height must be greater than zero.")
    else:
        axis_height_cm = None
        axis_width_cm = None

    dpi_text = (dpi_str or "").strip()
    try:
        dpi = int(dpi_text) if dpi_text else 300
        if dpi <= 0:
            raise ValueError("Image DPI must be greater than zero.")
    except (TypeError, ValueError):
        raise ValueError("Image DPI must be a positive whole number.") from None

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
