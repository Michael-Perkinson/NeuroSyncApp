from __future__ import annotations

import logging
from typing import Callable

from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.gui.shared.qt_bindings import ComboBoxControl, LineEditControl, ObservableValue
from src.gui.shared.qt_log_handler import QtTextHandler
from src.gui.shared.qt_view_styles import (
    MONO_FONT_FAMILY,
    apply_button_role,
    panel_stylesheet,
    section_stylesheet,
    subtitle_stylesheet,
    title_stylesheet,
)
from src.gui.shared.view_state_models import ExportOptionsViewState


class ExportOptionsPanel(QFrame):
    def __init__(
        self,
        parent: QWidget | None,
        file_path_var,
        settings_manager,
        extract_button_click_handler: Callable[[], None],
        save_image: Callable[[], None],
        **kwargs,
    ) -> None:
        super().__init__(parent, **kwargs)
        self.settings_manager = settings_manager
        self.file_path_var = file_path_var
        self.extract_button_click_handler = extract_button_click_handler
        self.save_image = save_image
        self.view_state = ExportOptionsViewState()

        self.use_auc_var = ObservableValue(True)
        self.use_max_amp_var = ObservableValue(True)
        self.use_mean_dff_var = ObservableValue(True)
        self.use_binned_data_var = ObservableValue(True)
        self.combine_csv_var = ObservableValue(True)
        self.image_format_var = ObservableValue("PNG")
        self.dpi_var = ObservableValue("600")
        self.width_var = ObservableValue("")
        self.height_var = ObservableValue("")
        self.log_handler = None
        self.font_settings = {
            "xlabel_fontsize": "",
            "ylabel_fontsize": "",
            "xtick_fontsize": "",
            "ytick_fontsize": "",
            "y_axis_name": "",
        }

        self._build_ui()
        self._attach_log_handler()

    def _build_ui(self) -> None:
        self.setObjectName("exportOptionsPanel")
        self.setStyleSheet(
            panel_stylesheet("exportOptionsPanel")
            + section_stylesheet("exportOptionsSection")
            + section_stylesheet("exportOptionsSectionAlt", alt=True)
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QLabel("Export Options", self)
        title.setStyleSheet(title_stylesheet())
        layout.addWidget(title)

        current_frame = QFrame(self)
        current_frame.setObjectName("exportOptionsSection")
        current_layout = QGridLayout(current_frame)
        current_layout.setContentsMargins(8, 8, 8, 8)
        current_layout.setHorizontalSpacing(10)
        current_layout.setVerticalSpacing(8)
        layout.addWidget(current_frame)

        extract_button = QPushButton("Extract Data", current_frame)
        apply_button_role(extract_button, "primary")
        extract_button.clicked.connect(self.extract_button_click_handler)
        current_layout.addWidget(extract_button, 0, 0)

        image_frame = QFrame(self)
        image_frame.setObjectName("exportOptionsSectionAlt")
        image_layout = QGridLayout(image_frame)
        image_layout.setContentsMargins(8, 8, 8, 8)
        image_layout.setHorizontalSpacing(10)
        image_layout.setVerticalSpacing(8)
        layout.addWidget(image_frame)

        image_layout.addWidget(QLabel("Image Format:", image_frame), 0, 0)
        self.image_format_combobox = ComboBoxControl(self.image_format_var, image_frame)
        self.image_format_combobox.set_options(["EPS", "SVG", "TIFF", "PNG", "JPG"])
        self.image_format_combobox.set("PNG")
        image_layout.addWidget(self.image_format_combobox, 0, 1)

        image_layout.addWidget(QLabel("DPI:", image_frame), 0, 2)
        self.dpi_entry = LineEditControl(self.dpi_var, image_frame)
        self.dpi_entry.setMaximumWidth(80)
        image_layout.addWidget(self.dpi_entry, 0, 3)

        image_layout.addWidget(QLabel("Width (cm):", image_frame), 1, 0)
        self.width_entry = LineEditControl(self.width_var, image_frame)
        self.width_entry.setMaximumWidth(80)
        image_layout.addWidget(self.width_entry, 1, 1)

        image_layout.addWidget(QLabel("Height (cm):", image_frame), 1, 2)
        self.height_entry = LineEditControl(self.height_var, image_frame)
        self.height_entry.setMaximumWidth(80)
        image_layout.addWidget(self.height_entry, 1, 3)

        font_button = QPushButton("Font Settings", image_frame)
        apply_button_role(font_button)
        font_button.clicked.connect(self.open_font_settings_popup)
        image_layout.addWidget(font_button, 0, 4)

        save_button = QPushButton("Save Image", image_frame)
        apply_button_role(save_button, "primary")
        save_button.clicked.connect(self.save_image)
        image_layout.addWidget(save_button, 1, 4)

        log_frame = QFrame(self)
        log_frame.setObjectName("exportOptionsSection")
        log_layout = QVBoxLayout(log_frame)
        log_layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(log_frame, 1)

        header = QHBoxLayout()
        log_layout.addLayout(header)
        title = QLabel("Run Log", log_frame)
        title.setStyleSheet("font-size: 13px; font-weight: 700;")
        header.addWidget(title)
        header.addStretch(1)

        clear_button = QPushButton("Clear", log_frame)
        apply_button_role(clear_button)
        clear_button.clicked.connect(self.clear_log_output)
        header.addWidget(clear_button)

        self.log_output = QPlainTextEdit(log_frame)
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(80)
        self.log_output.setStyleSheet(
            "background: #f7fafc; "
            "border: 1px solid #b8c4cf; "
            f"font-family: '{MONO_FONT_FAMILY}';"
        )
        log_layout.addWidget(self.log_output, 1)

    def _attach_log_handler(self) -> None:
        self.log_handler = QtTextHandler(self.log_output)
        self.log_handler.setLevel(logging.INFO)
        self.log_handler.setFormatter(
            logging.Formatter("%(levelname)s | %(name)s | %(message)s")
        )
        logging.getLogger().addHandler(self.log_handler)
        # closeEvent only fires for top-level windows; when this panel is
        # destroyed as a child of a closing/switching tool the handler would
        # otherwise stay registered on the root logger and later crash on a
        # deleted widget. Deregister as soon as the log widget is destroyed.
        self.log_output.destroyed.connect(self._detach_log_handler)

    def _detach_log_handler(self) -> None:
        if self.log_handler is not None:
            logging.getLogger().removeHandler(self.log_handler)
            self.log_handler.close()
            self.log_handler = None

    def clear_log_output(self) -> None:
        try:
            self.log_output.clear()
        except RuntimeError:
            self._detach_log_handler()

    def closeEvent(self, event) -> None:  # pragma: no cover - GUI lifecycle
        self.prepare_for_unload()
        super().closeEvent(event)

    def prepare_for_unload(self) -> bool:
        self._detach_log_handler()
        return True

    def open_font_settings_popup(self) -> None:
        popup = QDialog(self)
        popup.setWindowTitle("Font Settings")
        layout = QGridLayout(popup)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(8)

        y_axis_name_var = ObservableValue(self.font_settings["y_axis_name"])
        ylabel_var = ObservableValue(self.font_settings["ylabel_fontsize"])
        ytick_var = ObservableValue(self.font_settings["ytick_fontsize"])
        xlabel_var = ObservableValue(self.font_settings["xlabel_fontsize"])
        xtick_var = ObservableValue(self.font_settings["xtick_fontsize"])

        layout.addWidget(QLabel("Overwrite Y-axis Name:", popup), 0, 0)
        y_axis_name_entry = LineEditControl(y_axis_name_var, popup)
        layout.addWidget(y_axis_name_entry, 0, 1, 1, 3)

        layout.addWidget(QLabel("Y-label Font Size:", popup), 1, 0)
        y_label_entry = LineEditControl(ylabel_var, popup)
        layout.addWidget(y_label_entry, 1, 1)

        layout.addWidget(QLabel("Y-ticks Font Size:", popup), 2, 0)
        y_tick_entry = LineEditControl(ytick_var, popup)
        layout.addWidget(y_tick_entry, 2, 1)

        layout.addWidget(QLabel("X-label Font Size:", popup), 1, 2)
        x_label_entry = LineEditControl(xlabel_var, popup)
        layout.addWidget(x_label_entry, 1, 3)

        layout.addWidget(QLabel("X-ticks Font Size:", popup), 2, 2)
        x_tick_entry = LineEditControl(xtick_var, popup)
        layout.addWidget(x_tick_entry, 2, 3)

        save_button = QPushButton("Apply & Close", popup)
        save_button.clicked.connect(
            lambda: self._apply_font_settings(
                popup,
                y_axis_name_var,
                ylabel_var,
                ytick_var,
                xlabel_var,
                xtick_var,
            )
        )
        layout.addWidget(save_button, 3, 0, 1, 4)

        popup.exec()

    def _apply_font_settings(
        self,
        popup: QDialog,
        y_axis_name_var: ObservableValue[str],
        ylabel_var: ObservableValue[str],
        ytick_var: ObservableValue[str],
        xlabel_var: ObservableValue[str],
        xtick_var: ObservableValue[str],
    ) -> None:
        self.font_settings["y_axis_name"] = (y_axis_name_var.get() or "").strip()
        self.font_settings["ylabel_fontsize"] = (ylabel_var.get() or "").strip()
        self.font_settings["ytick_fontsize"] = (ytick_var.get() or "").strip()
        self.font_settings["xlabel_fontsize"] = (xlabel_var.get() or "").strip()
        self.font_settings["xtick_fontsize"] = (xtick_var.get() or "").strip()
        popup.accept()
