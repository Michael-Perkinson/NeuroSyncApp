from __future__ import annotations

import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PySide6.QtCore import QObject, Qt, QThread, Signal
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

from src import default_dirs
from src.core.app_settings_manager import AppSettingsManager
from src.dfer import compute_options, run_analysis, run_pfer
from src.dfer.df_common import detect_photometry_file_type
from src.dfer.df_plots import mpl_pfer_figure
from src.gui.shared.qt_view_styles import (
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
    return float(value)


def _normalise_window_input(text: str, aliases: set[str]) -> str:
    value = text.strip()
    if not value or value.lower() in aliases:
        return ""
    return value


def _safe_path_part(value: str) -> str:
    safe = "".join(c if c not in '<>:"/\\|?*' else "_" for c in value).strip()
    return safe or "recording"


def _strip_data_suffix(stem: str) -> str:
    if stem.endswith("_Dual_Data"):
        return stem.removesuffix("_Data")
    if stem.endswith("_Data"):
        return stem.removesuffix("_Data")
    return stem


def _graph_time_values(axis) -> np.ndarray | None:
    values: list[float] = []
    for line in axis.lines:
        x_data = np.asarray(line.get_xdata(), dtype=float)
        if x_data.size:
            values.extend([float(np.nanmin(x_data)), float(np.nanmax(x_data))])
    if not values:
        return None
    return np.asarray(values, dtype=float)


def _tighten_time_axes(figure: Figure) -> None:
    for axis in figure.axes:
        values = _graph_time_values(axis)
        if values is None:
            continue
        finite = values[np.isfinite(values)]
        if finite.size == 0:
            continue
        x_min = float(np.min(finite))
        x_max = float(np.max(finite))
        if x_min == x_max:
            axis.set_xlim(x_min - 0.5, x_max + 0.5)
        else:
            pad = (x_max - x_min) * 0.005
            axis.set_xlim(x_min - pad, x_max + pad)
        axis.margins(x=0)


_OPTION_TITLES = [
    "Option 1: Good noise correction and bleach correction",
    "Option 2: Assumes shifts in 465 baseline are independent of activity",
    "Option 3: No noise correction",
    "Option 4: No noise correction, no activity-dependent baseline correction",
]


def _normalise_dfer_result_frame(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lstrip("#").strip() for c in df.columns]
    return df


def _mpl_dfer_results_figure_from_frame(
    df: pd.DataFrame,
    graph: str = "dfof",
    show_405: bool = True,
) -> Figure:
    """Return a single-panel DFer result figure from a normalised result frame."""
    df = _normalise_dfer_result_frame(df)
    t_min = df["t_min"].to_numpy(dtype=float)
    is_dual = "dFoF_470" in df.columns

    fig = Figure(figsize=(12, 4), tight_layout=True)
    ax = fig.add_subplot(1, 1, 1)

    if is_dual:
        if graph == "dfof":
            ax.plot(
                t_min,
                df["dFoF_470"].to_numpy(dtype=float),
                color="green",
                linewidth=0.6,
                alpha=0.55,
                label="470nm dF/F",
            )
            ax.plot(
                t_min,
                df["dFoF_560"].to_numpy(dtype=float),
                color="red",
                linewidth=0.6,
                alpha=0.4,
                label="560nm dF/F",
            )
            ax.set_ylabel("dF/F")
        else:
            ax.plot(
                t_min,
                df["Z_470"].to_numpy(dtype=float),
                color="green",
                linewidth=0.6,
                alpha=0.55,
                label="470nm Z-score",
            )
            ax.plot(
                t_min,
                df["Z_560"].to_numpy(dtype=float),
                color="red",
                linewidth=0.6,
                alpha=0.4,
                label="560nm Z-score",
            )
            ax.set_ylabel("Z-score")
    else:
        if graph == "dfof":
            if show_405:
                ax.plot(t_min, df["dFoF_405"].to_numpy(dtype=float), color="purple", linewidth=0.6, label="405nm dF/F")
            ax.plot(t_min, df["dFoF_465"].to_numpy(dtype=float), color="green", linewidth=0.6, label="465nm dF/F")
            ax.set_ylabel("dF/F")
        else:
            if show_405:
                ax.plot(t_min, df["Z_405"].to_numpy(dtype=float), color="purple", linewidth=0.6, label="405nm Z-score")
            ax.plot(t_min, df["Z_465"].to_numpy(dtype=float), color="green", linewidth=0.6, label="465nm Z-score")
            ax.set_ylabel("Z-score")

    ax.set_xlabel("Time (min)")
    ax.legend(fontsize=8, loc="upper right")
    _tighten_time_axes(fig)
    return fig


def _mpl_dfer_results_figure(csv_path: str, graph: str = "dfof", show_405: bool = True) -> Figure:
    """Read a DFer output CSV and return a single-panel matplotlib Figure.

    graph: 'dfof' | 'zscore'
    Always shows all channels together (both 470+560 for dual, 405+465 for single).
    """
    df = pd.read_csv(csv_path, index_col=False)
    return _mpl_dfer_results_figure_from_frame(df, graph, show_405)


def _mpl_single_option_figure(data: dict, idx: int, dual_display: str = "both") -> Figure:
    """Render one DFer option as a full-canvas figure."""
    t = data["t_min"]
    file_type = data.get("file_type", "single")
    title = _OPTION_TITLES[idx]

    fig = Figure(figsize=(12, 4), tight_layout=True)
    ax = fig.add_subplot(1, 1, 1)

    if file_type == "single":
        adj_key = ["smooth_adj_1", "smooth_adj_2", "smooth_adj_3", "smooth_adj_4"][idx]
        ax.plot(t, data["smooth_465"], color="green", linewidth=0.6, label="465nm")
        ax.plot(t, data[adj_key], color="red", linewidth=0.6, alpha=0.7, label="fitted control")
    else:
        key = ["adj1", "adj2", "adj3", "adj4"][idx]
        if dual_display in {"both", "470"}:
            ax.plot(t, data["p470"]["target_smooth"], color="green", linewidth=0.6,
                    alpha=0.8, label="470nm")
            ax.plot(t, data["p470"][key], color="green", linewidth=0.6,
                    alpha=0.3, linestyle="--", label="470 fitted")
        if dual_display in {"both", "560"}:
            ax.plot(t, data["p560"]["target_smooth"], color="red", linewidth=0.6,
                    alpha=0.8, label="560nm")
            ax.plot(t, data["p560"][key], color="red", linewidth=0.6,
                    alpha=0.3, linestyle="--", label="560 fitted")

    ax.set_title(title, fontsize=10)
    ax.set_ylabel("RFU")
    ax.set_xlabel("Time (min)")
    ax.legend(fontsize=8, loc="upper right")
    _tighten_time_axes(fig)
    return fig


@dataclass
class GraphReference:
    figure: Figure
    primary_axis: object
    secondary_axis: object
    start_line: object
    end_line: object


class GraphPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.canvas: FigureCanvasQTAgg | None = None
        self.toolbar: NavigationToolbar2QT | None = None
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(6)

    def set_figure(self, figure: Figure) -> None:
        self.clear()
        self.canvas = FigureCanvasQTAgg(figure)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        self._layout.addWidget(self.canvas, 1)
        self._layout.addWidget(self.toolbar)
        self.canvas.draw()

    def clear(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                if isinstance(widget, FigureCanvasQTAgg):
                    widget._draw_pending = False
                    widget._is_drawing = False
                    try:
                        widget.figure.clear()
                    except Exception:
                        pass
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        self.canvas = None
        self.toolbar = None


# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------

class _Worker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, fn, kwargs: dict) -> None:
        super().__init__()
        self._fn = fn
        self._kwargs = kwargs

    def run(self) -> None:
        try:
            result = self._fn(**self._kwargs)
        except Exception as exc:
            self.failed.emit(str(exc))
        else:
            self.finished.emit(result)


# ---------------------------------------------------------------------------
# Log handler → routes logger output to the in-app log widget via Signal
# ---------------------------------------------------------------------------

class _QtLogHandler(logging.Handler):
    def __init__(self, signal: Signal) -> None:
        super().__init__()
        self._signal = signal

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._signal.emit(self.format(record))
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Shared spinbox / radio styling
# ---------------------------------------------------------------------------

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
    spacing: 6px;
}}
"""


def _raw_graph_tabs_stylesheet() -> str:
    return APP_TABS_STYLESHEET + f"""
