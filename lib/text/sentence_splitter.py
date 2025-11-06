"""
Sentence Splitter Module
Handles multi-language sentence segmentation with max character constraints.

Supports ideogrammatic languages (Chinese, Japanese, Korean, Thai, Lao, Burmese, Khmer)
with specialized tokenizers and buffer management.
"""

import regex as re

from lib.core.exceptions import DependencyError
from lib.conf import TTS_SML
from lib.lang import (
    language_mapping,
    punctuation_split_hard_set,
    punctuation_split_soft_set,
    punctuation_list_set
)


def get_sentences(text: str, lang: str, tts_engine: str) -> list[str] | None:
    """
    Segment text into sentences with max character constraints per language.

    This function implements a sophisticated multi-stage splitting algorithm:
    1. SML token preservation (break/pause markers)
    2. Hard punctuation split (., !, ?, etc.)
    3. Soft punctuation split (,, ;, :, etc.) with buffer optimization
    4. Language-specific tokenization for ideogrammatic languages
    5. Buffer management to respect max_chars limits

    Multi-Language Support:
        - Alphabetic languages: Word-based splitting
        - Chinese (zho): jieba tokenizer
        - Japanese (jpn): sudachi tokenizer
        - Korean (kor): soynlp LTokenizer
        - Thai/Lao/Burmese/Khmer: pythainlp newmm tokenizer

    Args:
        text: Input text to segment
        lang: Language code (e.g., 'eng', 'fra', 'zho', 'jpn')
        tts_engine: TTS engine name (for engine-specific handling)

    Returns:
        list[str]: List of sentence segments
        None: If processing fails

    Example:
        >>> text = "Hello world! How are you? I'm fine."
        >>> get_sentences(text, 'eng', 'xtts')
        ['Hello world!', 'How are you?', "I'm fine."]

        >>> text = "你好世界！今天天气很好。"
        >>> get_sentences(text, 'zho', 'xtts')
        ['你好世界！', '今天天气很好。']

    Notes:
        - Respects language_mapping[lang]['max_chars'] limits
        - Preserves SML tokens (‡break‡, ‡pause‡)
        - Handles buffer overflow gracefully with backtracking
        - Imports tokenizers conditionally for each language

    Algorithm Stages:
        1. **SML Splitting**: Preserve break/pause markers
        2. **Hard Punctuation**: Split on sentence-ending punctuation
        3. **Soft Punctuation**: Split on clause-separating punctuation
        4. **Buffer Optimization**: Merge short segments when possible
        5. **Ideogrammatic Processing**: Language-specific tokenization
        6. **Final Buffer Assembly**: Join tokens with max_chars constraint
    """

    def split_inclusive(text: str, pattern):
        """
        Split text on pattern while including the matched delimiter.

        Args:
            text: Input text
            pattern: Compiled regex pattern

        Returns:
            list: Segments including delimiters
        """
        result = []
        last_end = 0
        for match in pattern.finditer(text):
            result.append(text[last_end:match.end()].strip())
            last_end = match.end()
        if last_end < len(text):
            tail = text[last_end:].strip()
            if tail:
                result.append(tail)
        return result

    def segment_ideogramms(text: str):
        """
        Tokenize ideogrammatic languages with specialized tokenizers.

        Supports:
        - Chinese (jieba)
        - Japanese (sudachi)
        - Korean (soynlp)
        - Thai/Lao/Burmese/Khmer (pythainlp)

        Args:
            text: Input text to tokenize

        Returns:
            list: List of tokens
        """
        sml_pattern = "|".join(re.escape(token) for token in sml_tokens)
        segments = re.split(f"({sml_pattern})", text)
        result = []
        try:
            for segment in segments:
                if not segment:
                    continue
                # If the segment is a SML token, keep as its own
                if re.fullmatch(sml_pattern, segment):
                    result.append(segment)
                else:
                    if lang == 'zho':
                        import jieba
                        result.extend([t for t in jieba.cut(segment) if t.strip()])
                    elif lang == 'jpn':
                        from sudachipy import dictionary, tokenizer
                        sudachi = dictionary.Dictionary().create()
                        mode = tokenizer.Tokenizer.SplitMode.C
                        result.extend([m.surface() for m in sudachi.tokenize(segment, mode) if m.surface().strip()])
                    elif lang == 'kor':
                        from soynlp.tokenizer import LTokenizer
                        ltokenizer = LTokenizer()
                        result.extend([t for t in ltokenizer.tokenize(segment) if t.strip()])
                    elif lang in ['tha', 'lao', 'mya', 'khm']:
                        from pythainlp import word_tokenize
                        result.extend([t for t in word_tokenize(segment, engine='newmm') if t.strip()])
                    else:
                        result.append(segment.strip())
            return result
        except Exception as e:
            DependencyError(e)
            return [text]

    def join_ideogramms(idg_list):
        """
        Join tokenized ideogrammatic text with buffer management.

        Yields segments that don't exceed max_chars while preserving
        SML tokens as separate segments.

        Args:
            idg_list: List of tokens

        Yields:
            str: Buffered segments
        """
        try:
            buffer = ''
            for token in idg_list:
                # 1) On sml token: flush & emit buffer, then emit the token
                if token.strip() in sml_tokens:
                    if buffer:
                        yield buffer
                        buffer = ''
                    yield token
                    continue
                # 2) If adding this token would overflow, flush current buffer first
                if buffer and len(buffer) + len(token) > max_chars:
                    yield buffer
                    buffer = ''
                # 3) Append the token (word, punctuation, whatever) unless it's a sml token (already checked)
                buffer += token
            # 4) Flush any trailing text
            if buffer:
                yield buffer
        except Exception as e:
            DependencyError(e)
            if buffer:
                yield buffer

    try:
        max_chars = language_mapping[lang]['max_chars'] - 4
        min_tokens = 5
        # List or tuple of tokens that must never be appended to buffer
        sml_tokens = tuple(TTS_SML.values())

        # Stage 1: Split on SML tokens
        sml_list = re.split(rf"({'|'.join(map(re.escape, sml_tokens))})", text)
        sml_list = [s for s in sml_list if s.strip() or s in sml_tokens]

        # Stage 2: Hard punctuation split
        pattern_split = '|'.join(map(re.escape, punctuation_split_hard_set))
        pattern = re.compile(rf"(.*?(?:{pattern_split}){''.join(punctuation_list_set)})(?=\s|$)", re.DOTALL)
        hard_list = []

        for s in sml_list:
            if s in [TTS_SML['break'], TTS_SML['pause']] or len(s) <= max_chars:
                hard_list.append(s)
            else:
                parts = split_inclusive(s, pattern)
                if parts:
                    for text_part in parts:
                        text_part = text_part.strip()
                        if text_part:
                            hard_list.append(text_part)
                else:
                    s = s.strip()
                    if s:
                        hard_list.append(s)

        # Stage 3: Soft punctuation split with buffer optimization
        pattern_split = '|'.join(map(re.escape, punctuation_split_soft_set))
        pattern = re.compile(rf"(.*?(?:{pattern_split}))(?=\s|$)", re.DOTALL)
        soft_list = []

        for s in hard_list:
            if s in [TTS_SML['break'], TTS_SML['pause']] or len(s) <= max_chars:
                soft_list.append(s)
            elif len(s) > max_chars:
                parts = [p for p in split_inclusive(s, pattern) if p]
                if parts:
                    buffer = ''
                    for idx, part in enumerate(parts):
                        # Predict length if we glue this part
                        predicted_length = len(buffer) + (1 if buffer else 0) + len(part)
                        # Peek ahead to see if gluing will exceed max_chars
                        if predicted_length <= max_chars:
                            buffer = (buffer + ' ' + part).strip() if buffer else part
                        else:
                            # If we overshoot, check if buffer ends with punctuation
                            if buffer and not any(buffer.rstrip().endswith(p) for p in punctuation_split_soft_set):
                                # Try to backtrack to last punctuation inside buffer
                                last_punct_idx = max((buffer.rfind(p) for p in punctuation_split_soft_set if p in buffer), default=-1)
                                if last_punct_idx != -1:
                                    soft_list.append(buffer[:last_punct_idx+1].strip())
                                    leftover = buffer[last_punct_idx+1:].strip()
                                    buffer = leftover + ' ' + part if leftover else part
                                else:
                                    # No punctuation, just split as-is
                                    soft_list.append(buffer.strip())
                                    buffer = part
                            else:
                                soft_list.append(buffer.strip())
                                buffer = part
                    if buffer:
                        cleaned = re.sub(r'[^\p{L}\p{N} ]+', '', buffer)
                        if any(ch.isalnum() for ch in cleaned):
                            soft_list.append(buffer.strip())
                else:
                    cleaned = re.sub(r'[^\p{L}\p{N} ]+', '', s)
                    if any(ch.isalnum() for ch in cleaned):
                        soft_list.append(s.strip())
            else:
                cleaned = re.sub(r'[^\p{L}\p{N} ]+', '', s)
                if any(ch.isalnum() for ch in cleaned):
                    soft_list.append(s.strip())

        # Stage 4: Language-specific processing
        if lang in ['zho', 'jpn', 'kor', 'tha', 'lao', 'mya', 'khm']:
            # Ideogrammatic languages: tokenize and buffer
            result = []
            for s in soft_list:
                if s in [TTS_SML['break'], TTS_SML['pause']]:
                    result.append(s)
                else:
                    tokens = segment_ideogramms(s)
                    if isinstance(tokens, list):
                        result.extend([t for t in tokens if t.strip()])
                    else:
                        tokens = tokens.strip()
                        if tokens:
                            result.append(tokens)
            return list(join_ideogramms(result))
        else:
            # Alphabetic languages: word-based splitting
            sentences = []
            for s in soft_list:
                if s in [TTS_SML['break'], TTS_SML['pause']] or len(s) <= max_chars:
                    sentences.append(s)
                else:
                    words = s.split(' ')
                    text_part = words[0]
                    for w in words[1:]:
                        if len(text_part) + 1 + len(w) <= max_chars:
                            text_part += ' ' + w
                        else:
                            text_part = text_part.strip()
                            if text_part:
                                sentences.append(text_part)
                            text_part = w
                    if text_part:
                        cleaned = re.sub(r'[^\p{L}\p{N} ]+', '', text_part).strip()
                        if not any(ch.isalnum() for ch in cleaned):
                            continue
                        sentences.append(text_part)
            return sentences

    except Exception as e:
        error = f'get_sentences() error: {e}'
        print(error)
        return None
