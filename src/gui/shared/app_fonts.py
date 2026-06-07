from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase

from src.gui.shared.qt_view_styles import (
    APP_FONT_FAMILY,
    APP_FONT_POINT_SIZE,
    MONO_FONT_FAMILY,
)


FONT_FILES = (
    "DejaVuSans.ttf",
    "DejaVuSans-Bold.ttf",
    "DejaVuSansMono.ttf",
    "DejaVuSansMono-Bold.ttf",
)


def _matplotlib_font_dir() -> Path | None:
    try:
        import matplotlib
    except Exception:
        return None
    return Path(matplotlib.get_data_path()) / "fonts" / "ttf"


def register_app_fonts() -> None:
    font_dir = _matplotlib_font_dir()
    if font_dir is None:
        return

    for filename in FONT_FILES:
        font_path = font_dir / filename
        if font_path.exists():
            QFontDatabase.addApplicationFont(str(font_path))


def apply_application_font(app) -> None:
    register_app_fonts()
    point_size = int(os.environ.get("NEUROSYNC_QT_FONT_SIZE", APP_FONT_POINT_SIZE))
    app.setFont(QFont(APP_FONT_FAMILY, point_size))

    try:
        import matplotlib as mpl
    except Exception:
        return

    mpl.rcParams["font.family"] = APP_FONT_FAMILY
    mpl.rcParams["font.sans-serif"] = [APP_FONT_FAMILY]
    mpl.rcParams["font.monospace"] = [MONO_FONT_FAMILY]
