"""Legacy compatibility wrapper for moved Tk-backed GUI state helpers."""

from __future__ import annotations


def _moved(*_args, **_kwargs):
    raise RuntimeError(
        "Tk-backed state helpers moved to src.gui.shared.data_selection_state."
    )


initialize_attributes = _moved
init_file_vars = _moved
init_time_vars = _moved
init_display_vars = _moved
init_graph_settings = _moved
init_behaviour_vars = _moved
init_analysis_state = _moved