QTabBar::tab:disabled {{
    color: {PALETTE["muted"]};
    background: {PALETTE["card_alt_bg"]};
    border-color: {PALETTE["border"]};
}}
QTabBar::tab:enabled {{
    color: {PALETTE["text"]};
}}
"""


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
        self.setStyleSheet(
            f"#rawPhotometryRoot {{ background: {PALETTE['app_bg']}; }}"
        )

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
        raw_page_layout.addWidget(self.raw_graph_panel)
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
        self._option_preview_combo.currentIndexChanged.connect(self._on_option_dropdown_changed)
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
        self._dfer_results_combo.currentIndexChanged.connect(self._on_dfer_results_channel_changed)
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
        btn_save_dfer.clicked.connect(lambda: self._save_graph_image(self.dfer_results_graph, "dfer_result"))
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
        btn_save_pfer.clicked.connect(lambda: self._save_graph_image(self.pfer_graph, "pfer_result"))
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

    # ── top panels ─────────────────────────────────────────────────────────

    def _build_data_selection_panel(self) -> QFrame:
        panel = QFrame(self.top_frame)
        panel.setObjectName("rawPhotDataPanel")
        panel.setStyleSheet(
            panel_stylesheet("rawPhotDataPanel")
            + section_stylesheet("rawPhotDataCard")
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
            "Single-channel (405/465 nm) or dual-channel (470/560 nm) CSV"
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
        }
        for key in ("1", "2", "3", "4"):
            rb = QRadioButton(opt_labels[key], choose_card)
            self._opt_button_group.addButton(rb)
            self._opt_buttons[key] = rb
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
    background: {PALETTE['card_alt_bg']};
    border: none;
    color: {PALETTE['muted']};
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
            except Exception:
                pass
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

        base_title = QLabel("Baseline window for PFer normalization (seconds, optional)", base_card)
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
            QApplication.setOverrideCursor(Qt.WaitCursor)
        else:
            QApplication.restoreOverrideCursor()

    # ── folder opener ──────────────────────────────────────────────────────

    def _open_folder(self, path: str, label: str) -> None:
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            _open_path(path)
        except Exception as exc:
            QMessageBox.critical(self, "Open folder failed", str(exc))

    def _open_current_output_folder(self, label: str) -> None:
        if self._output_folder is None:
            QMessageBox.warning(
                self,
                "No output folder",
                "Select a raw photometry CSV first.",
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
            "CSV Files (*.csv);;All Files (*.*)",
        )
        if file_path:
            self._load_photometry_file(file_path)

    def _load_photometry_file(self, file_path: str) -> None:
        try:
            self._draw_raw_graph(file_path)
        except Exception as exc:
            QMessageBox.critical(self, "Load Error", str(exc))
            return
        file_type, _ = detect_photometry_file_type(file_path)
        self._selected_file = file_path
        if file_type == "dual":
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
            t = df["#time(seconds)"][1:].to_numpy(dtype=float)
            y405 = df["405nm"][1:].to_numpy(dtype=float)
            y465_col = "465nm" if "465nm" in df.columns else "490nm"
            y465 = df[y465_col][1:].to_numpy(dtype=float)
            self._draw_single_raw(t, y405, y465)
        else:
            df = pd.read_csv(file_path, skiprows=skiprows, index_col=False, low_memory=False)
            t = df["TimeStamp"].astype(float).to_numpy() / 1000.0
            y470 = df["CH1-470"].astype(float).to_numpy()
            y560 = df["CH1-560"].astype(float).to_numpy()
            self._draw_dual_raw(t, y470, y560)

    def _draw_single_raw(self, t: np.ndarray, y405: np.ndarray, y465: np.ndarray) -> None:
        figure = Figure(figsize=(10, 4), dpi=100)
        ax465 = figure.add_subplot(111)
        ax405 = ax465.twinx()

        s405_min, s405_max = float(y405.min()), float(y405.max())
        y_top_405 = s405_max + s405_min
        y_bot_405 = s405_min - 0.01 * s405_min
        range_405 = y_top_405 - y_bot_405

        s465_min, s465_max = float(y465.min()), float(y465.max())
        ax465.plot(t, y465, color="green", linewidth=0.6)
        ax405.plot(t, y405, color="purple", linewidth=0.6, alpha=0.5)
        ax465.set_ylabel("465nm Signal", color="green")
        ax405.set_ylabel("405nm Signal", color="purple")
        ax465.tick_params(axis="y", labelcolor="green")
        ax405.tick_params(axis="y", labelcolor="purple")
        ax465.set_ylim([s465_min - 0.5 * range_405, s465_max * 1.02])
        ax405.set_ylim(y_bot_405, y_top_405)

        start_line = ax465.axvline(x=t[0], color="red", linestyle="--", linewidth=1.5, label="Window start")
        end_line = ax465.axvline(x=t[-1], color="blue", linestyle="--", linewidth=1.5, label="Window end")
        ax465.set_title("Raw Data — single channel")
        ax465.set_xlabel("Time (s)")
        ax465.set_xlim([t[0], t[-1]])
        handles, labels = ax465.get_legend_handles_labels()
        ax465.legend(handles, labels, fontsize=8, loc="upper right")
        _tighten_time_axes(figure)
        figure.tight_layout()

        self._raw_graph_ref = GraphReference(figure, ax465, ax405, start_line, end_line)
        self.raw_graph_panel.set_figure(figure)

    def _draw_dual_raw(self, t: np.ndarray, y470: np.ndarray, y560: np.ndarray) -> None:
        figure = Figure(figsize=(10, 4), dpi=100)
        ax = figure.add_subplot(111)
        ax.plot(t, y470, color="green", linewidth=0.6, label="470nm")
        ax.plot(t, y560, color="red", linewidth=0.6, alpha=0.8, label="560nm")
        ax.set_ylabel("RFU")
        ax.set_xlabel("Time (s)")
        ax.set_title("Raw Data — dual channel")
        start_line = ax.axvline(x=t[0], color="red", linestyle="--", linewidth=1.5, label="Window start")
        end_line = ax.axvline(x=t[-1], color="blue", linestyle="--", linewidth=1.5, label="Window end")
        ax.legend(fontsize=8, loc="upper right")
        ax.set_xlim([t[0], t[-1]])
        _tighten_time_axes(figure)
        figure.tight_layout()

        self._raw_graph_ref = GraphReference(figure, ax, None, start_line, end_line)
        self.raw_graph_panel.set_figure(figure)

    # ── time window ────────────────────────────────────────────────────────

    def _refresh_time_preview(self) -> None:
        ref = self._raw_graph_ref
        if ref is None:
            return
        lines = ref.primary_axis.lines
        if not lines:
            return
        x_data = lines[0].get_xdata()
        if len(x_data) == 0:
            return
        t_min_val, t_max_val = float(x_data[0]), float(x_data[-1])
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
        if ref.figure.canvas:
            ref.figure.canvas.draw_idle()

    def _apply_window(self) -> None:
        """Apply the current start/end window to the raw graph markers."""
        if not self._selected_file:
            QMessageBox.warning(self, "No file", "Please select a raw photometry CSV first.")
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

    # ── DFer option plots ──────────────────────────────────────────────────

    def _on_generate_options(self, show_missing_file_warning: bool = True) -> None:
        if not self._selected_file:
            if show_missing_file_warning:
                QMessageBox.warning(self, "No file", "Please select a raw photometry CSV first.")
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
        self._options_data = data
        try:
            is_dual = isinstance(data, dict) and data.get("file_type") == "dual"
            self._configure_option_signal_selector(is_dual)
            self._render_option(self._option_preview_combo.currentIndex())
            self._append_log("INFO  [DFer] Preview complete. Choose option 1-4, then run final.")
        except Exception as exc:
            QMessageBox.critical(self, "Plot error", str(exc))

    def _options_failed(self, message: str) -> None:
        if self._unloading:
            return
        self._set_busy(False)
        QMessageBox.critical(self, "DFer options error", message)

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
        loaded_new_result = self._dfer_result_frame is None or self._dfer_result_csv != csv_path
        if loaded_new_result:
            self._dfer_result_frame = _normalise_dfer_result_frame(
                pd.read_csv(csv_path, index_col=False)
            )
            self._dfer_result_csv = csv_path
        is_dual = "dFoF_470" in self._dfer_result_frame.columns
        self._dfer_show_405_checkbox.blockSignals(True)
        self._dfer_show_405_checkbox.setEnabled(not is_dual)
        if is_dual:
            self._dfer_show_405_checkbox.setChecked(False)
        elif loaded_new_result:
            self._dfer_show_405_checkbox.setChecked(True)
        self._dfer_show_405_checkbox.blockSignals(False)
        show_405 = self._dfer_show_405_checkbox.isChecked()
        fig = _mpl_dfer_results_figure_from_frame(
            self._dfer_result_frame, graph, show_405
        )
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
                f"{selected.parent.name}_Dual"
                if file_type == "dual"
                else selected.stem
            )
        else:
            result_stem = default_stem

        safe_stem = _safe_path_part(result_stem)
        recording_name = safe_stem.removesuffix("_Dual")
        output_base = Path(self._output_folder or default_dirs.module)
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
            QMessageBox.warning(self, "No plot", "Nothing to save — run the analysis first.")
            return
        path = self._next_plot_path(default_stem)
        try:
            panel.canvas.figure.savefig(path, dpi=150, bbox_inches="tight")
        except Exception as exc:
            QMessageBox.critical(self, "Save error", str(exc))
            return
        self._append_log(f"INFO  [Plot] Saved image: {path}")

    # ── DFer final analysis ────────────────────────────────────────────────

    def _on_run_final(self) -> None:
        if not self._selected_file:
            QMessageBox.warning(self, "No file", "Please select a photometry CSV first.")
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
                    self, "Plot warning",
                    f"Analysis complete but plot failed:\n{exc}"
                )
        else:
            self._dfer_result_label.setText("Analysis complete — no output path returned.")

    def _run_final_failed(self, message: str) -> None:
        if self._unloading:
            return
        self._set_busy(False)
        QMessageBox.critical(self, "DFer error", message)

    # ── PFer ───────────────────────────────────────────────────────────────

    def _on_run_pfer(self) -> None:
        if not self._pfer_selected_csv:
            QMessageBox.warning(self, "No file", "Please select a DFer output CSV first.")
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
        try:
            fig = mpl_pfer_figure(self._pfer_selected_csv, stats_csv)
            self.pfer_graph.set_figure(fig)
            self.notebook_graphs.setTabEnabled(3, True)
            self.notebook_graphs.setCurrentIndex(3)
        except Exception as exc:
            QMessageBox.warning(
                self, "Plot warning",
                f"Peak finding complete but plot failed:\n{exc}"
            )

    def _pfer_failed(self, message: str) -> None:
        if self._unloading:
            return
        self._set_busy(False)
        QMessageBox.critical(self, "PFer error", message)
