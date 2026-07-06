"""Controller for telemetry file-loading and setup orchestration."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from pathlib import Path
import re

import pandas as pd
from PySide6.QtWidgets import QFileDialog

from src.gui.shared.qt_bindings import ObservableValue

logger = logging.getLogger(__name__)


def _date_name_variants(date: str | None) -> set[str]:
    match = re.fullmatch(r"(\d+)-(\d+)-(\d+)", str(date or "").strip())
    if match is None:
        return {str(date or "").strip()}

    year, month, day = match.groups()
    return {
        f"{year}-{int(month)}-{int(day)}",
        f"{year}-{int(month):02d}-{int(day):02d}",
    }


def _filename_matches_date(file_name: str, date: str | None) -> bool:
    file_name_lower = file_name.lower()
    for variant in _date_name_variants(date):
        if not variant:
            continue
        pattern = rf"(?<!\d){re.escape(variant.lower())}(?!\d)"
        if re.search(pattern, file_name_lower):
            return True
    return False


def _shift_date_name(date: str | None, days: int) -> str | None:
    match = re.fullmatch(r"(\d+)-(\d+)-(\d+)", str(date or "").strip())
    if match is None:
        return None

    year, month, day = match.groups()
    full_year = int(year) if len(year) == 4 else 2000 + int(year)
    shifted = datetime(full_year, int(month), int(day)) + timedelta(days=days)
    output_year = f"{shifted.year:04d}" if len(year) == 4 else shifted.strftime("%y")
    return f"{output_year}-{shifted.month}-{shifted.day}"


def _matching_files_for_date(file_names: list[str], label: str, date: str | None) -> list[str]:
    exact_matches = [
        file_name
        for file_name in file_names
        if label in file_name.lower() and _filename_matches_date(file_name, date)
    ]
    if exact_matches:
        return exact_matches

    previous_date = _shift_date_name(date, -1)
    if previous_date is None:
        return []

    return [
        file_name
        for file_name in file_names
        if label in file_name.lower()
        and _filename_matches_date(file_name, previous_date)
    ]


class TelemetryAssociatedFileLocator:
    """Owns telemetry-associated file selection and data-file setup flow."""

    def __init__(self, app):
        self.app = app

    def select_folder_for_telemetry_data(self, date):
        folder_path_str = QFileDialog.getExistingDirectory(
            self.app,
            f"Select folder for telemetry data of {date}",
        )

        if not folder_path_str:
            logger.info("Telemetry folder selection cancelled.")
            return None, None

        folder_path = Path(folder_path_str)
        self.app.settings_manager.telemetry_folder_path = str(folder_path)

        folder_files = [
            file.name
            for file in folder_path.iterdir()
            if file.is_file() and not file.name.startswith("._")
        ]
        temp_files = _matching_files_for_date(folder_files, "temp", date)
        act_files = _matching_files_for_date(folder_files, "act", date)

        temp_file_path = str(folder_path / temp_files[0]) if temp_files else None
        act_file_path = str(folder_path / act_files[0]) if act_files else None

        if not act_file_path or not temp_file_path:
            logger.warning(
                "Could not find associated Act or Temp files for date %s in %s.",
                date,
                folder_path,
            )

        if temp_file_path:
            self.app.associated_temp_data_entry.set(Path(temp_file_path).name)
        if act_file_path:
            self.app.associated_act_data_entry.set(Path(act_file_path).name)

        self.app.settings_manager.save_variables()
        return act_file_path, temp_file_path

    def handle_new_data_file(
        self,
        file_path_var,
        selected_column_var,
        column_dropdown,
        mouse_name,
        dataframe,
        is_time_based_data,
    ) -> None:
        if not hasattr(selected_column_var, "set") and hasattr(column_dropdown, "set"):
            selected_column_var, column_dropdown = column_dropdown, selected_column_var

        if not hasattr(file_path_var, "get"):
            normalized_file_path = ObservableValue(str(file_path_var))
            file_path_var = normalized_file_path

        self.common_setup(file_path_var, dataframe, mouse_name)

        self.app.selected_column_var = selected_column_var
        self.app.column_dropdown = column_dropdown

        if is_time_based_data is not None and not is_time_based_data:
            self.app.data_type = "optogenetics"
            self.app.process_opto_data_file()
            return

        self.app.data_type = "photometry"
        self.process_photometry_data_file()

    def common_setup(self, file_path_var, dataframe, mouse_name) -> None:
        self.app.file_path = file_path_var
        self.app.file_path_var.set(file_path_var.get())
        self.app.view_state.file_path = file_path_var.get()
        self.app.dataframe = dataframe
        self.app.cluster_options_created = False
        self.app.cluster_table_panel.clear_table()
        self.app.table_treeview.delete(*self.app.table_treeview.get_children())
        self.app.data_dict = {}
        self.app.seconds_removed = 0
        self.app.cluster_dict = {}
        self.app.mean_cluster_data = {}
        self.app.data_type = None
        self.app.start_time_timedelta = None

        date, mouse_number = self.extract_date_and_mouse_number(file_path_var, mouse_name)
        self.app.mouse_name = mouse_name
        self.app.date = date

        if not date or not mouse_number:
            logger.warning(
                "Could not extract date or mouse number from file name %s.",
                file_path_var.get(),
            )
            return

        self.app.act_file_path, self.app.temp_file_path = self.retrieve_associated_files(
            date, file_path_var
        )
        if not self.app.act_file_path or not self.app.temp_file_path:
            self.app.act_file_path, self.app.temp_file_path = (
                self.select_folder_for_telemetry_data(date)
            )

    def extract_date_and_mouse_number(self, file_path_var, mouse_name):
        main_file_name = Path(file_path_var.get()).name
        date_match = re.search(r"(\d+)-(\d+)-(\d+)", main_file_name)
        date = (
            f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
            if date_match
            else None
        )
        return date, mouse_name

    def retrieve_associated_files(self, date, file_path_var):
        main_file_directory = Path(file_path_var.get()).parent
        if not main_file_directory.exists():
            return None, None

        all_files = [
            file.name
            for file in main_file_directory.iterdir()
            if file.is_file() and not file.name.startswith("._")
        ]

        temp_files = _matching_files_for_date(all_files, "temp", date)
        act_files = _matching_files_for_date(all_files, "act", date)

        temp_file_path = (
            str(main_file_directory / temp_files[0]) if temp_files else None
        )
        act_file_path = str(main_file_directory / act_files[0]) if act_files else None

        telemetry_folder_path = self.app.settings_manager.telemetry_folder_path
        if (not temp_file_path or not act_file_path) and telemetry_folder_path:
            telemetry_directory = Path(telemetry_folder_path)
            if telemetry_directory.exists():
                if not temp_file_path:
                    telemetry_files = [
                        file.name
                        for file in telemetry_directory.iterdir()
                        if file.is_file() and not file.name.startswith("._")
                    ]
                    temp_files = _matching_files_for_date(
                        telemetry_files, "temp", date
                    )
                    temp_file_path = (
                        str(telemetry_directory / temp_files[0]) if temp_files else None
                    )
                if not act_file_path:
                    telemetry_files = [
                        file.name
                        for file in telemetry_directory.iterdir()
                        if file.is_file() and not file.name.startswith("._")
                    ]
                    act_files = _matching_files_for_date(
                        telemetry_files, "act", date
                    )
                    act_file_path = (
                        str(telemetry_directory / act_files[0]) if act_files else None
                    )

        self.app.associated_temp_data_entry.set(temp_files[0] if temp_files else "")
        self.app.associated_act_data_entry.set(act_files[0] if act_files else "")
        self.app.update_idletasks()
        return act_file_path, temp_file_path

    def process_photometry_data_file(self) -> None:
        self.app.update_column_headings()
        self.app.plot_service.precalculate_data_versions()

        (
            time_column,
            data_column,
            detected_peaks,
            clusters_final,
            grouped_clusters,
        ) = self.app.plot_service.get_current_photometry_data()

        self.app.time_column = time_column
        self.app.data_column = data_column
        self.app.detected_peaks = detected_peaks
        self.app.clusters_final = clusters_final
        self.app.grouped_clusters = grouped_clusters
        self.app.duration_main_data = time_column.iloc[-1] - time_column.iloc[0]

        self.app.plot_service.visualize_photometry_data_with_overlays(
            time_column, data_column, detected_peaks, clusters_final, self.app.graph_canvas
        )

        self.app.static_settings_store.populate_data_dict()
        self.app.cluster_table_panel.populate_table()
        self.app.populate_static_input_dropdown()
        self.app.display_dropdown.configure(state="disabled")
        self.app.selected_display.set("Full Trace Display")

    def handle_opto_data_file(self) -> None:
        self.app.stim_timings = None
        file_path = Path(self.app.file_path.get())
        file_extension = file_path.suffix.lower()

        if file_extension == ".csv":
            stim_data_df = pd.read_csv(file_path)
        elif file_extension in [".xls", ".xlsx"]:
            stim_data_df = pd.read_excel(file_path)
        else:
            raise ValueError(f"Unsupported file extension: {file_extension}")

        if hasattr(self.app.label_settings_button, "hide"):
            self.app.label_settings_button.hide()
        elif hasattr(self.app.label_settings_button, "grid_remove"):
            self.app.label_settings_button.grid_remove()

        stim_data_df["Stim onset (hh:mm:ss)"] = stim_data_df["Stim onset (hh:mm:ss)"].apply(
            lambda value: pd.to_timedelta(
                datetime.strptime(value, "%I:%M:%S %p").strftime("%H:%M:%S")
            )
            if "am" in value.lower() or "pm" in value.lower()
            else pd.to_timedelta(datetime.strptime(value, "%H:%M:%S").strftime("%H:%M:%S"))
        )
        stim_data_df["Start time (hh:mm:ss)"] = stim_data_df["Start time (hh:mm:ss)"].apply(
            lambda value: pd.to_timedelta(
                datetime.strptime(value, "%I:%M:%S %p").strftime("%H:%M:%S")
            )
            if pd.notna(value) and ("am" in value.lower() or "pm" in value.lower())
            else pd.to_timedelta(
                datetime.strptime(value, "%H:%M:%S").strftime("%H:%M:%S")
            )
            if pd.notna(value)
            else pd.NaT
        )

        self.app.data_selection_frame.selected_column_var.set("Not used")
        self.app.data_selection_frame.column_dropdown["state"] = "disabled"

        start_time_timedelta = stim_data_df["Start time (hh:mm:ss)"].iloc[0]
        self.app.start_time_timedelta = str(start_time_timedelta).split(" days ")[-1]
        self.app.duration_main_data = stim_data_df["Duration of test (min)"].iloc[0]
        self.app.temp_and_act_start_time_var.set(self.app.start_time_timedelta)
        self.app.stim_timings = self.app.plot_service.calculate_stim_timings(
            stim_data_df
        )

        expected_length = int(stim_data_df["Duration of test (min)"].iloc[0])
        self.app.duration_main_data = expected_length

        self.app.plot_service.overlay_temp_and_act()
