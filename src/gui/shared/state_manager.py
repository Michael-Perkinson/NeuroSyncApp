import os
import json
import sys
from typing import Optional


def get_state_file_path() -> str:
    """
    Get the path to the app state file stored in a hidden `.neurosync` folder.

    Creates the folder if it doesn't exist and ensures it is hidden on Windows.

    Returns:
    - str: The full path to the `app_state.json` file inside the hidden folder.
    """
    if getattr(sys, "frozen", False):  # Check if running as a frozen executable
        base_path = sys._MEIPASS  # For PyInstaller
    else:
        base_path = os.path.dirname(os.path.abspath(
            __file__))  # For normal Python script

    # Define the hidden folder
    hidden_folder = os.path.join(base_path, ".neurosync")

    # Create the hidden folder if it doesn't exist
    if not os.path.exists(hidden_folder):
        os.makedirs(hidden_folder)

        # Make the folder hidden on Windows
        if os.name == "nt":  # Check if running on Windows
            import ctypes
            ctypes.windll.kernel32.SetFileAttributesW(
                hidden_folder, 0x02)  # 0x02 is the hidden attribute

    # Return the path to the app state file inside the hidden folder
    return os.path.join(hidden_folder, "app_state.json")


def save_state(app_name: str) -> None:
    """
    Save the current state of the application in a JSON file.

    Parameters:
    - app_name (str): The name of the application state to save.
    """
    file_path = get_state_file_path()
    try:
        with open(file_path, "w") as f:
            json.dump({"last_app": app_name}, f)
    except IOError as e:
        print(f"Error saving state: {e}")


def load_state() -> Optional[str]:
    """
    Load the last saved application state from a JSON file.

    Returns:
    - Optional[str]: The name of the last application state, or None if the file doesn't exist or is invalid.
    """
    file_path = get_state_file_path()
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                state = json.load(f)
                return state.get("last_app")
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading state: {e}")
            return None
    return None
