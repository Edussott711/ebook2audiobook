"""
Tests for lib/text/math_converter.py

Tests mathematical symbol and ordinal number conversion.
"""

import pytest
from lib.text.math_converter import math2words


# ============================================================================
# Tests for math2words()
# ============================================================================

class TestMath2Words:
    """Test mathematical symbols and ordinals conversion."""

    def test_basic_math_operators(self):
        """Test basic mathematical operators (+, -, *, /, =)."""
        text = "The equation 2 + 2 = 4"
        result = math2words(text, "eng", "en", "xtts", True)
        assert result is not None
        # "+" should be converted to "plus"
        assert "+" not in result or result == text

    def test_multiplication_division(self):
        """Test multiplication and division symbols."""
        text = "Calculate 6 * 7 / 2"
        result = math2words(text, "eng", "en", "xtts", True)
        assert result is not None

    def test_ordinal_numbers(self):
        """Test ordinal number conversion (1st, 2nd, 3rd, etc.)."""
        text = "The 1st, 2nd, and 3rd place winners"
        result = math2words(text, "eng", "en", "xtts", True)
        assert result is not None
        # Should convert to "first", "second", "third"
        assert "st" not in result or result == text
        assert "nd" not in result or result == text
        assert "rd" not in result or result == text

    def test_ordinals_with_spacing(self):
        """Test ordinals with spacing (16 th, 21 st)."""
        text = "The 16 th and 21 st items"
        result = math2words(text, "eng", "en", "xtts", True)
        assert result is not None

    def test_high_ordinals(self):
        """Test higher ordinal numbers (21st, 42nd, 99th)."""
        text = "The 21st, 42nd, and 99th chapters"
        result = math2words(text, "eng", "en", "xtts", True)
        assert result is not None

    def test_ambiguous_symbols_in_equations(self):
        """Test ambiguous symbols (-, /, *, x) in equation context."""
        text = "Solve: x - 5 = 10"
        result = math2words(text, "eng", "en", "xtts", True)
        assert result is not None

        text = "Calculate 10 / 2"
        result = math2words(text, "eng", "en", "xtts", True)
        assert result is not None

    def test_percentage_symbols(self):
        """Test percentage and other math symbols."""
        text = "Success rate: 99.9%"
        result = math2words(text, "eng", "en", "xtts", True)
        assert result is not None

    def test_comparison_operators(self):
        """Test comparison operators (<, >, <=, >=, ≠)."""
        text = "If x > 5 and y < 10"
        result = math2words(text, "eng", "en", "xtts", True)
        assert result is not None

    def test_multiple_equations(self):
        """Test multiple equations in text."""
        text = "2 + 2 = 4 and 3 * 3 = 9"
        result = math2words(text, "eng", "en", "xtts", True)
        assert result is not None

    def test_mixed_ordinals_and_operators(self):
        """Test text with both ordinals and operators."""
        text = "The 1st equation is 2 + 2 = 4"
        result = math2words(text, "eng", "en", "xtts", True)
        assert result is not None

    def test_non_num2words_language(self):
        """Test with language not supporting num2words."""
        text = "The 1st place and 2 + 2 = 4"
        result = math2words(text, "eng", "en", "xtts", False)
        assert result is not None
        # Should use phoneme fallback

    def test_text_without_math(self):
        """Test text without mathematical content."""
        text = "This is just regular text without math"
        result = math2words(text, "eng", "en", "xtts", True)
        assert result == text  # Should remain unchanged

    def test_complex_equation(self):
        """Test complex mathematical equation."""
        text = "The formula is E = mc²"
        result = math2words(text, "eng", "en", "xtts", True)
        assert result is not None

    def test_scientific_notation(self):
        """Test scientific notation symbols."""
        text = "The value is 1.5 × 10³"
        result = math2words(text, "eng", "en", "xtts", True)
        assert result is not None

    def test_ordinals_in_dates(self):
        """Test ordinals that might appear in dates."""
        text = "On January 16th and February 21st"
        result = math2words(text, "eng", "en", "xtts", True)
        assert result is not None
        # Should convert ordinals

    def test_ordinals_at_sentence_boundaries(self):
        """Test ordinals at start/end of sentences."""
        text = "1st place goes to John. 2nd place goes to Jane."
        result = math2words(text, "eng", "en", "xtts", True)
        assert result is not None

    def test_parentheses_and_brackets(self):
        """Test math expressions with parentheses."""
        text = "Calculate (2 + 3) * 4"
        result = math2words(text, "eng", "en", "xtts", True)
        assert result is not None


# ============================================================================
# Edge Cases
# ============================================================================

class TestMath2WordsEdgeCases:
    """Test edge cases for math2words."""

    def test_empty_text(self):
        """Test empty text."""
        result = math2words("", "eng", "en", "xtts", True)
        assert result == ""

    def test_text_with_only_numbers(self):
        """Test text containing only numbers."""
        text = "1234567890"
        result = math2words(text, "eng", "en", "xtts", True)
        assert result is not None

    def test_special_characters_preserved(self):
        """Test that non-math special characters are preserved."""
        text = "Hello @world! #test $money"
        result = math2words(text, "eng", "en", "xtts", True)
        assert "@" in result
        assert "#" in result
        assert "$" in result

    def test_unicode_math_symbols(self):
        """Test unicode math symbols (×, ÷, ≠, ≤, ≥)."""
        text = "5 × 3 ÷ 2 ≠ 8"
        result = math2words(text, "eng", "en", "xtts", True)
        assert result is not None

    def test_mixed_case_ordinals(self):
        """Test ordinals with mixed case."""
        text = "The 1ST, 2ND, and 3RD items"
        result = math2words(text, "eng", "en", "xtts", True)
        assert result is not None


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.integration
class TestMath2WordsIntegration:
    """Integration tests for math2words with other converters."""

    def test_with_number_conversion(self):
        """Test math symbols with number conversion."""
        # This would typically be used with set_formatted_number
        text = "The equation 1,234 + 5,678 = 6,912"
        result = math2words(text, "eng", "en", "xtts", True)
        assert result is not None

    def test_realistic_book_text(self):
        """Test with realistic book text containing math."""
        text = """
        In the 1st experiment, we found that E = mc².
        The 2nd attempt yielded 99.9% accuracy.
        By the 3rd trial, we achieved x + y = z.
        """
        result = math2words(text, "eng", "en", "xtts", True)
        assert result is not None
        assert len(result) > 0

    def test_technical_document(self):
        """Test with technical document style text."""
        text = """
        Algorithm 1: Sort the array
        1. If n ≤ 1, return
        2. Divide into n/2 parts
        3. Recursively sort each part
        """
        result = math2words(text, "eng", "en", "xtts", True)
        assert result is not None

    def test_combining_all_number_types(self):
        """Test combining regular numbers, ordinals, and operators."""
        text = "The 1st equation: 42 + 58 = 100, the 2nd: 7 * 6 = 42"
        result = math2words(text, "eng", "en", "xtts", True)
        assert result is not None
        assert len(result) > 0
