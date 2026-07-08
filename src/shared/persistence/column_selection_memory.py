"""Remember which signal columns a user ticked for a given set of columns.

Dual-signal recordings are usually processed in batches of files that share
the same column layout (e.g. ``dFoF_465`` + ``dFoF_405``). Rather than make
the user re-tick the same columns for every file, the selection is keyed by
the *set* of available column titles and recalled the next time a file with
the same columns is loaded.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from src.shared.persistence.app_paths import config_file_path

logger = logging.getLogger(__name__)

_FILE_NAME = "signal_column_selections.json"


def _path() -> Path:
    return config_file_path(_FILE_NAME)


def _key(column_titles: list[str]) -> str:
    """Order-independent key for a set of column titles."""
    return "|".join(sorted(column_titles))


def _load() -> dict[str, list[str]]:
    try:
        return json.loads(_path().read_text(encoding="utf-8"))
    except (IOError, json.JSONDecodeError):
        return {}


def recall_selection(column_titles: list[str]) -> list[str] | None:
    """Return the remembered selection for *column_titles*, or ``None``.

    Only columns still present in *column_titles* are returned, preserving
    the saved order. Returns ``None`` when nothing was saved for this column
    set or none of the saved columns survive.
    """
    if not column_titles:
        return None
    saved = _load().get(_key(column_titles))
    if not saved:
        return None
    available = set(column_titles)
    surviving = [column for column in saved if column in available]
    return surviving or None


def remember_selection(column_titles: list[str], selected: list[str]) -> None:
    """Persist *selected* as the choice for the *column_titles* set."""
    if not column_titles or not selected:
        return
    data = _load()
    data[_key(column_titles)] = list(selected)
    try:
        _path().write_text(json.dumps(data), encoding="utf-8")
    except IOError:
        logger.warning("Could not persist signal column selection.", exc_info=True)
