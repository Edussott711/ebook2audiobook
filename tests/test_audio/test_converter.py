"""
Tests for lib/audio/converter.py

Tests TTS orchestration: convert_chapters2audio.
"""

import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
from lib.audio.converter import convert_chapters2audio


# ============================================================================
# Tests for convert_chapters2audio()
# ============================================================================

class TestConvertChapters2Audio:
    """Test TTS conversion orchestration."""

    @patch('lib.audio.converter.context')
    @patch('lib.audio.converter.TTSManager')
    @patch('lib.audio.converter.combine_audio_sentences')
    def test_convert_chapters_success(self, mock_combine, mock_tts_manager, mock_context):
        """Test successful chapter conversion."""
        # Mock session
        session = {
            'cancellation_requested': False,
            'tts_engine': 'xtts',
            'chapters': [
                ["Sentence 1.", "Sentence 2."],
                ["Sentence 3.", "Sentence 4."]
            ],
            'chapters_dir': '/tmp/chapters',
            'chapters_dir_sentences': '/tmp/sentences'
        }
        mock_context.get_session.return_value = session

        # Mock TTSManager
        mock_tts = MagicMock()
        mock_tts.convert_sentence2audio.return_value = True
        mock_tts_manager.return_value = mock_tts

        # Mock combine_audio_sentences
        mock_combine.return_value = True

        # Create temp directories
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            chapters_dir = Path(tmpdir) / "chapters"
            sentences_dir = Path(tmpdir) / "sentences"
            chapters_dir.mkdir()
            sentences_dir.mkdir()

            session['chapters_dir'] = str(chapters_dir)
            session['chapters_dir_sentences'] = str(sentences_dir)

            result = convert_chapters2audio('test-session')

            assert result is True
            # TTS should have been called for each sentence
            assert mock_tts.convert_sentence2audio.call_count >= 2
            # Combine should have been called for each chapter
            assert mock_combine.call_count == 2

    @patch('lib.audio.converter.context')
    def test_convert_chapters_cancellation(self, mock_context):
        """Test cancellation handling."""
        session = {
            'cancellation_requested': True,
            'tts_engine': 'xtts',
            'chapters': [],
            'chapters_dir': '/tmp/chapters',
            'chapters_dir_sentences': '/tmp/sentences'
        }
        mock_context.get_session.return_value = session

        result = convert_chapters2audio('test-session')

        assert result is False

    @patch('lib.audio.converter.context')
    @patch('lib.audio.converter.TTSManager')
    def test_convert_chapters_tts_manager_failure(self, mock_tts_manager, mock_context):
        """Test when TTSManager cannot be initialized."""
        session = {
            'cancellation_requested': False,
            'tts_engine': 'xtts',
            'chapters': [],
            'chapters_dir': '/tmp/chapters',
            'chapters_dir_sentences': '/tmp/sentences'
        }
        mock_context.get_session.return_value = session

        # TTSManager returns falsy value
        mock_tts_manager.return_value = None

        result = convert_chapters2audio('test-session')

        assert result is False

    @patch('lib.audio.converter.context')
    @patch('lib.audio.converter.TTSManager')
    def test_convert_chapters_no_chapters(self, mock_tts_manager, mock_context):
        """Test when no chapters are found."""
        session = {
            'cancellation_requested': False,
            'tts_engine': 'xtts',
            'chapters': [],  # No chapters
            'chapters_dir': '/tmp/chapters',
            'chapters_dir_sentences': '/tmp/sentences'
        }
        mock_context.get_session.return_value = session

        mock_tts = MagicMock()
        mock_tts_manager.return_value = mock_tts

        result = convert_chapters2audio('test-session')

        assert result is False

    @patch('lib.audio.converter.context')
    @patch('lib.audio.converter.TTSManager')
    @patch('lib.audio.converter.combine_audio_sentences')
    def test_convert_chapters_no_sentences(self, mock_combine, mock_tts_manager, mock_context):
        """Test when no actual sentences are found (only SML tokens)."""
        session = {
            'cancellation_requested': False,
            'tts_engine': 'xtts',
            'chapters': [
                ["‡break‡", "‡pause‡"]  # Only SML tokens
            ],
            'chapters_dir': '/tmp/chapters',
            'chapters_dir_sentences': '/tmp/sentences'
        }
        mock_context.get_session.return_value = session

        mock_tts = MagicMock()
        mock_tts_manager.return_value = mock_tts

        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            chapters_dir = Path(tmpdir) / "chapters"
            sentences_dir = Path(tmpdir) / "sentences"
            chapters_dir.mkdir()
            sentences_dir.mkdir()

            session['chapters_dir'] = str(chapters_dir)
            session['chapters_dir_sentences'] = str(sentences_dir)

            result = convert_chapters2audio('test-session')

            assert result is False  # No real sentences

    @patch('lib.audio.converter.context')
    @patch('lib.audio.converter.TTSManager')
    @patch('lib.audio.converter.combine_audio_sentences')
    def test_convert_chapters_tts_failure(self, mock_combine, mock_tts_manager, mock_context):
        """Test when TTS conversion fails for a sentence."""
        session = {
            'cancellation_requested': False,
            'tts_engine': 'xtts',
            'chapters': [
                ["Sentence 1.", "Sentence 2."]
            ],
            'chapters_dir': '/tmp/chapters',
            'chapters_dir_sentences': '/tmp/sentences'
        }
        mock_context.get_session.return_value = session

        mock_tts = MagicMock()
        # First sentence succeeds, second fails
        mock_tts.convert_sentence2audio.side_effect = [True, False]
        mock_tts_manager.return_value = mock_tts

        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            chapters_dir = Path(tmpdir) / "chapters"
            sentences_dir = Path(tmpdir) / "sentences"
            chapters_dir.mkdir()
            sentences_dir.mkdir()

            session['chapters_dir'] = str(chapters_dir)
            session['chapters_dir_sentences'] = str(sentences_dir)

            result = convert_chapters2audio('test-session')

            assert result is False

    @patch('lib.audio.converter.context')
    @patch('lib.audio.converter.TTSManager')
    @patch('lib.audio.converter.combine_audio_sentences')
    def test_convert_chapters_combine_failure(self, mock_combine, mock_tts_manager, mock_context):
        """Test when combining audio sentences fails."""
        session = {
            'cancellation_requested': False,
            'tts_engine': 'xtts',
            'chapters': [
                ["Sentence 1.", "Sentence 2."]
            ],
            'chapters_dir': '/tmp/chapters',
            'chapters_dir_sentences': '/tmp/sentences'
        }
        mock_context.get_session.return_value = session

        mock_tts = MagicMock()
        mock_tts.convert_sentence2audio.return_value = True
        mock_tts_manager.return_value = mock_tts

        # Combine fails
        mock_combine.return_value = False

        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            chapters_dir = Path(tmpdir) / "chapters"
            sentences_dir = Path(tmpdir) / "sentences"
            chapters_dir.mkdir()
            sentences_dir.mkdir()

            session['chapters_dir'] = str(chapters_dir)
            session['chapters_dir_sentences'] = str(sentences_dir)

            result = convert_chapters2audio('test-session')

            assert result is False


