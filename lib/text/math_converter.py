"""
Math Converter Module
Handles conversion of mathematical symbols and expressions to words for TTS.
"""

import regex as re
from typing import Optional
from num2words import num2words

from lib.lang import language_math_phonemes, default_language_code


def math2words(text: str, lang: str, lang_iso1: str, tts_engine: str, is_num2words_compat: bool) -> str:
    """
    Convert mathematical symbols and expressions to words.

    Handles:
    - Mathematical operators (+, -, *, /, =, etc.)
    - Ordinal numbers (1st, 2nd, 3rd, etc.)
    - Ambiguous symbols in equation context (-, /, *, x)
    - Numbers via set_formatted_number

    Args:
        text: Input text containing mathematical expressions
        lang: Language code (e.g., 'eng', 'fra')
        lang_iso1: ISO 639-1 language code (e.g., 'en', 'fr')
        tts_engine: TTS engine name
        is_num2words_compat: Whether num2words supports this language

    Returns:
        str: Text with mathematical expressions converted to words

    Example:
        >>> math2words("3 + 4 = 7", "eng", "en", "xtts", True)
        "three plus four equals seven"
        >>> math2words("1st place", "eng", "en", "xtts", True)
        "first place"
    """
    from lib.text.number_converter import set_formatted_number

    def repl_ambiguous(match):
        """Handle ambiguous symbols (-, /, *, x) in equation context."""
        # Handles "num SYMBOL num" and "SYMBOL num"
        if match.group(2) and match.group(2) in ambiguous_replacements:
            return f"{match.group(1)} {ambiguous_replacements[match.group(2)]} {match.group(3)}"
        if match.group(3) and match.group(3) in ambiguous_replacements:
            return f"{ambiguous_replacements[match.group(3)]} {match.group(4)}"
        return match.group(0)

    def _ordinal_to_words(m):
        """Convert ordinal numbers (1st, 2nd, etc.) to words."""
        n = int(m.group(1))
        if is_num2words_compat:
            try:
                return num2words(n, to="ordinal", lang=(lang_iso1 or "en"))
            except Exception:
                pass
        # If num2words isn't available/compatible, keep original token as-is
        return m.group(0)

    # Convert ordinals (1st, 2nd, 3rd, etc.)
    # Matches any digits + optional space/NBSP + st/nd/rd/th, not glued into words
    re_ordinal = re.compile(r'(?<!\w)(\d+)(?:\s|\u00A0)*(?:st|nd|rd|th)(?!\w)')

    # Clean up parentheses before numbers
    text = re.sub(r'(\d)\)', r'\1 : ', text)

    # Replace ordinals
    text = re_ordinal.sub(_ordinal_to_words, text)

    # Symbol phonemes
    ambiguous_symbols = {"-", "/", "*", "x"}
    phonemes_list = language_math_phonemes.get(lang, language_math_phonemes[default_language_code])
    replacements = {k: v for k, v in phonemes_list.items() if not k.isdigit() and k not in [',', '.']}

    normal_replacements = {k: v for k, v in replacements.items() if k not in ambiguous_symbols}
    ambiguous_replacements = {k: v for k, v in replacements.items() if k in ambiguous_symbols}

    # Replace unambiguous symbols everywhere
    if normal_replacements:
        sym_pat = r'(' + '|'.join(map(re.escape, normal_replacements.keys())) + r')'
        text = re.sub(sym_pat, lambda m: f" {normal_replacements[m.group(1)]} ", text)

    # Replace ambiguous symbols only in valid equation contexts
    if ambiguous_replacements:
        ambiguous_pattern = (
            r'(?<!\S)'                   # no non-space before
            r'(\d+)\s*([-/*x])\s*(\d+)'  # num SYMBOL num
            r'(?!\S)'                    # no non-space after
            r'|'                         # or
            r'(?<!\S)([-/*x])\s*(\d+)(?!\S)'  # SYMBOL num
        )
        text = re.sub(ambiguous_pattern, repl_ambiguous, text)

    # Convert remaining numbers
    text = set_formatted_number(text, lang, lang_iso1, is_num2words_compat)

    return text
