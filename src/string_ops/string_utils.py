

def normalize_deduplicate_and_order_strings(strings: list[str]) -> list[str]:
    """Normalize, deduplicate, and alphabetically order a list of strings."""
    allowed_special_chars = "-'"

    normalized_strings = [
        clean_string(string, allowed_special_chars)
        for string in strings
        if string.strip() and not all(char in allowed_special_chars for char in string)
    ]

    seen = set()
    unique_strings = []
    for string in normalized_strings:
        if string not in seen:
            seen.add(string)
            unique_strings.append(string)

    return sorted(unique_strings)


def clean_string(string: str, allowed_special_chars: str) -> str:
    """Strip disallowed characters from a string, then trim and capitalize it."""
    cleaned = "".join(
        char for char in string if char.isalnum() or char.isspace() or char in allowed_special_chars
    )
    return cleaned.strip().capitalize()
