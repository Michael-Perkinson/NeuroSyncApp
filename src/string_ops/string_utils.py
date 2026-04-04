from typing import List


def normalize_deduplicate_and_order_strings(strings: List[str]) -> List[str]:
    """
    Normalize, deduplicate, and alphabetically order a list of strings.

    Parameters:
    - strings (List[str]): List of strings to process.

    Returns:
    - List[str]: A deduplicated and alphabetically sorted list of normalized strings.
    """
    # Define allowed characters (alphanumeric + spaces + optional special chars)
    allowed_special_chars = "-'"

    # Normalize strings using the helper function
    normalized_strings = [
        clean_string(string, allowed_special_chars)
        for string in strings
        if string.strip() and not all(char in allowed_special_chars for char in string)
    ]

    # Deduplicate while preserving order
    seen = set()
    unique_strings = []
    for string in normalized_strings:
        if string not in seen:
            seen.add(string)
            unique_strings.append(string)

    # Alphabetically sort the unique strings
    return sorted(unique_strings)


def clean_string(string: str, allowed_special_chars: str) -> str:
    """
    Clean a string by removing unwanted characters, stripping whitespace, and capitalizing.

    Parameters:
    - string (str): The string to clean.
    - allowed_special_chars (str): A string of additional allowed special characters.

    Returns:
    - str: The cleaned, stripped, and capitalized string.
    """
    # Keep only allowed characters
    cleaned = "".join(
        char for char in string if char.isalnum() or char.isspace() or char in allowed_special_chars
    )
    # Normalize spacing and capitalize
    return cleaned.strip().capitalize()
