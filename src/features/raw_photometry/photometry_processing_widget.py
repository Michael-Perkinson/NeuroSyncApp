from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import cast

import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src import path_config
from src.core.app_settings_manager import AppSettingsManager
from src.dfer import compute_options, run_analysis, run_pfer
from src.dfer.df_common import (
    analysis_option_from_frame,
    detect_photometry_file_type,
    load_dual_photometry,
    read_analysis_output,
    validate_dual_df,
    validate_single_df,
)
from src.dfer.df_plots import mpl_pfer_figure
from src.features.raw_photometry.plotting import (
    OPTION_TITLES as _OPTION_TITLES,
)
from src.features.raw_photometry.plotting import (
    _tighten_time_axes,
)
from src.features.raw_photometry.plotting import (
    mpl_dfer_results_figure_from_frame as _mpl_dfer_results_figure_from_frame,
)
from src.features.raw_photometry.plotting import (
    mpl_single_option_figure as _mpl_single_option_figure,
)
from src.features.raw_photometry.plotting import (
    normalise_dfer_result_frame as _normalise_dfer_result_frame,
)
from src.features.raw_photometry.views.graph_panel import GraphPanel, GraphReference
from src.features.raw_photometry.workers import (
    AnalysisWorker as _Worker,
)
from src.features.raw_photometry.workers import (
    QtSignalLogHandler as _QtLogHandler,
)
from src.gui.framework.messages_and_errors import format_action_error, show_action_error
from src.gui.framework.qt_view_styles import (
    APP_TABS_STYLESHEET,
    PALETTE,
    apply_button_role,
    combo_stylesheet,
    panel_stylesheet,
    section_stylesheet,
    section_title_stylesheet,
    subtitle_stylesheet,
    title_stylesheet,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _open_path(path: str) -> None:
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"Path does not exist:\n{target}")
    if sys.platform.startswith("win"):
        os.startfile(str(target))
        return
    if sys.platform == "darwin":
        subprocess.Popen(["open", str(target)])
        return
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices

    if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(target))):
        raise RuntimeError(f"Could not open:\n{target}")


def _format_duration(seconds: float) -> str:
    total = round(seconds)
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    if h > 0:
        return f"{h}h {m}m {s}s"
    if m > 0:
        return f"{m}m {s}s"
    return f"{s}s"


def _parse_window_endpoint(text: str, fallback: float, aliases: set[str]) -> float:
    value = text.strip().lower()
    if not value or value in aliases:
        return fallback
    try:
        return float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid time endpoint: {text!r}") from error


def _normalise_window_input(text: str, aliases: set[str]) -> str:
    value = text.strip()
    if not value or value.lower() in aliases:
        return ""
    return value


def _signal_range(values: np.ndarray) -> tuple[float, float] | None:
    try:
        finite_values = np.asarray(values, dtype=float)
        finite_values = finite_values[np.isfinite(finite_values)]
        if finite_values.size == 0:
            return None
        return float(np.min(finite_values)), float(np.max(finite_values))
    except (TypeError, ValueError) as error:
        raise ValueError("Signal values must be numeric") from error


def _raw_time_bounds(values: np.ndarray) -> tuple[float, float]:
    try:
        return float(values[0]), float(values[-1])
    except (IndexError, TypeError, ValueError) as error:
        raise ValueError("Raw signal data must contain numeric time values") from error


_RAW_CONTROL_OCCUPANCY = 0.30
_RAW_LARGER_SIGNAL_OCCUPANCY = 0.80
_RAW_SMALLER_SIGNAL_OCCUPANCY = 0.50
_RAW_INDIVIDUAL_CONTROL_ALPHA = 0.55
_RAW_INDIVIDUAL_SIGNAL_ALPHA = 0.65
_RAW_GRAPH_BOTTOM_MARGIN = 0.09


def _signal_span(values: np.ndarray) -> float:
    observed_range = _signal_range(values)
    if observed_range is None:
        return 0.0
    return observed_range[1] - observed_range[0]


def _signal_axis_limits(
    values: np.ndarray, occupancy: float = 1.0
) -> tuple[float, float]:
    """Return y-limits with an optional fraction of the axis occupied by data."""
    if not 0 < occupancy <= 1:
        raise ValueError("occupancy must be greater than zero and at most one")

    observed_range = _signal_range(values)
    if observed_range is None:
        return (0.0, 1.0)

    value_min, value_max = observed_range
    value_span = value_max - value_min
    scale_reference = max(abs(value_min), abs(value_max))
    if value_span == 0:
        value_span = max(scale_reference * 0.002, 1e-6)

    if occupancy < 1:
        axis_span = value_span / occupancy
        midpoint = (value_min + value_max) / 2
        return midpoint - axis_span / 2, midpoint + axis_span / 2

    padding = max(value_span * 0.04, scale_reference * 0.001, 1e-6)
    return value_min - padding, value_max + padding


def _shared_signal_axis_limits(signals: list[np.ndarray]) -> tuple[float, float]:
    """Keep all signals visible while letting the widest range set the padding."""
    observed_ranges = [
        observed_range
        for signal in signals
        if (observed_range := _signal_range(signal)) is not None
    ]
    if not observed_ranges:
        return (0.0, 1.0)

    value_min = min(observed_range[0] for observed_range in observed_ranges)
    value_max = max(observed_range[1] for observed_range in observed_ranges)
    global_span = value_max - value_min
    dominant_span = max(
        observed_range[1] - observed_range[0] for observed_range in observed_ranges
    )
    scale_reference = max(abs(value_min), abs(value_max))
    padding = max(dominant_span * 0.04, scale_reference * 0.001, 1e-6)
    if global_span == 0:
        padding = max(scale_reference * 0.02, 1e-6)
    return value_min - padding, value_max + padding


def _safe_path_part(value: str) -> str:
    safe = "".join(c if c not in '<>:"/\\|?*' else "_" for c in value).strip()
    return safe or "recording"


def _strip_data_suffix(stem: str) -> str:
    if stem.endswith("_Dual_Data"):
        return stem.removesuffix("_Data")
    if stem.endswith("_Data"):
        return stem.removesuffix("_Data")
    return stem


def _spinbox_css(panel_name: str) -> str:
    return f"""
#{panel_name} QDoubleSpinBox,
#{panel_name} QSpinBox {{
    background: {PALETTE["card_bg"]};
    border: 1px solid {PALETTE["border"]};
    border-radius: 6px;
    padding: 3px 6px;
    color: {PALETTE["text"]};
}}
#{panel_name} QRadioButton {{
    color: {PALETTE["text"]};
    spacing: 8px;
    padding: 4px 6px;
    border-radius: 6px;
}}
#{panel_name} QRadioButton:hover {{
    background: {PALETTE["button_bg"]};
}}
#{panel_name} QRadioButton:checked {{
    color: {PALETTE["accent"]};
    background: {PALETTE["accent_soft"]};
    font-weight: 600;
}}
#{panel_name} QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 2px solid {PALETTE["border_strong"]};
    border-radius: 9px;
    background: {PALETTE["card_bg"]};
}}
#{panel_name} QRadioButton::indicator:hover {{
    border-color: {PALETTE["accent"]};
}}
#{panel_name} QRadioButton::indicator:checked {{
    border-color: {PALETTE["accent"]};
    background: {PALETTE["accent"]};
}}
"""


def _raw_graph_tabs_stylesheet() -> str:
    return (
        APP_TABS_STYLESHEET
        + f"""
QTabBar::tab:disabled {{
    color: {PALETTE["muted"]};
    background: {PALETTE["card_alt_bg"]};
    border-color: {PALETTE["border"]};
}}
QTabBar::tab:enabled {{
    color: {PALETTE["text"]};
}}
"""
    )


