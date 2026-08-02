from __future__ import annotations

from src.dashboard.main import (
    _is_pyside6_available,
    build_parser,
    logger,
)
from src.dashboard.main import run_dashboard as _run_dashboard
from src.dashboard.main import run_tool_window as _run_tool_window


def run_dashboard() -> int:
    return _run_dashboard()


def run_tool_window(tool_id: str) -> int:
    return _run_tool_window(tool_id)


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
