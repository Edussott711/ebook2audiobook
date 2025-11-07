"""
Text Processor Module
Handles advanced text processing for EPUB chapters.

This module provides the main pipeline for converting EPUB HTML content
into TTS-ready sentences with proper normalization and formatting.
"""

import unicodedata
import regex as re
from bs4 import BeautifulSoup, NavigableString, Tag
from num2words import num2words

from lib.core.exceptions import DependencyError
from lib.models import TTS_SML
from lib.lang import language_mapping, specialchars_remove
from lib.text.date_converter import get_date_entities, year2words, clock2words
from lib.text.math_converter import math2words
from lib.text.number_converter import roman2number
from lib.text.normalizer import normalize_text
from lib.text.sentence_splitter import get_sentences


def filter_chapter(doc, lang, lang_iso1, tts_engine, stanza_nlp, is_num2words_compat):
    """
    Filter and process an EPUB chapter document for TTS conversion.

    This is the main text processing pipeline that:
    1. Parses HTML content (BeautifulSoup)
    2. Extracts text, headings, and tables
    3. Filters excluded EPUB types (TOC, frontmatter, etc.)
    4. Converts dates, numbers, and mathematical symbols to words
    5. Normalizes text for TTS engines
    6. Segments into sentences

    Pipeline Stages:
        1. HTML Parsing → Extract structured content (headings, text, tables, breaks)
        2. Table Processing → Convert tables to descriptive text
        3. Break Optimization → Merge short sentences when possible
        4. Date/Number Conversion → NLP-based entity recognition and conversion
        5. Symbol Conversion → Roman numerals, clock times, math symbols
        6. Character Normalization → Remove special characters
        7. Text Normalization → Emoji removal, abbreviation expansion
        8. Sentence Segmentation → Language-specific sentence splitting

    Args:
        doc: EPUB document item (ebooklib.epub.EpubItem)
        lang: Language code (e.g., 'eng', 'fra')
        lang_iso1: ISO 639-1 language code (e.g., 'en', 'fr')
        tts_engine: TTS engine name (e.g., 'xtts', 'bark')
        stanza_nlp: Stanza NLP pipeline for date entity extraction (optional)
        is_num2words_compat: Whether num2words supports this language

    Returns:
        list: List of processed sentence strings ready for TTS
        None: If processing fails or no valid content found

    Example:
        >>> from ebooklib import epub
        >>> book = epub.read_epub('book.epub')
        >>> chapter = book.get_items_of_type(ebooklib.ITEM_DOCUMENT)[0]
        >>> sentences = filter_chapter(chapter, 'eng', 'en', 'xtts', stanza_nlp, True)
        >>> print(sentences[0])
        "Chapter One. The beginning of the story..."

    Notes:
        - Excludes EPUB frontmatter, backmatter, TOC, titlepage, etc.
        - Tables are converted to "Header: Value — Header: Value" format
        - Breaks are intelligently merged to avoid very short sentences
        - Uses Stanza NLP for date entity recognition when available
        - Special characters are removed or normalized
        - Returns None for empty or invalid chapters

    EPUB Types Excluded:
        frontmatter, backmatter, toc, titlepage, colophon, acknowledgments,
        dedication, glossary, index, appendix, bibliography, copyright-page,
        landmark
    """

    def tuple_row(node, last_text_char=None):
        """
        Recursively extract structured content from HTML nodes.

        Yields tuples of (type, content) where type is one of:
        - "text": Plain text content
        - "heading": Heading text (h1-h4)
        - "table": Table element
        - "break": Line break marker
        - "pause": Pause marker

        Args:
            node: BeautifulSoup Tag or NavigableString
            last_text_char: Last character from previous text (for break detection)

        Yields:
            tuple: (type, content) pairs
        """
        try:
            for child in node.children:
                if isinstance(child, NavigableString):
                    text = child.strip()
                    if text:
                        yield ("text", text)
                        last_text_char = text[-1] if text else last_text_char

                elif isinstance(child, Tag):
                    name = child.name.lower()
                    if name in heading_tags:
                        title = child.get_text(strip=True)
                        if title:
                            yield ("heading", title)
                            last_text_char = title[-1] if title else last_text_char

                    elif name == "table":
                        yield ("table", child)

                    else:
                        return_data = False
                        if name in proc_tags:
                            for inner in tuple_row(child, last_text_char):
                                return_data = True
                                yield inner
                                # Track last char if this is text or heading
                                if inner[0] in ("text", "heading") and inner[1]:
                                    last_text_char = inner[1][-1]

                            if return_data:
                                if name in break_tags:
                                    # Only yield break if last char is NOT alnum or space
                                    if not (last_text_char and (last_text_char.isalnum() or last_text_char.isspace())):
                                        yield ("break", TTS_SML['break'])
                                elif name in heading_tags or name in pause_tags:
                                    yield ("pause", TTS_SML['pause'])

                        else:
                            yield from tuple_row(child, last_text_char)

        except Exception as e:
            error = f'filter_chapter() tuple_row() error: {e}'
            DependencyError(error)
            return None

    try:
        # Define HTML tag categories
        heading_tags = [f'h{i}' for i in range(1, 5)]
        break_tags = ['br', 'p']
        pause_tags = ['div', 'span']
        proc_tags = heading_tags + break_tags + pause_tags

        # Parse HTML
        raw_html = doc.get_body_content().decode("utf-8")
        soup = BeautifulSoup(raw_html, 'html.parser')
        body = soup.body
        if not body or not body.get_text(strip=True):
            return []

        # Skip known non-chapter types
        epub_type = body.get("epub:type", "").lower()
        if not epub_type:
            section_tag = soup.find("section")
            if section_tag:
                epub_type = section_tag.get("epub:type", "").lower()
        excluded = {
            "frontmatter", "backmatter", "toc", "titlepage", "colophon",
            "acknowledgments", "dedication", "glossary", "index",
            "appendix", "bibliography", "copyright-page", "landmark"
        }
        if any(part in epub_type for part in excluded):
            return []

        # Remove scripts/styles
        for tag in soup(["script", "style"]):
            tag.decompose()

        # Extract structured content
        tuples_list = list(tuple_row(body))
        if not tuples_list:
            error = 'No tuples_list from body created!'
            print(error)
            return None

        # Process tuples into text
        text_list = []
        handled_tables = set()
        prev_typ = None

        for typ, payload in tuples_list:
            if typ == "heading":
                text_list.append(payload.strip())

            elif typ == "break":
                if prev_typ != 'break':
                    text_list.append(TTS_SML['break'])

            elif typ == 'pause':
                if prev_typ != 'pause':
                    text_list.append(TTS_SML['pause'])

            elif typ == "table":
                table = payload
                if table in handled_tables:
                    prev_typ = typ
                    continue
                handled_tables.add(table)

                # Process table rows
                rows = table.find_all("tr")
                if not rows:
                    prev_typ = typ
                    continue

                # Extract headers from first row
                headers = [c.get_text(strip=True) for c in rows[0].find_all(["td", "th"])]

                # Process data rows
                for row in rows[1:]:
                    cells = [c.get_text(strip=True).replace('\xa0', ' ') for c in row.find_all("td")]
                    if not cells:
                        continue

                    # Format as "Header: Value — Header: Value"
                    if len(cells) == len(headers) and headers:
                        line = " — ".join(f"{h}: {c}" for h, c in zip(headers, cells))
                    else:
                        line = " — ".join(cells)

                    if line:
                        text_list.append(line.strip())

            else:  # typ == "text"
                text = payload.strip()
                if text:
                    text_list.append(text)

            prev_typ = typ

        # Optimize breaks (merge short sentences)
        max_chars = language_mapping[lang]['max_chars'] - 4
        clean_list = []
        i = 0

        while i < len(text_list):
            current = text_list[i]

            if current == "‡break‡":
                if clean_list:
                    prev = clean_list[-1]

                    # Skip consecutive breaks/pauses
                    if prev in ("‡break‡", "‡pause‡"):
                        i += 1
                        continue

                    # Try to merge if previous ends with alnum or space
                    if prev and (prev[-1].isalnum() or prev[-1] == ' '):
                        if i + 1 < len(text_list):
                            next_sentence = text_list[i + 1]
                            merged_length = len(prev.rstrip()) + 1 + len(next_sentence.lstrip())

                            # Merge if within max_chars limit
                            if merged_length <= max_chars:
                                # Merge with space handling
                                if not prev.endswith(" ") and not next_sentence.startswith(" "):
                                    clean_list[-1] = prev + " " + next_sentence
                                else:
                                    clean_list[-1] = prev + next_sentence
                                i += 2
                                continue
                            else:
                                clean_list.append(current)
                                i += 1
                                continue

            clean_list.append(current)
            i += 1

        # Join into single text
        text = ' '.join(clean_list)

        # Validate text has content
        if not re.search(r"[^\W_]", text):
            error = 'No valid text found!'
            print(error)
            return None

        # NLP-based date/number conversion
        if stanza_nlp:
            # Check if there are positive integers so possible date to convert
            re_ordinal = re.compile(
                r'(?<!\w)(0?[1-9]|[12][0-9]|3[01])(?:\s|\u00A0)*(?:st|nd|rd|th)(?!\w)',
                re.IGNORECASE
            )
            re_num = re.compile(r'(?<!\w)[-+]?\d+(?:\.\d+)?(?!\w)')

            text = unicodedata.normalize('NFKC', text).replace('\u00A0', ' ')

            if re_num.search(text) and re_ordinal.search(text):
                date_spans = get_date_entities(text, stanza_nlp)

                if date_spans:
                    # Process dates with NLP entity recognition
                    result = []
                    last_pos = 0

                    for start, end, date_text in date_spans:
                        result.append(text[last_pos:start])

                        # 1) Convert 4-digit years
                        processed = re.sub(
                            r"\b\d{4}\b",
                            lambda m: year2words(m.group(), lang, lang_iso1, is_num2words_compat),
                            date_text
                        )

                        # 2) Convert ordinal days like "16th"/"16 th" -> "sixteenth"
                        if is_num2words_compat:
                            processed = re_ordinal.sub(
                                lambda m: num2words(int(m.group(1)), to="ordinal", lang=(lang_iso1 or "en")),
                                processed
                            )
                        else:
                            processed = re_ordinal.sub(
                                lambda m: math2words(m.group(), lang, lang_iso1, tts_engine, is_num2words_compat),
                                processed
                            )

                        # 3) Convert other numbers (skip 4-digit years)
                        def _num_repl(m):
                            s = m.group(0)
                            # Leave years alone (already handled above)
                            if re.fullmatch(r"\d{4}", s):
                                return s
                            n = float(s) if "." in s else int(s)
                            if is_num2words_compat:
                                return num2words(n, lang=(lang_iso1 or "en"))
                            else:
                                return math2words(m, lang, lang_iso1, tts_engine, is_num2words_compat)

                        processed = re_num.sub(_num_repl, processed)
                        result.append(processed)
                        last_pos = end

                    result.append(text[last_pos:])
                    text = ''.join(result)

                else:
                    # No date entities found, process ordinals and years globally
                    if is_num2words_compat:
                        text = re_ordinal.sub(
                            lambda m: num2words(int(m.group(1)), to="ordinal", lang=(lang_iso1 or "en")),
                            text
                        )
                    else:
                        text = re_ordinal.sub(
                            lambda m: math2words(int(m.group(1)), lang, lang_iso1, tts_engine, is_num2words_compat),
                            text
                        )

                    text = re.sub(
                        r"\b\d{4}\b",
                        lambda m: year2words(m.group(), lang, lang_iso1, is_num2words_compat),
                        text
                    )

        # Convert roman numerals
        text = roman2number(text)

        # Convert clock times
        text = clock2words(text, lang, lang_iso1, tts_engine, is_num2words_compat)

        # Convert math symbols
        text = math2words(text, lang, lang_iso1, tts_engine, is_num2words_compat)

        # Remove special characters
        specialchars_remove_table = str.maketrans({ch: ' ' for ch in specialchars_remove})
        text = text.translate(specialchars_remove_table)

        # Normalize text
        text = normalize_text(text, lang, lang_iso1, tts_engine)

        # Segment into sentences
        sentences = get_sentences(text, lang, tts_engine)

        if len(sentences) == 0:
            error = 'No sentences found!'
            print(error)
            return None

        return get_sentences(text, lang, tts_engine)

    except Exception as e:
        error = f'filter_chapter() error: {e}'
        DependencyError(error)
        return None
