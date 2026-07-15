"""Controller for behaviour-file selection and parsing entrypoint."""

from __future__ import annotations

from src.features.behaviour_alignment.services.reset_helpers import (
    clear_common_selections,
    clear_photometry_app_specific_selections,
)
from src.gui.shared.file_dialogs import select_csv_file
from src.gui.shared.messages_and_errors import show_action_error, show_error
from src.gui.shared.validation_checks import validate_baseline_state


class BehaviourFileSelector:
    """Owns behaviour file selection + parse dispatch."""

    def __init__(self, app):
        self.app = app

    def handle_behaviour_file_selection(self) -> None:
        if not validate_baseline_state(
            self.app.checkbox_state,
            self.app.data_selection_frame.baseline_button_pressed,
            lambda title, message: show_error(title, message, self.app),
        ):
            return

        if self.app.is_file_parsed:
            clear_common_selections(self.app)
            clear_photometry_app_specific_selections(self.app)

        file_path = select_csv_file(self.app)
        if file_path:
            self.process_file(file_path)

    def process_file(self, file_path) -> None:
        try:
            parsed = self.app.manual_session_service.parse_manual_data(file_path)
            self.app.is_file_parsed = parsed is True
        except Exception as error:
            show_action_error(
                "Behaviour import failed",
                "NeuroSyncApp could not finish importing the behaviour file",
                error,
                self.app,
                "Check the selected file and configured column names, then try again.",
            )
            self.app.is_file_parsed = False
