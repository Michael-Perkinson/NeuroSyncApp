from abc import ABC, abstractmethod


class BaseDashboard(ABC):
    @abstractmethod
    def setup_window(self) -> None:
        """
        Set up main window properties such as title, size, etc.
        """
        pass

    @abstractmethod
    def setup_sidebar(self) -> None:
        """
        Create and configure the sidebar with navigation or functional buttons.
        """
        pass

    @abstractmethod
    def load_app(self, app_name: str, app_class: type) -> None:
        """
        Dynamically load and display a module or sub-application.

        Parameters:
            app_name (str): A string identifier for the module.
            app_class (type): The class to instantiate for this module.
        """
        pass

    @abstractmethod
    def run(self) -> None:
        """
        Start the main event loop of the application.
        """
        pass
