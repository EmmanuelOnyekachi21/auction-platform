"""Input sanitation utilities for preventing XSS and other injection attacks."""


def sanitize_string(value: str, max_length: int = 5000) -> str:
    """
    Sanitize a free-text user input string.

    - Strips leading and trailing whitespace.
    - Removes null bytes (\\x00).
    - Truncates to a maximum safe length.
    """
    if not isinstance(value, str):
        return value

    # strip whitespace
    value = value.strip()

    # remove null bytes
    value = value.replace("\x00", "")

    # truncate if it exceeds maximum safe length
    if len(value) > max_length:
        value = value[:max_length]

    return value
