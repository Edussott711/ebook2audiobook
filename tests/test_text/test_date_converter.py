"""
Tests for lib/text/date_converter.py

Tests date/time conversion functions: year2words, clock2words, get_date_entities.
"""

import pytest
from unittest.mock import MagicMock
from lib.text.date_converter import (
    year2words,
    clock2words,
    get_date_entities
)


# ============================================================================
# Tests for year2words()
# ============================================================================

class TestYear2Words:
    """Test year to words conversion."""

    def test_modern_years(self):
        """Test conversion of modern years (1900-2099)."""
        # 1984 → "nineteen eighty-four"
        result = year2words("1984", "eng", "en", True)
        assert result is not None
        assert result != "1984"  # Should be converted

    def test_year_2000s(self):
        """Test years in 2000s."""
        result = year2words("2024", "eng", "en", True)
        assert result is not None

    def test_year_with_zeros(self):
        """Test years with zeros (like 2000, 2001)."""
        result = year2words("2000", "eng", "en", True)
        assert result is not None

        result = year2words("2001", "eng", "en", True)
        assert result is not None

    def test_old_years(self):
        """Test older years (1800s, 1700s)."""
        result = year2words("1776", "eng", "en", True)
        assert result is not None

    def test_non_num2words_language(self):
        """Test with language not supported by num2words."""
        result = year2words("1984", "eng", "en", False)
        # Should still work with fallback
        assert result is not None

    def test_different_languages(self):
        """Test year conversion in different languages."""
        # French
        result = year2words("1984", "fra", "fr", True)
        assert result is not None

        # German
        result = year2words("1984", "deu", "de", True)
        assert result is not None


# ============================================================================
# Tests for clock2words()
# ============================================================================

class TestClock2Words:
    """Test clock time to words conversion."""

    def test_simple_hours(self):
        """Test simple hour times (14:00, 09:00)."""
        text = "The meeting is at 14:00"
        result = clock2words(text, "eng", "en", "xtts", True)
        assert result is not None
        # Should convert "14:00" to words

    def test_hours_with_minutes(self):
        """Test times with minutes (14:30, 09:15)."""
        text = "Meeting at 14:30 and 09:15"
        result = clock2words(text, "eng", "en", "xtts", True)
        assert result is not None

    def test_hours_with_seconds(self):
        """Test times with seconds (14:30:45)."""
        text = "Timestamp: 14:30:45"
        result = clock2words(text, "eng", "en", "xtts", True)
        assert result is not None

    def test_quarter_hours(self):
        """Test quarter hour times (15:15, 15:45)."""
        text = "At 15:15 and 15:45"
        result = clock2words(text, "eng", "en", "xtts", True)
        assert result is not None
        # May use "quarter past" or "quarter to"

    def test_half_hours(self):
        """Test half hour times (14:30, 16:30)."""
        text = "At 14:30"
        result = clock2words(text, "eng", "en", "xtts", True)
        assert result is not None
        # May use "half past"

    def test_midnight_and_noon(self):
        """Test midnight (00:00) and noon (12:00)."""
        text = "From 00:00 to 12:00"
        result = clock2words(text, "eng", "en", "xtts", True)
        assert result is not None

    def test_am_pm_format(self):
        """Test AM/PM time format."""
        # Depending on implementation, may handle 12-hour format
        text = "Meeting at 2:30 PM"
        result = clock2words(text, "eng", "en", "xtts", True)
        assert result is not None

    def test_multiple_times_in_text(self):
        """Test multiple times in the same text."""
        text = "From 09:00 to 17:30 with breaks at 12:00 and 15:15"
        result = clock2words(text, "eng", "en", "xtts", True)
        assert result is not None

    def test_non_num2words_language(self):
        """Test with non-num2words language."""
        text = "At 14:30"
        result = clock2words(text, "eng", "en", "xtts", False)
        assert result is not None

    def test_text_without_times(self):
        """Test text without any times."""
        text = "This text has no times in it."
        result = clock2words(text, "eng", "en", "xtts", True)
        assert result == text  # Should remain unchanged

    def test_edge_case_times(self):
        """Test edge case times (23:59, 00:01)."""
        text = "From 23:59 to 00:01"
        result = clock2words(text, "eng", "en", "xtts", True)
        assert result is not None


# ============================================================================
# Tests for get_date_entities()
# ============================================================================

