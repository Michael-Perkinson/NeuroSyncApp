from __future__ import annotations

import hashlib

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.gui.shared.qt_bindings import (
    CheckBoxControl,
    ComboBoxControl,
    LineEditControl,
    ObservableValue,
)
from src.gui.shared.qt_view_styles import (
    PALETTE,
    apply_button_role,
    panel_stylesheet,
    section_stylesheet,
    section_title_stylesheet,
    subtitle_stylesheet,
    title_stylesheet,
)
from src.gui.shared.view_state_models import GraphSettingsViewState


class GraphSettingsPanel(QFrame):
    def __init__(
        self,
        parent: QWidget | None,
        widgets_to_include=None,
        appearance_section_title: str = "Trace & Styling",
        advanced_buttons_title: str | None = "Advanced Settings",
        advanced_button_role: str = "secondary",
        axis_range_button_role: str = "secondary",
        photometry_button_text: str = "Photometry Settings",
        temperature_button_text: str = "Temperature Settings",
        activity_button_text: str = "Activity Settings",
        overlay_visibility_in_appearance: bool = False,
        visibility_section_title: str = "Behaviours",
        show_visibility_card: bool = True,
        app_name=None,
        settings_manager=None,
        refresh_graph_display_callback=None,
        update_duration_box_callback=None,
        handle_behaviour_change_callback=None,
        load_variables_callback=None,
        save_variables_callback=None,
        create_behaviour_options_callback=None,
        update_box_colors_callback=None,
        save_and_close_axis_callback=None,
        redraw_graph_callback=None,
        **kwargs,
    ) -> None:
        super().__init__(parent, **kwargs)
        self.widgets_to_include = set(widgets_to_include or [])
        self.appearance_section_title = appearance_section_title
        self.advanced_buttons_title = advanced_buttons_title
        self.advanced_button_role = advanced_button_role
        self.axis_range_button_role = axis_range_button_role
        self.photometry_button_text = photometry_button_text
        self.temperature_button_text = temperature_button_text
        self.activity_button_text = activity_button_text
        self.overlay_visibility_in_appearance = overlay_visibility_in_appearance
        self.visibility_section_title = visibility_section_title
        self.show_visibility_card = show_visibility_card
        self.app_name = app_name
        self.settings_manager = settings_manager
        self.refresh_graph_display_callback = refresh_graph_display_callback
        self.update_duration_box_callback = update_duration_box_callback
        self.handle_behaviour_change_callback = handle_behaviour_change_callback
        self.load_variables_callback = load_variables_callback
        self.save_variables_callback = save_variables_callback
        self.create_behaviour_options_callback = create_behaviour_options_callback
        self.update_box_colors_callback = update_box_colors_callback
        self.save_and_close_axis_callback = save_and_close_axis_callback
        self.redraw_graph_callback = redraw_graph_callback
        self.view_state = GraphSettingsViewState(
            selected_photometry_line_width=str(
                getattr(self.settings_manager, "selected_photometry_line_width", "0.5")
            ),
            duration_box_placement=str(
                getattr(self.settings_manager, "duration_box_placement", "1.0")
            ),
            display_duration_box=bool(
                getattr(self.settings_manager, "display_duration_box_var", True)
            ),
            num_instances_box=bool(
                getattr(self.settings_manager, "num_instances_box_var", True)
            ),
        )

        self._initialize_value_models()
        self._build_ui()
        self._connect_callbacks()

    def _initialize_value_models(self) -> None:
        self.selected_photometry_line_width = ObservableValue(
            self.view_state.selected_photometry_line_width
        )
        self.box_height_factor_var = ObservableValue(
            str(getattr(self.settings_manager, "box_height_factor", "0.2"))
        )
        self.alpha_var = ObservableValue(
            str(getattr(self.settings_manager, "alpha", "0.2"))
        )
        self.bar_graph_size_var = ObservableValue(
            str(getattr(self.settings_manager, "bar_graph_size", "0.2"))
        )
        self.onset_line_thickness_var = ObservableValue(
            str(getattr(self.settings_manager, "onset_line_thickness", "1"))
        )
        self.onset_line_style_var = ObservableValue(
            str(getattr(self.settings_manager, "onset_line_style", "--"))
        )
        self.number_of_minor_ticks_var = ObservableValue(
            str(getattr(self.settings_manager, "number_of_minor_ticks", "0"))
        )
        self.duration_box_placement = ObservableValue(self.view_state.duration_box_placement)
        self.display_duration_box_var = ObservableValue(self.view_state.display_duration_box)
        self.num_instances_box_var = ObservableValue(self.view_state.num_instances_box)
        self.time_unit_var = ObservableValue(self.view_state.time_unit)
        self.x_gridlines_var = ObservableValue(self.view_state.x_gridlines)
        self.y_gridlines_var = ObservableValue(self.view_state.y_gridlines)
        self.x_axis_min_var = ObservableValue(self.view_state.x_axis_min)
        self.x_axis_max_var = ObservableValue(self.view_state.x_axis_max)
        self.y_axis_min_var = ObservableValue(self.view_state.y_axis_min)
        self.y_axis_max_var = ObservableValue(self.view_state.y_axis_max)
        self.activity_data_var = ObservableValue(self.view_state.activity_data_enabled)
        self.temperature_data_var = ObservableValue(
            self.view_state.temperature_data_enabled
        )
        self.limit_axis_range_var = ObservableValue(self.view_state.limit_axis_range)
        self.zero_x_axis_checkbox_var = ObservableValue(
            bool(self.view_state.zero_x_axis_to_behaviour)
        )
        self.selected_behaviour_to_zero = ObservableValue(
            self.view_state.selected_behaviour_to_zero.strip()
        )
        self.remove_first_60_minutes_var = ObservableValue(
            bool(getattr(self.settings_manager, "remove_first_60_minutes_var", True))
        )

        self.selected_bar_fill_color = getattr(
            self.settings_manager, "selected_bar_fill_color", "blue"
        )
        self.selected_bar_border_color = getattr(
            self.settings_manager, "selected_bar_border_color", "black"
        )
        self.selected_line_color = getattr(
            self.settings_manager, "selected_line_color", "red"
        )
        self.selected_bar_sem_color = getattr(
            self.settings_manager, "selected_bar_sem_color", "grey"
        )
        self.selected_cluster_box_color = getattr(
            self.settings_manager, "selected_cluster_box_color", "orange"
        )

        self._bind_setting(
            self.selected_photometry_line_width, "selected_photometry_line_width"
        )
        self._bind_setting(self.box_height_factor_var, "box_height_factor")
        self._bind_setting(self.alpha_var, "alpha")
        self._bind_setting(self.bar_graph_size_var, "bar_graph_size")
        self._bind_setting(self.onset_line_thickness_var, "onset_line_thickness")
        self._bind_setting(self.onset_line_style_var, "onset_line_style")
        self._bind_setting(self.duration_box_placement, "duration_box_placement")
        self._bind_setting(self.display_duration_box_var, "display_duration_box_var")
        self._bind_setting(self.num_instances_box_var, "num_instances_box_var")
        self._bind_setting(self.number_of_minor_ticks_var, "number_of_minor_ticks")
        self._bind_setting(self.remove_first_60_minutes_var, "remove_first_60_minutes_var")

    def _bind_setting(self, value_model: ObservableValue, setting_name: str) -> None:
        if self.settings_manager is None:
            return

        def update_setting() -> None:
            setattr(self.settings_manager, setting_name, value_model.get())

        value_model.trace_add("write", update_setting)
        update_setting()

    def _build_ui(self) -> None:
        self.setObjectName("graphSettingsPanel")
        self.setStyleSheet(
            panel_stylesheet("graphSettingsPanel")
            + section_stylesheet("graphSectionCard")
            + section_stylesheet("graphSectionCardAlt", alt=True)
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(8)

        title = QLabel("Graph Settings", self)
        title.setStyleSheet(title_stylesheet())
        outer.addWidget(title)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll, 1)

        scroll_content = QWidget(scroll)
        scroll.setWidget(scroll_content)

        content_col = QVBoxLayout(scroll_content)
        content_col.setContentsMargins(0, 0, 4, 0)
        content_col.setSpacing(8)

        if self.show_visibility_card:
            content_col.addWidget(self._build_visibility_card())

        appearance_card = self._build_appearance_card()
        if appearance_card is not None:
            content_col.addWidget(appearance_card)

        time_axis_card = self._build_time_axis_card()
        if time_axis_card is not None:
            content_col.addWidget(time_axis_card)

        display_card = self._build_display_card()
        if display_card is not None:
            content_col.addWidget(display_card)

        content_col.addStretch(1)

    def _include(self, widget_name: str) -> bool:
        return not self.widgets_to_include or widget_name in self.widgets_to_include

    def _connect_callbacks(self) -> None:
        self.zero_x_axis_checkbox_var.trace_add("write", self._sync_zero_axis_state)
        self._sync_zero_axis_state()

    def _build_appearance_card(self) -> QWidget | None:
        if not any(
            self._include(name)
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

        card, layout = self._create_card(
            self.appearance_section_title,
            "",
        )
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        layout.addLayout(grid)

        field_specs = []
        if self._include("line_width"):
            field_specs.append(
                ("Line Width", "line_width_entry", self.selected_photometry_line_width)
            )
        if self._include("box_height"):
            field_specs.append(
                ("Box Height", "box_height_entry", self.box_height_factor_var)
            )
        if self._include("alpha"):
            field_specs.append(("Alpha", "alpha_entry", self.alpha_var))
        if self._include("bar_graph_size"):
            field_specs.append(
                ("Bar Size", "bar_graph_size_entry", self.bar_graph_size_var)
            )
        if self._include("onset_line_thickness"):
            field_specs.append(
                (
                    "Onset Width",
                    "onset_line_thickness_entry",
                    self.onset_line_thickness_var,
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

        if self._include("onset_line_style"):
            # Place in next available slot on the current row, or a new row if full
            remainder = len(field_specs) % 3
            if field_specs and remainder != 0:
                style_col = remainder * 2
            else:
                row += 1 if field_specs else 0
                style_col = 0
            grid.addWidget(QLabel("Onset Style", card), row, style_col)
            self.onset_line_style_combobox = ComboBoxControl(
                self.onset_line_style_var, card
            )
            self.onset_line_style_combobox.set_options(["--", "-", "-.", ":"])
            self.onset_line_style_combobox.set(self.onset_line_style_var.get() or "--")
            self.onset_line_style_combobox.setMaximumWidth(120)
            grid.addWidget(self.onset_line_style_combobox, row, style_col + 1)
            row += 1

        # Stretch col 6 so label/button pairs in the 3-column colour section stay tight
        grid.setColumnStretch(6, 1)

        if self._include("color_buttons"):
            palette_title = QLabel("Colour Shortcuts", card)
            palette_title.setStyleSheet(section_title_stylesheet())
            grid.addWidget(palette_title, row, 0, 1, 6)
            row += 1

            color_specs = [
                ("Bar Fill", "bar_fill_color_button", "selected_bar_fill_color"),
                ("Bar Border", "bar_border_color_button", "selected_bar_border_color"),
                ("Onset Line", "line_color_button", "selected_line_color"),
                ("Bar SEM", "sem_color_button", "selected_bar_sem_color"),
            ]
            if self._include("cluster_box_color"):
                color_specs.append(
                    ("Cluster Box", "cluster_box_color_button", "selected_cluster_box_color")
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
        if self._include("photometry_settings"):
            self.photometry_settings_button = QPushButton(
                self.photometry_button_text, card
            )
            self.photometry_settings_button.clicked.connect(
                self.open_photometry_settings_popup
            )
            apply_button_role(
                self.photometry_settings_button, self.advanced_button_role
            )
            advanced_buttons.append(self.photometry_settings_button)
        if self._include("temperature_settings"):
            self.temperature_settings_button = QPushButton(
                self.temperature_button_text, card
            )
            self.temperature_settings_button.clicked.connect(
                self.open_temperature_settings_popup
            )
            apply_button_role(
                self.temperature_settings_button, self.advanced_button_role
            )
            advanced_buttons.append(self.temperature_settings_button)
        if self._include("activity_settings"):
            self.activity_settings_button = QPushButton(
                self.activity_button_text, card
            )
            self.activity_settings_button.clicked.connect(
                self.open_activity_settings_popup
            )
            apply_button_role(
                self.activity_settings_button, self.advanced_button_role
            )
            advanced_buttons.append(self.activity_settings_button)

        if advanced_buttons:
            if self.advanced_buttons_title:
                buttons_label = QLabel(self.advanced_buttons_title, card)
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

        if self.overlay_visibility_in_appearance:
            row = self._add_overlay_visibility_controls(
                grid,
                row,
                card,
                "Show on Graph",
            )

        self.update_button_colors()
        return card

    def _build_display_card(self) -> QWidget | None:
        show_overlay_visibility = not self.overlay_visibility_in_appearance and (
            self._include("temperature_settings") or self._include("activity_settings")
        )

        if not any(
            self._include(name)
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
        if self._include("checkboxes"):
            self.display_duration_checkbox = CheckBoxControl(
                "Display Duration",
                self.display_duration_box_var,
                card,
            )
            self.display_duration_checkbox.clicked.connect(self._refresh_graph)
            grid.addWidget(self.display_duration_checkbox, row, 0, 1, 2)

            self.num_instances_checkbox = CheckBoxControl(
                "Display Number of Instances",
                self.num_instances_box_var,
                card,
            )
            self.num_instances_checkbox.clicked.connect(self._refresh_graph)
            grid.addWidget(self.num_instances_checkbox, row, 2, 1, 2)
            row += 1

            grid.addWidget(QLabel("Duration Box Placement (+/-)", card), row, 0, 1, 2)
            self.duration_box_placement_entry = LineEditControl(
                self.duration_box_placement, card
            )
            self.duration_box_placement_entry.setMaximumWidth(90)
            self.duration_box_placement_entry.editingFinished.connect(
                self.update_duration_box
            )
            grid.addWidget(self.duration_box_placement_entry, row, 2)
            row += 1

        if show_overlay_visibility:
            row = self._add_overlay_visibility_controls(
                grid,
                row,
                card,
                "Overlay Visibility",
            )

        if self._include("remove_first_60_minutes"):
            self.remove_first_60_minutes_checkbox = CheckBoxControl(
                "Remove first 60 minutes",
                self.remove_first_60_minutes_var,
                card,
            )
            self.remove_first_60_minutes_checkbox.clicked.connect(self._redraw_graph)
            grid.addWidget(self.remove_first_60_minutes_checkbox, row, 0, 1, 4)

        return card

    def _add_overlay_visibility_controls(
        self,
        grid: QGridLayout,
        row: int,
        card: QWidget,
        title: str | None,
    ) -> int:
        has_temperature = self._include("temperature_settings")
        has_activity = self._include("activity_settings")
        if not has_temperature and not has_activity:
            return row

        if title:
            toggles_label = QLabel(title, card)
            toggles_label.setStyleSheet(section_title_stylesheet())
            grid.addWidget(toggles_label, row, 0, 1, 4)
            row += 1

        if has_temperature:
            self.temperature_checkbox = CheckBoxControl(
                "Temperature Data",
                self.temperature_data_var,
                card,
            )
            self.temperature_checkbox.clicked.connect(self._redraw_graph)
            grid.addWidget(self.temperature_checkbox, row, 0, 1, 2)

        if has_activity:
            self.activity_checkbox = CheckBoxControl(
                "Activity Data",
                self.activity_data_var,
                card,
            )
            self.activity_checkbox.clicked.connect(self._redraw_graph)
            grid.addWidget(self.activity_checkbox, row, 2, 1, 2)

        return row + 1

    def _build_time_axis_card(self) -> QWidget | None:
        if not any(
            self._include(name)
            for name in (
                "graph_time_labels",
                "axis_range",
                "zero_x_axis_to_behaviour",
                "number_of_minor_ticks",
            )
        ):
            return None

        card, layout = self._create_card(
            "Time & Axis",
            "",
        )
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        layout.addLayout(grid)

        row = 0
        update_button_pending = False
        if self._include("graph_time_labels"):
            grid.addWidget(QLabel("Time Unit", card), row, 0)
            self.time_unit_menu = ComboBoxControl(self.time_unit_var, card)
            self.time_unit_menu.set_options(["minutes", "seconds", "hours"])
            self.time_unit_menu.set(self.time_unit_var.get() or "minutes")
            self.time_unit_menu.currentTextChanged.connect(
                lambda *_args: self._refresh_graph()
            )
            grid.addWidget(self.time_unit_menu, row, 1)

            grid.addWidget(QLabel("X Ticks", card), row, 2)
            self.x_gridlines_entry = LineEditControl(self.x_gridlines_var, card)
            self.x_gridlines_entry.setMaximumWidth(90)
            grid.addWidget(self.x_gridlines_entry, row, 3)

            self.y_gridlines_label = QLabel("Y Ticks", card)
            grid.addWidget(self.y_gridlines_label, row, 4)
            self.y_gridlines_entry = LineEditControl(self.y_gridlines_var, card)
            self.y_gridlines_entry.setMaximumWidth(90)
            grid.addWidget(self.y_gridlines_entry, row, 5)

            self.update_button = QPushButton("Update Settings", card)
            apply_button_role(self.update_button, "primary")
            self.update_button.clicked.connect(self._refresh_graph)
            update_button_pending = True
            row += 1
        else:
            self.time_unit_menu = ComboBoxControl(self.time_unit_var, card)
            self.y_gridlines_label = QLabel("Y Ticks", card)
            self.y_gridlines_entry = LineEditControl(self.y_gridlines_var, card)

        if self._include("number_of_minor_ticks"):
            grid.addWidget(QLabel("Minor Ticks", card), row, 0)
            self.number_of_minor_ticks_entry = LineEditControl(
                self.number_of_minor_ticks_var, card
            )
            self.number_of_minor_ticks_entry.setMaximumWidth(90)
            grid.addWidget(self.number_of_minor_ticks_entry, row, 1)
            row += 1

        if self._include("axis_range"):
            self.limit_axis_checkbox = CheckBoxControl(
                "Limit Axis Range",
                self.limit_axis_range_var,
                card,
            )
            self.limit_axis_checkbox.clicked.connect(
                lambda *_args: self.save_and_close_axis(close=False)
            )
            grid.addWidget(self.limit_axis_checkbox, row, 0, 1, 2)

            self.axis_range_button = QPushButton("Set Axis Range", card)
            apply_button_role(self.axis_range_button, self.axis_range_button_role)
            self.axis_range_button.clicked.connect(self.open_axis_range_popup)
            grid.addWidget(self.axis_range_button, row, 2, 1, 2)

            if update_button_pending:
                grid.addWidget(self.update_button, row, 4, 1, 2)
                update_button_pending = False
            row += 1

        if update_button_pending:
            grid.addWidget(self.update_button, row, 0, 1, 2)
            row += 1

        if self._include("zero_x_axis_to_behaviour"):
            self.zero_axis_checkbox = CheckBoxControl(
                "Zero X-axis with behaviour",
                self.zero_x_axis_checkbox_var,
                card,
            )
            self.zero_axis_checkbox.clicked.connect(self._on_zero_axis_clicked)
            grid.addWidget(self.zero_axis_checkbox, row, 0, 1, 3)

            self.behaviour_to_zero_dropdown = ComboBoxControl(
                self.selected_behaviour_to_zero, card
            )
            self.behaviour_to_zero_dropdown.configure(state="disabled")
            self.behaviour_to_zero_dropdown.currentTextChanged.connect(
                lambda *_args: self._handle_behaviour_change()
            )
            grid.addWidget(self.behaviour_to_zero_dropdown, row, 3, 1, 3)

        return card

    def _build_visibility_card(self) -> QWidget:
        card, layout = self._create_card(
            self.visibility_section_title,
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
        self.behaviour_frame = content
        self.behaviour_frame_layout = QVBoxLayout(self.behaviour_frame)
        self.behaviour_frame_layout.setContentsMargins(0, 0, 0, 0)
        self.behaviour_frame_layout.setSpacing(8)
        self.behaviour_frame_layout.addStretch(1)
        return card

    def _create_card(
        self,
        heading: str,
        description: str,
        alt: bool = False,
    ) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame(self)
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
        layout.addWidget(QLabel(label_text, self), row, column)
        entry = LineEditControl(value, self)
        entry.setMaximumWidth(90)
        setattr(self, attribute_name, entry)
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
        button = QPushButton(label_text, self)
        button.clicked.connect(
            lambda _checked=False, attr=color_attr, target=button: self.choose_color(
                attr, target
            )
        )
        setattr(self, button_name, button)
        layout.addWidget(button, row, column, 1, 2)

    def _sync_zero_axis_state(self) -> None:
        dropdown = getattr(self, "behaviour_to_zero_dropdown", None)
        if dropdown is None:
            return
        enabled = bool(self.zero_x_axis_checkbox_var.get())
        dropdown.configure(state="normal" if enabled else "disabled")

    def _on_zero_axis_clicked(self) -> None:
        self._sync_zero_axis_state()
        self._handle_behaviour_change()

    def _handle_behaviour_change(self) -> None:
        if self.handle_behaviour_change_callback:
            self.handle_behaviour_change_callback()

    def _refresh_graph(self) -> None:
        if self.refresh_graph_display_callback:
            self.refresh_graph_display_callback()

    def _redraw_graph(self) -> None:
        if self.redraw_graph_callback:
            self.redraw_graph_callback()
        elif self.refresh_graph_display_callback:
            self.refresh_graph_display_callback()

    def complete_initialization(self) -> None:
        if self.load_variables_callback:
            self.load_variables_callback()
        self._sync_from_settings_manager()
        self.update_button_colors()

    def _sync_from_settings_manager(self) -> None:
        self.selected_photometry_line_width.set(
            str(getattr(self.settings_manager, "selected_photometry_line_width", "0.5"))
        )
        self.box_height_factor_var.set(
            str(getattr(self.settings_manager, "box_height_factor", "0.2"))
        )
        self.alpha_var.set(str(getattr(self.settings_manager, "alpha", "0.2")))
        self.bar_graph_size_var.set(
            str(getattr(self.settings_manager, "bar_graph_size", "0.2"))
        )
        self.onset_line_thickness_var.set(
            str(getattr(self.settings_manager, "onset_line_thickness", "1"))
        )
        self.onset_line_style_var.set(
            str(getattr(self.settings_manager, "onset_line_style", "--"))
        )
        self.duration_box_placement.set(
            str(getattr(self.settings_manager, "duration_box_placement", "1.0"))
        )
        self.display_duration_box_var.set(
            bool(getattr(self.settings_manager, "display_duration_box_var", True))
        )
        self.num_instances_box_var.set(
            bool(getattr(self.settings_manager, "num_instances_box_var", True))
        )
        self.number_of_minor_ticks_var.set(
            str(getattr(self.settings_manager, "number_of_minor_ticks", "0"))
        )
        self.remove_first_60_minutes_var.set(
            bool(getattr(self.settings_manager, "remove_first_60_minutes_var", True))
        )

        self.selected_bar_fill_color = getattr(
            self.settings_manager, "selected_bar_fill_color", "blue"
        )
        self.selected_bar_border_color = getattr(
            self.settings_manager, "selected_bar_border_color", "black"
        )
        self.selected_line_color = getattr(
            self.settings_manager, "selected_line_color", "red"
        )
        self.selected_bar_sem_color = getattr(
            self.settings_manager, "selected_bar_sem_color", "grey"
        )
        self.selected_cluster_box_color = getattr(
            self.settings_manager, "selected_cluster_box_color", "orange"
        )

    def setup_canvas(self) -> None:
        if not hasattr(self, "behaviour_frame_layout"):
            return
        while self.behaviour_frame_layout.count():
            item = self.behaviour_frame_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def update_button_colors(self) -> None:
        for button_name, color_attr in {
            "bar_fill_color_button": "selected_bar_fill_color",
            "bar_border_color_button": "selected_bar_border_color",
            "line_color_button": "selected_line_color",
            "sem_color_button": "selected_bar_sem_color",
            "cluster_box_color_button": "selected_cluster_box_color",
        }.items():
            button = getattr(self, button_name, None)
            if button is None:
                continue
            self._set_color_button_style(button, getattr(self, color_attr))

    def _set_color_button_style(self, button: QPushButton, color_value: str) -> None:
        foreground = "white" if self.brightness(color_value) < 0.56 else PALETTE["text"]
        button.setStyleSheet(
            "QPushButton {"
            f"background: {color_value};"
            f"color: {foreground};"
            "border: 1px solid rgba(23, 50, 77, 0.16);"
            "border-radius: 10px;"
            "padding: 7px 12px;"
            "font-weight: 600;"
            "}"
        )

    def string_to_color(self, input_string: str):
        digest = hashlib.md5(input_string.encode("utf-8")).hexdigest()
        red = int(digest[0:2], 16) / 255.0
        green = int(digest[2:4], 16) / 255.0
        blue = int(digest[4:6], 16) / 255.0
        return red, green, blue

    def brightness(self, color) -> float:
        if isinstance(color, (tuple, list)) and len(color) >= 3:
            red = float(color[0])
            green = float(color[1])
            blue = float(color[2])
            return (red * 299 + green * 587 + blue * 114) / 1000.0
        qcolor = QColor(color)
        if not qcolor.isValid():
            return 1.0
        red, green, blue, _alpha = qcolor.getRgb()
        return (
            (red / 255.0) * 299 + (green / 255.0) * 587 + (blue / 255.0) * 114
        ) / 1000.0

    def choose_color(self, behavior_or_attr, color_button) -> None:
        current_color = getattr(self, behavior_or_attr, "#000000")
        dialog_color = QColor(current_color) if QColor(current_color).isValid() else QColor()
        color = QColorDialog.getColor(dialog_color, self)
        if not color.isValid():
            return

        if behavior_or_attr.startswith("selected_"):
            selected = color.name()
            setattr(self, behavior_or_attr, selected)
            if self.settings_manager is not None and hasattr(
                self.settings_manager, behavior_or_attr
            ):
                setattr(self.settings_manager, behavior_or_attr, selected)
            self._set_color_button_style(color_button, selected)
            if self.handle_behaviour_change_callback:
                self.handle_behaviour_change_callback()
        elif self.update_box_colors_callback:
            self.update_box_colors_callback(behavior_or_attr, color.getRgbF()[:3])
        if self.save_variables_callback:
            self.save_variables_callback()
        elif self.settings_manager is not None:
            self.settings_manager.save_variables()

    def update_duration_box(self) -> None:
        if self.update_duration_box_callback:
            self.update_duration_box_callback()

    def _persist_and_redraw(self) -> None:
        if self.save_variables_callback:
            self.save_variables_callback()
        elif self.settings_manager is not None:
            self.settings_manager.save_variables()
        self._redraw_graph()

    def save_and_close_axis(
        self,
        popup: QDialog | None = None,
        close: bool = True,
    ) -> None:
        if self.save_and_close_axis_callback:
            self.save_and_close_axis_callback(popup=popup, close=close)

    def open_axis_range_popup(self) -> None:
        popup = self._create_popup(
            "Axis Range",
            "",
        )
        form = QGridLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)
        popup.layout().addLayout(form)

        axis_fields = [
            ("X Min", self.x_axis_min_var, "x_axis_min_entry"),
            ("X Max", self.x_axis_max_var, "x_axis_max_entry"),
            ("Y Min", self.y_axis_min_var, "y_axis_min_entry"),
            ("Y Max", self.y_axis_max_var, "y_axis_max_entry"),
        ]
        for index, (label_text, value_model, attr_name) in enumerate(axis_fields):
            row = index // 2
            column = (index % 2) * 2
            form.addWidget(QLabel(label_text, popup), row, column)
            entry = LineEditControl(value_model, popup)
            entry.setMaximumWidth(120)
            setattr(self, attr_name, entry)
            form.addWidget(entry, row, column + 1)

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(8)
        popup.layout().addLayout(buttons)

        apply_button = QPushButton("Apply", popup)
        apply_button_role(apply_button)
        apply_button.clicked.connect(
            lambda: self.save_and_close_axis(popup=popup, close=False)
        )
        buttons.addWidget(apply_button)

        save_button = QPushButton("Apply & Close", popup)
        apply_button_role(save_button, "primary")
        save_button.clicked.connect(lambda: self.save_and_close_axis(popup=popup))
        buttons.addWidget(save_button)
        buttons.addStretch(1)

        popup.exec()

    def open_photometry_settings_popup(self) -> None:
        popup = self._create_popup(
            "Photometry Settings",
            "",
        )
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        popup.layout().addLayout(grid)

        line_color = ObservableValue(
            str(getattr(self.settings_manager, "selected_photometry_line_color", "black"))
        )
        line_width = ObservableValue(
            str(getattr(self.settings_manager, "selected_photometry_line_width", "0.5"))
        )
        line_alpha = ObservableValue(
            str(getattr(self.settings_manager, "selected_photometry_line_alpha", "1.0"))
        )

        grid.addWidget(QLabel("Line Colour", popup), 0, 0)
        colour_button = QPushButton(popup)
        self._set_color_button_style(colour_button, line_color.get() or "black")
        colour_button.clicked.connect(
            lambda: self._select_popup_color(line_color, colour_button)
        )
        grid.addWidget(colour_button, 0, 1)

        grid.addWidget(QLabel("Line Width", popup), 1, 0)
        grid.addWidget(LineEditControl(line_width, popup), 1, 1)

        grid.addWidget(QLabel("Line Alpha", popup), 2, 0)
        grid.addWidget(LineEditControl(line_alpha, popup), 2, 1)

        save_button = QPushButton("Save & Close", popup)
        apply_button_role(save_button, "primary")
        save_button.clicked.connect(
            lambda: self._save_photometry_settings(
                popup, line_color.get(), line_width.get(), line_alpha.get()
            )
        )
        popup.layout().addWidget(save_button, alignment=Qt.AlignLeft)

        popup.exec()

    def _save_photometry_settings(
        self,
        popup: QDialog,
        line_color: str | None,
        line_width: str | None,
        line_alpha: str | None,
    ) -> None:
        self.settings_manager.selected_photometry_line_color = line_color or "black"
        self.settings_manager.selected_photometry_line_width = line_width or "0.5"
        self.settings_manager.selected_photometry_line_alpha = line_alpha or "1.0"
        self.selected_photometry_line_width.set(
            self.settings_manager.selected_photometry_line_width
        )
        self._persist_and_redraw()
        popup.accept()

    def open_temperature_settings_popup(self) -> None:
        popup = self._create_popup(
            "Temperature Settings",
            "",
        )
        controls = self._build_temperature_popup_fields(popup)
        save_button = QPushButton("Save & Close", popup)
        apply_button_role(save_button, "primary")
        save_button.clicked.connect(
            lambda: self._save_temperature_settings(popup, controls)
        )
        popup.layout().addWidget(save_button, alignment=Qt.AlignLeft)
        popup.exec()

    def _build_temperature_popup_fields(self, popup: QDialog) -> dict[str, ObservableValue]:
        controls = {
            "mean_line_width": ObservableValue(
                str(getattr(self.settings_manager, "selected_temp_mean_line_width", "1"))
            ),
            "mean_line_color": ObservableValue(
                str(
                    getattr(
                        self.settings_manager,
                        "selected_temp_mean_line_color",
                        "red",
                    )
                )
            ),
            "mean_line_alpha": ObservableValue(
                str(getattr(self.settings_manager, "selected_temp_mean_line_alpha", "1.0"))
            ),
            "sem_color": ObservableValue(
                str(getattr(self.settings_manager, "selected_temp_sem_color", "orange"))
            ),
            "sem_line_alpha": ObservableValue(
                str(getattr(self.settings_manager, "selected_temp_sem_line_alpha", "0.1"))
            ),
            "desired_offset": ObservableValue(
                str(getattr(self.settings_manager, "selected_temp_desired_offset", "0.5"))
            ),
            "desired_scale": ObservableValue(
                str(getattr(self.settings_manager, "selected_temp_desired_scale", "0.4"))
            ),
            "y_axis_color": ObservableValue(
                str(getattr(self.settings_manager, "selected_temp_y_axis_color", "red"))
            ),
            "num_ticks": ObservableValue(
                str(getattr(self.settings_manager, "selected_temp_num_ticks", "10"))
            ),
        }
        self._build_common_settings_popup(
            popup,
            controls,
            include_line_width=True,
            include_sem=True,
        )
        return controls

    def _save_temperature_settings(
        self,
        popup: QDialog,
        controls: dict[str, ObservableValue],
    ) -> None:
        self.settings_manager.selected_temp_mean_line_width = (
            controls["mean_line_width"].get() or "1"
        )
        self.settings_manager.selected_temp_line_width = (
            self.settings_manager.selected_temp_mean_line_width
        )
        self.settings_manager.selected_temp_mean_line_color = (
            controls["mean_line_color"].get() or "red"
        )
        self.settings_manager.selected_temp_sem_color = (
            controls["sem_color"].get() or "orange"
        )
        self.settings_manager.selected_temp_mean_line_alpha = (
            controls["mean_line_alpha"].get() or "1.0"
        )
        self.settings_manager.selected_temp_sem_line_alpha = (
            controls["sem_line_alpha"].get() or "0.1"
        )
        self.settings_manager.selected_temp_desired_offset = (
            controls["desired_offset"].get() or "0.5"
        )
        self.settings_manager.selected_temp_desired_scale = (
            controls["desired_scale"].get() or "0.4"
        )
        self.settings_manager.selected_temp_y_axis_color = (
            controls["y_axis_color"].get() or "red"
        )
        self.settings_manager.selected_temp_num_ticks = (
            controls["num_ticks"].get() or "10"
        )
        self._persist_and_redraw()
        popup.accept()

    def open_activity_settings_popup(self) -> None:
        popup = self._create_popup(
            "Activity Settings",
            "",
        )
        controls = self._build_activity_popup_fields(popup)
        save_button = QPushButton("Save & Close", popup)
        apply_button_role(save_button, "primary")
        save_button.clicked.connect(lambda: self._save_activity_settings(popup, controls))
        popup.layout().addWidget(save_button, alignment=Qt.AlignLeft)
        popup.exec()

    def _build_activity_popup_fields(self, popup: QDialog) -> dict[str, ObservableValue]:
        controls = {
            "mean_bar_color": ObservableValue(
                str(
                    getattr(
                        self.settings_manager,
                        "selected_activity_mean_bar_color",
                        "green",
                    )
                )
            ),
            "mean_bar_alpha": ObservableValue(
                str(getattr(self.settings_manager, "selected_activity_mean_bar_alpha", "0.5"))
            ),
            "desired_offset": ObservableValue(
                str(getattr(self.settings_manager, "selected_activity_desired_offset", "0"))
            ),
            "desired_scale": ObservableValue(
                str(getattr(self.settings_manager, "selected_activity_desired_scale", "0.3"))
            ),
            "y_axis_color": ObservableValue(
                str(getattr(self.settings_manager, "selected_activity_y_axis_color", "green"))
            ),
            "num_ticks": ObservableValue(
                str(getattr(self.settings_manager, "selected_activity_num_ticks", "10"))
            ),
            "num_bins": ObservableValue(
                str(getattr(self.settings_manager, "selected_activity_num_bins", ""))
            ),
        }
        self._build_common_settings_popup(
            popup,
            controls,
            include_line_width=False,
            include_sem=False,
        )
        return controls

    def _save_activity_settings(
        self,
        popup: QDialog,
        controls: dict[str, ObservableValue],
    ) -> None:
        self.settings_manager.selected_activity_mean_bar_color = (
            controls["mean_bar_color"].get() or "green"
        )
        self.settings_manager.selected_activity_mean_bar_alpha = (
            controls["mean_bar_alpha"].get() or "0.5"
        )
        self.settings_manager.selected_activity_desired_offset = (
            controls["desired_offset"].get() or "0"
        )
        self.settings_manager.selected_activity_desired_scale = (
            controls["desired_scale"].get() or "0.3"
        )
        self.settings_manager.selected_activity_y_axis_color = (
            controls["y_axis_color"].get() or "green"
        )
        self.settings_manager.selected_activity_num_ticks = (
            controls["num_ticks"].get() or "10"
        )
        self.settings_manager.selected_activity_num_bins = (
            controls["num_bins"].get() or ""
        )
        self._persist_and_redraw()
        popup.accept()

    def _build_common_settings_popup(
        self,
        popup: QDialog,
        controls: dict[str, ObservableValue],
        include_line_width: bool,
        include_sem: bool,
    ) -> None:
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        popup.layout().addLayout(grid)

        row = 0
        if include_line_width:
            grid.addWidget(QLabel("Line Width", popup), row, 0)
            grid.addWidget(LineEditControl(controls["mean_line_width"], popup), row, 1)
            row += 1

        color_key = "mean_line_color" if include_line_width else "mean_bar_color"
        color_label = "Mean Line Colour" if include_line_width else "Mean Bar Colour"
        grid.addWidget(QLabel(color_label, popup), row, 0)
        mean_color_button = QPushButton(popup)
        self._set_color_button_style(mean_color_button, controls[color_key].get() or "black")
        mean_color_button.clicked.connect(
            lambda: self._select_popup_color(controls[color_key], mean_color_button)
        )
        grid.addWidget(mean_color_button, row, 1)
        row += 1

        alpha_key = "mean_line_alpha" if include_line_width else "mean_bar_alpha"
        alpha_label = "Line Alpha" if include_line_width else "Bar Alpha"
        grid.addWidget(QLabel(alpha_label, popup), row, 0)
        grid.addWidget(LineEditControl(controls[alpha_key], popup), row, 1)
        row += 1

        if include_sem:
            grid.addWidget(QLabel("SEM Colour", popup), row, 0)
            sem_button = QPushButton(popup)
            self._set_color_button_style(sem_button, controls["sem_color"].get() or "orange")
            sem_button.clicked.connect(
                lambda: self._select_popup_color(controls["sem_color"], sem_button)
            )
            grid.addWidget(sem_button, row, 1)
            row += 1

            grid.addWidget(QLabel("SEM Alpha", popup), row, 0)
            grid.addWidget(LineEditControl(controls["sem_line_alpha"], popup), row, 1)
            row += 1

        grid.addWidget(QLabel("Desired Offset", popup), row, 0)
        grid.addWidget(LineEditControl(controls["desired_offset"], popup), row, 1)
        row += 1

        grid.addWidget(QLabel("Desired Scale", popup), row, 0)
        grid.addWidget(LineEditControl(controls["desired_scale"], popup), row, 1)
        row += 1

        grid.addWidget(QLabel("Y Axis Colour", popup), row, 0)
        axis_button = QPushButton(popup)
        self._set_color_button_style(axis_button, controls["y_axis_color"].get() or "black")
        axis_button.clicked.connect(
            lambda: self._select_popup_color(controls["y_axis_color"], axis_button)
        )
        grid.addWidget(axis_button, row, 1)
        row += 1

        grid.addWidget(QLabel("Number of Ticks", popup), row, 0)
        grid.addWidget(LineEditControl(controls["num_ticks"], popup), row, 1)
        row += 1

        if "num_bins" in controls:
            grid.addWidget(QLabel("Number of Bins", popup), row, 0)
            grid.addWidget(LineEditControl(controls["num_bins"], popup), row, 1)

    def _create_popup(self, heading: str, description: str) -> QDialog:
        popup = QDialog(self)
        popup.setWindowTitle(heading)
        popup.setObjectName("graphSettingsPanel")
        popup.setStyleSheet(
            panel_stylesheet("graphSettingsPanel")
            + section_stylesheet("graphSectionCard")
        )
        layout = QVBoxLayout(popup)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel(heading, popup)
        title.setStyleSheet(title_stylesheet())
        layout.addWidget(title)

        subtitle = QLabel(description, popup)
        subtitle.setStyleSheet(subtitle_stylesheet())
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)
        return popup

    def _select_popup_color(
        self,
        value_model: ObservableValue[str],
        button: QPushButton,
    ) -> None:
        current = value_model.get() or "#000000"
        selected_color = QColorDialog.getColor(QColor(current), self)
        if not selected_color.isValid():
            return
        value_model.set(selected_color.name())
        self._set_color_button_style(button, selected_color.name())