# ---------------------------------------------------------------------------
# Main widget
# ---------------------------------------------------------------------------


class RawPhotometryProcessingQt(QWidget):
    _log_signal = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings_manager = AppSettingsManager(app_type="raw_photometry_processing")
        self.settings_manager.load_variables()
        self._selected_file: str | None = None
        self._output_folder: str | None = None
        self._raw_graph_ref: GraphReference | None = None
        self._raw_graph_controls: QWidget
        self._raw_control_toggle: QCheckBox
        self._raw_individual_y_axes_toggle: QCheckBox
        self.dfer_results_graph: GraphPanel
        self.pfer_graph: GraphPanel
        self._options_data: dict | None = None
        self._dfer_result_csv: str | None = None
        self._dfer_result_frame: pd.DataFrame | None = None
        self._pfer_selected_csv: str | None = None
        self._plot_save_counts: dict[str, int] = {}
        self._thread: QThread | None = None
        self._worker: _Worker | None = None
        self._log_handler: _QtLogHandler | None = None
        self._log_handler_loggers: list[logging.Logger] = []
        self._log_signal_connected = False
        self._log_edit: QPlainTextEdit | None = None
        self._unloading = False
        self._build_ui()

    # ── UI construction ────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.setObjectName("rawPhotometryRoot")
        self.setStyleSheet(f"#rawPhotometryRoot {{ background: {PALETTE['app_bg']}; }}")

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        # ── top frame ──────────────────────────────────────────────────────
        self.top_frame = QWidget(self)
        top_layout = QGridLayout(self.top_frame)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setHorizontalSpacing(10)
        top_layout.addWidget(self._build_data_selection_panel(), 0, 0)
        top_layout.addWidget(self._build_analysis_window_panel(), 0, 1)
        top_layout.setColumnStretch(0, 5)
        top_layout.setColumnStretch(1, 3)
        root.addWidget(self.top_frame)

        # ── bottom frame ───────────────────────────────────────────────────
        self.bottom_frame = QWidget(self)
        bottom_layout = QGridLayout(self.bottom_frame)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setHorizontalSpacing(10)

        self.notebook_graphs = QTabWidget(self.bottom_frame)
        self.notebook_graphs.setStyleSheet(_raw_graph_tabs_stylesheet())
        self.notebook_settings = QTabWidget(self.bottom_frame)
        self.notebook_settings.setStyleSheet(APP_TABS_STYLESHEET)

        bottom_layout.addWidget(self.notebook_graphs, 0, 0)
        bottom_layout.addWidget(self.notebook_settings, 0, 1)
        bottom_layout.setColumnStretch(0, 3)
        bottom_layout.setColumnStretch(1, 2)
        root.addWidget(self.bottom_frame, 1)

        # ── graph tabs ─────────────────────────────────────────────────────
        self.raw_graph_panel = GraphPanel()
        raw_page = QWidget()
        raw_page_layout = QVBoxLayout(raw_page)
        raw_page_layout.setContentsMargins(0, 0, 0, 0)
        raw_page_layout.setSpacing(0)

        raw_header = QFrame(raw_page)
        raw_header.setObjectName("rawGraphHeader")
        raw_header.setStyleSheet(
            f"""
#rawGraphHeader {{
    background: {PALETTE["panel_bg"]};
    border-bottom: 1px solid {PALETTE["border"]};
}}
#rawGraphHeader QCheckBox {{
    color: {PALETTE["text"]};
    spacing: 6px;
}}
#rawGraphHeader QCheckBox:disabled {{
    color: {PALETTE["muted"]};
}}
#rawGraphHeader QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {PALETTE["border_strong"]};
    background: {PALETTE["card_bg"]};
}}
#rawGraphHeader QCheckBox::indicator:checked {{
    background: {PALETTE["accent"]};
    border-color: {PALETTE["accent"]};
}}
"""
        )
        raw_header_layout = QHBoxLayout(raw_header)
        raw_header_layout.setContentsMargins(10, 6, 10, 6)
        raw_header_layout.setSpacing(8)

        raw_header_title = QLabel("Raw signal", raw_header)
        raw_header_title.setStyleSheet(title_stylesheet())
        raw_header_layout.addWidget(raw_header_title)
        raw_header_layout.addStretch(1)

        self._raw_graph_controls = QWidget(raw_header)
        raw_controls_layout = QHBoxLayout(self._raw_graph_controls)
        raw_controls_layout.setContentsMargins(0, 0, 0, 0)
        raw_controls_layout.setSpacing(12)

        self._raw_control_toggle = QCheckBox(
            "Show control signal", self._raw_graph_controls
        )
        self._raw_control_toggle.setChecked(True)
        self._raw_control_toggle.setAccessibleName("Show raw control signal")
        self._raw_control_toggle.setToolTip(
            "Show or hide the 405 nm or 410 nm control signal."
        )
        raw_controls_layout.addWidget(self._raw_control_toggle)

        self._raw_individual_y_axes_toggle = QCheckBox(
            "Individual y-axes", self._raw_graph_controls
        )
        self._raw_individual_y_axes_toggle.setAccessibleName(
            "Use individual raw signal y-axes"
        )
        self._raw_individual_y_axes_toggle.setToolTip(
            "On: range-based axis for each signal. Off: one shared axis, padded from the widest signal range."
        )
        self._restore_raw_y_axis_mode()
        self._raw_control_toggle.toggled.connect(
            self._on_raw_control_visibility_changed
        )
        self._raw_individual_y_axes_toggle.toggled.connect(
            self._on_raw_y_axis_mode_changed
        )
        raw_controls_layout.addWidget(self._raw_individual_y_axes_toggle)
        raw_header_layout.addWidget(self._raw_graph_controls)
        self._raw_graph_controls.setVisible(False)
        self._raw_individual_y_axes_toggle.setVisible(False)
        self._raw_individual_y_axes_toggle.setEnabled(False)

        raw_page_layout.addWidget(raw_header)
        raw_page_layout.addWidget(self.raw_graph_panel, 1)
        self.notebook_graphs.addTab(raw_page, "Raw Data")

        # DFer Options tab — dropdown + full-canvas single-option plot
        dfer_opts_page = QWidget()
        dfer_opts_layout = QVBoxLayout(dfer_opts_page)
        dfer_opts_layout.setContentsMargins(0, 0, 0, 0)
        dfer_opts_layout.setSpacing(0)

        opts_bar = QWidget(dfer_opts_page)
        opts_bar.setStyleSheet(
            f"background: {PALETTE['panel_bg']}; "
            f"border-bottom: 1px solid {PALETTE['border']};"
        )
        opts_bar_layout = QHBoxLayout(opts_bar)
        opts_bar_layout.setContentsMargins(10, 6, 10, 6)
        opts_bar_layout.setSpacing(8)
        opts_bar_layout.addWidget(QLabel("Preview option:", opts_bar))
        self._option_preview_combo = QComboBox(opts_bar)
        self._option_preview_combo.addItems(_OPTION_TITLES)
        self._option_preview_combo.setStyleSheet(combo_stylesheet())
        self._option_preview_combo.currentIndexChanged.connect(
            self._on_option_dropdown_changed
        )
        opts_bar_layout.addWidget(self._option_preview_combo, 1)
        opts_bar_layout.addWidget(QLabel("Signals:", opts_bar))
        self._dual_option_display_combo = QComboBox(opts_bar)
        self._dual_option_display_combo.addItems(["Both", "470nm", "560nm"])
        self._dual_option_display_combo.setStyleSheet(combo_stylesheet())
        self._dual_option_display_combo.setEnabled(False)
        self._dual_option_display_combo.currentIndexChanged.connect(
            lambda _idx: self._render_option(self._option_preview_combo.currentIndex())
        )
        opts_bar_layout.addWidget(self._dual_option_display_combo)
        dfer_opts_layout.addWidget(opts_bar)

        self.dfer_options_graph = GraphPanel()
        dfer_opts_layout.addWidget(self.dfer_options_graph, 1)
        self.notebook_graphs.addTab(dfer_opts_page, "DFer Options")

        # DFer Results tab — channel dropdown + save button
        dfer_results_page = QWidget()
        dfer_results_layout = QVBoxLayout(dfer_results_page)
        dfer_results_layout.setContentsMargins(0, 0, 0, 0)
        dfer_results_layout.setSpacing(0)

        dfer_res_bar = QWidget(dfer_results_page)
        dfer_res_bar.setStyleSheet(
            f"background: {PALETTE['panel_bg']}; "
            f"border-bottom: 1px solid {PALETTE['border']};"
        )
        dfer_res_bar_layout = QHBoxLayout(dfer_res_bar)
        dfer_res_bar_layout.setContentsMargins(10, 6, 10, 6)
        dfer_res_bar_layout.setSpacing(8)
        dfer_res_bar_layout.addWidget(QLabel("Channel:", dfer_res_bar))
        self._dfer_results_combo = QComboBox(dfer_res_bar)
        self._dfer_results_combo.addItems(["dF/F", "Z-score"])
        self._dfer_results_combo.setStyleSheet(combo_stylesheet())
        self._dfer_results_combo.currentIndexChanged.connect(
            self._on_dfer_results_channel_changed
        )
        dfer_res_bar_layout.addWidget(self._dfer_results_combo)
        self._dfer_show_405_checkbox = QCheckBox("Show 405", dfer_res_bar)
        self._dfer_show_405_checkbox.setChecked(True)
        self._dfer_show_405_checkbox.toggled.connect(
            lambda _checked: self._on_dfer_results_channel_changed(0)
        )
        dfer_res_bar_layout.addWidget(self._dfer_show_405_checkbox)
        dfer_res_bar_layout.addStretch(1)
        btn_save_dfer = QPushButton("Save image", dfer_res_bar)
        apply_button_role(btn_save_dfer)
        btn_save_dfer.clicked.connect(
            lambda: self._save_graph_image(self.dfer_results_graph, "dfer_result")
        )
        dfer_res_bar_layout.addWidget(btn_save_dfer)
        dfer_results_layout.addWidget(dfer_res_bar)

        self.dfer_results_graph = GraphPanel()
        dfer_results_layout.addWidget(self.dfer_results_graph, 1)
        self.notebook_graphs.addTab(dfer_results_page, "DFer Results")

        # PFer Results tab — save button
        pfer_results_page = QWidget()
        pfer_results_layout = QVBoxLayout(pfer_results_page)
        pfer_results_layout.setContentsMargins(0, 0, 0, 0)
        pfer_results_layout.setSpacing(0)

        pfer_res_bar = QWidget(pfer_results_page)
        pfer_res_bar.setStyleSheet(
            f"background: {PALETTE['panel_bg']}; "
            f"border-bottom: 1px solid {PALETTE['border']};"
        )
        pfer_res_bar_layout = QHBoxLayout(pfer_res_bar)
        pfer_res_bar_layout.setContentsMargins(10, 6, 10, 6)
        pfer_res_bar_layout.setSpacing(8)
        pfer_res_bar_layout.addStretch(1)
        btn_save_pfer = QPushButton("Save image", pfer_res_bar)
        apply_button_role(btn_save_pfer)
        btn_save_pfer.clicked.connect(
            lambda: self._save_graph_image(self.pfer_graph, "pfer_result")
        )
        pfer_res_bar_layout.addWidget(btn_save_pfer)
        pfer_results_layout.addWidget(pfer_res_bar)

        self.pfer_graph = GraphPanel()
        pfer_results_layout.addWidget(self.pfer_graph, 1)
        self.notebook_graphs.addTab(pfer_results_page, "PFer Results")

        # ── settings tabs ──────────────────────────────────────────────────
        dfer_page = QWidget()
        dfer_page_layout = QVBoxLayout(dfer_page)
        dfer_page_layout.setContentsMargins(8, 8, 8, 8)
        dfer_page_layout.addWidget(self._build_dfer_settings_panel())
        self.notebook_settings.addTab(dfer_page, "DFer")

        pfer_page = QWidget()
        pfer_page_layout = QVBoxLayout(pfer_page)
        pfer_page_layout.setContentsMargins(8, 8, 8, 8)
        pfer_page_layout.addWidget(self._build_pfer_settings_panel())
        self.notebook_settings.addTab(pfer_page, "PFer")

        self._set_initial_tab_state()

    def _set_initial_tab_state(self) -> None:
        self.notebook_graphs.setTabEnabled(0, True)
        self.notebook_graphs.setTabEnabled(1, False)
        self.notebook_graphs.setTabEnabled(2, False)
        self.notebook_graphs.setTabEnabled(3, False)

    def _restore_raw_y_axis_mode(self) -> None:
        mode = str(getattr(self.settings_manager, "raw_dual_y_axis_mode", "shared"))
        self._raw_individual_y_axes_toggle.setChecked(mode == "individual")

    def _raw_y_axis_mode(self) -> str:
        return (
            "individual" if self._raw_individual_y_axes_toggle.isChecked() else "shared"
        )

    def _raw_show_control_signal(self) -> bool:
        return self._raw_control_toggle.isChecked()

    def _on_raw_y_axis_mode_changed(self, _checked: bool) -> None:
        mode = self._raw_y_axis_mode()
        self.settings_manager.raw_dual_y_axis_mode = mode
        self.settings_manager.save_variables()
        if self._selected_file:
            self._draw_raw_graph(self._selected_file)
            self._refresh_time_preview()

    def _on_raw_control_visibility_changed(self, _checked: bool) -> None:
        if self._selected_file:
            self._draw_raw_graph(self._selected_file)
            self._refresh_time_preview()

    def _set_raw_control_label(self, file_type: str) -> None:
        wavelength = "410 nm" if file_type == "dual" else "405 nm"
        self._raw_control_toggle.setText(f"Show {wavelength} control")

    # ── top panels ─────────────────────────────────────────────────────────

    def _build_data_selection_panel(self) -> QFrame:
        panel = QFrame(self.top_frame)
        panel.setObjectName("rawPhotDataPanel")
        panel.setStyleSheet(
            panel_stylesheet("rawPhotDataPanel") + section_stylesheet("rawPhotDataCard")
        )

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QLabel("Data Selection", panel)
        title.setStyleSheet(title_stylesheet())
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        card = QFrame(panel)
        card.setObjectName("rawPhotDataCard")
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(8, 8, 8, 8)
        card_layout.setSpacing(8)

        folder_btn = QPushButton("Select Folder", card)
        apply_button_role(folder_btn)
        folder_btn.clicked.connect(self._select_default_data_folder)
        folder_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        card_layout.addWidget(folder_btn)

        raw_btn = QPushButton("Raw Photometry File", card)
        apply_button_role(raw_btn)
        raw_btn.clicked.connect(self._select_file)
        raw_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        card_layout.addWidget(raw_btn)

        self.file_path_edit = QLineEdit(card)
        self.file_path_edit.setReadOnly(True)
        self.file_path_edit.setPlaceholderText(
            "Single-channel (405/465 nm) or dual-channel CSV/OFRS"
        )
        self.file_path_edit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        card_layout.addWidget(self.file_path_edit, 1)

        layout.addWidget(card)
        return panel

    def _build_analysis_window_panel(self) -> QFrame:
        panel = QFrame(self.top_frame)
        panel.setObjectName("rawPhotWindowPanel")
        panel.setStyleSheet(
            panel_stylesheet("rawPhotWindowPanel")
            + section_stylesheet("rawPhotWindowCard")
        )

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QLabel("Analysis Window", panel)
        title.setStyleSheet(title_stylesheet())
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        card = QFrame(panel)
        card.setObjectName("rawPhotWindowCard")
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(8, 8, 8, 8)
        card_layout.setSpacing(8)

        card_layout.addWidget(QLabel("Start (s)", card))
        self.start_time_edit = QLineEdit(card)
        self.start_time_edit.setPlaceholderText("start")
        self.start_time_edit.setFixedWidth(63)
        card_layout.addWidget(self.start_time_edit)

        card_layout.addWidget(QLabel("End (s)", card))
        self.end_time_edit = QLineEdit(card)
        self.end_time_edit.setPlaceholderText("end")
        self.end_time_edit.setFixedWidth(63)
        card_layout.addWidget(self.end_time_edit)

        dur_lbl = QLabel("Duration", card)
        card_layout.addWidget(dur_lbl)
        self.total_time_label = QLabel("—", card)
        self.total_time_label.setMinimumWidth(84)
        self.total_time_label.setStyleSheet(
            f"color: {PALETTE['accent']}; font-weight: 700;"
        )
        card_layout.addWidget(self.total_time_label)

        self.btn_apply_window = QPushButton("Apply", card)
        apply_button_role(self.btn_apply_window)
        self.btn_apply_window.clicked.connect(self._apply_window)
        self.btn_apply_window.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        card_layout.addWidget(self.btn_apply_window)

        self.start_time_edit.textChanged.connect(self._refresh_time_preview)
        self.end_time_edit.textChanged.connect(self._refresh_time_preview)

        layout.addWidget(card)
        return panel

    # ── DFer settings panel ────────────────────────────────────────────────

    def _build_dfer_settings_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("dferSettingsPanel")
        panel.setStyleSheet(
            panel_stylesheet("dferSettingsPanel")
            + section_stylesheet("dferChooseCard")
            + section_stylesheet("dferRunCard")
            + section_stylesheet("dferLogCard")
            + _spinbox_css("dferSettingsPanel")
        )
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QLabel("DFer Settings", panel)
        title.setStyleSheet(title_stylesheet())
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # ── Choose option and run ──────────────────────────────────────────
        choose_card = QFrame(panel)
        choose_card.setObjectName("dferChooseCard")
        choose_layout = QVBoxLayout(choose_card)
        choose_layout.setContentsMargins(8, 8, 8, 8)
        choose_layout.setSpacing(6)

        folder_row = QHBoxLayout()
        folder_row.setSpacing(6)
        btn_open_plots = QPushButton("Open plot folder", choose_card)
        apply_button_role(btn_open_plots)
        btn_open_plots.clicked.connect(
            lambda: self._open_current_output_folder("DFer outputs")
        )
        folder_row.addWidget(btn_open_plots)

        btn_open_results = QPushButton("Open DFer results", choose_card)
        apply_button_role(btn_open_results)
        btn_open_results.clicked.connect(
            lambda: self._open_current_output_folder("DFer results")
        )
        folder_row.addWidget(btn_open_results)
        choose_layout.addLayout(folder_row)

        choose_title = QLabel("Choose DFer option", choose_card)
        choose_title.setStyleSheet(section_title_stylesheet())
        choose_layout.addWidget(choose_title)

        self._opt_button_group = QButtonGroup(self)
        self._opt_buttons: dict[str, QRadioButton] = {}
        opt_labels = {
            "1": "1 = standard baseline and noise correction",
            "2": "2 = alternative baseline fit",
            "3": "3 = no noise correction",
            "4": "4 = no noise correction and no activity baseline correction",
            "5": "5 = independent 10% msbackadj (no 405/410 control)",
        }
        for key in ("1", "2", "3", "4", "5"):
            rb = QRadioButton(opt_labels[key], choose_card)
            self._opt_button_group.addButton(rb)
            self._opt_buttons[key] = rb
            rb.toggled.connect(
                lambda checked, option=key: self._on_dfer_option_radio_toggled(
                    option, checked
                )
            )
            choose_layout.addWidget(rb)
        self._restore_dfer_option_selection()

        run_title = QLabel("Run final DFer analysis", choose_card)
        run_title.setStyleSheet(section_title_stylesheet())
        choose_layout.addWidget(run_title)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        self.btn_run_final = QPushButton("Run final analysis", choose_card)
        apply_button_role(self.btn_run_final)
        self.btn_run_final.clicked.connect(self._on_run_final)
        btn_row.addWidget(self.btn_run_final)
        choose_layout.addLayout(btn_row)

        self._dfer_result_label = QLabel("No result yet.", choose_card)
        self._dfer_result_label.setWordWrap(True)
        self._dfer_result_label.setStyleSheet(subtitle_stylesheet())
        choose_layout.addWidget(self._dfer_result_label)
        layout.addWidget(choose_card)

        # ── Log ────────────────────────────────────────────────────────────
        log_card = QFrame(panel)
        log_card.setObjectName("dferLogCard")
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(8, 8, 8, 8)
        log_layout.setSpacing(4)

        log_title = QLabel("Log", log_card)
        log_title.setStyleSheet(section_title_stylesheet())
        log_layout.addWidget(log_title)

        self._log_edit = QPlainTextEdit(log_card)
        self._log_edit.setReadOnly(True)
        mono = QFont("Courier New", 9)
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self._log_edit.setFont(mono)
        self._log_edit.setStyleSheet(f"""
QPlainTextEdit {{
    background: {PALETTE["card_alt_bg"]};
    border: none;
    color: {PALETTE["muted"]};
    border-radius: 4px;
}}
""")
        log_layout.addWidget(self._log_edit, 1)
        layout.addWidget(log_card, 1)

        self._setup_log_handler()
        return panel

    def _setup_log_handler(self) -> None:
        self._teardown_log_handler()
        self._log_signal.connect(self._append_log)
        self._log_signal_connected = True
        handler = _QtLogHandler(self._log_signal)
        handler.setFormatter(logging.Formatter("%(levelname)s  %(message)s"))
        handler.setLevel(logging.DEBUG)
        self._log_handler = handler
        for name in ("src.dfer", "src.pfer", __name__):
            logger_obj = logging.getLogger(name)
            logger_obj.addHandler(handler)
            self._log_handler_loggers.append(logger_obj)
        logging.getLogger("src.dfer").setLevel(logging.DEBUG)

    def _append_log(self, msg: str) -> None:
        log_edit = self._log_edit
        if log_edit is None:
            return
        try:
            log_edit.appendPlainText(msg)
            scroll_bar = log_edit.verticalScrollBar()
            scroll_bar.setValue(scroll_bar.maximum())
        except RuntimeError:
            self._log_edit = None
            self._teardown_log_handler()

    def closeEvent(self, event) -> None:  # pragma: no cover - Qt lifecycle
        if not self.prepare_for_unload():
            event.ignore()
            return
        super().closeEvent(event)

    def prepare_for_unload(self) -> bool:
        self._unloading = True
        if not self._shutdown_for_close():
            self._unloading = False
            return False
        return True

    def _shutdown_for_close(self) -> bool:
        self._teardown_log_handler()
        if self._thread is not None and self._thread.isRunning():
            self._thread.quit()
            if not self._thread.wait(3000):
                # The dashboard will keep this tool alive when unload returns
                # False. Restore the handler that was detached at the start of
                # shutdown so the still-running tool remains fully usable.
                self._setup_log_handler()
                QMessageBox.information(
                    self,
                    "Still working",
                    "Analysis is still finishing. Close the window again when it is done.",
                )
                return False
            QApplication.processEvents()
        while QApplication.overrideCursor() is not None:
            QApplication.restoreOverrideCursor()
        for panel in (
            self.raw_graph_panel,
            self.dfer_options_graph,
            self.dfer_results_graph,
            self.pfer_graph,
        ):
            panel.clear()
        return True

    def _teardown_log_handler(self) -> None:
        if self._log_signal_connected:
            try:
                self._log_signal.disconnect(self._append_log)
            except RuntimeError:
                logging.getLogger(__name__).debug(
                    "Signal disconnect: Qt object already deleted"
                )
            self._log_signal_connected = False

        if self._log_handler is not None:
            for logger_obj in self._log_handler_loggers:
                logger_obj.removeHandler(self._log_handler)
            self._log_handler.close()
        self._log_handler_loggers.clear()
        self._log_handler = None

    # ── PFer settings panel ────────────────────────────────────────────────

    def _build_pfer_settings_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("pferSettingsPanel")
        panel.setStyleSheet(
            panel_stylesheet("pferSettingsPanel")
            + section_stylesheet("pferBaselineCard")
            + section_stylesheet("pferParamsCard")
            + section_stylesheet("pferRunCard")
            + _spinbox_css("pferSettingsPanel")
        )
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QLabel("PFer Settings", panel)
        title.setStyleSheet(title_stylesheet())
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # ── Baseline window ────────────────────────────────────────────────
        base_card = QFrame(panel)
        base_card.setObjectName("pferBaselineCard")
        base_layout = QVBoxLayout(base_card)
        base_layout.setContentsMargins(8, 8, 8, 8)
        base_layout.setSpacing(6)

        base_title = QLabel(
            "Baseline window for PFer normalization (seconds, optional)", base_card
        )
        base_title.setStyleSheet(section_title_stylesheet())
        base_title.setWordWrap(True)
        base_layout.addWidget(base_title)

        base_form = QFormLayout()
        base_form.setHorizontalSpacing(8)
        base_form.setVerticalSpacing(6)
        self._pfer_start_edit = QLineEdit(base_card)
        self._pfer_start_edit.setPlaceholderText("blank = use full trace")
        self._pfer_end_edit = QLineEdit(base_card)
        self._pfer_end_edit.setPlaceholderText("blank = use full trace")
        base_form.addRow("Start:", self._pfer_start_edit)
        base_form.addRow("End:", self._pfer_end_edit)
        base_layout.addLayout(base_form)
        layout.addWidget(base_card)

        # ── Peak-finding parameters ────────────────────────────────────────
        param_card = QFrame(panel)
        param_card.setObjectName("pferParamsCard")
        param_layout = QVBoxLayout(param_card)
        param_layout.setContentsMargins(8, 8, 8, 8)
        param_layout.setSpacing(6)

        param_title = QLabel("Peak-finding parameters", param_card)
        param_title.setStyleSheet(section_title_stylesheet())
        param_layout.addWidget(param_title)

        param_form = QFormLayout()
        param_form.setHorizontalSpacing(8)
        param_form.setVerticalSpacing(6)

        self._prominence_spin = QDoubleSpinBox(param_card)
        self._prominence_spin.setRange(0.0001, 1.0)
        self._prominence_spin.setSingleStep(0.001)
        self._prominence_spin.setDecimals(4)
        self._prominence_spin.setValue(0.003)
        self._prominence_spin.setToolTip("Minimum peak prominence in dF/F.")

        self._artifact_spin = QSpinBox(param_card)
        self._artifact_spin.setRange(1, 500)
        self._artifact_spin.setValue(10)
        self._artifact_spin.setToolTip("Minimum samples between trough onset and peak.")

        param_form.addRow("Prominence:", self._prominence_spin)
        param_form.addRow("Artifact threshold:", self._artifact_spin)
        param_layout.addLayout(param_form)
        layout.addWidget(param_card)

        # ── Run PFer ───────────────────────────────────────────────────────
        run_card = QFrame(panel)
        run_card.setObjectName("pferRunCard")
        run_layout = QVBoxLayout(run_card)
        run_layout.setContentsMargins(8, 8, 8, 8)
        run_layout.setSpacing(6)

        run_title = QLabel("Run PFer", run_card)
        run_title.setStyleSheet(section_title_stylesheet())
        run_layout.addWidget(run_title)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        self.btn_run_pfer = QPushButton("Run peak finder", run_card)
        apply_button_role(self.btn_run_pfer)
        self.btn_run_pfer.clicked.connect(self._on_run_pfer)
        btn_row.addWidget(self.btn_run_pfer)

        btn_open_pfer = QPushButton("Open PFer results", run_card)
        apply_button_role(btn_open_pfer)
        btn_open_pfer.clicked.connect(
            lambda: self._open_current_output_folder("PFer results")
        )
        btn_row.addWidget(btn_open_pfer)
        run_layout.addLayout(btn_row)
        layout.addWidget(run_card)

        layout.addStretch(1)
        return panel

    # ── threading helpers ──────────────────────────────────────────────────

    def _start_worker(self, fn, kwargs: dict, on_success, on_error) -> None:
        self._thread = QThread(self)
        self._worker = _Worker(fn, kwargs)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(on_success)
        self._worker.failed.connect(on_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._cleanup_worker)
        self._thread.start()

    def _cleanup_worker(self) -> None:
        self._thread = None
        self._worker = None

    def _set_busy(self, busy: bool) -> None:
        self.btn_run_final.setEnabled(not busy)
        self.btn_run_pfer.setEnabled(not busy)
        self.btn_apply_window.setEnabled(not busy)
        if busy:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        else:
            QApplication.restoreOverrideCursor()

    # ── folder opener ──────────────────────────────────────────────────────

    def _open_folder(self, path: str, label: str) -> None:
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            _open_path(path)
        except Exception as exc:
            show_action_error(
                "Folder could not be opened",
                f"NeuroSyncApp could not open the {label.lower()}",
                exc,
                self,
                "Check that the folder is available and that you have permission to access it.",
            )

    def _open_current_output_folder(self, label: str) -> None:
        if self._output_folder is None:
            QMessageBox.warning(
                self,
                "No output folder",
                "Select a raw photometry file first.",
            )
            return
        self._open_folder(self._output_folder, label)

    # ── file selection ─────────────────────────────────────────────────────

    def _select_default_data_folder(self) -> None:
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Default Data Folder",
            self.settings_manager.default_data_folder_path or "",
        )
        if folder_path:
            self.settings_manager.default_data_folder_path = folder_path
            self.settings_manager.save_variables()

    def _select_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Photometry Data File",
            self.settings_manager.default_data_folder_path or "",
            "Photometry Files (*.csv *.ofrs);;CSV Files (*.csv);;OFRS Files (*.ofrs);;All Files (*.*)",
        )
        if file_path:
            self._load_photometry_file(file_path)

    def _load_photometry_file(self, file_path: str) -> None:
        try:
            self._draw_raw_graph(file_path)
        except Exception as exc:
            show_action_error(
                "Photometry file not recognised",
                "NeuroSyncApp could not load the selected photometry file",
                exc,
                self,
                "Select the original raw photometry CSV or OFRS recording rather than a processed DFer or PFer output file.",
            )
            return
        file_type, _ = detect_photometry_file_type(file_path)
        self._selected_file = file_path
        is_dual = file_type == "dual"
        self._set_raw_control_label(file_type)
        self._raw_graph_controls.setVisible(True)
        self._raw_control_toggle.setEnabled(True)
        self._raw_individual_y_axes_toggle.setVisible(is_dual)
        self._raw_individual_y_axes_toggle.setEnabled(is_dual)
        if is_dual:
            self._output_folder = str(Path(file_path).parent.parent / "dfof_results")
        else:
            self._output_folder = str(Path(file_path).parent / "dfof_results")
        self.file_path_edit.setText(file_path)
        self._options_data = None
        self._dfer_result_csv = None
        self._dfer_result_frame = None
        self._pfer_selected_csv = None
        self.notebook_graphs.setTabEnabled(1, True)
        self.notebook_graphs.setTabEnabled(2, False)
        self.notebook_graphs.setTabEnabled(3, False)
        self.notebook_settings.setCurrentIndex(0)
        self._refresh_time_preview()
        self.notebook_graphs.setCurrentIndex(0)
        self._append_log(f"INFO  [DFer] Selected: {file_path}")
        self._on_generate_options(show_missing_file_warning=False)

    # ── raw graph ──────────────────────────────────────────────────────────

    def _draw_raw_graph(self, file_path: str) -> None:
        file_type, skiprows = detect_photometry_file_type(file_path)
        if file_type == "single":
            df = pd.read_csv(file_path, index_col=False, low_memory=False)
            validate_single_df(df)
            t = df["#time(seconds)"][1:].to_numpy(dtype=float)
            y405 = df["405nm"][1:].to_numpy(dtype=float)
            y465_col = "465nm" if "465nm" in df.columns else "490nm"
            y465 = df[y465_col][1:].to_numpy(dtype=float)
            self._draw_single_raw(t, y405, y465, y465_col)
        else:
            df = load_dual_photometry(file_path, skiprows)
            validate_dual_df(df)
            t = df["TimeStamp"].astype(float).to_numpy() / 1000.0
            y410 = df["CH1-410"].astype(float).to_numpy()
            y470 = df["CH1-470"].astype(float).to_numpy()
            y560 = df["CH1-560"].astype(float).to_numpy()
            self._draw_dual_raw(t, y410, y470, y560)

    def _draw_single_raw(
        self,
        t: np.ndarray,
        y405: np.ndarray,
        y465: np.ndarray,
        signal_label: str = "465nm",
    ) -> None:
        figure = Figure(figsize=(10, 4), dpi=100)
        ax465 = cast(Axes, figure.add_subplot(111))
        ax405 = cast(Axes, ax465.twinx())
        time_start, time_end = _raw_time_bounds(t)

        show_control = self._raw_show_control_signal()
        ax465.plot(
            t,
            y465,
            color="green",
            linewidth=0.6,
            alpha=_RAW_INDIVIDUAL_SIGNAL_ALPHA,
        )
        ax465.set_ylabel(signal_label, color="green")
        ax465.tick_params(axis="y", colors="green")
        ax465.spines["left"].set_color("green")
        ax465.set_ylim(*_signal_axis_limits(y465, _RAW_LARGER_SIGNAL_OCCUPANCY))
        if show_control:
            ax405.plot(
                t,
                y405,
                color="purple",
                linewidth=0.6,
                alpha=_RAW_INDIVIDUAL_CONTROL_ALPHA,
            )
            ax405.set_ylabel("405nm", color="purple")
            ax405.tick_params(axis="y", colors="purple")
            ax405.spines["right"].set_color("purple")
            ax405.set_ylim(*_signal_axis_limits(y405, _RAW_CONTROL_OCCUPANCY))
        else:
            ax405.set_visible(False)

        for axis in (ax465, ax405):
            axis.yaxis.label.set_visible(False)

        start_line = ax465.axvline(
            x=time_start,
            color="red",
            linestyle="--",
            linewidth=1.5,
            label="Window start",
        )
        end_line = ax465.axvline(
            x=time_end,
            color="blue",
            linestyle="--",
            linewidth=1.5,
            label="Window end",
        )
        ax465.set_title("Raw Data — single channel")
        ax465.set_xlabel("Time (s)")
        ax465.set_xlim((time_start, time_end))
        handles, labels = ax465.get_legend_handles_labels()
        ax465.legend(handles, labels, fontsize=8, loc="upper right")
        _tighten_time_axes(figure)
        figure.tight_layout()
        figure.subplots_adjust(bottom=_RAW_GRAPH_BOTTOM_MARGIN)

        self._raw_graph_ref = GraphReference(
            figure,
            ax465,
            ax405,
            start_line,
            end_line,
            time_start,
            time_end,
        )
        self.raw_graph_panel.set_figure(figure, compact_axis_labels=True)

    def _draw_dual_raw(
        self,
        t: np.ndarray,
        y410: np.ndarray,
        y470: np.ndarray,
        y560: np.ndarray,
    ) -> None:
        figure = Figure(figsize=(10, 4), dpi=100)
        axis470 = cast(Axes, figure.add_subplot(111))
        time_start, time_end = _raw_time_bounds(t)
        individual_axes = self._raw_y_axis_mode() == "individual"
        show_control = self._raw_show_control_signal()
        line410: Line2D | None = None
        span470 = _signal_span(y470)
        span560 = _signal_span(y560)
        if span470 >= span560:
            occupancy470 = _RAW_LARGER_SIGNAL_OCCUPANCY
            occupancy560 = _RAW_SMALLER_SIGNAL_OCCUPANCY
        else:
            occupancy470 = _RAW_SMALLER_SIGNAL_OCCUPANCY
            occupancy560 = _RAW_LARGER_SIGNAL_OCCUPANCY

        if individual_axes:
            axis410 = cast(Axes, axis470.twinx())
            axis560 = cast(Axes, axis470.twinx())
            axis410.spines["right"].set_position(("axes", 1.0))
            axis560.spines["right"].set_position(
                ("axes", 1.06 if show_control else 1.0)
            )
            axis410.patch.set_visible(False)
            axis560.patch.set_visible(False)

            line470 = axis470.plot(
                t,
                y470,
                color="green",
                linewidth=0.6,
                alpha=_RAW_INDIVIDUAL_SIGNAL_ALPHA,
                label="470nm",
            )[0]
            line560 = axis560.plot(
                t,
                y560,
                color="red",
                linewidth=0.6,
                alpha=_RAW_INDIVIDUAL_SIGNAL_ALPHA,
                label="560nm",
            )[0]
            axis470.set_ylabel("470nm", color="green")
            axis470.tick_params(axis="y", colors="green")
            axis470.spines["left"].set_color("green")
            axis470.set_ylim(*_signal_axis_limits(y470, occupancy470))
            if show_control:
                line410 = axis410.plot(
                    t,
                    y410,
                    color="purple",
                    linewidth=0.6,
                    alpha=_RAW_INDIVIDUAL_CONTROL_ALPHA,
                    label="410nm control",
                )[0]
                axis410.set_ylabel("410nm", color="purple")
                axis410.tick_params(axis="y", colors="purple")
                axis410.spines["right"].set_color("purple")
                axis410.set_ylim(*_signal_axis_limits(y410, _RAW_CONTROL_OCCUPANCY))
            else:
                axis410.set_visible(False)
            axis560.set_ylabel("560nm", color="red")
            axis560.tick_params(axis="y", colors="red")
            axis560.spines["right"].set_color("red")
            axis560.set_ylim(*_signal_axis_limits(y560, occupancy560))
            secondary_axis = axis410 if show_control else axis560
        else:
            displayed_signals = [y470, y560]
            if show_control:
                line410 = axis470.plot(
                    t,
                    y410,
                    color="purple",
                    linewidth=0.6,
                    alpha=_RAW_INDIVIDUAL_CONTROL_ALPHA,
                    label="410nm control",
                )[0]
                displayed_signals.insert(0, y410)
            line470 = axis470.plot(
                t,
                y470,
                color="green",
                linewidth=0.6,
                alpha=_RAW_INDIVIDUAL_SIGNAL_ALPHA,
                label="470nm",
            )[0]
            line560 = axis470.plot(
                t,
                y560,
                color="red",
                linewidth=0.6,
                alpha=_RAW_INDIVIDUAL_SIGNAL_ALPHA,
                label="560nm",
            )[0]
            axis470.set_ylim(*_shared_signal_axis_limits(displayed_signals))
            axis470.set_ylabel("470nm", color="black")
            axis470.tick_params(axis="y", colors="black")
            axis470.spines["left"].set_color("black")
            secondary_axis = None

        for axis in figure.axes:
            if axis.get_visible() and axis.get_ylabel():
                axis.yaxis.label.set_visible(False)

        axis470.set_xlabel("Time (s)")
        axis470.set_title("Raw Data — dual channel")
        start_line = axis470.axvline(
            x=time_start,
            color="black",
            linestyle="--",
            linewidth=1.2,
            label="Window start",
        )
        end_line = axis470.axvline(
            x=time_end,
            color="blue",
            linestyle="--",
            linewidth=1.2,
            label="Window end",
        )
        axis470.set_xlim((time_start, time_end))
        handles = [line470, line560, start_line, end_line]
        legend_labels = ["470nm", "560nm", "Window start", "Window end"]
        if line410 is not None:
            handles.insert(0, line410)
            legend_labels.insert(0, "410nm control")
        axis470.legend(handles, legend_labels, fontsize=8, loc="upper right")
        _tighten_time_axes(figure)
        figure.tight_layout()
        figure.subplots_adjust(bottom=_RAW_GRAPH_BOTTOM_MARGIN)
        if individual_axes:
            figure.subplots_adjust(right=0.90 if show_control else 0.94)

        self._raw_graph_ref = GraphReference(
            figure,
            axis470,
            secondary_axis,
            start_line,
            end_line,
            time_start,
            time_end,
        )
        self.raw_graph_panel.set_figure(figure, compact_axis_labels=True)

    # ── time window ────────────────────────────────────────────────────────

    def _refresh_time_preview(self) -> None:
        ref = self._raw_graph_ref
        if ref is None:
            return
        t_min_val, t_max_val = ref.time_start, ref.time_end
        try:
            start = _parse_window_endpoint(
                self.start_time_edit.text(), t_min_val, {"start", "min"}
            )
            end = _parse_window_endpoint(
                self.end_time_edit.text(), t_max_val, {"end", "max"}
            )
        except ValueError:
            self.total_time_label.setText("Invalid")
            return
        start = max(start, t_min_val)
        end = min(end, t_max_val)
        if end <= start:
            self.total_time_label.setText("Invalid")
            return
        self.total_time_label.setText(_format_duration(end - start))
        ref.start_line.set_xdata([start, start])
        ref.end_line.set_xdata([end, end])
        canvas = ref.figure.canvas
        if canvas:
            try:
                canvas.draw()
            except RuntimeError:
                logging.getLogger(__name__).debug(
                    "Raw graph redraw skipped: Qt canvas already deleted"
                )

    def _apply_window(self) -> None:
        """Apply the current start/end window to the raw graph markers."""
        if not self._selected_file:
            QMessageBox.warning(
                self, "No file", "Please select a raw photometry file first."
            )
            return
        self._refresh_time_preview()
        self._append_log("INFO  [DFer] Analysis window updated.")
        self._on_generate_options(show_missing_file_warning=False)

    def _window_inputs(self) -> tuple[str, str]:
        return (
            _normalise_window_input(self.start_time_edit.text(), {"start", "min"}),
            _normalise_window_input(self.end_time_edit.text(), {"end", "max"}),
        )

    def _selected_option(self) -> str:
        for key, btn in self._opt_buttons.items():
            if btn.isChecked():
                return key
        return "1"

    def _restore_dfer_option_selection(self) -> None:
        option = str(getattr(self.settings_manager, "last_run_dfer_option", "1"))
        if option not in self._opt_buttons:
            option = "1"
        self._opt_buttons[option].setChecked(True)

    def _save_dfer_option_selection(self, option: str) -> None:
        if option not in self._opt_buttons:
            return
        self.settings_manager.last_run_dfer_option = option
        self.settings_manager.save_variables()

    def _set_dfer_option_button(self, option: str) -> None:
        if option not in self._opt_buttons:
            return
        button = self._opt_buttons[option]
        if button.isChecked():
            return
        for candidate in self._opt_buttons.values():
            candidate.blockSignals(True)
        try:
            button.setChecked(True)
        finally:
            for candidate in self._opt_buttons.values():
                candidate.blockSignals(False)

    def _on_dfer_option_radio_toggled(self, option: str, checked: bool) -> None:
        if not checked or option not in self._opt_buttons:
            return
        try:
            index = int(option) - 1
        except ValueError:
            return
        self._option_preview_combo.blockSignals(True)
        try:
            self._option_preview_combo.setCurrentIndex(index)
        finally:
            self._option_preview_combo.blockSignals(False)
        self._render_option(index)

    # ── DFer option plots ──────────────────────────────────────────────────

    def _on_generate_options(self, show_missing_file_warning: bool = True) -> None:
        if not self._selected_file:
            if show_missing_file_warning:
                QMessageBox.warning(
                    self, "No file", "Please select a raw photometry file first."
                )
            return
        w_start, w_end = self._window_inputs()
        self._set_busy(True)
        self._start_worker(
            compute_options,
            {"selectedfile": self._selected_file, "w_start": w_start, "w_end": w_end},
            self._options_done,
            self._options_failed,
        )

    def _options_done(self, data: object) -> None:
        if self._unloading:
            return
        self._set_busy(False)
        if not isinstance(data, dict):
            self._options_failed(TypeError("DFer preview returned invalid data"))
            return
        self._options_data = data
        try:
            is_dual = data.get("file_type") == "dual"
            self._configure_option_signal_selector(is_dual)
            self._render_option(self._option_preview_combo.currentIndex())
            self._append_log(
                "INFO  [DFer] Preview complete. Choose option 1-5, then run final."
            )
        except Exception as exc:
            show_action_error(
                "DFer preview could not be displayed",
                "DFer generated preview data but NeuroSyncApp could not draw the plot",
                exc,
                self,
                "Try regenerating the preview. If the problem continues, check the application log.",
            )

    def _options_failed(self, error: object) -> None:
        if self._unloading:
            return
        self._set_busy(False)
        exc = error if isinstance(error, BaseException) else RuntimeError(str(error))
        QMessageBox.critical(
            self,
            "DFer preview failed",
            format_action_error(
                "DFer could not generate the option preview",
                exc,
                "Check the CSV or OFRS format and ensure the analysis window contains at least 120 seconds of numeric data.",
            ),
        )

    def _render_option(self, idx: int) -> None:
        if self._options_data is None:
            return
        dual_display = {
            "Both": "both",
            "470nm": "470",
            "560nm": "560",
        }.get(self._dual_option_display_combo.currentText(), "both")
        fig = _mpl_single_option_figure(self._options_data, idx, dual_display)
        self.dfer_options_graph.set_figure(fig)

    def _on_option_dropdown_changed(self, idx: int) -> None:
        if 0 <= idx < len(_OPTION_TITLES):
            self._set_dfer_option_button(str(idx + 1))
        self._render_option(idx)

    def _configure_option_signal_selector(self, is_dual: bool) -> None:
        self._dual_option_display_combo.blockSignals(True)
        self._dual_option_display_combo.clear()
        if is_dual:
            self._dual_option_display_combo.addItems(["Both", "470nm", "560nm"])
            self._dual_option_display_combo.setEnabled(True)
        else:
            signal_label = "465nm"
            if isinstance(self._options_data, dict):
                signal_label = str(self._options_data.get("signal_label", signal_label))
            self._dual_option_display_combo.addItem(signal_label)
            self._dual_option_display_combo.setEnabled(False)
        self._dual_option_display_combo.blockSignals(False)

    # ── DFer Results rendering ─────────────────────────────────────────────

    def _render_dfer_results(self, csv_path: str) -> None:
        """Render the DFer Results graph for the currently selected graph type."""
        graph = "zscore" if self._dfer_results_combo.currentIndex() == 1 else "dfof"
        loaded_new_result = (
            self._dfer_result_frame is None or self._dfer_result_csv != csv_path
        )
        result_frame: pd.DataFrame | None
        if loaded_new_result:
            result_frame = _normalise_dfer_result_frame(read_analysis_output(csv_path))
            self._dfer_result_frame = result_frame
            self._dfer_result_csv = csv_path
        else:
            result_frame = self._dfer_result_frame
        if result_frame is None:
            return
        is_dual = "dFoF_470" in result_frame.columns
        uses_independent_msbackadj = analysis_option_from_frame(result_frame) == 5
        show_405_available = not is_dual and not uses_independent_msbackadj
        self._dfer_show_405_checkbox.blockSignals(True)
        self._dfer_show_405_checkbox.setEnabled(show_405_available)
        if not show_405_available:
            self._dfer_show_405_checkbox.setChecked(False)
        elif loaded_new_result:
            self._dfer_show_405_checkbox.setChecked(True)
        self._dfer_show_405_checkbox.blockSignals(False)
        show_405 = self._dfer_show_405_checkbox.isChecked()
        fig = _mpl_dfer_results_figure_from_frame(result_frame, graph, show_405)
        self.dfer_results_graph.set_figure(fig)

    def _on_dfer_results_channel_changed(self, idx: int) -> None:
        if self._dfer_result_csv:
            self._render_dfer_results(self._dfer_result_csv)

    # ── Save graph image ───────────────────────────────────────────────────

    def _plot_export_base(self, default_stem: str) -> tuple[Path, str]:
        if self._dfer_result_csv:
            result_stem = _strip_data_suffix(Path(self._dfer_result_csv).stem)
        elif self._selected_file:
            selected = Path(self._selected_file)
            try:
                file_type, _ = detect_photometry_file_type(selected)
            except Exception:
                file_type = "single"
            result_stem = (
                f"{selected.parent.name}_Dual" if file_type == "dual" else selected.stem
            )
        else:
            result_stem = default_stem

        safe_stem = _safe_path_part(result_stem)
        recording_name = safe_stem.removesuffix("_Dual")
        output_base = Path(self._output_folder or path_config.module)
        plots_root = output_base.parent / "plots"
        return plots_root / _safe_path_part(recording_name), safe_stem

    def _next_plot_path(self, default_stem: str) -> Path:
        plot_dir, base_stem = self._plot_export_base(default_stem)
        plot_dir.mkdir(parents=True, exist_ok=True)
        index = self._plot_save_counts.get(base_stem, 0) + 1
        self._plot_save_counts[base_stem] = index
        return plot_dir / f"{base_stem}_plot_{index}.png"

    def _save_graph_image(self, panel: GraphPanel, default_stem: str) -> None:
        if panel.canvas is None:
            QMessageBox.warning(
                self, "No plot", "Nothing to save — run the analysis first."
            )
            return
        path = self._next_plot_path(default_stem)
        try:
            panel.canvas.figure.savefig(path, dpi=150, bbox_inches="tight")
        except Exception as exc:
            show_action_error(
                "Plot image could not be saved",
                "NeuroSyncApp could not save the plot image",
                exc,
                self,
                "Check the output-folder permissions and available disk space, then try again.",
            )
            return
        self._append_log(f"INFO  [Plot] Saved image: {path}")

    # ── DFer final analysis ────────────────────────────────────────────────

    def _on_run_final(self) -> None:
        if not self._selected_file:
            QMessageBox.warning(
                self, "No file", "Please select a photometry file first."
            )
            return
        w_start, w_end = self._window_inputs()
        option = self._selected_option()
        self._save_dfer_option_selection(option)
        self._set_busy(True)
        self._start_worker(
            run_analysis,
            {
                "selectedfile": self._selected_file,
                "w_start": w_start,
                "w_end": w_end,
                "analysis_path": option,
                "make_plots": False,
                "mode": "full",
                "plot_stage": "final",
            },
            self._run_final_done,
            self._run_final_failed,
        )

    def _run_final_done(self, out_csv: object) -> None:
        if self._unloading:
            return
        self._set_busy(False)
        self._dfer_result_csv = str(out_csv) if out_csv else None
        self._dfer_result_frame = None
        if self._dfer_result_csv:
            self._dfer_result_label.setText(
                f"Saved: {Path(self._dfer_result_csv).name}"
            )
            self._dfer_result_label.setStyleSheet(
                f"color: {PALETTE['accent']}; font-size: 11px;"
            )
            try:
                self._render_dfer_results(self._dfer_result_csv)
                self.notebook_graphs.setTabEnabled(2, True)
                self.notebook_graphs.setCurrentIndex(2)
            except Exception as exc:
                QMessageBox.warning(
                    self,
                    "DFer result plot unavailable",
                    format_action_error(
                        "DFer completed and saved its output, but the result plot could not be displayed",
                        exc,
                        "The CSV result is still available in the DFer output folder.",
                    ),
                )
        else:
            self._dfer_result_label.setText(
                "Analysis complete — no output path returned."
            )

    def _run_final_failed(self, error: object) -> None:
        if self._unloading:
            return
        self._set_busy(False)
        exc = error if isinstance(error, BaseException) else RuntimeError(str(error))
        QMessageBox.critical(
            self,
            "DFer analysis failed",
            format_action_error(
                "DFer could not complete the analysis",
                exc,
                "Check the selected raw CSV or OFRS file, analysis window, and output-folder permissions, then try again.",
            ),
        )

    # ── PFer ───────────────────────────────────────────────────────────────

    def _on_run_pfer(self) -> None:
        if not self._pfer_selected_csv:
            QMessageBox.warning(
                self, "No file", "Please select a DFer output CSV first."
            )
            return
        self._set_busy(True)
        self._start_worker(
            run_pfer,
            {
                "csv_path": self._pfer_selected_csv,
                "w_start": self._pfer_start_edit.text().strip(),
                "w_end": self._pfer_end_edit.text().strip(),
                "prominence": self._prominence_spin.value(),
                "artifact_threshold": self._artifact_spin.value(),
                "make_plots": False,
            },
            self._pfer_done,
            self._pfer_failed,
        )

    def _pfer_done(self, out_csv: object) -> None:
        if self._unloading:
            return
        self._set_busy(False)
        if not out_csv:
            QMessageBox.information(self, "PFer complete", "Peak finding complete.")
            return
        stats_csv = str(out_csv).splitlines()[0]
        csv_path = self._pfer_selected_csv
        if not csv_path:
            QMessageBox.warning(
                self,
                "PFer result plot unavailable",
                "PFer completed, but its source DFer CSV is no longer selected.",
            )
            return
        try:
            fig = mpl_pfer_figure(csv_path, stats_csv)
            self.pfer_graph.set_figure(fig)
            self.notebook_graphs.setTabEnabled(3, True)
            self.notebook_graphs.setCurrentIndex(3)
        except Exception as exc:
            QMessageBox.warning(
                self,
                "PFer result plot unavailable",
                format_action_error(
                    "PFer completed and saved its output, but the peak plot could not be displayed",
                    exc,
                    "The PFer statistics CSV is still available in the output folder.",
                ),
            )

    def _pfer_failed(self, error: object) -> None:
        if self._unloading:
            return
        self._set_busy(False)
        exc = error if isinstance(error, BaseException) else RuntimeError(str(error))
        QMessageBox.critical(
            self,
            "PFer analysis failed",
            format_action_error(
                "PFer could not complete peak finding",
                exc,
                "Select a DFer result CSV and check the baseline and peak settings before retrying.",
            ),
        )
