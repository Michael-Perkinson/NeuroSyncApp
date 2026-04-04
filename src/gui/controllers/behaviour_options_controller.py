"""Controller for behaviour option widgets (colors + visibility checkboxes)."""

from __future__ import annotations

import tkinter as tk


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
            self.app.behaviour_frame.destroy()

    def create_control_buttons(self) -> None:
        select_all_button = tk.Button(
            self.app.graph_settings_container_instance.behaviour_frame,
            text="Select All",
            command=self.app.behaviour_settings_controller.select_all,
        )
        select_all_button.grid(row=0, column=1, padx=10, pady=(5, 2), sticky=tk.W)

        deselect_all_button = tk.Button(
            self.app.graph_settings_container_instance.behaviour_frame,
            text="Deselect All",
            command=self.app.behaviour_settings_controller.deselect_all,
        )
        deselect_all_button.grid(row=0, column=2, padx=10, pady=(5, 2), sticky=tk.W)

    def create_behaviour_labels_and_controls(self, sorted_behaviours) -> None:
        behaviour_list_label = tk.Label(
            self.app.graph_settings_container_instance.behaviour_frame,
            text="Behaviours",
            bg="snow",
            font=("Helvetica", 12, "bold"),
        )
        behaviour_list_label.grid(row=0, column=0, padx=10, pady=(5, 2), sticky=tk.W)

        self.app.color_buttons = {}
        for row_index, behaviour in enumerate(sorted_behaviours, start=1):
            self.create_behaviour_control(behaviour, row_index)

    def create_behaviour_control(self, behaviour, row_index) -> None:
        behaviour_color = self.app.behaviour_colors.get(behaviour)
        if behaviour_color is None:
            return

        color_code, text_color = self.get_color_code_and_text_color(behaviour_color)
        self.create_color_button(behaviour, color_code, text_color, row_index)
        self.create_checkbox(behaviour, row_index)

    def get_color_code_and_text_color(self, behaviour_color):
        r, g, b = [int(component * 255) for component in behaviour_color[:3]]
        color_code = "#%02x%02x%02x" % (r, g, b)
        color_brightness = self.app.graph_settings_container_instance.brightness(
            behaviour_color
        )
        text_color = "black" if color_brightness > 0.5 else "white"
        return color_code, text_color

    def create_color_button(self, behaviour, color_code, text_color, row_index) -> None:
        color_button = tk.Button(
            self.app.graph_settings_container_instance.behaviour_frame,
            text=behaviour,
            command=lambda b=behaviour: self.app.graph_settings_container_instance.choose_color(
                b, color_button
            ),
        )
        color_button.grid(row=row_index, column=0, padx=10, pady=(5, 2), sticky=tk.W)
        color_button.config(fg=text_color, bg=color_code)
        self.app.color_buttons[behaviour] = color_button

    def create_checkbox(self, behaviour, row_index) -> None:
        behaviour_option_checkbox = tk.Checkbutton(
            self.app.graph_settings_container_instance.behaviour_frame,
            variable=self.app.behaviour_display_status[behaviour],
            command=self.app.behaviour_settings_controller.refresh_behaviour_options,
            bg="snow",
        )
        behaviour_option_checkbox.grid(
            row=row_index, column=1, padx=10, pady=(5, 2), sticky=tk.W
        )
        behaviour_option_checkbox.config(font=("Helvetica", 8))
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
                button_to_update.config(bg=color_hex)
                behaviour_color = self.app.behaviour_colors[behaviour]
                color_brightness = self.app.graph_settings_container_instance.brightness(
                    behaviour_color
                )
                text_color = "black" if color_brightness > 0.5 else "white"
                button_to_update.config(fg=text_color)

        self.app.settings_manager.update_behaviour_colors(self.app.behaviour_colors)
