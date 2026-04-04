from screeninfo import get_monitors
import tkinter as tk
from typing import Optional


def center_window_on_screen(window: tk.Tk) -> None:
    """
    Center a Tkinter window on the screen where the cursor is located.

    Parameters:
    - window (tk.Tk | tk.Toplevel): The window to center.
    """
    window.update_idletasks()  # Ensure window dimensions are updated

    x, y = window.winfo_pointerxy()  # Get cursor coordinates
    screen_number = find_screen_by_coordinates(x, y)

    # Get the corresponding screen or default to the first screen
    screens = get_monitors()
    screen = screens[screen_number] if screen_number is not None else screens[0]

    # Calculate center position
    window_width = window.winfo_width()
    window_height = window.winfo_height()
    x_position = screen.x + (screen.width - window_width) // 2
    y_position = screen.y + (screen.height - window_height) // 2

    # Set window position
    window.geometry(f"+{x_position}+{y_position}")


def find_screen_by_coordinates(x: int, y: int) -> Optional[int]:
    """
    Find the screen index that contains the given coordinates.

    Parameters:
    - x (int): The x-coordinate.
    - y (int): The y-coordinate.

    Returns:
    - Optional[int]: The screen index that contains the given coordinates, or 0 if none found.
    """
    screens = get_monitors()
    for screen_number, screen in enumerate(screens):
        if screen.x <= x < screen.x + screen.width and screen.y <= y < screen.y + screen.height:
            return screen_number
    return None  # Return None explicitly if no screen contains the coordinates


def centered_input_dialog(parent: tk.Tk, title: str, prompt: str) -> Optional[str]:
    """
    Display a centered input dialog.

    Parameters:
    - parent (tk.Tk | tk.Toplevel): The parent window.
    - title (str): The title of the dialog.
    - prompt (str): The prompt for the input.

    Returns:
    - Optional[str]: The input from the user, or None if the dialog is closed without input.
    """
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.geometry('300x100')
    center_window_on_screen(dialog)

    # Add prompt label
    label = tk.Label(dialog, text=prompt)
    label.pack(pady=10)

    # Add entry field
    entry = tk.Entry(dialog)
    entry.pack(pady=10, padx=10)

    result: Optional[str] = None

    def on_submit() -> None:
        """Callback for the submit button."""
        nonlocal result
        result = entry.get()
        dialog.destroy()

    # Add submit button
    submit_button = tk.Button(dialog, text="Submit", command=on_submit)
    submit_button.pack(pady=5)

    dialog.wait_window()  # Wait for the dialog to close
    return result
