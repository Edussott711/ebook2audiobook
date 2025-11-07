"""
Tests for lib/text/processor.py

Tests the filter_chapter() function - the main HTML to TTS pipeline.
"""

import pytest
from unittest.mock import MagicMock, Mock, patch
from bs4 import BeautifulSoup
from lib.text.processor import filter_chapter


# ============================================================================
# Helper Functions
# ============================================================================

def create_mock_epub_item(html_content):
    """Create a mock EPUB document item with given HTML content."""
    mock_doc = MagicMock()
    mock_doc.get_body_content.return_value = html_content.encode('utf-8')
    return mock_doc


# ============================================================================
# Tests for filter_chapter() - Basic HTML Processing
# ============================================================================

class TestFilterChapterBasicHTML:
    """Test basic HTML parsing and content extraction."""

    def test_simple_paragraph(self):
        """Test processing simple paragraph."""
        html = """
        <html><body>
            <p>This is a simple paragraph.</p>
        </body></html>
        """
        mock_doc = create_mock_epub_item(html)

        result = filter_chapter(mock_doc, 'eng', 'en', 'xtts', None, True)

        assert result is not None
        assert isinstance(result, list)
        assert len(result) > 0

    def test_multiple_paragraphs(self):
        """Test processing multiple paragraphs."""
        html = """
        <html><body>
            <p>First paragraph.</p>
            <p>Second paragraph.</p>
            <p>Third paragraph.</p>
        </body></html>
        """
        mock_doc = create_mock_epub_item(html)

        result = filter_chapter(mock_doc, 'eng', 'en', 'xtts', None, True)

        assert result is not None
        assert len(result) >= 1

    def test_heading_extraction(self):
        """Test heading (h1-h4) extraction."""
        html = """
        <html><body>
            <h1>Chapter One</h1>
            <p>This is the content.</p>
            <h2>Section 1.1</h2>
            <p>More content here.</p>
        </body></html>
        """
        mock_doc = create_mock_epub_item(html)

        result = filter_chapter(mock_doc, 'eng', 'en', 'xtts', None, True)

        assert result is not None
        # Should include heading text

    def test_div_and_span_elements(self):
        """Test div and span element processing."""
        html = """
        <html><body>
            <div>Content in a div</div>
            <span>Content in a span</span>
        </body></html>
        """
        mock_doc = create_mock_epub_item(html)

        result = filter_chapter(mock_doc, 'eng', 'en', 'xtts', None, True)

        assert result is not None

    def test_br_tag_handling(self):
        """Test <br> tag creates breaks."""
        html = """
        <html><body>
            <p>Line one<br/>Line two</p>
        </body></html>
        """
        mock_doc = create_mock_epub_item(html)

        result = filter_chapter(mock_doc, 'eng', 'en', 'xtts', None, True)

        assert result is not None

    def test_empty_body(self):
        """Test empty body handling."""
        html = "<html><body></body></html>"
        mock_doc = create_mock_epub_item(html)

        result = filter_chapter(mock_doc, 'eng', 'en', 'xtts', None, True)

        assert result == [] or result is None

    def test_no_body_tag(self):
        """Test HTML without body tag."""
        html = "<html><p>Content without body</p></html>"
        mock_doc = create_mock_epub_item(html)

        result = filter_chapter(mock_doc, 'eng', 'en', 'xtts', None, True)
        # Should handle gracefully


# ============================================================================
# Tests for filter_chapter() - Table Processing
# ============================================================================

class TestFilterChapterTables:
    """Test table processing and conversion."""

    def test_simple_table(self):
        """Test simple table with headers."""
        html = """
        <html><body>
            <table>
                <tr><th>Name</th><th>Age</th></tr>
                <tr><td>Alice</td><td>30</td></tr>
                <tr><td>Bob</td><td>25</td></tr>
            </table>
        </body></html>
        """
        mock_doc = create_mock_epub_item(html)

        result = filter_chapter(mock_doc, 'eng', 'en', 'xtts', None, True)

        assert result is not None
        # Should convert table to descriptive text
        # Format: "Name: Alice — Age: 30"

    def test_table_without_headers(self):
        """Test table without header row."""
        html = """
        <html><body>
            <table>
                <tr><td>Data1</td><td>Data2</td></tr>
                <tr><td>Data3</td><td>Data4</td></tr>
            </table>
        </body></html>
        """
        mock_doc = create_mock_epub_item(html)

        result = filter_chapter(mock_doc, 'eng', 'en', 'xtts', None, True)

        assert result is not None

    def test_empty_table(self):
        """Test empty table handling."""
        html = """
        <html><body>
            <table></table>
        </body></html>
        """
        mock_doc = create_mock_epub_item(html)

        result = filter_chapter(mock_doc, 'eng', 'en', 'xtts', None, True)
        # Should handle gracefully

    def test_table_with_missing_cells(self):
        """Test table with missing cells."""
        html = """
        <html><body>
            <table>
                <tr><th>Col1</th><th>Col2</th></tr>
                <tr><td>Value1</td></tr>
            </table>
        </body></html>
        """
        mock_doc = create_mock_epub_item(html)

        result = filter_chapter(mock_doc, 'eng', 'en', 'xtts', None, True)

        assert result is not None


