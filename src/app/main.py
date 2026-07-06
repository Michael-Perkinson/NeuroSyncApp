from __future__ import annotations

import argparse
import importlib.util
import logging
import sys

from src.app.catalog import get_app_definition

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)

logging.basicConfig(
    level=logging.INFO,
    handlers=[console_handler],
    format="%(levelname)s:%(name)s:%(message)s",
)
logger = logging.getLogger(__name__)


def _is_pyside6_available() -> bool:
    return importlib.util.find_spec("PySide6") is not None


def _create_qapplication():
    from PySide6.QtWidgets import QApplication, QStyleFactory

    from src.gui.shared.app_fonts import apply_application_font

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv[:1])
    app.setStyle(QStyleFactory.create("Fusion"))
    apply_application_font(app)
    return app


def run_dashboard() -> int:
    print("Starting NeuroSyncApp...", flush=True)
    from src.app.dashboard import QtDashboard

    app = _create_qapplication()
    dashboard = QtDashboard()
    dashboard.show()
    print("Ready.", flush=True)
    return app.exec()


def run_tool_window(tool_id: str) -> int:
    from PySide6.QtWidgets import QMainWindow

    class ToolWindow(QMainWindow):
        def closeEvent(self, event) -> None:  # pragma: no cover - Qt lifecycle
            widget = self.centralWidget()
            prepare_for_unload = getattr(widget, "prepare_for_unload", None)
            if callable(prepare_for_unload):
                result = prepare_for_unload()
                if result is not None and not result:
                    event.ignore()
                    return
            super().closeEvent(event)

    definition = get_app_definition(tool_id)
    if not definition.qt_supported:
        raise NotImplementedError(
            f"Tool '{tool_id}' has not been ported to PySide6 yet."
        )

    app = _create_qapplication()
    window = ToolWindow()
    widget_class = definition.load_widget_class()
    widget = widget_class(window)
    window.setCentralWidget(widget)
    window.setWindowTitle(definition.label)
    window.resize(1400, 820)
    window.show()
    return app.exec()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Launch NeuroSyncApp.")
    parser.add_argument("--tool", help="Launch a specific tool window directly.")
    parser.add_argument(
        "--framework",
        default="qt",
        choices=["qt"],
        help="GUI framework to use.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not _is_pyside6_available():
        logger.error("PySide6 is not installed.")
        return 1

    try:
        if args.tool:
            return run_tool_window(args.tool)
        return run_dashboard()
    except Exception:
        logger.exception("Application failed to start.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
