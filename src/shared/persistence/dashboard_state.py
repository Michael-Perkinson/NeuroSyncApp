"""Persistence helpers for dashboard state."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from src.shared.persistence.app_paths import config_file_path, legacy_repo_file_path


def state_file_path() -> Path:
    """Return the file path used for the dashboard state."""
    return config_file_path("state", "app_state.json")


def _legacy_state_file_path() -> Path:
    return legacy_repo_file_path("src", "gui", "shared", ".neurosync", "app_state.json")


def get_state_file_path() -> str:
    """Return the state path as a string for compatibility callers."""
    return str(state_file_path())


def save_state(app_name: str) -> None:
    """Save the last-opened application id."""
    file_path = state_file_path()
    try:
        with file_path.open("w", encoding="utf-8") as handle:
            json.dump({"last_app": app_name}, handle)
    except IOError:
        return


def load_state() -> Optional[str]:
    """Load the last-opened application id."""
    for file_path in (state_file_path(), _legacy_state_file_path()):
        if not file_path.exists():
            continue
        try:
            with file_path.open("r", encoding="utf-8") as handle:
                state = json.load(handle)
        except (json.JSONDecodeError, IOError):
            return None
        return state.get("last_app")
    return None

