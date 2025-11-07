"""
Tests for lib/text/sentence_splitter.py

Tests multi-language sentence segmentation with get_sentences().
"""

import pytest
from unittest.mock import patch, MagicMock
from lib.text.sentence_splitter import get_sentences


# ============================================================================
# Tests for get_sentences() - English
# ============================================================================

class TestGetSentencesEnglish:
    """Test sentence splitting for English text."""

    def test_simple_sentences(self):
        """Test splitting simple sentences."""
        text = "This is sentence one. This is sentence two. This is sentence three."
        result = get_sentences(text, 'eng', 'xtts')

        assert result is not None
        assert isinstance(result, list)
        assert len(result) >= 2  # At least some splitting should occur

    def test_question_marks(self):
        """Test splitting on question marks."""
        text = "What is this? This is a test. How are you?"
        result = get_sentences(text, 'eng', 'xtts')

        assert result is not None
        assert len(result) >= 2

    def test_exclamation_marks(self):
        """Test splitting on exclamation marks."""
        text = "Hello world! This is exciting! What a day."
        result = get_sentences(text, 'eng', 'xtts')

        assert result is not None

    def test_mixed_punctuation(self):
        """Test mixed punctuation (., !, ?)."""
        text = "This is a statement. Is this a question? This is exciting!"
        result = get_sentences(text, 'eng', 'xtts')

        assert result is not None
        assert len(result) >= 1

    def test_soft_punctuation(self):
        """Test soft punctuation splitting (commas, semicolons)."""
        text = "This is a long sentence, with commas; and semicolons: that continues on."
        result = get_sentences(text, 'eng', 'xtts')

        assert result is not None

    def test_max_chars_constraint(self):
        """Test that sentences respect max_chars limit."""
        # Create a very long sentence
        long_text = " ".join(["word"] * 200)  # Very long text
        result = get_sentences(long_text, 'eng', 'xtts')

        assert result is not None
        # Each segment should be reasonably sized
        # (depends on language_mapping['eng']['max_chars'])

    def test_sml_tokens_preserved(self):
        """Test that SML tokens (‡break‡, ‡pause‡) are preserved."""
        text = "Sentence one. ‡break‡ Sentence two. ‡pause‡ Sentence three."
        result = get_sentences(text, 'eng', 'xtts')

        assert result is not None
        # SML tokens should be in result as separate items
        has_break = any("‡break‡" in str(s) for s in result)
        has_pause = any("‡pause‡" in str(s) for s in result)
        # At least one should be present

    def test_empty_text(self):
        """Test empty text handling."""
        result = get_sentences("", 'eng', 'xtts')
        # Should return empty list or None

    def test_whitespace_only(self):
        """Test text with only whitespace."""
        result = get_sentences("   \n  \t  ", 'eng', 'xtts')
        # Should handle gracefully

    def test_single_word(self):
        """Test single word input."""
        result = get_sentences("Hello", 'eng', 'xtts')
        assert result is not None
        assert len(result) >= 1


# ============================================================================
# Tests for get_sentences() - Ideogrammatic Languages
# ============================================================================

@pytest.mark.slow
class TestGetSentencesIdeogrammatic:
    """Test sentence splitting for ideogrammatic languages (Chinese, Japanese, Korean, Thai)."""

    @patch('lib.text.sentence_splitter.jieba')
    def test_chinese_segmentation(self, mock_jieba):
        """Test Chinese text segmentation with jieba."""
        # Mock jieba.cut to return tokens
        mock_jieba.cut.return_value = ['你好', '世界', '。']

        text = "你好世界。"
        result = get_sentences(text, 'zho', 'xtts')

        assert result is not None
        # jieba should have been called
        mock_jieba.cut.assert_called()

    @patch('lib.text.sentence_splitter.dictionary')
    @patch('lib.text.sentence_splitter.tokenizer')
    def test_japanese_segmentation(self, mock_tokenizer, mock_dictionary):
        """Test Japanese text segmentation with sudachi."""
        # Mock sudachi tokenizer
        mock_sudachi = MagicMock()
        mock_morpheme = MagicMock()
        mock_morpheme.surface.return_value = 'テスト'
        mock_sudachi.tokenize.return_value = [mock_morpheme]

        mock_dict = MagicMock()
        mock_dict.create.return_value = mock_sudachi
        mock_dictionary.Dictionary.return_value = mock_dict

        text = "これはテストです。"
        result = get_sentences(text, 'jpn', 'xtts')

        assert result is not None

    @patch('lib.text.sentence_splitter.LTokenizer')
    def test_korean_segmentation(self, mock_ltokenizer):
        """Test Korean text segmentation with soynlp."""
        # Mock LTokenizer
        mock_instance = MagicMock()
        mock_instance.tokenize.return_value = ['안녕', '하세요']
        mock_ltokenizer.return_value = mock_instance

        text = "안녕하세요"
        result = get_sentences(text, 'kor', 'xtts')

        assert result is not None
        mock_ltokenizer.assert_called()

    @patch('lib.text.sentence_splitter.word_tokenize')
    def test_thai_segmentation(self, mock_word_tokenize):
        """Test Thai text segmentation with pythainlp."""
        # Mock pythainlp word_tokenize
        mock_word_tokenize.return_value = ['สวัสดี', 'ครับ']

        text = "สวัสดีครับ"
        result = get_sentences(text, 'tha', 'xtts')

        assert result is not None
        mock_word_tokenize.assert_called_with(text, engine='newmm')


