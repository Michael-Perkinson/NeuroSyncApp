"""Shared path resolution for app-owned config and state files."""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "NeuroSyncApp"
CONFIG_DIR_ENV_VAR = "NEUROSYNCAPP_CONFIG_DIR"


def repo_root() -> Path:
    """Return the repository root."""
    return Path(__file__).resolve().parents[3]


def _fallback_user_config_dir() -> Path:
    if os.name == "nt":
        base = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / APP_NAME


def _workspace_fallback_dir() -> Path:
    return repo_root() / ".neurosync_config"


def app_config_dir() -> Path:
    """Return the per-user config directory for NeuroSyncApp."""
    override = os.getenv(CONFIG_DIR_ENV_VAR)
    if override:
        path = Path(override).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        return path

    try:
        from platformdirs import user_config_dir
    except ImportError:
        path = _fallback_user_config_dir()
    else:
        path = Path(user_config_dir(APP_NAME, appauthor=False))

    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        path = _workspace_fallback_dir()
        path.mkdir(parents=True, exist_ok=True)
    return path


def config_file_path(*parts: str) -> Path:
    """Return a path inside the per-user NeuroSyncApp config directory."""
    path = app_config_dir().joinpath(*parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def legacy_repo_file_path(*parts: str) -> Path:
    """Return the legacy repo-local path for a persisted file."""
    return repo_root().joinpath(*parts)
