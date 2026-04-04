# gui/tk_dashboard.py
import tkinter as tk
from tkinter import messagebox
from src.gui.shared.base_dashboard import BaseDashboard
from src.gui.shared.window_manager import center_window_on_screen
from src.gui.shared.state_manager import load_state, save_state
from src.main_apps.raw_photometry_processing_app import RawPhotometryProcessingApp
from src.main_apps.align_photometry_behaviour import DataProcessingSingleInstance
from src.main_apps.align_telemetry_photom_opto import TelemetryPhotomOptoProcessingApp


class TkDashboard(tk.Tk, BaseDashboard):
    def __init__(self) -> None:
        super().__init__()
        self.sidebar_expanded = True
        self.content = None
        self.sidebar = None
        self.toggle_btn = None

        # Set up the window and sidebar
        self.setup_window()
        self.setup_sidebar()
        self.hide_sidebar()

        # Load the last used app or a default one
        self.load_initial_app()

    def setup_window(self) -> None:
        """
        Configure the main window: title, size, and main content frame.
        """
        self.title("NeuroSyncApp")
        self.geometry("1390x780")
        self.resizable(False, False)

        # Create a content frame where sub-applications will be loaded
        self.content = tk.Frame(self, bg="#EEEEEE", width=700, height=500)
        self.content.pack_propagate(False)
        self.content.place(relx=0, rely=0, relwidth=1, relheight=1)

        # Optionally center the window on the screen using a helper function
        center_window_on_screen(self)

    def setup_sidebar(self) -> None:
        """
        Create and configure the sidebar with a toggle button and navigation buttons.
        """
        # Sidebar frame
        self.sidebar = tk.Frame(
            self, width=200, bg="#111111", height=500, relief="sunken", borderwidth=2
        )
        self.sidebar.pack_propagate(False)
        self.sidebar.place(relx=0, rely=0, relwidth=0.15, relheight=1)

        # Toggle button to show/hide the sidebar
        self.toggle_btn = tk.Button(
            self,
            text="≡",
            command=self.toggle_sidebar,
            bg="#333333",
            fg="#FFFFFF",
            font=("Arial", 14),
            relief="raised",
            borderwidth=2,
            padx=5,
            pady=2,
        )
        self.toggle_btn.configure(text="\u2630")
        self.toggle_btn.place(x=5, y=0, anchor="nw")

        # Define the functionalities with their corresponding methods
        functionalities = [
            ("Analyse Raw Data", self.show_raw_analysis),
            ("Align Photometry and Behaviour", self.show_single_animal_analysis),
            ("Align Telemetry Data", self.show_telemetry_photom_opto),
            ("Combine Data", self.show_combine_data),
        ]

        # Create a button for each functionality
        for name, command in functionalities:
            btn = tk.Button(
                self.sidebar,
                text=name,
                command=command,
                relief="flat",
                bg="#333333",
                fg="#FFFFFF",
                wraplength=150,
                font=("Arial", 10),
            )
            btn.pack(fill="x", padx=10, pady=5)

    def load_app(self, app_name: str, app_class: type) -> None:
        """
        Clear the current content and load a new module.

        Parameters:
            app_name (str): Identifier for the module to save as the current state.
            app_class (type): The class to instantiate for the module.
        """
        # Clear current content
        for widget in self.content.winfo_children():
            widget.destroy()

        # Save the current state
        save_state(app_name)
        self.hide_sidebar()

        try:
            # Instantiate and pack the new sub-application
            frame = app_class(self.content)
            frame.pack(fill="both", expand=True)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load {app_name}: {e}")

    def run(self) -> None:
        """
        Start the application's main event loop.
        """
        self.mainloop()

    def toggle_sidebar(self) -> None:
        """
        Toggle the visibility of the sidebar.
        """
        self.sidebar_expanded = not self.sidebar_expanded
        if self.sidebar_expanded:
            self.sidebar.place(relx=0, rely=0, relwidth=0.15, relheight=1)
        else:
            # Hide the sidebar
            self.sidebar.place_forget()
        # Ensure the toggle button remains on top
        self.toggle_btn.lift()

    def hide_sidebar(self) -> None:
        """Hide the sidebar."""
        self.sidebar.place(relwidth=0)
        self.sidebar_expanded = False

    def load_initial_app(self) -> None:
        """
        Load the last used sub-application (if any) or default to a preset module.
        """
        last_app = load_state()
        if last_app:
            if last_app == "raw_analysis":
                self.show_raw_analysis()
            elif last_app == "single_animal":
                self.show_single_animal_analysis()
            elif last_app == "telemetry_photom_opto":
                self.show_telemetry_photom_opto()
            elif last_app == "combine_data":
                self.show_combine_data()
            else:
                self.show_single_animal_analysis()
        else:
            self.show_single_animal_analysis()

    # The following methods are responsible for switching between different sub-applications.
    def show_raw_analysis(self) -> None:
        self.load_app("raw_analysis", RawPhotometryProcessingApp)

    def show_single_animal_analysis(self) -> None:
        self.load_app("single_animal", DataProcessingSingleInstance)

    def show_telemetry_photom_opto(self) -> None:
        self.load_app("telemetry_photom_opto", TelemetryPhotomOptoProcessingApp)

    def show_combine_data(self) -> None:
        """
        Placeholder for a module to combine data.
        """
        # For now, display a simple placeholder message
        for widget in self.content.winfo_children():
            widget.destroy()
        placeholder = tk.Label(
            self.content, text="Combine Data Module Coming Soon!", font=("Arial", 16)
        )
        placeholder.pack(expand=True)


if __name__ == "__main__":
    app = TkDashboard()
    app.run()
