"""
Text Normalizer Module
Handles text normalization for TTS processing.
"""

import regex as re
from lib.models import TTS_SML
from lib.lang import (
    abbreviations_mapping,
    emojis_list,
    punctuation_switch,
    punctuation_split_hard_set,
    punctuation_split_soft_set,
    specialchars_mapping,
    default_language_code
)


def filter_sml(text: str) -> str:
    """
    Filter and replace SML (Speech Markup Language) tags with their equivalents.

    Supports tags like '###', '[pause]', '[break]' for TTS control.

    Args:
        text: Input text containing SML tags

    Returns:
        str: Text with SML tags replaced by internal markers
    """
    for key, value in TTS_SML.items():
        if key == '###':
            pattern = re.escape(key)
        else:
            pattern = r'\[' + re.escape(key) + r'\]'

        text = re.sub(pattern, f" {value} ", text)

    return text


def normalize_text(text: str, lang: str, lang_iso1: str, tts_engine: str) -> str:
    """
    Normalize text for TTS processing.

    Performs comprehensive text cleaning and normalization:
    - Removes emojis
    - Expands abbreviations
    - Converts acronyms to uppercase
    - Processes SML tags
    - Normalizes whitespace
    - Replaces problematic punctuation
    - Converts special characters to words

    Args:
        text: Input text to normalize
        lang: Language code (e.g., 'eng', 'fra')
        lang_iso1: ISO 639-1 language code (e.g., 'en', 'fr')
        tts_engine: TTS engine name (for engine-specific processing)

    Returns:
        str: Normalized text ready for TTS
    """
    # Remove emojis
    emoji_pattern = re.compile(f"[{''.join(emojis_list)}]+", flags=re.UNICODE)
    text = emoji_pattern.sub('', text)

    # Expand abbreviations (language-specific)
    if lang in abbreviations_mapping:
        def repl_abbreviations(match: re.Match) -> str:
            token = match.group(1)
            for k, expansion in mapping.items():
                if token.lower() == k.lower():
                    return expansion
            return token  # fallback

        mapping = abbreviations_mapping[lang]

        # Sort keys by descending length so longer ones match first
        keys = sorted(mapping.keys(), key=len, reverse=True)

        # Build a regex that only matches whole "words" (tokens) exactly
        pattern = re.compile(
            r'(?<!\w)(' + '|'.join(re.escape(k) for k in keys) + r')(?!\w)',
            flags=re.IGNORECASE
        )
        text = pattern.sub(repl_abbreviations, text)

    # Convert acronyms to uppercase (e.g., "c.i.a." -> "CIA")
    # This regex matches sequences like a., c.i.a., f.d.a., m.c., etc...
    text = re.sub(
        r'\b(?:[a-zA-Z]\.){1,}[a-zA-Z]?\b\.?',
        lambda m: m.group().replace('.', '').upper(),
        text
    )

    # Prepare SML tags
    text = filter_sml(text)

    # Replace multiple newlines ("\n\n", "\r\r", "\n\r", etc.) with pause (1.4sec)
    pattern = r'(?:\r\n|\r|\n){2,}'
    text = re.sub(pattern, f" {TTS_SML['pause']} ", text)

    # Replace single newlines ("\n" or "\r") with spaces
    text = re.sub(r'\r\n|\r|\n', ' ', text)

    # Replace punctuations causing hallucinations
    pattern = f"[{''.join(map(re.escape, punctuation_switch.keys()))}]"
    text = re.sub(
        pattern,
        lambda match: punctuation_switch.get(match.group(), match.group()),
        text
    )

    # Replace NBSP (non-breaking space) with a normal space
    text = text.replace("\xa0", " ")

    # Replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', text)

    # Replace "ok" by "Okay"
    text = re.sub(r'\bok\b', 'Okay', text, flags=re.IGNORECASE)

    # Replace parentheses with double quotes
    text = re.sub(r'\(([^)]+)\)', r'"\1"', text)

    # Reduce multiple consecutive hard punctuations
    pattern = '|'.join(map(re.escape, punctuation_split_hard_set))
    text = re.sub(rf'(\s*({pattern})\s*)+', r'\2 ', text).strip()

    # Reduce multiple consecutive soft punctuations
    pattern = '|'.join(map(re.escape, punctuation_split_soft_set))
    text = re.sub(rf'(\s*({pattern})\s*)+', r'\2 ', text).strip()

    # Add a space between UTF-8 characters and numbers
    text = re.sub(r'(?<=[\p{L}])(?=\d)|(?<=\d)(?=[\p{L}])', ' ', text)

    # Replace special chars with words (language-specific)
    specialchars = specialchars_mapping.get(
        lang,
        specialchars_mapping.get(default_language_code, specialchars_mapping['eng'])
    )
    specialchars_table = {ord(char): f" {word} " for char, word in specialchars.items()}
    text = text.translate(specialchars_table)

    # Final cleanup: normalize whitespace
    text = ' '.join(text.split())

    return text
