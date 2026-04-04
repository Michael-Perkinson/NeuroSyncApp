"""Legacy compatibility wrapper for moved GUI reset helpers."""

from __future__ import annotations


def clear_common_selections(*_args, **_kwargs) -> None:
    raise RuntimeError(
        "Behaviour reset helpers moved to src.gui.controllers.behaviour_reset_helpers."
    )


def clear_photometry_app_specific_selections(*_args, **_kwargs) -> None:
    raise RuntimeError(
        "Behaviour reset helpers moved to src.gui.controllers.behaviour_reset_helpers."
    )
