"""
System Utilities Module
Provides general utility functions for system operations.
"""

import regex as re


def get_sanitized(text: str, replacement: str = "_") -> str:
    """
    Sanitize a string for use in file paths and names.

    Removes or replaces forbidden characters, multiple spaces, and
    invalid filename characters.

    Args:
        text: The string to sanitize
        replacement: Character to use for replacing forbidden characters (default: "_")

    Returns:
        str: Sanitized string safe for use in file paths
    """
    # Replace ampersands with 'And'
    text = text.replace('&', 'And')

    # Define forbidden characters for filenames
    # Includes: < > : " / \ | ? * and control characters (0x00-0x1F)
    forbidden_chars = r'[<>:"/\\|?*\x00-\x1F ()]'

    # Replace multiple spaces with the replacement character
    sanitized = re.sub(r'\s+', replacement, text)

    # Replace forbidden characters with the replacement character
    sanitized = re.sub(forbidden_chars, replacement, sanitized)

    # Remove leading/trailing underscores
    sanitized = sanitized.strip("_")

    return sanitized
