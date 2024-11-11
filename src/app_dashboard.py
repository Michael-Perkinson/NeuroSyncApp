import pickle
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
from align_photometry_behaviour import DataProcessingSingleInstance
from align_telemetry_opto_photom import MenopauseDataProcessingApp
from window_utils import center_window_on_screen


class AppDashboard(tk.Tk):
    def __init__(self):
        """Initialize the main window of the application."""
        super().__init__()

        self.title("Data Analysis and Processing App")
        self.geometry("1380x780")
        self.sidebar_expanded = True
        self.content = tk.Frame(self, bg='#EEEEEE', width=700, height=500)
        self.content.pack_propagate(0)
        self.content.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.sidebar = tk.Frame(
            self, width=200, bg='#111111', height=500, relief='sunken', borderwidth=2)
        self.sidebar.pack_propagate(0)
        self.sidebar.place(relx=0, rely=0, relwidth=0.15,
                           relheight=1)

        self.toggle_btn = tk.Button(self, text="≡", command=self.toggle_sidebar, bg='#333333', fg='#FFFFFF',
                                    font=("Arial", 14), relief='raised', borderwidth=2, padx=5, pady=2)
        self.toggle_btn.place(x=5, y=0, anchor='nw')

        functionalities = [
            ("Align Photometry and Behaviour",
             self.show_single_animal_analysis_app),
            ("Combine Data from Multiple Mice", self.show_combine_data),
            ("Menopause App", self.show_menopause_app)
        ]

        for name, func in functionalities:
            btn = tk.Button(self.sidebar, text=name, command=func,
                            relief='flat', bg='#333333', fg='#FFFFFF')
            btn.pack(fill='x', padx=10, pady=5)

        self.center_window()

        last_app = self.load_state()
        if last_app:
            if last_app == "single_animal":
                self.show_single_animal_analysis_app()
            elif last_app == "menopause_app":
                self.show_menopause_app()
            elif last_app == "combine_data":
                self.show_combine_data()
        else:
            self.show_single_animal_analysis_app()

    def save_state(self, app_name):
        """
        Save the current state of the application.
        
        Parameters:
        - app_name (str): The name of the application that is currently running.
        """
        with open("app_state.pkl", "wb") as f:
            pickle.dump(app_name, f)

    def load_state(self):
        """
        Load the last state of the application.
        
        Returns:
        - app_name (str): The name of the last application that was running.
            
        Raises:
        - FileNotFoundError: If the file does not exist.        
        """
        try:
            with open("app_state.pkl", "rb") as f:
                app_name = pickle.load(f)
                return app_name
        except FileNotFoundError:
            return None

    def center_window(self):
        """Center the window on the screen."""
        center_window_on_screen(self)

    def clear_content(self):
        """Clear the content frame of the application."""
        for widget in self.content.winfo_children():
            widget.destroy()

    def show_single_animal_analysis_app(self):
        """Show the single animal analysis app."""
        self.save_state("single_animal")
        self.clear_content()

        app_instance = DataProcessingSingleInstance(self.content)

        self.toggle_btn = tk.Button(self, text="≡", command=self.toggle_sidebar, bg="#333333", fg="#FFFFFF", font=("Arial", 14), relief="raised", borderwidth=2,
                                    padx=5, pady=2)
        self.toggle_btn.place(x=5, y=0, anchor='nw')
        self.hide_sidebar()

    def show_menopause_app(self):
        """Show the menopause app."""
        self.save_state("menopause_app")
        self.hide_sidebar()
        self.clear_content()
        menopause_frame = MenopauseDataProcessingApp(self.content)
        menopause_frame.pack(fill='both', expand=True)
        label = tk.Label(
            self.content, text="Menopause App Running", font=("Arial", 16))
        label.pack(pady=200)
        self.toggle_btn = tk.Button(self, text="≡", command=self.toggle_sidebar, bg="#333333", fg="#FFFFFF", font=("Arial", 14), relief="raised", borderwidth=2,
                                    padx=5, pady=2)
        self.toggle_btn.place(x=5, y=0, anchor='nw')

    def show_combine_data(self):
        """Show the combine data app."""
        self.save_state("combine_data")
        self.hide_sidebar()
        self.clear_content()
        label = tk.Label(
            self.content, text="Combine Data Running", font=("Arial", 16))
        label.pack(pady=200)
        self.toggle_btn = tk.Button(self, text="≡", command=self.toggle_sidebar, bg="#333333", fg="#FFFFFF", font=("Arial", 14), relief="raised", borderwidth=2,
                                    padx=5, pady=2)
        self.toggle_btn.place(x=5, y=0, anchor='nw')

    def toggle_sidebar(self):
        """Toggle the sidebar visibility."""
        if self.sidebar_expanded:
            self.sidebar.place(relwidth=0)
            self.toggle_btn.config(text="≡")
            self.sidebar_expanded = False
        else:
            self.sidebar.place(relwidth=0.15)
            self.sidebar.lift()
            self.toggle_btn.lift()
            self.toggle_btn.config(text="≡")
            self.sidebar_expanded = True

    def hide_sidebar(self):
        """Hide the sidebar."""
        self.sidebar.place(relwidth=0)
        self.toggle_btn.config(text="≡")
        self.sidebar_expanded = False
