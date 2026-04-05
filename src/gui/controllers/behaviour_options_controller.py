"""Controller for behaviour option widgets (colors + visibility checkboxes)."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from src.gui.shared.qt_bindings import CheckBoxControl


class BehaviourOptionsController:
    """Owns behaviour options frame construction and box color updates."""

    def __init__(self, app):
        self.app = app

    def create_behaviour_options(self, unique_behaviour_names, destroy_frame=True) -> None:
        if destroy_frame:
            self.destroy_existing_frame()

        self.app.behaviour_checkboxes = {}
        self.app.settings_manager.update_unique_behaviours(unique_behaviour_names)
        self.app.graph_settings_container_instance.setup_canvas()
        self.create_control_buttons()
        self.create_behaviour_labels_and_controls(unique_behaviour_names)

    def destroy_existing_frame(self) -> None:
        if hasattr(self.app, "behaviour_frame"):
            self.app.graph_settings_container_instance.setup_canvas()

    def create_control_buttons(self) -> None:
        controls_row = QWidget(self.app.graph_settings_container_instance.behaviour_frame)
        controls_layout = QHBoxLayout(controls_row)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(10)

        behaviour_list_label = QLabel("Behaviours", controls_row)
        controls_layout.addWidget(behaviour_list_label)

        select_all_button = QPushButton(
            "Select All", self.app.graph_settings_container_instance.behaviour_frame
        )
        select_all_button.clicked.connect(self.app.behaviour_settings_controller.select_all)
        controls_layout.addWidget(select_all_button)

        deselect_all_button = QPushButton(
            "Deselect All", self.app.graph_settings_container_instance.behaviour_frame
        )
        deselect_all_button.clicked.connect(
            self.app.behaviour_settings_controller.deselect_all
        )
        controls_layout.addWidget(deselect_all_button)
        controls_layout.addStretch(1)
        self.app.graph_settings_container_instance.behaviour_frame_layout.addWidget(controls_row)

    def create_behaviour_labels_and_controls(self, sorted_behaviours) -> None:
        self.app.color_buttons = {}
        for behaviour in sorted_behaviours:
            self.create_behaviour_control(behaviour)

    def create_behaviour_control(self, behaviour) -> None:
        behaviour_color = self.app.behaviour_colors.get(behaviour)
        if behaviour_color is None:
            return

        color_code, text_color = self.get_color_code_and_text_color(behaviour_color)
        row_widget = QWidget(self.app.graph_settings_container_instance.behaviour_frame)
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(10)
        self.create_checkbox(behaviour, row_layout, row_widget)
        self.create_color_button(behaviour, color_code, text_color, row_layout, row_widget)
        row_layout.addStretch(1)
        self.app.graph_settings_container_instance.behaviour_frame_layout.addWidget(row_widget)

    def get_color_code_and_text_color(self, behaviour_color):
        r, g, b = [int(component * 255) for component in behaviour_color[:3]]
        color_code = "#%02x%02x%02x" % (r, g, b)
        color_brightness = self.app.graph_settings_container_instance.brightness(
            behaviour_color
        )
        text_color = "black" if color_brightness > 0.5 else "white"
        return color_code, text_color

    def create_color_button(self, behaviour, color_code, text_color, row_layout, parent) -> None:
        color_button = QPushButton(behaviour, parent)
        color_button.clicked.connect(
            lambda _checked=False, b=behaviour: self.app.graph_settings_container_instance.choose_color(
                b, color_button
            )
        )
        color_button.setStyleSheet(f"background: {color_code}; color: {text_color};")
        row_layout.addWidget(color_button)
        self.app.color_buttons[behaviour] = color_button

    def create_checkbox(self, behaviour, row_layout, parent) -> None:
        behaviour_option_checkbox = CheckBoxControl(
            "",
            self.app.behaviour_display_status[behaviour],
            parent,
        )
        behaviour_option_checkbox.clicked.connect(
            self.app.behaviour_settings_controller.refresh_behaviour_options
        )
        row_layout.addWidget(behaviour_option_checkbox)
        self.app.behaviour_checkboxes[behaviour] = behaviour_option_checkbox

    def update_box_colors_and_behaviour_options(self, behaviour, color_rgb) -> None:
        if behaviour in self.app.behaviour_boxes:
            for box in self.app.behaviour_boxes[behaviour]:
                box.set_facecolor(color_rgb)

            self.app.figure_canvas.draw_idle()

            color_hex = "#%02x%02x%02x" % (
                int(color_rgb[0] * 255),
                int(color_rgb[1] * 255),
                int(color_rgb[2] * 255),
            )
            button_to_update = self.app.color_buttons.get(behaviour)
            self.app.behaviour_colors[behaviour] = color_rgb

            if button_to_update:
                button_to_update.setStyleSheet(f"background: {color_hex};")
                behaviour_color = self.app.behaviour_colors[behaviour]
                color_brightness = self.app.graph_settings_container_instance.brightness(
                    behaviour_color
                )
                text_color = "black" if color_brightness > 0.5 else "white"
                button_to_update.setStyleSheet(
                    f"background: {color_hex}; color: {text_color};"
                )

        self.app.settings_manager.update_behaviour_colors(self.app.behaviour_colors)
