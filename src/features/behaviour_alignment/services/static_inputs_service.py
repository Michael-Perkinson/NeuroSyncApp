"""Controller for static behaviour settings and visibility toggles."""

from __future__ import annotations

from src.data.json_handler import save_behaviour_static_inputs
from src.shared.persistence.app_paths import config_file_path


class BehaviourStaticInputsService:
    """Owns settings edits and checkbox-based behaviour visibility updates."""

    def __init__(self, app):
        self.app = app

    def save_inputs(self) -> None:
        pre_behaviour_time = self.app.static_inputs_frame.pre_behaviour_time_entry.get()
        post_behaviour_time = self.app.static_inputs_frame.post_behaviour_time_entry.get()
        bin_size = self.app.static_inputs_frame.bin_size_entry.get()
        selected_behaviour = self.app.static_inputs_frame.selected_behaviour.get()

        current_df = self.app.tables.get(self.app.current_table_key)
        if current_df is None:
            print("No current dataframe found.")
            return

        if selected_behaviour == "All Behaviours":
            self.update_behaviour_times(
                current_df, pre_behaviour_time, post_behaviour_time, bin_size
            )
        else:
            self.update_selected_behaviour_times(
                current_df,
                selected_behaviour,
                pre_behaviour_time,
                post_behaviour_time,
                bin_size,
            )

        self.app.tables[self.app.current_table_key] = current_df
        self.app.behaviour_table_panel.update_table(current_df, new=True)
        save_behaviour_static_inputs(current_df, config_file_path("behaviour_settings.json"))

    def update_behaviour_times(self, df, pre_time, post_time, bin_size) -> None:
        df["Pre Behaviour Time"] = pre_time
        df["Post Behaviour Time"] = post_time
        df["Bin Size"] = bin_size

    def update_selected_behaviour_times(
        self, df, behaviour, pre_time, post_time, bin_size
    ) -> None:
        mask = df["Behaviour Name"] == behaviour
        df.loc[mask, "Pre Behaviour Time"] = pre_time
        df.loc[mask, "Post Behaviour Time"] = post_time
        df.loc[mask, "Bin Size"] = bin_size

    def toggle_behaviour_start_time(self) -> None:
        if self.app.behaviour_event_input_frame.behaviour_type_var.get() == "Point":
            self.app.behaviour_event_input_frame.start_time_entry.config(state="normal")
            self.app.behaviour_event_input_frame.end_time_entry.config(state="disabled")
            self.app.behaviour_event_input_frame.end_time_var.set("")
        else:
            self.app.behaviour_event_input_frame.start_time_entry.config(state="normal")
            self.app.behaviour_event_input_frame.end_time_entry.config(state="normal")

    def toggle_behaviour_end_time(self) -> None:
        if self.app.behaviour_event_input_frame.behaviour_type_var.get() == "Continuous":
            self.app.behaviour_event_input_frame.start_time_entry.config(state="normal")
            self.app.behaviour_event_input_frame.end_time_entry.config(state="normal")
        else:
            self.app.behaviour_event_input_frame.start_time_entry.config(state="normal")
            self.app.behaviour_event_input_frame.end_time_entry.config(state="disabled")

    def select_all(self) -> None:
        for behaviour, checkbox in self.app.behaviour_checkboxes.items():
            checkbox.select()
            self.app.behaviour_display_status[behaviour].set(1)
        self.refresh_behaviour_options()

    def deselect_all(self) -> None:
        for behaviour, checkbox in self.app.behaviour_checkboxes.items():
            checkbox.deselect()
            self.app.behaviour_display_status[behaviour].set(0)
        self.refresh_behaviour_options()

    def refresh_behaviour_options(self) -> None:
        for behaviour in self.app.behaviour_boxes:
            visible = bool(self.app.behaviour_display_status[behaviour].get())
            for box in self.app.behaviour_boxes[behaviour]:
                box.set_visible(visible)

        self.app.figure_canvas.draw_idle()