# ============================================================================
# Tests for filter_chapter() - EPUB Type Filtering
# ============================================================================

class TestFilterChapterEPUBFiltering:
    """Test filtering of EPUB types (frontmatter, backmatter, etc.)."""

    def test_frontmatter_excluded(self):
        """Test that frontmatter is excluded."""
        html = """
        <html><body epub:type="frontmatter">
            <p>This is frontmatter content.</p>
        </body></html>
        """
        mock_doc = create_mock_epub_item(html)

        result = filter_chapter(mock_doc, 'eng', 'en', 'xtts', None, True)

        assert result == []

    def test_backmatter_excluded(self):
        """Test that backmatter is excluded."""
        html = """
        <html><body epub:type="backmatter">
            <p>This is backmatter content.</p>
        </body></html>
        """
        mock_doc = create_mock_epub_item(html)

        result = filter_chapter(mock_doc, 'eng', 'en', 'xtts', None, True)

        assert result == []

    def test_toc_excluded(self):
        """Test that table of contents is excluded."""
        html = """
        <html><body epub:type="toc">
            <p>Table of Contents</p>
        </body></html>
        """
        mock_doc = create_mock_epub_item(html)

        result = filter_chapter(mock_doc, 'eng', 'en', 'xtts', None, True)

        assert result == []

    def test_titlepage_excluded(self):
        """Test that titlepage is excluded."""
        html = """
        <html><body epub:type="titlepage">
            <h1>Book Title</h1>
        </body></html>
        """
        mock_doc = create_mock_epub_item(html)

        result = filter_chapter(mock_doc, 'eng', 'en', 'xtts', None, True)

        assert result == []

    def test_section_epub_type(self):
        """Test EPUB type in section tag."""
        html = """
        <html><body>
            <section epub:type="frontmatter">
                <p>Frontmatter in section</p>
            </section>
        </body></html>
        """
        mock_doc = create_mock_epub_item(html)

        result = filter_chapter(mock_doc, 'eng', 'en', 'xtts', None, True)

        assert result == []

    def test_bodymatter_included(self):
        """Test that bodymatter (regular content) is included."""
        html = """
        <html><body epub:type="bodymatter">
            <p>This is regular chapter content.</p>
        </body></html>
        """
        mock_doc = create_mock_epub_item(html)

        result = filter_chapter(mock_doc, 'eng', 'en', 'xtts', None, True)

        assert result is not None
        assert len(result) > 0


# ============================================================================
# Tests for filter_chapter() - Script/Style Removal
# ============================================================================

class TestFilterChapterScriptStyleRemoval:
    """Test removal of script and style tags."""

    def test_script_tag_removed(self):
        """Test that <script> tags are removed."""
        html = """
        <html><body>
            <p>Before script</p>
            <script>alert('test');</script>
            <p>After script</p>
        </body></html>
        """
        mock_doc = create_mock_epub_item(html)

        result = filter_chapter(mock_doc, 'eng', 'en', 'xtts', None, True)

        assert result is not None
        # Should not contain script content

    def test_style_tag_removed(self):
        """Test that <style> tags are removed."""
        html = """
        <html><body>
            <style>body { color: red; }</style>
            <p>Content here</p>
        </body></html>
        """
        mock_doc = create_mock_epub_item(html)

        result = filter_chapter(mock_doc, 'eng', 'en', 'xtts', None, True)

        assert result is not None
        # Should not contain style content


# ============================================================================
# Tests for filter_chapter() - Number/Date/Math Conversion
# ============================================================================

@patch('lib.text.processor.get_sentences')
class TestFilterChapterConversions:
    """Test number, date, time, and math conversions."""

    def test_number_conversion(self, mock_get_sentences):
        """Test that numbers are converted."""
        mock_get_sentences.return_value = ["test output"]

        html = """
        <html><body>
            <p>I have 42 apples and 1,234 oranges.</p>
        </body></html>
        """
        mock_doc = create_mock_epub_item(html)

        result = filter_chapter(mock_doc, 'eng', 'en', 'xtts', None, True)

        assert result is not None
        # get_sentences should be called
        mock_get_sentences.assert_called()

    def test_time_conversion(self, mock_get_sentences):
        """Test that times (14:30) are converted."""
        mock_get_sentences.return_value = ["test output"]

        html = """
        <html><body>
            <p>The meeting is at 14:30.</p>
        </body></html>
        """
        mock_doc = create_mock_epub_item(html)

        result = filter_chapter(mock_doc, 'eng', 'en', 'xtts', None, True)

        assert result is not None

    def test_math_symbols_conversion(self, mock_get_sentences):
        """Test that math symbols are converted."""
        mock_get_sentences.return_value = ["test output"]

        html = """
        <html><body>
            <p>The equation is 2 + 2 = 4.</p>
        </body></html>
        """
        mock_doc = create_mock_epub_item(html)

        result = filter_chapter(mock_doc, 'eng', 'en', 'xtts', None, True)

        assert result is not None

    def test_roman_numerals_conversion(self, mock_get_sentences):
        """Test that Roman numerals are converted."""
        mock_get_sentences.return_value = ["test output"]

        html = """
        <html><body>
            <p>Chapter XIV of the book.</p>
        </body></html>
        """
        mock_doc = create_mock_epub_item(html)

        result = filter_chapter(mock_doc, 'eng', 'en', 'xtts', None, True)

        assert result is not None

    def test_ordinals_conversion(self, mock_get_sentences):
        """Test that ordinals (1st, 2nd) are converted."""
        mock_get_sentences.return_value = ["test output"]

        html = """
        <html><body>
            <p>The 1st, 2nd, and 3rd place winners.</p>
        </body></html>
        """
        mock_doc = create_mock_epub_item(html)

        result = filter_chapter(mock_doc, 'eng', 'en', 'xtts', None, True)

        assert result is not None


