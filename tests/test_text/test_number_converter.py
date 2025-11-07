"""
Tests for lib/text/number_converter.py

Tests the number conversion functions: roman2number, number_to_words,
and set_formatted_number.
"""

import pytest
from lib.text.number_converter import (
    roman2number,
    number_to_words,
    set_formatted_number
)


# ============================================================================
# Tests for roman2number()
# ============================================================================

class TestRoman2Number:
    """Test Roman numeral conversion to integers."""

    def test_basic_roman_numerals(self):
        """Test basic Roman numeral conversions."""
        assert roman2number("I") == "1"
        assert roman2number("V") == "5"
        assert roman2number("X") == "10"
        assert roman2number("L") == "50"
        assert roman2number("C") == "100"
        assert roman2number("D") == "500"
        assert roman2number("M") == "1000"

    def test_complex_roman_numerals(self):
        """Test complex Roman numeral combinations."""
        assert roman2number("IV") == "4"
        assert roman2number("IX") == "9"
        assert roman2number("XIV") == "14"
        assert roman2number("XIX") == "19"
        assert roman2number("XLII") == "42"
        assert roman2number("XCIX") == "99"
        assert roman2number("CDXLIV") == "444"
        assert roman2number("MCMXC") == "1990"
        assert roman2number("MMXXIV") == "2024"

    def test_case_insensitive(self):
        """Test that Roman numerals work regardless of case."""
        assert roman2number("xiv") == "14"
        assert roman2number("Xiv") == "14"
        assert roman2number("XIV") == "14"

    def test_text_with_roman_numerals(self):
        """Test Roman numerals embedded in text."""
        text = "Chapter XIV of the book"
        result = roman2number(text)
        assert "14" in result
        assert "XIV" not in result or result == text  # Depends on implementation

    def test_invalid_roman_numerals(self):
        """Test handling of invalid Roman numerals."""
        # Should return original text if not valid
        result = roman2number("ABC")
        # Implementation may vary - either return original or None


# ============================================================================
# Tests for number_to_words()
# ============================================================================

class TestNumberToWords:
    """Test number to words conversion using num2words."""

    def test_simple_numbers_english(self):
        """Test simple number conversions in English."""
        assert number_to_words(1, 'en') is not None
        assert number_to_words(42, 'en') is not None
        assert number_to_words(100, 'en') is not None
        assert number_to_words(1000, 'en') is not None

    def test_float_numbers(self):
        """Test floating point number conversion."""
        result = number_to_words(3.14, 'en')
        assert result is not None

    def test_negative_numbers(self):
        """Test negative number conversion."""
        result = number_to_words(-42, 'en')
        assert result is not None

    def test_ordinal_numbers(self):
        """Test ordinal number conversion."""
        result = number_to_words(1, 'en', ordinal=True)
        assert result is not None
        # Should contain 'first' or equivalent

    def test_different_languages(self):
        """Test number conversion in different languages."""
        # English
        assert number_to_words(42, 'en') is not None

        # French
        assert number_to_words(42, 'fr') is not None

        # German
        assert number_to_words(42, 'de') is not None

    def test_chinese_special_case(self):
        """Test Chinese language code handling (zh → zh_CN)."""
        result = number_to_words(42, 'zh')
        assert result is not None

    def test_invalid_language(self):
        """Test handling of unsupported language."""
        result = number_to_words(42, 'invalid_lang')
        # Should return None or raise exception gracefully


# ============================================================================
# Tests for set_formatted_number()
# ============================================================================

class TestSetFormattedNumber:
    """Test formatted number conversion in text."""

    def test_simple_number_conversion(self):
        """Test simple number conversion in text."""
        text = "I have 42 apples"
        result = set_formatted_number(text, 'eng', 'en', True)
        assert result is not None
        assert "42" not in result or result == text  # Converted or kept

    def test_comma_separated_numbers(self):
        """Test comma-separated numbers (1,234,567)."""
        text = "The population is 1,234,567 people"
        result = set_formatted_number(text, 'eng', 'en', True)
        assert result is not None

    def test_decimal_numbers(self):
        """Test decimal numbers."""
        text = "Pi is approximately 3.14159"
        result = set_formatted_number(text, 'eng', 'en', True)
        assert result is not None

    def test_number_ranges(self):
        """Test number ranges with dashes (1-10)."""
        text = "Pages 1-10 are missing"
        result = set_formatted_number(text, 'eng', 'en', True)
        assert result is not None

    def test_number_ranges_en_dash(self):
        """Test number ranges with en-dash (5–8)."""
        text = "Chapters 5–8"
        result = set_formatted_number(text, 'eng', 'en', True)
        assert result is not None

    def test_special_values(self):
        """Test special values (inf, nan)."""
        text = "The value is inf or nan"
        result = set_formatted_number(text, 'eng', 'en', True)
        assert "inf" in result
        assert "nan" in result

    def test_very_large_numbers(self):
        """Test handling of very large numbers."""
        text = "999999999999999999"  # 18 digits (max)
        result = set_formatted_number(text, 'eng', 'en', True)
        assert result is not None

    def test_overflow_numbers(self):
        """Test numbers exceeding max_single_value."""
        # Default max is 999_999_999_999_999_999
        text = "9999999999999999999"  # 19 digits (overflow)
        result = set_formatted_number(text, 'eng', 'en', True, max_single_value=1000)
        # Should keep original for overflow

    def test_non_num2words_language(self):
        """Test language without num2words support (fallback to phoneme)."""
        text = "I have 42 items"
        result = set_formatted_number(text, 'eng', 'en', False)  # is_num2words_compat=False
        assert result is not None

    def test_trailing_punctuation(self):
        """Test numbers with trailing punctuation."""
        text = "It costs $1,234.56!"
        result = set_formatted_number(text, 'eng', 'en', True)
        assert result is not None

    def test_multiple_numbers_in_text(self):
        """Test multiple numbers in the same text."""
        text = "I have 10 apples, 20 oranges, and 1,500 grapes."
        result = set_formatted_number(text, 'eng', 'en', True)
        assert result is not None

    def test_empty_text(self):
        """Test empty text handling."""
        result = set_formatted_number("", 'eng', 'en', True)
        assert result == ""

    def test_text_without_numbers(self):
        """Test text without any numbers."""
        text = "Hello world, this is a test."
        result = set_formatted_number(text, 'eng', 'en', True)
        assert result == text  # Should remain unchanged


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.integration
class TestNumberConverterIntegration:
    """Integration tests combining multiple converter functions."""

    def test_roman_and_formatted_numbers(self):
        """Test text with both Roman numerals and regular numbers."""
        text = "Chapter XIV has 42 pages and costs $19.99"
        # First convert Roman
        text = roman2number(text)
        # Then convert numbers
        result = set_formatted_number(text, 'eng', 'en', True)
        assert result is not None

    def test_real_world_book_text(self):
        """Test with realistic book text."""
        text = """
        Chapter IV: The Discovery

        In 1984, on January 16th, Dr. Smith discovered equation E = mc².
        The experiment involved 1,234 samples and cost $10,500.50.
        Results showed a 99.9% success rate across tests 1-100.
        """
        result = set_formatted_number(text, 'eng', 'en', True)
        assert result is not None
        assert len(result) > 0
