"""
EPUB Metadata Module
Handles extraction and management of EPUB metadata.
"""

from typing import Optional, List
from bs4 import BeautifulSoup
from ebooklib import epub


def get_ebook_title(epub_book: epub.EpubBook, all_docs: List) -> Optional[str]:
    """
    Extract the title from an EPUB book using multiple fallback methods.

    Tries in order:
    1. Official EPUB metadata (DC:title)
    2. <title> tag in the first XHTML document
    3. <img alt="..."> attribute if available

    Args:
        epub_book: EpubBook object from ebooklib
        all_docs: List of EPUB document items

    Returns:
        str | None: Book title if found, None otherwise
    """
    # 1. Try metadata (official EPUB title)
    meta_title = epub_book.get_metadata("DC", "title")
    if meta_title and meta_title[0][0].strip():
        return meta_title[0][0].strip()

    # 2. Try <title> in the head of the first XHTML document
    if all_docs:
        html = all_docs[0].get_content().decode("utf-8")
        soup = BeautifulSoup(html, "html.parser")

        title_tag = soup.select_one("head > title")
        if title_tag and title_tag.text.strip():
            return title_tag.text.strip()

        # 3. Try <img alt="..."> if no visible <title>
        img = soup.find("img", alt=True)
        if img:
            alt = img['alt'].strip()
            if alt and "cover" not in alt.lower():
                return alt

    return None


def extract_toc(epub_book: epub.EpubBook, language: str, language_iso1: str, tts_engine: str) -> List[str]:
    """
    Extract and normalize Table of Contents from EPUB.

    Args:
        epub_book: EpubBook object from ebooklib
        language: Language code (e.g., 'eng', 'fra')
        language_iso1: ISO 639-1 language code (e.g., 'en', 'fr')
        tts_engine: TTS engine name for normalization

    Returns:
        list: List of normalized TOC entries
    """
    from lib.text.normalizer import normalize_text

    try:
        toc = epub_book.toc  # Extract TOC
        toc_list = [
            nt for item in toc if hasattr(item, 'title')
            if (nt := normalize_text(
                str(item.title),
                language,
                language_iso1,
                tts_engine
            )) is not None
        ]
        return toc_list
    except Exception as toc_error:
        error = f"Error extracting TOC: {toc_error}"
        print(error)
        return []


def get_all_spine_documents(epub_book: epub.EpubBook) -> List:
    """
    Get all EPUB documents in spine (reading) order.

    Args:
        epub_book: EpubBook object from ebooklib

    Returns:
        list: List of EPUB document items in reading order
    """
    import ebooklib

    # Get spine item IDs (reading order)
    spine_ids = [item[0] for item in epub_book.spine]

    # Filter only spine documents
    all_docs = [
        item for item in epub_book.get_items_of_type(ebooklib.ITEM_DOCUMENT)
        if item.id in spine_ids
    ]

    return all_docs