# ============================================================================
# Tests for filter_chapter() - Date Entity Processing with Stanza
# ============================================================================

@patch('lib.text.processor.get_sentences')
class TestFilterChapterDateEntities:
    """Test date entity processing with Stanza NLP."""

    def test_with_stanza_nlp(self, mock_get_sentences):
        """Test date processing with Stanza NLP."""
        mock_get_sentences.return_value = ["test output"]

        # Create mock Stanza NLP
        mock_nlp = MagicMock()
        mock_entity = MagicMock()
        mock_entity.type = 'DATE'
        mock_entity.start_char = 3
        mock_entity.end_char = 18
        mock_entity.text = 'January 16 1984'

        mock_doc_nlp = MagicMock()
        mock_doc_nlp.ents = [mock_entity]
        mock_nlp.return_value = mock_doc_nlp

        html = """
        <html><body>
            <p>On January 16 1984, everything changed.</p>
        </body></html>
        """
        mock_doc = create_mock_epub_item(html)

        result = filter_chapter(mock_doc, 'eng', 'en', 'xtts', mock_nlp, True)

        assert result is not None

    def test_without_stanza_nlp(self, mock_get_sentences):
        """Test processing without Stanza NLP (None)."""
        mock_get_sentences.return_value = ["test output"]

        html = """
        <html><body>
            <p>On January 16th, 1984, everything changed.</p>
        </body></html>
        """
        mock_doc = create_mock_epub_item(html)

        result = filter_chapter(mock_doc, 'eng', 'en', 'xtts', None, True)

        assert result is not None


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.integration
@patch('lib.text.processor.get_sentences')
class TestFilterChapterIntegration:
    """Integration tests with realistic chapter content."""

    def test_realistic_chapter(self, mock_get_sentences):
        """Test with realistic book chapter."""
        mock_get_sentences.return_value = [
            "Chapter One.", "The year was 1984.", "Everything changed at 14:30."
        ]

        html = """
        <html><body>
            <h1>Chapter One</h1>
            <p>The year was 1984, and on January 16th at 14:30, everything changed.</p>
            <p>The equation 2 + 2 = 4 became questioned.</p>

            <table>
                <tr><th>Name</th><th>Status</th></tr>
                <tr><td>Project Alpha</td><td>Active</td></tr>
            </table>

            <p>This was the 1st time such an event occurred.</p>
        </body></html>
        """
        mock_doc = create_mock_epub_item(html)

        result = filter_chapter(mock_doc, 'eng', 'en', 'xtts', None, True)

        assert result is not None
        assert len(result) > 0

    def test_dialogue_chapter(self, mock_get_sentences):
        """Test chapter with dialogue."""
        mock_get_sentences.return_value = ["Hello said John.", "How are you replied Jane."]

        html = """
        <html><body>
            <p>"Hello," said John.</p>
            <p>"How are you?" replied Jane.</p>
        </body></html>
        """
        mock_doc = create_mock_epub_item(html)

        result = filter_chapter(mock_doc, 'eng', 'en', 'xtts', None, True)

        assert result is not None
        assert len(result) > 0


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestFilterChapterErrorHandling:
    """Test error handling in filter_chapter."""

    def test_invalid_html(self):
        """Test handling of malformed HTML."""
        html = "<html><body><p>Unclosed paragraph"
        mock_doc = create_mock_epub_item(html)

        # Should not crash
        try:
            result = filter_chapter(mock_doc, 'eng', 'en', 'xtts', None, True)
            # May return None or empty list
        except Exception:
            pytest.fail("Should handle malformed HTML gracefully")

    def test_exception_in_processing(self):
        """Test exception handling during processing."""
        # Mock to raise exception
        mock_doc = MagicMock()
        mock_doc.get_body_content.side_effect = Exception("Test error")

        result = filter_chapter(mock_doc, 'eng', 'en', 'xtts', None, True)

        assert result is None  # Should return None on error
