"""
Ebook Module
Provides utilities for EPUB manipulation, extraction, and conversion.
"""

from .converter import convert2epub
from .extractor import get_cover, get_chapters
from .metadata import get_ebook_title, extract_toc, get_all_spine_documents
from .models import EbookMetadata, Chapter, Ebook

__all__ = [
    # Converter
    'convert2epub',
    # Extractor
    'get_cover',
    'get_chapters',
    # Metadata
    'get_ebook_title',
    'extract_toc',
    'get_all_spine_documents',
    # Models
    'EbookMetadata',
    'Chapter',
    'Ebook',
]
