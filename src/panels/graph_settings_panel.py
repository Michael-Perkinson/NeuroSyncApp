from __future__ import annotations

import hashlib

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QDialog,
    QFrame,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.gui.framework.qt_view_styles import (
    PALETTE,
    panel_stylesheet,
    section_stylesheet,
    title_stylesheet,
)
from src.gui.framework.tk_compat_controls import ObservableValue
from src.gui.framework.view_state_models import GraphSettingsViewState

from .graph_settings_dialogs import (
    ActivitySettingsDialog,
    AxisRangeDialog,
    PhotometrySettingsDialog,
    TemperatureSettingsDialog,
)
from .graph_settings_sections import GraphSettingsSectionBuilder


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
                getattr(self.settings_manager,
                        "selected_photometry_line_width", "0.5")
            ),
            duration_box_placement=str(
                getattr(self.settings_manager, "duration_box_placement", "1.0")
            ),
            display_duration_box=bool(
                getattr(self.settings_manager,
                        "display_duration_box_var", True)
            ),
            num_instances_box=bool(
                getattr(self.settings_manager, "num_instances_box_var", True)
            ),
        )

        self._initialize_value_models()
        self._section_builder = GraphSettingsSectionBuilder(self)
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
        self.duration_box_placement = ObservableValue(
            self.view_state.duration_box_placement)
        self.display_duration_box_var = ObservableValue(
            self.view_state.display_duration_box)
        self.num_instances_box_var = ObservableValue(
            self.view_state.num_instances_box)
        self.time_unit_var = ObservableValue(self.view_state.time_unit)
        self.x_gridlines_var = ObservableValue(self.view_state.x_gridlines)
        self.y_gridlines_var = ObservableValue(self.view_state.y_gridlines)
        self.x_axis_min_var = ObservableValue(self.view_state.x_axis_min)
        self.x_axis_max_var = ObservableValue(self.view_state.x_axis_max)
        self.y_axis_min_var = ObservableValue(self.view_state.y_axis_min)
        self.y_axis_max_var = ObservableValue(self.view_state.y_axis_max)
        self.activity_data_var = ObservableValue(
            self.view_state.activity_data_enabled)
        self.temperature_data_var = ObservableValue(
            self.view_state.temperature_data_enabled
        )
        self.limit_axis_range_var = ObservableValue(
            self.view_state.limit_axis_range)
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
        self._bind_setting(self.onset_line_thickness_var,
                           "onset_line_thickness")
        self._bind_setting(self.onset_line_style_var, "onset_line_style")
        self._bind_setting(self.duration_box_placement,
                           "duration_box_placement")
        self._bind_setting(self.display_duration_box_var,
                           "display_duration_box_var")
        self._bind_setting(self.num_instances_box_var, "num_instances_box_var")
        self._bind_setting(self.number_of_minor_ticks_var,
                           "number_of_minor_ticks")
        self._bind_setting(self.remove_first_60_minutes_var,
                           "remove_first_60_minutes_var")

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
        self.zero_x_axis_checkbox_var.trace_add(
            "write", self._sync_zero_axis_state)
        self._sync_zero_axis_state()

    def _build_appearance_card(self) -> QWidget | None:
        return self._section_builder.build_appearance_card()

    def _build_display_card(self) -> QWidget | None:
        return self._section_builder.build_display_card()

    def _build_time_axis_card(self) -> QWidget | None:
        return self._section_builder.build_time_axis_card()

    def _build_visibility_card(self) -> QWidget:
        return self._section_builder.build_visibility_card()

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
            str(getattr(self.settings_manager,
                "selected_photometry_line_width", "0.5"))
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
        foreground = "white" if self.brightness(
            color_value) < 0.56 else PALETTE["text"]
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
        dialog_color = QColor(current_color) if QColor(
            current_color).isValid() else QColor()
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
            self.update_box_colors_callback(
                behavior_or_attr, color.getRgbF()[:3])
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
        AxisRangeDialog(self).exec()

    def open_photometry_settings_popup(self) -> None:
        PhotometrySettingsDialog(self).exec()

    def open_temperature_settings_popup(self) -> None:
        TemperatureSettingsDialog(self).exec()

    def open_activity_settings_popup(self) -> None:
        ActivitySettingsDialog(self).exec()

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
