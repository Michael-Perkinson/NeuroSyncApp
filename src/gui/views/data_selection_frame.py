"""Compatibility export for the Qt data-selection panel."""

from __future__ import annotations

from src.gui.views.data_selection_panel import DataSelectionPanel


class DataSelectionFrame(DataSelectionPanel):
    """Backward-compatible alias kept while callers migrate module paths."""

    pass
