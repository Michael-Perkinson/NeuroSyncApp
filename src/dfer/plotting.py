from __future__ import annotations

import logging
import os
import webbrowser
from pathlib import Path

from src import default_dirs

logger = logging.getLogger(__name__)


def is_wsl() -> bool:
    """Return True when running under Windows Subsystem for Linux."""
    return bool(os.environ.get("WSL_DISTRO_NAME"))


def plot_out_path(html_name: str) -> Path:
    """Return the output path for a generated HTML plot."""
    return Path(default_dirs.processor) / html_name


def render_html(obj, html_name: str, title: str, open_in_browser: bool) -> Path:
    """Save a Bokeh object to HTML and optionally open it in a browser."""
    from bokeh.plotting import output_file, save  # lazy — bokeh is optional

    html_path = plot_out_path(html_name)
    html_path.parent.mkdir(parents=True, exist_ok=True)
    output_file(str(html_path), title=title)
    save(obj)

    if open_in_browser and (not is_wsl()):
        webbrowser.open_new_tab(html_path.as_uri())

    logger.info("Saved plot HTML: %s", html_path)
    return html_path
