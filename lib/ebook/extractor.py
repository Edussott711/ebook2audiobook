"""
EPUB Extractor Module
Handles extraction of content from EPUB files (cover, chapters, etc.).
"""

import os
import io
from typing import Dict, Any, Tuple, List, Optional
from PIL import Image
import ebooklib
from ebooklib import epub
import stanza

from lib.core.exceptions import DependencyError
from lib.ebook.metadata import get_ebook_title, get_all_spine_documents
from lib.text.processor import filter_chapter
from lib.text.utils import get_num2words_compat
from lib.conf import year_to_decades_languages


def get_cover(epub_book: epub.EpubBook, session: Dict[str, Any]) -> str | bool:
    """
    Extract and save the cover image from an EPUB file.

    Searches for cover in two ways:
    1. Items marked as ITEM_COVER type
    2. Images with 'cover' in filename or ID

    Args:
        epub_book: EpubBook object from ebooklib
        session: Session context dictionary containing:
            - process_dir: Directory to save the cover image
            - filename_noext: Base filename (without extension)
            - cancellation_requested: Flag to check for cancellation

    Returns:
        str | bool: Path to saved cover image if found, True if no cover, False on error
    """
    try:
        if session.get('cancellation_requested'):
            msg = 'Cancel requested'
            print(msg)
            return False

        cover_image = None
        cover_path = os.path.join(session['process_dir'], session['filename_noext'] + '.jpg')

        # 1. Try to get official cover item
        for item in epub_book.get_items_of_type(ebooklib.ITEM_COVER):
            cover_image = item.get_content()
            break

        # 2. Fallback: search images with 'cover' in name/ID
        if not cover_image:
            for item in epub_book.get_items_of_type(ebooklib.ITEM_IMAGE):
                if 'cover' in item.file_name.lower() or 'cover' in item.get_id().lower():
                    cover_image = item.get_content()
                    break

        if cover_image:
            # Open the image from bytes
            image = Image.open(io.BytesIO(cover_image))

            # Convert to RGB if needed (JPEG doesn't support alpha)
            if image.mode in ('RGBA', 'P'):
                image = image.convert('RGB')

            # Save as JPEG
            image.save(cover_path, format='JPEG')
            return cover_path

        # No cover found
        return True

    except Exception as e:
        DependencyError(str(e))
        return False


def get_chapters(epub_book: epub.EpubBook, session: Dict[str, Any]) -> Tuple[Optional[List], Optional[List]]:
    """
    Extract and process all chapters from an EPUB file.

    Processes each document in the spine (reading order) by:
    1. Extracting text content
    2. Normalizing numbers, dates, and times
    3. Splitting into sentences
    4. Filtering and cleaning text

    Args:
        epub_book: EpubBook object from ebooklib
        session: Session context dictionary containing:
            - language: Language code (e.g., 'eng', 'fra')
            - language_iso1: ISO 639-1 code (e.g., 'en', 'fr')
            - tts_engine: TTS engine name
            - cancellation_requested: Flag to check for cancellation

    Returns:
        tuple: (toc_list, chapters_list) where:
            - toc_list: List of Table of Contents entries (normalized)
            - chapters_list: List of chapters, each chapter is a list of sentences
            Returns (None, None) on error
    """
    try:
        # Display informational message about character warnings
        msg = r'''
*******************************************************************************
NOTE:
The warning "Character xx not found in the vocabulary."
MEANS THE MODEL CANNOT INTERPRET THE CHARACTER AND WILL MAYBE GENERATE
(AS WELL AS WRONG PUNCTUATION POSITION) AN HALLUCINATION TO IMPROVE THIS MODEL,
IT NEEDS TO ADD THIS CHARACTER INTO A NEW TRAINING MODEL.
YOU CAN IMPROVE IT OR ASK TO A TRAINING MODEL EXPERT.
*******************************************************************************
        '''
        print(msg)

        if session.get('cancellation_requested'):
            print('Cancel requested')
            return False, False

        # Step 1: Extract TOC (Table of Contents)
        from lib.ebook.metadata import extract_toc
        toc_list = extract_toc(
            epub_book,
            session['language'],
            session['language_iso1'],
            session['tts_engine']
        )

        # Step 2: Get all spine documents (reading order)
        all_docs = get_all_spine_documents(epub_book)

        if not all_docs:
            return [], []

        # Extract book title for reference
        title = get_ebook_title(epub_book, all_docs)

        # Step 3: Initialize NLP pipeline if needed (for date/year extraction)
        chapters = []
        stanza_nlp = False

        if session['language'] in year_to_decades_languages:
            stanza.download(session['language_iso1'])
            stanza_nlp = stanza.Pipeline(
                session['language_iso1'],
                processors='tokenize,ner'
            )

        is_num2words_compat = get_num2words_compat(session['language_iso1'])

        msg = 'Analyzing numbers, maths signs, dates and time to convert in words...'
        print(msg)

        # Step 4: Process each document
        for doc in all_docs:
            sentences_list = filter_chapter(
                doc,
                session['language'],
                session['language_iso1'],
                session['tts_engine'],
                stanza_nlp,
                is_num2words_compat
            )

            if sentences_list is None:
                break
            elif len(sentences_list) > 0:
                chapters.append(sentences_list)

        if len(chapters) == 0:
            error = 'No chapters found!'
            print(error)
            return None, None

        return toc_list, chapters

    except Exception as e:
        error = f'Error extracting main content pages: {e}'
        DependencyError(error)
        return None, None
