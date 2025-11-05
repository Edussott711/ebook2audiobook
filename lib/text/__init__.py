"""
Text Module
Provides text processing, normalization, and conversion utilities for TTS.
"""

from .normalizer import normalize_text, filter_sml
from .number_converter import roman2number, number_to_words, set_formatted_number
from .date_converter import get_date_entities, year2words, clock2words
from .math_converter import math2words
from .utils import get_num2words_compat
from .processor import filter_chapter

__all__ = [
    # Normalizer
    'normalize_text',
    'filter_sml',
    # Number converter
    'roman2number',
    'number_to_words',
    'set_formatted_number',
    # Date converter
    'get_date_entities',
    'year2words',
    'clock2words',
    # Math converter
    'math2words',
    # Utils
    'get_num2words_compat',
    # Processor
    'filter_chapter',
]
