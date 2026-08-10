"""Section construction for the graph settings panel."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.gui.framework.qt_view_styles import (
    apply_button_role,
    section_title_stylesheet,
    subtitle_stylesheet,
)
from src.gui.framework.tk_compat_controls import (
    CheckBoxControl,
    ComboBoxControl,
    LineEditControl,
    ObservableValue,
)

if TYPE_CHECKING:
    from .graph_settings_panel import GraphSettingsPanel


class GraphSettingsSectionBuilder:
    """Build graph settings cards while exposing controls on the panel."""

    def __init__(self, panel: GraphSettingsPanel) -> None:
        self.panel = panel

    def build_appearance_card(self) -> QWidget | None:
        panel = self.panel
        if not any(
            panel._include(name)
            for name in (
                "line_width",
                "box_height",
                "alpha",
                "bar_graph_size",
                "onset_line_thickness",
                "onset_line_style",
                "color_buttons",
                "photometry_settings",
                "temperature_settings",
                "activity_settings",
            )
        ):
            return None

        card, layout = self._create_card(panel.appearance_section_title, "")
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        layout.addLayout(grid)

        field_specs = []
        if panel._include("line_width"):
            field_specs.append(
                ("Line Width", "line_width_entry", panel.selected_photometry_line_width)
            )
        if panel._include("box_height"):
            field_specs.append(
                ("Box Height", "box_height_entry", panel.box_height_factor_var)
            )
        if panel._include("alpha"):
            field_specs.append(("Alpha", "alpha_entry", panel.alpha_var))
        if panel._include("bar_graph_size"):
            field_specs.append(
                ("Bar Size", "bar_graph_size_entry", panel.bar_graph_size_var)
            )
        if panel._include("onset_line_thickness"):
            field_specs.append(
                (
                    "Onset Width",
                    "onset_line_thickness_entry",
                    panel.onset_line_thickness_var,
                )
            )

        row = 0
        for index, (label_text, attr_name, value_model) in enumerate(field_specs):
            column = (index % 3) * 2
            if index and index % 3 == 0:
                row += 1
            self._add_compact_line_edit(
                grid,
                row,
                column,
                label_text,
                attr_name,
                value_model,
            )

        if panel._include("onset_line_style"):
            remainder = len(field_specs) % 3
            if field_specs and remainder != 0:
                style_col = remainder * 2
            else:
                row += 1 if field_specs else 0
                style_col = 0
            grid.addWidget(QLabel("Onset Style", card), row, style_col)
            panel.onset_line_style_combobox = ComboBoxControl(
                panel.onset_line_style_var, card
            )
            panel.onset_line_style_combobox.set_options(["--", "-", "-.", ":"])
            panel.onset_line_style_combobox.set(
                panel.onset_line_style_var.get() or "--"
            )
            panel.onset_line_style_combobox.setMaximumWidth(120)
            grid.addWidget(panel.onset_line_style_combobox, row, style_col + 1)
            row += 1

        grid.setColumnStretch(6, 1)

        if panel._include("color_buttons"):
            palette_title = QLabel("Colour Shortcuts", card)
            palette_title.setStyleSheet(section_title_stylesheet())
            grid.addWidget(palette_title, row, 0, 1, 6)
            row += 1

            color_specs = [
                ("Bar Fill", "bar_fill_color_button", "selected_bar_fill_color"),
                (
                    "Bar Border",
                    "bar_border_color_button",
                    "selected_bar_border_color",
                ),
                ("Onset Line", "line_color_button", "selected_line_color"),
                ("Bar SEM", "sem_color_button", "selected_bar_sem_color"),
            ]
            if panel._include("cluster_box_color"):
                color_specs.append(
                    (
                        "Cluster Box",
                        "cluster_box_color_button",
                        "selected_cluster_box_color",
                    )
                )
            for index, (label_text, button_name, color_attr) in enumerate(color_specs):
                column = (index % 3) * 2
                if index and index % 3 == 0:
                    row += 1
                self._add_color_control(
                    grid,
                    row,
                    column,
                    label_text,
                    button_name,
                    color_attr,
                )
            row += 1

        advanced_buttons = []
        if panel._include("photometry_settings"):
            panel.photometry_settings_button = QPushButton(
                panel.photometry_button_text, card
            )
            panel.photometry_settings_button.clicked.connect(
                panel.open_photometry_settings_popup
            )
            apply_button_role(
                panel.photometry_settings_button, panel.advanced_button_role
            )
            advanced_buttons.append(panel.photometry_settings_button)
        if panel._include("temperature_settings"):
            panel.temperature_settings_button = QPushButton(
                panel.temperature_button_text, card
            )
            panel.temperature_settings_button.clicked.connect(
                panel.open_temperature_settings_popup
            )
            apply_button_role(
                panel.temperature_settings_button, panel.advanced_button_role
            )
            advanced_buttons.append(panel.temperature_settings_button)
        if panel._include("activity_settings"):
            panel.activity_settings_button = QPushButton(panel.activity_button_text, card)
            panel.activity_settings_button.clicked.connect(
                panel.open_activity_settings_popup
            )
            apply_button_role(
                panel.activity_settings_button, panel.advanced_button_role
            )
            advanced_buttons.append(panel.activity_settings_button)

        if advanced_buttons:
            if panel.advanced_buttons_title:
                buttons_label = QLabel(panel.advanced_buttons_title, card)
                buttons_label.setStyleSheet(section_title_stylesheet())
                grid.addWidget(buttons_label, row, 0, 1, 6)
                row += 1

            buttons_row = QHBoxLayout()
            buttons_row.setContentsMargins(0, 0, 0, 0)
            buttons_row.setSpacing(8)
            for button in advanced_buttons:
                buttons_row.addWidget(button)
            buttons_row.addStretch(1)
            grid.addLayout(buttons_row, row, 0, 1, 6)
            row += 1

        if panel.overlay_visibility_in_appearance:
            row = self._add_overlay_visibility_controls(
                grid, row, card, "Show on Graph"
            )

        panel.update_button_colors()
        return card

    def build_display_card(self) -> QWidget | None:
        panel = self.panel
        show_overlay_visibility = not panel.overlay_visibility_in_appearance and (
            panel._include("temperature_settings")
            or panel._include("activity_settings")
        )

        if not any(
            panel._include(name)
            for name in (
                "checkboxes",
                "remove_first_60_minutes",
            )
        ) and not show_overlay_visibility:
            return None

        card, layout = self._create_card(
            "Display & Overlays" if show_overlay_visibility else "Display",
            "",
            alt=True,
        )
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        layout.addLayout(grid)

        row = 0
        if panel._include("checkboxes"):
            panel.display_duration_checkbox = CheckBoxControl(
                "Display Duration",
                panel.display_duration_box_var,
                card,
            )
            panel.display_duration_checkbox.clicked.connect(panel._refresh_graph)
            grid.addWidget(panel.display_duration_checkbox, row, 0, 1, 2)

            panel.num_instances_checkbox = CheckBoxControl(
                "Display Number of Instances",
                panel.num_instances_box_var,
                card,
            )
            panel.num_instances_checkbox.clicked.connect(panel._refresh_graph)
            grid.addWidget(panel.num_instances_checkbox, row, 2, 1, 2)
            row += 1

            grid.addWidget(
                QLabel("Duration Box Placement (+/-)", card), row, 0, 1, 2
            )
            panel.duration_box_placement_entry = LineEditControl(
                panel.duration_box_placement, card
            )
            panel.duration_box_placement_entry.setMaximumWidth(90)
            panel.duration_box_placement_entry.editingFinished.connect(
                panel.update_duration_box
            )
            grid.addWidget(panel.duration_box_placement_entry, row, 2)
            row += 1

        if show_overlay_visibility:
            row = self._add_overlay_visibility_controls(
                grid,
                row,
                card,
                "Overlay Visibility",
            )

        if panel._include("remove_first_60_minutes"):
            panel.remove_first_60_minutes_checkbox = CheckBoxControl(
                "Remove first 60 minutes",
                panel.remove_first_60_minutes_var,
                card,
            )
            panel.remove_first_60_minutes_checkbox.clicked.connect(panel._redraw_graph)
            grid.addWidget(panel.remove_first_60_minutes_checkbox, row, 0, 1, 4)

        return card

    def _add_overlay_visibility_controls(
        self,
        grid: QGridLayout,
        row: int,
        card: QWidget,
        title: str | None,
    ) -> int:
        panel = self.panel
        has_temperature = panel._include("temperature_settings")
        has_activity = panel._include("activity_settings")
        if not has_temperature and not has_activity:
            return row

        if title:
            toggles_label = QLabel(title, card)
            toggles_label.setStyleSheet(section_title_stylesheet())
            grid.addWidget(toggles_label, row, 0, 1, 4)
            row += 1

        if has_temperature:
            panel.temperature_checkbox = CheckBoxControl(
                "Temperature Data",
                panel.temperature_data_var,
                card,
            )
            panel.temperature_checkbox.clicked.connect(panel._redraw_graph)
            grid.addWidget(panel.temperature_checkbox, row, 0, 1, 2)

        if has_activity:
            panel.activity_checkbox = CheckBoxControl(
                "Activity Data",
                panel.activity_data_var,
                card,
            )
            panel.activity_checkbox.clicked.connect(panel._redraw_graph)
            grid.addWidget(panel.activity_checkbox, row, 2, 1, 2)

        return row + 1

    def build_time_axis_card(self) -> QWidget | None:
        panel = self.panel
        if not any(
            panel._include(name)
            for name in (
                "graph_time_labels",
                "axis_range",
                "zero_x_axis_to_behaviour",
                "number_of_minor_ticks",
            )
        ):
            return None

        card, layout = self._create_card("Time & Axis", "")
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        layout.addLayout(grid)

        row = 0
        update_button_pending = False
        if panel._include("graph_time_labels"):
            grid.addWidget(QLabel("Time Unit", card), row, 0)
            panel.time_unit_menu = ComboBoxControl(panel.time_unit_var, card)
            panel.time_unit_menu.setMinimumWidth(120)
            panel.time_unit_menu.set_options(["minutes", "seconds", "hours"])
            panel.time_unit_menu.set(panel.time_unit_var.get() or "minutes")
            panel.time_unit_menu.currentTextChanged.connect(
                lambda *_args: panel._refresh_graph()
            )
            grid.addWidget(panel.time_unit_menu, row, 1)

            grid.addWidget(QLabel("X Ticks", card), row, 2)
            panel.x_gridlines_entry = LineEditControl(panel.x_gridlines_var, card)
            panel.x_gridlines_entry.setMaximumWidth(90)
            grid.addWidget(panel.x_gridlines_entry, row, 3)

            panel.y_gridlines_label = QLabel("Y Ticks", card)
            grid.addWidget(panel.y_gridlines_label, row, 4)
            panel.y_gridlines_entry = LineEditControl(panel.y_gridlines_var, card)
            panel.y_gridlines_entry.setMaximumWidth(90)
            grid.addWidget(panel.y_gridlines_entry, row, 5)

            panel.update_button = QPushButton("Update Settings", card)
            apply_button_role(panel.update_button, "primary")
            panel.update_button.clicked.connect(panel._refresh_graph)
            update_button_pending = True
            row += 1
        else:
            panel.time_unit_menu = ComboBoxControl(panel.time_unit_var, card)
            panel.time_unit_menu.setMinimumWidth(120)
            panel.y_gridlines_label = QLabel("Y Ticks", card)
            panel.y_gridlines_entry = LineEditControl(panel.y_gridlines_var, card)

        if panel._include("number_of_minor_ticks"):
            grid.addWidget(QLabel("Minor Ticks", card), row, 0)
            panel.number_of_minor_ticks_entry = LineEditControl(
                panel.number_of_minor_ticks_var, card
            )
            panel.number_of_minor_ticks_entry.setMaximumWidth(90)
            grid.addWidget(panel.number_of_minor_ticks_entry, row, 1)
            row += 1

        if panel._include("axis_range"):
            panel.limit_axis_checkbox = CheckBoxControl(
                "Limit Axis Range",
                panel.limit_axis_range_var,
                card,
            )
            panel.limit_axis_checkbox.clicked.connect(
                lambda *_args: panel.save_and_close_axis(close=False)
            )
            grid.addWidget(panel.limit_axis_checkbox, row, 0, 1, 2)

            panel.axis_range_button = QPushButton("Set Axis Range", card)
            apply_button_role(panel.axis_range_button, panel.axis_range_button_role)
            panel.axis_range_button.clicked.connect(panel.open_axis_range_popup)
            grid.addWidget(panel.axis_range_button, row, 2, 1, 2)

            if update_button_pending:
                grid.addWidget(panel.update_button, row, 4, 1, 2)
                update_button_pending = False
            row += 1

        if update_button_pending:
            grid.addWidget(panel.update_button, row, 0, 1, 2)
            row += 1

        if panel._include("zero_x_axis_to_behaviour"):
            panel.zero_axis_checkbox = CheckBoxControl(
                "Zero X-axis with behaviour",
                panel.zero_x_axis_checkbox_var,
                card,
            )
            panel.zero_axis_checkbox.clicked.connect(panel._on_zero_axis_clicked)
            grid.addWidget(panel.zero_axis_checkbox, row, 0, 1, 3)

            panel.behaviour_to_zero_dropdown = ComboBoxControl(
                panel.selected_behaviour_to_zero, card
            )
            panel.behaviour_to_zero_dropdown.configure(state="disabled")
            panel.behaviour_to_zero_dropdown.currentTextChanged.connect(
                lambda *_args: panel._handle_behaviour_change()
            )
            grid.addWidget(panel.behaviour_to_zero_dropdown, row, 3, 1, 3)

        return card

    def build_visibility_card(self) -> QWidget:
        panel = self.panel
        card, layout = self._create_card(
            panel.visibility_section_title,
            "",
            alt=True,
        )

        scroll = QScrollArea(card)
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(160)
        scroll.setMaximumHeight(220)
        layout.addWidget(scroll)

        content = QWidget(scroll)
        scroll.setWidget(content)
        panel.behaviour_frame = content
        panel.behaviour_frame_layout = QVBoxLayout(panel.behaviour_frame)
        panel.behaviour_frame_layout.setContentsMargins(0, 0, 0, 0)
        panel.behaviour_frame_layout.setSpacing(8)
        panel.behaviour_frame_layout.addStretch(1)
        return card

    def _create_card(
        self,
        heading: str,
        description: str,
        alt: bool = False,
    ) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame(self.panel)
        card.setObjectName("graphSectionCardAlt" if alt else "graphSectionCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        title = QLabel(heading, card)
        title.setStyleSheet(section_title_stylesheet())
        layout.addWidget(title)

        if description:
            subtitle = QLabel(description, card)
            subtitle.setStyleSheet(subtitle_stylesheet())
            subtitle.setWordWrap(True)
            layout.addWidget(subtitle)
        return card, layout

    def _add_compact_line_edit(
        self,
        layout: QGridLayout,
        row: int,
        column: int,
        label_text: str,
        attribute_name: str,
        value: ObservableValue[str],
    ) -> None:
        panel = self.panel
        layout.addWidget(QLabel(label_text, panel), row, column)
        entry = LineEditControl(value, panel)
        entry.setMaximumWidth(90)
        setattr(panel, attribute_name, entry)
        layout.addWidget(entry, row, column + 1)

    def _add_color_control(
        self,
        layout: QGridLayout,
        row: int,
        column: int,
        label_text: str,
        button_name: str,
        color_attr: str,
    ) -> None:
        panel = self.panel
        button = QPushButton(label_text, panel)
        button.clicked.connect(
            lambda _checked=False, attr=color_attr, target=button: panel.choose_color(
                attr, target
            )
        )
        setattr(panel, button_name, button)
        layout.addWidget(button, row, column, 1, 2)
