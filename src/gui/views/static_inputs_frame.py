from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from src.gui.shared.qt_bindings import ComboBoxControl, LineEditControl, ObservableValue
from src.gui.shared.qt_view_styles import (
    apply_button_role,
    panel_stylesheet,
    section_stylesheet,
    title_stylesheet,
)
from src.gui.shared.view_state_models import StaticInputsViewState


class StaticInputsFrame(QFrame):
    def __init__(self, parent: QWidget | None, width=None, save_inputs_callback=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.view_state = StaticInputsViewState()
        self.pre_behaviour_time_var = ObservableValue("")
        self.post_behaviour_time_var = ObservableValue("")
        self.bin_size_var = ObservableValue("")
        self.selected_behaviour = ObservableValue(self.view_state.selected_behaviour)
        self.pre_behaviour_time_var.trace_add(
            "write", lambda: setattr(self.view_state, "pre_behaviour_time", self.pre_behaviour_time_var.get() or "")
        )
        self.post_behaviour_time_var.trace_add(
            "write", lambda: setattr(self.view_state, "post_behaviour_time", self.post_behaviour_time_var.get() or "")
        )
        self.bin_size_var.trace_add(
            "write", lambda: setattr(self.view_state, "bin_size", self.bin_size_var.get() or "")
        )
        self.selected_behaviour.trace_add(
            "write", lambda: setattr(self.view_state, "selected_behaviour", self.selected_behaviour.get() or "")
        )

        self.save_inputs_callback = save_inputs_callback
        self.width = width
        self._build_ui()

    def _build_ui(self) -> None:
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setObjectName("staticInputsFrame")
        self.setStyleSheet(
            panel_stylesheet("staticInputsFrame")
            + section_stylesheet("staticInputsSection", alt=True)
        )
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        layout = QGridLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(6)
        layout.setRowStretch(1, 1)

        title = QLabel("Static Inputs", self)
        title.setStyleSheet(title_stylesheet())
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title, 0, 0, 1, 2)

        form_frame = QFrame(self)
        form_frame.setObjectName("staticInputsSection")
        form_layout = QGridLayout(form_frame)
        form_layout.setContentsMargins(8, 8, 8, 8)
        form_layout.setHorizontalSpacing(8)
        form_layout.setVerticalSpacing(6)
        layout.addWidget(form_frame, 1, 0, 1, 2)

        self.pre_behaviour_time_label = QLabel("Pre-behaviour Time (s):", self)
        form_layout.addWidget(self.pre_behaviour_time_label, 0, 0)
        self.pre_behaviour_time_entry = LineEditControl(self.pre_behaviour_time_var, form_frame)
        self.pre_behaviour_time_entry.setMaximumWidth(90)
        form_layout.addWidget(self.pre_behaviour_time_entry, 0, 1)

        self.post_behaviour_time_label = QLabel("Post-behaviour Time (s):", self)
        form_layout.addWidget(self.post_behaviour_time_label, 1, 0)
        self.post_behaviour_time_entry = LineEditControl(self.post_behaviour_time_var, form_frame)
        self.post_behaviour_time_entry.setMaximumWidth(90)
        form_layout.addWidget(self.post_behaviour_time_entry, 1, 1)

        self.bin_size_label = QLabel("Bin Size (s):", self)
        form_layout.addWidget(self.bin_size_label, 2, 0)
        self.bin_size_entry = LineEditControl(self.bin_size_var, form_frame)
        self.bin_size_entry.setMaximumWidth(90)
        form_layout.addWidget(self.bin_size_entry, 2, 1)

        row3_container = QWidget(form_frame)
        row3_layout = QHBoxLayout(row3_container)
        row3_layout.setContentsMargins(0, 0, 0, 0)
        row3_layout.setSpacing(8)

        save_button = QPushButton("Insert Times", row3_container)
        apply_button_role(save_button, "primary")
        save_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        save_button.clicked.connect(
            self.save_inputs_callback if self.save_inputs_callback else self.default_save
        )
        row3_layout.addWidget(save_button)

        self.behaviour_dropdown = ComboBoxControl(self.selected_behaviour, row3_container)
        self.behaviour_dropdown.setEnabled(False)
        row3_layout.addWidget(self.behaviour_dropdown, 1)

        form_layout.addWidget(row3_container, 3, 0, 1, 2)

    def set_behaviour_options(self, options: list[str]) -> None:
        self.behaviour_dropdown.set_options(options)
        self.behaviour_dropdown.setEnabled(bool(options))

    def default_save(self) -> None:
        return

