"""
Date Converter Module
Handles conversion of dates, times, and years to words for TTS.
"""

import regex as re
from typing import List, Tuple, Optional
from num2words import num2words

from lib.lang import language_clock, language_math_phonemes, default_language_code


def get_date_entities(text: str, stanza_nlp) -> List[Tuple[int, int, str]] | bool:
    """
    Extract date entities from text using Stanza NLP.

    Args:
        text: Input text to analyze
        stanza_nlp: Stanza NLP pipeline with NER enabled

    Returns:
        list | bool: List of (start_char, end_char, text) tuples for DATE entities,
                     or False on error

    Example:
        >>> nlp = stanza.Pipeline('en', processors='tokenize,ner')
        >>> entities = get_date_entities("Meeting on January 15, 2024", nlp)
        >>> entities
        [(11, 28, 'January 15, 2024')]
    """
    try:
        doc = stanza_nlp(text)
        date_spans = []

        for ent in doc.ents:
            if ent.type == 'DATE':
                date_spans.append((ent.start_char, ent.end_char, ent.text))

        return date_spans

    except Exception as e:
        error = f'get_date_entities() error: {e}'
        print(error)
        return False


def year2words(year_str: str, lang: str, lang_iso1: str, is_num2words_compat: bool) -> str:
    """
    Convert a 4-digit year to words.

    For years like 1984, splits into "nineteen eighty-four" rather than
    "one thousand nine hundred eighty-four".

    Args:
        year_str: Year as string (e.g., "1984", "2024")
        lang: Language code (e.g., 'eng', 'fra')
        lang_iso1: ISO 639-1 language code (e.g., 'en', 'fr')
        is_num2words_compat: Whether num2words supports this language

    Returns:
        str: Year in words (e.g., "nineteen eighty-four")

    Example:
        >>> year2words("1984", "eng", "en", True)
        "nineteen eighty-four"
    """
    try:
        year = int(year_str)
        first_two = int(year_str[:2])
        last_two = int(year_str[2:])

        lang_iso1 = lang_iso1 if lang in language_math_phonemes.keys() else default_language_code
        lang_iso1 = lang_iso1.replace('zh', 'zh_CN')

        # If not a 4-digit year or last two digits < 10, use full number
        if not year_str.isdigit() or len(year_str) != 4 or last_two < 10:
            if is_num2words_compat:
                return num2words(year, lang=lang_iso1)
            else:
                return ' '.join(language_math_phonemes[lang].get(ch, ch) for ch in year_str)

        # Split year into two parts (e.g., 19 84)
        if is_num2words_compat:
            return f"{num2words(first_two, lang=lang_iso1)} {num2words(last_two, lang=lang_iso1)}"
        else:
            first_part = ' '.join(language_math_phonemes[lang].get(ch, ch) for ch in str(first_two))
            last_part = ' '.join(language_math_phonemes[lang].get(ch, ch) for ch in str(last_two))
            return f"{first_part} {last_part}"

    except Exception as e:
        error = f'year2words() error: {e}'
        print(error)
        raise


def clock2words(text: str, lang: str, lang_iso1: str, tts_engine: str, is_num2words_compat: bool) -> str:
    """
    Convert time expressions to words using language-specific rules.

    Supports various time formats (HH:MM, HH:MM:SS) and uses natural
    language expressions like "quarter past", "half past", etc.

    Args:
        text: Input text containing time expressions
        lang: Language code (e.g., 'eng', 'fra')
        lang_iso1: ISO 639-1 language code (e.g., 'en', 'fr')
        tts_engine: TTS engine name
        is_num2words_compat: Whether num2words supports this language

    Returns:
        str: Text with time expressions converted to words

    Example:
        >>> clock2words("Meeting at 14:30", "eng", "en", "xtts", True)
        "Meeting at half past two"
    """
    time_rx = re.compile(r'(\d{1,2})[:.](\d{1,2})(?:[:.](\d{1,2}))?')
    lang_lc = (lang or "").lower()
    lc = language_clock.get(lang_lc) if 'language_clock' in globals() else None

    # Cache for num2words conversions
    _n2w_cache = {}

    def n2w(n: int) -> str:
        """Convert number to words with caching."""
        key = (n, lang_lc, is_num2words_compat)
        if key in _n2w_cache:
            return _n2w_cache[key]

        if is_num2words_compat:
            word = num2words(n, lang=lang_lc)
        else:
            from lib.text.math_converter import math2words
            word = math2words(str(n), lang, lang_iso1, tts_engine, is_num2words_compat)

        _n2w_cache[key] = word
        return word

    def repl_num(m: re.Match) -> str:
        """Replace time match with words."""
        # Parse hh[:mm[:ss]]
        try:
            h = int(m.group(1))
            mnt = int(m.group(2))
            sec = m.group(3)
            sec = int(sec) if sec is not None else None
        except Exception:
            return m.group(0)

        # Basic validation; if out of range, keep original
        if not (0 <= h <= 23 and 0 <= mnt <= 59 and (sec is None or 0 <= sec <= 59)):
            return m.group(0)

        # If no language clock rules, just say numbers plainly
        if not lc:
            parts = [n2w(h)]
            if mnt != 0:
                parts.append(n2w(mnt))
            if sec is not None and sec > 0:
                parts.append(n2w(sec))
            return " ".join(parts)

        next_hour = (h + 1) % 24
        special_hours = lc.get("special_hours", {})

        # Build main phrase
        if mnt == 0 and (sec is None or sec == 0):
            # On the hour
            if h in special_hours:
                phrase = special_hours[h]
            else:
                phrase = lc["oclock"].format(hour=n2w(h))

        elif mnt == 15:
            # Quarter past
            phrase = lc["quarter_past"].format(hour=n2w(h))

        elif mnt == 30:
            # Half past (German uses next hour)
            if lang_lc == "deu":
                phrase = lc["half_past"].format(next_hour=n2w(next_hour))
            else:
                phrase = lc["half_past"].format(hour=n2w(h))

        elif mnt == 45:
            # Quarter to
            phrase = lc["quarter_to"].format(next_hour=n2w(next_hour))

        elif mnt < 30:
            # Minutes past the hour
            phrase = lc["past"].format(hour=n2w(h), minute=n2w(mnt)) if mnt != 0 else lc["oclock"].format(hour=n2w(h))

        else:
            # Minutes to the next hour
            minute_to_hour = 60 - mnt
            phrase = lc["to"].format(next_hour=n2w(next_hour), minute=n2w(minute_to_hour))

        # Append seconds if present
        if sec is not None and sec > 0:
            second_phrase = lc["second"].format(second=n2w(sec))
            phrase = lc["full"].format(phrase=phrase, second_phrase=second_phrase)

        return phrase

    return time_rx.sub(repl_num, text)
