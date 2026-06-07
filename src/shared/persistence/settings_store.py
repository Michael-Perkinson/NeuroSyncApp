"""Persistence helpers for app settings."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from src.shared.persistence.app_paths import config_file_path, legacy_repo_file_path


logger = logging.getLogger(__name__)


def settings_file_path(app_type: str) -> Path:
    """Return the JSON path used to persist settings for *app_type*."""
    return config_file_path("settings", f"{app_type}_settings.json")


def _legacy_settings_file_path(app_type: str) -> Path:
    return legacy_repo_file_path(f"{app_type}_settings.json")


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_settings(app_type: str) -> dict:
    """Load persisted settings for *app_type* or return an empty mapping."""
    candidates = [settings_file_path(app_type), _legacy_settings_file_path(app_type)]
    for path in candidates:
        try:
            return _load_json(path)
        except FileNotFoundError:
            continue
        except Exception:
            logger.exception("Error loading settings for %s from %s.", app_type, path)
            return {}
    logger.debug("No existing settings file found for %s.", app_type)
    return {}


def save_settings(app_type: str, config: dict) -> None:
    """Persist *config* for *app_type*."""
    path = settings_file_path(app_type)
    try:
        with path.open("w", encoding="utf-8") as handle:
            json.dump(config, handle)
    except Exception:
        logger.exception("Error saving settings for %s.", app_type)

