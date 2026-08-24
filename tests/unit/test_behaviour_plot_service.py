from __future__ import annotations

from types import SimpleNamespace

from src.features.behaviour_alignment.services.plot_service import plot_mean_and_sem_trace


def test_mean_and_sem_display_skips_when_behaviour_has_no_rows():
    app = SimpleNamespace(
        graph_helper_service=SimpleNamespace(
            fetch_behaviour_data=lambda: ([], "Signal", [], []),
        )
    )

    assert plot_mean_and_sem_trace(app, None) is None
