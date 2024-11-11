from screeninfo import get_monitors
import tkinter as tk


def center_window_on_screen(window):
    """
    Center a Tkinter window on the screen.

    Parameters:
    - window (tk.Tk|tk.Toplevel): The window to center.
    """
    window.update_idletasks()  # Update "idle" tasks to get updated dimensions

    x, y = window.winfo_pointerxy()
    screen_number = find_screen_by_coordinates(x, y, window)
    screen = get_monitors()[screen_number] if screen_number is not None else get_monitors()[
        0]

    screen_width = screen.width
    screen_height = screen.height

    window_width = window.winfo_width()
    window_height = window.winfo_height()

    x = screen.x + (screen_width - window_width) // 2
    y = screen.y + (screen_height - window_height) // 2

    window.geometry(f"+{x}+{y}")

def find_screen_by_coordinates(x, y, window):
    """
    Find the screen number that contains the given coordinates.

    Parameters:
    - x (int): The x-coordinate.
    - y (int): The y-coordinate.
    - window (tk.Tk|tk.Toplevel): The window to center.

    Returns:
    - screen_number (int): The screen number that contains the given coordinates.
    """
    screens = get_monitors()
    for screen_number, screen in enumerate(screens):
        if screen.x <= x < screen.x + screen.width and screen.y <= y < screen.y + screen.height:
            return screen_number
    return 0


def centered_input_dialog(parent, title, prompt):
    """
    Display a centered input dialog.

    Parameters:
    - parent (tk.Tk|tk.Toplevel): The parent window.
    - title (str): The title of the dialog.
    - prompt (str): The prompt for the input.

    Returns:
    - result (str): The input from the user.
    """
    # Create a Toplevel window
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.geometry('300x100')  # Adjust as needed

    # Center the window
    center_window_on_screen(dialog)

    # Add label and entry
    label = tk.Label(dialog, text=prompt)
    label.pack(pady=10)

    entry = tk.Entry(dialog)
    entry.pack(pady=10, padx=10)

    result = None
    
    def on_submit():
        """Callback for the submit button."""
        nonlocal result
        result = entry.get()
        dialog.destroy()

    submit_button = tk.Button(dialog, text="Submit", command=on_submit)
    submit_button.pack(pady=5)

    dialog.wait_window()
    return result
