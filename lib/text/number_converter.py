"""
Number Converter Module
Handles conversion of numbers to words for TTS.
"""

import math
import regex as re
import unicodedata
from typing import Optional
from num2words import num2words

from lib.lang import language_math_phonemes, default_language_code


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


def set_formatted_number(
    text: str,
    lang: str,
    lang_iso1: str,
    is_num2words_compat: bool,
    max_single_value: int = 999_999_999_999_999_999
) -> str:
    """
    Convert numbers in text to words, handling ranges and special cases.

    Processes numbers with advanced features:
    - Comma-separated numbers (1,234,567)
    - Decimal numbers (3.14159)
    - Number ranges with dashes (1-10, 5–8)
    - Very large numbers up to 18 digits
    - Special values (inf, infinity, nan)
    - Trailing punctuation preservation

    Args:
        text: Input text containing numbers
        lang: Language code (e.g., 'eng', 'fra')
        lang_iso1: ISO 639-1 language code (e.g., 'en', 'fr')
        is_num2words_compat: Whether num2words supports this language
        max_single_value: Maximum value to convert (default: 999 quadrillion)

    Returns:
        str: Text with numbers converted to words

    Example:
        >>> set_formatted_number("I have 1,234 apples", "eng", "en", True)
        "I have one thousand two hundred thirty-four apples"
        >>> set_formatted_number("Pages 10-20", "eng", "en", True)
        "Pages ten-twenty"

    Notes:
        - Uses num2words when available for better language support
        - Falls back to phoneme mapping for unsupported languages
        - Preserves original text for invalid/overflow numbers
    """
    # Match up to 18 digits, optional ",…" groups (allowing spaces or NBSP after comma),
    # optional decimal of up to 12 digits. Handle optional range with dash/en dash/em dash
    # between numbers, and allow trailing punctuation
    number_re = re.compile(
        r'(?<!\w)'
        r'(\d{1,18}(?:,\s*\d{1,18})*(?:\.\d{1,12})?)'      # first number
        r'(?:\s*([-–—])\s*'                                # dash type
        r'(\d{1,18}(?:,\s*\d{1,18})*(?:\.\d{1,12})?))?'    # optional second number
        r'([^\w\s]*)',                                     # optional trailing punctuation
        re.UNICODE
    )

    def normalize_commas(num_str: str) -> str:
        """Normalize number string to standard comma format: 1,234,567"""
        tok = num_str.replace('\u00A0', '').replace(' ', '')
        if '.' in tok:
            integer_part, decimal_part = tok.split('.', 1)
            integer_part = integer_part.replace(',', '')
            integer_part = "{:,}".format(int(integer_part))
            return f"{integer_part}.{decimal_part}"
        else:
            integer_part = tok.replace(',', '')
            return "{:,}".format(int(integer_part))

    def clean_single_num(num_str):
        """Convert a single number string to words."""
        tok = unicodedata.normalize('NFKC', num_str)
        if tok.lower() in ('inf', 'infinity', 'nan'):
            return tok
        clean = tok.replace(',', '').replace('\u00A0', '').replace(' ', '')
        try:
            num = float(clean) if '.' in clean else int(clean)
        except (ValueError, OverflowError):
            return tok
        if not math.isfinite(num) or abs(num) > max_single_value:
            return tok

        # Normalize commas before final output
        tok = normalize_commas(tok)

        if is_num2words_compat:
            new_lang_iso1 = lang_iso1.replace('zh', 'zh_CN')
            return num2words(num, lang=new_lang_iso1)
        else:
            phoneme_map = language_math_phonemes.get(
                lang,
                language_math_phonemes.get(default_language_code, language_math_phonemes['eng'])
            )
            return ' '.join(phoneme_map.get(ch, ch) for ch in str(num))

    def clean_match(match):
        """Process a regex match of number(s) with optional range."""
        first_num = clean_single_num(match.group(1))
        dash_char = match.group(2) or ''
        second_num = clean_single_num(match.group(3)) if match.group(3) else ''
        trailing = match.group(4) or ''
        if second_num:
            return f"{first_num}{dash_char}{second_num}{trailing}"
        else:
            return f"{first_num}{trailing}"

    return number_re.sub(clean_match, text)