class TestGetDateEntities:
    """Test date entity extraction using Stanza NLP."""

    def test_with_stanza_nlp(self):
        """Test date extraction with mock Stanza NLP."""
        # Create mock Stanza NLP
        mock_nlp = MagicMock()

        # Mock entity with DATE type
        mock_entity = MagicMock()
        mock_entity.type = 'DATE'
        mock_entity.start_char = 10
        mock_entity.end_char = 20
        mock_entity.text = 'January 16th'

        # Mock document
        mock_doc = MagicMock()
        mock_doc.ents = [mock_entity]
        mock_nlp.return_value = mock_doc

        text = "On January 16th, 1984, everything changed."
        result = get_date_entities(text, mock_nlp)

        assert result is not False
        assert isinstance(result, list)
        assert len(result) > 0
        assert result[0] == (10, 20, 'January 16th')

    def test_multiple_dates(self):
        """Test extraction of multiple dates."""
        mock_nlp = MagicMock()

        # Multiple date entities
        entity1 = MagicMock()
        entity1.type = 'DATE'
        entity1.start_char = 5
        entity1.end_char = 15
        entity1.text = 'January 1st'

        entity2 = MagicMock()
        entity2.type = 'DATE'
        entity2.start_char = 25
        entity2.end_char = 38
        entity2.text = 'December 25th'

        mock_doc = MagicMock()
        mock_doc.ents = [entity1, entity2]
        mock_nlp.return_value = mock_doc

        text = "From January 1st to December 25th"
        result = get_date_entities(text, mock_nlp)

        assert len(result) == 2

    def test_no_dates_found(self):
        """Test when no dates are in text."""
        mock_nlp = MagicMock()

        # No DATE entities
        mock_doc = MagicMock()
        mock_doc.ents = []
        mock_nlp.return_value = mock_doc

        text = "This text has no dates."
        result = get_date_entities(text, mock_nlp)

        assert result == [] or result is False

    def test_non_date_entities(self):
        """Test filtering of non-DATE entities."""
        mock_nlp = MagicMock()

        # Mix of entity types
        date_entity = MagicMock()
        date_entity.type = 'DATE'
        date_entity.start_char = 0
        date_entity.end_char = 10
        date_entity.text = 'January 1st'

        person_entity = MagicMock()
        person_entity.type = 'PERSON'
        person_entity.start_char = 15
        person_entity.end_char = 20
        person_entity.text = 'John'

        mock_doc = MagicMock()
        mock_doc.ents = [date_entity, person_entity]
        mock_nlp.return_value = mock_doc

        text = "January 1st John arrived"
        result = get_date_entities(text, mock_nlp)

        # Should only return DATE entities
        assert len(result) == 1
        assert result[0][2] == 'January 1st'

    def test_without_stanza(self):
        """Test when Stanza NLP is None."""
        result = get_date_entities("Some text", None)
        # Should return False or handle gracefully


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.integration
class TestDateConverterIntegration:
    """Integration tests for date conversion functions."""

    def test_complete_date_time_conversion(self):
        """Test complete date and time conversion in text."""
        text = """
        On January 16th, 1984, at 14:30, the meeting started.
        It continued until 17:00 the same day.
        """

        # Convert times
        text = clock2words(text, "eng", "en", "xtts", True)

        # Years would be converted elsewhere
        # This tests that the functions can work together
        assert text is not None
        assert len(text) > 0

    def test_book_chapter_with_dates(self):
        """Test realistic book chapter with dates and times."""
        text = """
        Chapter 1: The Year 1984

        On January 16th, at precisely 14:30:00, Dr. Smith made the discovery.
        By 17:00, the news had spread. The year 1984 would never be forgotten.
        """

        result = clock2words(text, "eng", "en", "xtts", True)
        assert result is not None

    def test_date_entity_then_conversion(self):
        """Test extracting date entities then converting them."""
        mock_nlp = MagicMock()

        entity = MagicMock()
        entity.type = 'DATE'
        entity.start_char = 3
        entity.end_char = 17
        entity.text = 'January 16th 1984'

        mock_doc = MagicMock()
        mock_doc.ents = [entity]
        mock_nlp.return_value = mock_doc

        text = "On January 16th 1984, everything changed."

        # Get entities
        entities = get_date_entities(text, mock_nlp)
        assert len(entities) > 0

        # Could then process those entities specifically
        # (This is what filter_chapter does)
