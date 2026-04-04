from typing import Callable


def validate_baseline_state(
    checkbox_state: bool,
    baseline_button_pressed: bool,
    error_callback: Callable[[str, str], None]
) -> bool:
    """
    Validate the baseline state based on the checkbox and button states.

    Parameters:
    - checkbox_state (bool): The state of the checkbox (True if checked, False otherwise).
    - baseline_button_pressed (bool): Whether the baseline button has been pressed.
    - error_callback (Callable[[str, str], None]): A callback function to display an error message.
      It takes two arguments: a title (str) and a message (str).

    Returns:
    - bool: True if the baseline state is valid, False otherwise.
    """
    if checkbox_state and not baseline_button_pressed:
        error_callback("Error", "Please remember to save the baseline values.")
        return False
    return True
