from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QWidget,
)

from src.gui.shared.qt_bindings import LineEditControl, ObservableValue
from src.gui.shared.qt_view_styles import (
    PALETTE,
    apply_button_role,
    panel_stylesheet,
    section_stylesheet,
    title_stylesheet,
)
from src.shared.persistence.app_paths import config_file_path


def _column_names_path() -> Path:
    return config_file_path("column_names.json")


class BehaviourInputFrame(QFrame):
    def __init__(
        self,
        parent: QWidget | None,
        width: Optional[int] = None,
        select_column_names_callback: Optional[Callable[[], None]] = None,
        select_event_file_callback: Optional[Callable[[], None]] = None,
        show_column_names: bool = True,
        save_column_names_callback: Optional[Callable[[], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(parent, **kwargs)
        self.width = width
        self.import_behaviour_callback = select_event_file_callback
        self.show_column_names = show_column_names
        self.save_column_names_callback = save_column_names_callback

        self.start_time_var = ObservableValue("0")
        self.end_time_var = ObservableValue("")

        # Column name mapping vars — loaded from JSON
        self.behaviours_col_var = ObservableValue("")
        self.start_col_var = ObservableValue("")
        self.end_col_var = ObservableValue("")
        self.time_unit_var = ObservableValue("seconds")
        self._load_saved_column_names()

        # Compatibility aliases for older widget field names
        self.behaviour_name_var = ObservableValue("")
        self.behaviour_type_var = ObservableValue("Point")

        self.behaviour_input_label: Optional[QLabel] = None
        self.behaviour_coding_frame: Optional[QFrame] = None
        self.synchronize_start_time_label: Optional[QLabel] = None
        self.synchronize_start_time_entry: Optional[LineEditControl] = None
        self.start_time_entry: Optional[LineEditControl] = None
        self.end_time_entry: Optional[LineEditControl] = None
        self.import_behaviour_button: Optional[QPushButton] = None
        self.column_names_button: Optional[QPushButton] = None  # legacy stub

        self._build_ui()

    def _load_saved_column_names(self) -> None:
        try:
            data = json.loads(_column_names_path().read_text(encoding="utf-8"))
            self.behaviours_col_var.set(data.get("Behaviours/events", ""))
            self.start_col_var.set(data.get("Start Time", ""))
            self.end_col_var.set(data.get("End Time", ""))
            self.time_unit_var.set(data.get("Time Unit", "seconds"))
        except (IOError, json.JSONDecodeError):
            pass

    def _build_ui(self) -> None:
        self.setObjectName("behaviourInputFrame")
        self.setStyleSheet(
            panel_stylesheet("behaviourInputFrame")
            + section_stylesheet("behaviourInputSection", alt=True)
            + section_stylesheet("behaviourColSection")
        )
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        outer_layout = QGridLayout(self)
        outer_layout.setContentsMargins(10, 10, 10, 10)
        outer_layout.setHorizontalSpacing(8)
        outer_layout.setVerticalSpacing(6)
        outer_layout.setRowStretch(1, 1)

        self.behaviour_input_label = QLabel("Behaviour Input", self)
        self.behaviour_input_label.setStyleSheet(title_stylesheet())
        self.behaviour_input_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer_layout.addWidget(self.behaviour_input_label, 0, 0, 1, 2)

        # --- Coding card ---
        self.behaviour_coding_frame = QFrame(self)
        self.behaviour_coding_frame.setObjectName("behaviourInputSection")
        coding_layout = QGridLayout(self.behaviour_coding_frame)
        coding_layout.setContentsMargins(8, 8, 8, 8)
        coding_layout.setHorizontalSpacing(8)
        coding_layout.setVerticalSpacing(6)
        outer_layout.addWidget(self.behaviour_coding_frame, 1, 0, 1, 2)

        self.synchronize_start_time_label = QLabel(
            "Video Coding Start Time (s):", self.behaviour_coding_frame
        )
        coding_layout.addWidget(self.synchronize_start_time_label, 0, 0)

        self.synchronize_start_time_entry = LineEditControl(
            self.start_time_var, self.behaviour_coding_frame
        )
        self.synchronize_start_time_entry.setMaximumWidth(90)
        coding_layout.addWidget(self.synchronize_start_time_entry, 0, 1)

        self.import_behaviour_button = QPushButton(
            "Import Behaviour Coding", self.behaviour_coding_frame
        )
        apply_button_role(self.import_behaviour_button, "primary")
        self.import_behaviour_button.clicked.connect(self.on_import_behaviour_click)
        coding_layout.addWidget(self.import_behaviour_button, 1, 0, 1, 2)

        # --- Collapsible column names section ---
        if self.show_column_names:
            self._col_toggle = QToolButton(self)
            self._col_toggle.setText("▶  CSV Column Names")
            self._col_toggle.setCheckable(True)
            self._col_toggle.setChecked(False)
            self._col_toggle.setCursor(Qt.PointingHandCursor)
            self._col_toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
            self._col_toggle.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
            self._col_toggle.setStyleSheet(f"""
                QToolButton {{
                    background: {PALETTE["button_bg"]};
                    color: {PALETTE["text"]};
                    border: 1px solid {PALETTE["border"]};
                    border-radius: 8px;
                    padding: 5px 10px;
                    font-weight: 600;
                    font-size: 12px;
                    text-align: left;
                }}
                QToolButton:hover {{
                    background: {PALETTE["button_hover"]};
                    border-color: {PALETTE["border_strong"]};
                }}
                QToolButton:checked {{
                    background: {PALETTE["card_alt_bg"]};
                    border-color: {PALETTE["border_strong"]};
                }}
            """)
            self._popup_just_closed = False
            self._col_toggle.toggled.connect(self._toggle_col_names)
            outer_layout.addWidget(self._col_toggle, 2, 0, 1, 2)

            # Floating popup — not in the layout
            self._col_content = QFrame(self, Qt.WindowType.Popup)
            self._col_content.setObjectName("behaviourColSection")
            self._col_content.setStyleSheet(section_stylesheet("behaviourColSection"))
            col_layout = QGridLayout(self._col_content)
            col_layout.setContentsMargins(8, 8, 8, 8)
            col_layout.setHorizontalSpacing(8)
            col_layout.setVerticalSpacing(6)

            col_layout.addWidget(QLabel("Behaviour col:", self._col_content), 0, 0)
            self._behaviours_col_entry = LineEditControl(self.behaviours_col_var, self._col_content)
            col_layout.addWidget(self._behaviours_col_entry, 0, 1)

            col_layout.addWidget(QLabel("Start col:", self._col_content), 1, 0)
            self._start_col_entry = LineEditControl(self.start_col_var, self._col_content)
            col_layout.addWidget(self._start_col_entry, 1, 1)

            col_layout.addWidget(QLabel("End col:", self._col_content), 2, 0)
            self._end_col_entry = LineEditControl(self.end_col_var, self._col_content)
            col_layout.addWidget(self._end_col_entry, 2, 1)

            col_layout.addWidget(QLabel("Time unit:", self._col_content), 3, 0)
            self._time_unit_dropdown = QComboBox(self._col_content)
            self._time_unit_dropdown.addItems(["seconds", "minutes"])
            self._time_unit_dropdown.setCurrentText(self.time_unit_var.get())
            self._time_unit_dropdown.currentTextChanged.connect(self.time_unit_var.set)
            col_layout.addWidget(self._time_unit_dropdown, 3, 1)

            save_btn = QPushButton("Save", self._col_content)
            apply_button_role(save_btn, "primary")
            save_btn.clicked.connect(self._on_save_column_names)
            col_layout.addWidget(save_btn, 4, 0, 1, 2)

            # When popup is dismissed (outside click or save), reset toggle
            original_hide = self._col_content.hideEvent

            def _hide_event(event, _orig=original_hide):
                _orig(event)
                self._popup_just_closed = True
                self._col_toggle.setChecked(False)
                self._col_toggle.setText("▶  CSV Column Names")

            self._col_content.hideEvent = _hide_event

        # Compatibility fields kept for older widget access patterns
        self.start_time_entry = self.synchronize_start_time_entry
        self.end_time_entry = LineEditControl(self.end_time_var, self)
        self.end_time_entry.setEnabled(False)
        self.end_time_entry.hide()

    def _toggle_col_names(self, checked: bool) -> None:
        if not checked:
            # Fired by hideEvent calling setChecked(False) — don't touch the flag here
            self._col_toggle.setText("▶  CSV Column Names")
            self._col_content.hide()
            return
        if self._popup_just_closed:
            # Button was clicked while popup was open — popup already closed, don't reopen
            self._popup_just_closed = False
            self._col_toggle.setChecked(False)
            return
        self._col_toggle.setText("▼  CSV Column Names")
        btn_bottom_left = self._col_toggle.mapToGlobal(
            QPoint(0, self._col_toggle.height() + 2)
        )
        self._col_content.adjustSize()
        self._col_content.move(btn_bottom_left)
        self._col_content.show()
        self._col_content.raise_()

    def _on_save_column_names(self) -> None:
        if self.save_column_names_callback:
            self.save_column_names_callback()
        else:
            data = {
                "Behaviours/events": self.behaviours_col_var.get(),
                "Start Time": self.start_col_var.get(),
                "End Time": self.end_col_var.get(),
                "Time Unit": self.time_unit_var.get(),
            }
            _column_names_path().write_text(json.dumps(data), encoding="utf-8")
        self._col_content.hide()

    def on_import_behaviour_click(self) -> None:
        if self.import_behaviour_callback:
            self.import_behaviour_callback()
