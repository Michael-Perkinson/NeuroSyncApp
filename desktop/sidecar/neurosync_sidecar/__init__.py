"""Headless Gate 0 sidecar. This package must remain independent of PySide6."""

PROTOCOL_VERSION = 1
SIDECAR_VERSION = "0.1.0"
APP_VERSION = "3.0.0"
MAX_FRAME_BYTES = 4 * 1024 * 1024
MAX_POINTS_PER_SERIES = 10_000
MAX_POINTS_ACROSS_PANELS = 50_000