# ============================================================================
# Tests for Resume Functionality
# ============================================================================

class TestConvertChaptersResume:
    """Test resume functionality for interrupted conversions."""

    @patch('lib.audio.converter.context')
    @patch('lib.audio.converter.TTSManager')
    @patch('lib.audio.converter.combine_audio_sentences')
    def test_resume_from_existing_chapters(self, mock_combine, mock_tts_manager, mock_context):
        """Test resuming from existing chapter files."""
        session = {
            'cancellation_requested': False,
            'tts_engine': 'xtts',
            'chapters': [
                ["Sentence 1.", "Sentence 2."],
                ["Sentence 3.", "Sentence 4."],
                ["Sentence 5.", "Sentence 6."]
            ],
            'chapters_dir': '/tmp/chapters',
            'chapters_dir_sentences': '/tmp/sentences'
        }
        mock_context.get_session.return_value = session

        mock_tts = MagicMock()
        mock_tts.convert_sentence2audio.return_value = True
        mock_tts_manager.return_value = mock_tts
        mock_combine.return_value = True

        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            chapters_dir = Path(tmpdir) / "chapters"
            sentences_dir = Path(tmpdir) / "sentences"
            chapters_dir.mkdir()
            sentences_dir.mkdir()

            # Create existing chapter files (simulating resume)
            (chapters_dir / "chapter_1.wav").touch()
            (chapters_dir / "chapter_2.wav").touch()

            session['chapters_dir'] = str(chapters_dir)
            session['chapters_dir_sentences'] = str(sentences_dir)

            result = convert_chapters2audio('test-session')

            assert result is True
            # Should resume from chapter 2 (or 3), not start from beginning

    @patch('lib.audio.converter.context')
    @patch('lib.audio.converter.TTSManager')
    @patch('lib.audio.converter.combine_audio_sentences')
    def test_resume_from_existing_sentences(self, mock_combine, mock_tts_manager, mock_context):
        """Test resuming from existing sentence files."""
        session = {
            'cancellation_requested': False,
            'tts_engine': 'xtts',
            'chapters': [
                ["Sentence 1.", "Sentence 2.", "Sentence 3."]
            ],
            'chapters_dir': '/tmp/chapters',
            'chapters_dir_sentences': '/tmp/sentences'
        }
        mock_context.get_session.return_value = session

        mock_tts = MagicMock()
        mock_tts.convert_sentence2audio.return_value = True
        mock_tts_manager.return_value = mock_tts
        mock_combine.return_value = True

        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            chapters_dir = Path(tmpdir) / "chapters"
            sentences_dir = Path(tmpdir) / "sentences"
            chapters_dir.mkdir()
            sentences_dir.mkdir()

            # Create existing sentence files
            (sentences_dir / "sentence_0.wav").touch()
            (sentences_dir / "sentence_1.wav").touch()

            session['chapters_dir'] = str(chapters_dir)
            session['chapters_dir_sentences'] = str(sentences_dir)

            result = convert_chapters2audio('test-session')

            assert result is True
            # Should skip already processed sentences


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.integration
class TestConvertChaptersIntegration:
    """Integration tests for chapter conversion."""

    @patch('lib.audio.converter.context')
    @patch('lib.audio.converter.TTSManager')
    @patch('lib.audio.converter.combine_audio_sentences')
    def test_full_conversion_workflow(self, mock_combine, mock_tts_manager, mock_context):
        """Test complete conversion workflow with multiple chapters."""
        session = {
            'cancellation_requested': False,
            'tts_engine': 'xtts',
            'chapters': [
                ["Chapter 1, Sentence 1.", "Chapter 1, Sentence 2.", "‡break‡"],
                ["Chapter 2, Sentence 1.", "‡pause‡", "Chapter 2, Sentence 2."],
                ["Chapter 3, Sentence 1."]
            ],
            'chapters_dir': '/tmp/chapters',
            'chapters_dir_sentences': '/tmp/sentences'
        }
        mock_context.get_session.return_value = session

        mock_tts = MagicMock()
        mock_tts.convert_sentence2audio.return_value = True
        mock_tts_manager.return_value = mock_tts
        mock_combine.return_value = True

        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            chapters_dir = Path(tmpdir) / "chapters"
            sentences_dir = Path(tmpdir) / "sentences"
            chapters_dir.mkdir()
            sentences_dir.mkdir()

            session['chapters_dir'] = str(chapters_dir)
            session['chapters_dir_sentences'] = str(sentences_dir)

            result = convert_chapters2audio('test-session')

            assert result is True
            # Should have processed all real sentences (not SML tokens)
            # 2 + 2 + 1 = 5 real sentences
            assert mock_tts.convert_sentence2audio.call_count >= 5


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestConvertChaptersErrorHandling:
    """Test error handling in convert_chapters2audio."""

    @patch('lib.audio.converter.context')
    @patch('lib.audio.converter.TTSManager')
    def test_exception_during_conversion(self, mock_tts_manager, mock_context):
        """Test exception handling during conversion."""
        session = {
            'cancellation_requested': False,
            'tts_engine': 'xtts',
            'chapters': [["Test sentence."]],
            'chapters_dir': '/tmp/chapters',
            'chapters_dir_sentences': '/tmp/sentences'
        }
        mock_context.get_session.return_value = session

        mock_tts = MagicMock()
        mock_tts.convert_sentence2audio.side_effect = Exception("TTS error")
        mock_tts_manager.return_value = mock_tts

        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            chapters_dir = Path(tmpdir) / "chapters"
            sentences_dir = Path(tmpdir) / "sentences"
            chapters_dir.mkdir()
            sentences_dir.mkdir()

            session['chapters_dir'] = str(chapters_dir)
            session['chapters_dir_sentences'] = str(sentences_dir)

            result = convert_chapters2audio('test-session')

            assert result is False

    @patch('lib.audio.converter.context')
    def test_invalid_session_id(self, mock_context):
        """Test handling of invalid session ID."""
        mock_context.get_session.side_effect = Exception("Session not found")

        result = convert_chapters2audio('invalid-session')

        assert result is False
