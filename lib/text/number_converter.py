"""
Number Converter Module
Handles conversion of numbers to words for TTS.
"""

from typing import Optional
from num2words import num2words


def roman2number(text: str) -> int | None:
    """
    Convert Roman numerals to integer.

    Args:
        text: Roman numeral string (e.g., 'XIV', 'MCMXC')

    Returns:
        int | None: Integer value or None if invalid
    """
    roman_values = {
        'I': 1, 'V': 5, 'X': 10, 'L': 50,
        'C': 100, 'D': 500, 'M': 1000
    }

    try:
        text = text.upper()
        total = 0
        prev_value = 0

        for char in reversed(text):
            value = roman_values.get(char)
            if value is None:
                return None

            if value < prev_value:
                total -= value
            else:
                total += value

            prev_value = value

        return total
    except Exception:
        return None


def number_to_words(
    number: int | float,
    lang_iso1: str,
    ordinal: bool = False
) -> Optional[str]:
    """
    Convert a number to words using num2words.

    Args:
        number: Number to convert
        lang_iso1: ISO 639-1 language code
        ordinal: If True, convert to ordinal (1st, 2nd, etc.)

    Returns:
        str | None: Number in words, or None if conversion fails
    """
    try:
        # Special case for Chinese
        lang_code = lang_iso1.replace('zh', 'zh_CN')

        if ordinal:
            try:
                return num2words(number, lang=lang_code, to='ordinal')
            except:
                # Fallback to cardinal if ordinal not supported
                return num2words(number, lang=lang_code)
        else:
            return num2words(number, lang=lang_code)

    except Exception as e:
        print(f"Warning: Failed to convert number {number} to words: {e}")
        return None
