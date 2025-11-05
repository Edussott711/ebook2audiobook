"""
Text Utilities Module
Provides utility functions for text processing.
"""

from num2words import num2words


def get_num2words_compat(lang_iso1: str) -> bool:
    """
    Check if num2words library supports the given language.

    Tests if the language is compatible with num2words by attempting
    to convert a test number.

    Args:
        lang_iso1: ISO 639-1 language code (e.g., 'en', 'fr', 'zh')

    Returns:
        bool: True if language is supported, False otherwise
    """
    try:
        # Special case for Chinese
        lang_code = lang_iso1.replace('zh', 'zh_CN')

        # Test conversion
        test = num2words(1, lang=lang_code)
        return True

    except NotImplementedError:
        return False
    except Exception:
        return False