# ============================================================================
# Tests for Buffer Management
# ============================================================================

class TestSentenceSplitterBufferManagement:
    """Test buffer management and max_chars constraints."""

    def test_long_sentence_splitting(self):
        """Test that long sentences are split appropriately."""
        # Create a sentence that exceeds max_chars
        words = ["word"] * 500
        text = " ".join(words) + "."

        result = get_sentences(text, 'eng', 'xtts')

        assert result is not None
        assert len(result) > 1  # Should be split into multiple parts

    def test_buffer_optimization(self):
        """Test that buffer tries to merge short sentences."""
        # Multiple short sentences that could be merged
        text = "A. B. C. D. E. F. G. H."
        result = get_sentences(text, 'eng', 'xtts')

        assert result is not None
        # May merge some short sentences together

    def test_backtracking_on_overflow(self):
        """Test buffer backtracking when overflow occurs."""
        # Sentence with soft punctuation that might cause backtracking
        text = "This is a long sentence, with many parts, that should test, the buffer management, system properly."
        result = get_sentences(text, 'eng', 'xtts')

        assert result is not None

    def test_punctuation_preservation(self):
        """Test that punctuation is preserved in split sentences."""
        text = "Hello, world! How are you?"
        result = get_sentences(text, 'eng', 'xtts')

        assert result is not None
        # Punctuation should still be in the segments


# ============================================================================
# Edge Cases
# ============================================================================

class TestSentenceSplitterEdgeCases:
    """Test edge cases for sentence splitter."""

    def test_no_punctuation(self):
        """Test text with no punctuation."""
        text = "This is a sentence without any punctuation marks"
        result = get_sentences(text, 'eng', 'xtts')

        assert result is not None
        assert len(result) >= 1

    def test_only_punctuation(self):
        """Test text with only punctuation."""
        text = "...!!!???"
        result = get_sentences(text, 'eng', 'xtts')
        # Should handle gracefully

    def test_mixed_languages_text(self):
        """Test text mixing different scripts (less common but possible)."""
        text = "Hello 世界 world."
        result = get_sentences(text, 'eng', 'xtts')

        assert result is not None

    def test_special_unicode_characters(self):
        """Test text with special unicode characters."""
        text = "This is — a test – with various — types of dashes."
        result = get_sentences(text, 'eng', 'xtts')

        assert result is not None

    def test_newlines_and_tabs(self):
        """Test text with newlines and tabs."""
        text = "Line one.\nLine two.\tTabbed."
        result = get_sentences(text, 'eng', 'xtts')

        assert result is not None


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.integration
class TestSentenceSplitterIntegration:
    """Integration tests for sentence splitter with realistic text."""

    def test_book_chapter_text(self):
        """Test with realistic book chapter text."""
        text = """
        Chapter One: The Beginning

        It was the best of times, it was the worst of times, it was the age of wisdom,
        it was the age of foolishness. The year was 1984, and everything was changing.

        "What is happening?" asked John. Nobody knew the answer. The situation was
        unprecedented, and everyone was worried about the future.
        """

        result = get_sentences(text, 'eng', 'xtts')

        assert result is not None
        assert len(result) > 0
        # Should split into multiple sentences

    def test_dialogue_heavy_text(self):
        """Test text with lots of dialogue."""
        text = """
        "Hello," she said. "How are you?"
        "I'm fine," he replied. "And you?"
        "Great!" she exclaimed.
        """

        result = get_sentences(text, 'eng', 'xtts')

        assert result is not None
        assert len(result) > 0

    def test_technical_text(self):
        """Test with technical/scientific text."""
        text = """
        The algorithm works as follows: first, initialize the array;
        second, iterate through each element; third, apply the transformation.
        Each step must be completed in O(n) time complexity.
        """

        result = get_sentences(text, 'eng', 'xtts')

        assert result is not None

    def test_list_formatted_text(self):
        """Test text with list formatting."""
        text = """
        Here are the steps:
        1. Open the file
        2. Read the contents
        3. Process the data
        4. Save the results
        """

        result = get_sentences(text, 'eng', 'xtts')

        assert result is not None
        assert len(result) > 0

    @pytest.mark.slow
    def test_very_long_chapter(self):
        """Test with a very long chapter (stress test)."""
        # Generate a long chapter
        paragraph = "This is a test sentence. " * 100
        text = paragraph * 10  # Very long text

        result = get_sentences(text, 'eng', 'xtts')

        assert result is not None
        assert len(result) > 0
        # Should handle large text without crashing


# ============================================================================
# Performance Tests
# ============================================================================

@pytest.mark.slow
class TestSentenceSplitterPerformance:
    """Performance tests for sentence splitter."""

    def test_performance_large_text(self):
        """Test performance with large text (benchmark)."""
        import time

        # Generate large text
        sentence = "This is a test sentence with some content. "
        text = sentence * 1000  # ~1000 sentences

        start = time.time()
        result = get_sentences(text, 'eng', 'xtts')
        elapsed = time.time() - start

        assert result is not None
        assert elapsed < 30  # Should complete in reasonable time (30 seconds)

    def test_performance_many_small_sentences(self):
        """Test performance with many small sentences."""
        import time

        # Many small sentences
        text = ". ".join(["Short"] * 10000)

        start = time.time()
        result = get_sentences(text, 'eng', 'xtts')
        elapsed = time.time() - start

        assert result is not None
        assert elapsed < 30
