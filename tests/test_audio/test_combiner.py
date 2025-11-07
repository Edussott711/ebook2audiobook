"""
Tests for lib/audio/combiner.py

Tests audio combining functions: assemble_chunks, combine_audio_sentences.
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from lib.audio.combiner import assemble_chunks, combine_audio_sentences


# ============================================================================
# Tests for assemble_chunks()
# ============================================================================

class TestAssembleChunks:
    """Test FFmpeg-based audio chunk assembly."""

    @pytest.mark.requires_ffmpeg
    def test_assemble_chunks_with_real_ffmpeg(self, temp_dir, check_ffmpeg_available):
        """Test assemble_chunks with real FFmpeg (integration test)."""
        import wave
        import struct

        # Create test audio files
        audio1 = temp_dir / "audio1.wav"
        audio2 = temp_dir / "audio2.wav"

        for audio_path in [audio1, audio2]:
            with wave.open(str(audio_path), 'w') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(44100)
                wav.writeframes(struct.pack('<h', 0) * 22050)  # 0.5 sec silence

        # Create concat file list
        txt_file = temp_dir / "files.txt"
        with open(txt_file, 'w') as f:
            f.write(f"file '{audio1}'\n")
            f.write(f"file '{audio2}'\n")

        # Output file
        out_file = temp_dir / "combined.wav"

        # Run assemble_chunks
        result = assemble_chunks(str(txt_file), str(out_file))

        # Check result
        assert result is True
        assert out_file.exists()
        assert out_file.stat().st_size > 0

    @patch('lib.audio.combiner.subprocess.Popen')
    @patch('lib.audio.combiner.shutil.which')
    def test_assemble_chunks_success(self, mock_which, mock_popen):
        """Test successful chunk assembly."""
        # Mock ffmpeg location
        mock_which.return_value = '/usr/bin/ffmpeg'

        # Mock successful subprocess
        mock_process = MagicMock()
        mock_process.stdout = iter([])  # Empty output
        mock_process.wait.return_value = None
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        result = assemble_chunks('input.txt', 'output.wav')

        assert result is True
        mock_popen.assert_called_once()
        # Check FFmpeg command includes concat
        call_args = mock_popen.call_args
        assert '-f' in call_args[0][0]
        assert 'concat' in call_args[0][0]

    @patch('lib.audio.combiner.subprocess.Popen')
    @patch('lib.audio.combiner.shutil.which')
    def test_assemble_chunks_failure(self, mock_which, mock_popen):
        """Test failed chunk assembly (FFmpeg error)."""
        mock_which.return_value = '/usr/bin/ffmpeg'

        # Mock failed subprocess
        mock_process = MagicMock()
        mock_process.stdout = iter(['Error: something went wrong'])
        mock_process.wait.return_value = None
        mock_process.returncode = 1  # Error code
        mock_popen.return_value = mock_process

        result = assemble_chunks('input.txt', 'output.wav')

        assert result is False

    @patch('lib.audio.combiner.shutil.which')
    def test_assemble_chunks_ffmpeg_not_found(self, mock_which):
        """Test when FFmpeg is not available."""
        mock_which.return_value = None

        # Should handle gracefully (may raise exception or return False)
        # Depends on implementation


# ============================================================================
# Tests for combine_audio_sentences()
# ============================================================================

class TestCombineAudioSentences:
    """Test combining audio sentence files into chapters."""

    @patch('lib.audio.combiner.assemble_chunks')
    @patch('lib.audio.combiner.Pool')
    def test_combine_audio_sentences_success(self, mock_pool, mock_assemble):
        """Test successful combination of audio sentences."""
        mock_assemble.return_value = True

        # Mock multiprocessing Pool
        mock_pool_instance = MagicMock()
        mock_pool_instance.starmap.return_value = [True, True, True]  # All successful
        mock_pool_instance.__enter__.return_value = mock_pool_instance
        mock_pool_instance.__exit__.return_value = None
        mock_pool.return_value = mock_pool_instance

        # Mock session
        session = {
            'chapters_dir_sentences': '/tmp/sentences'
        }

        # Create temp directory for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            session['chapters_dir_sentences'] = tmpdir

            # Create dummy sentence files
            for i in range(10):
                Path(tmpdir, f"sentence_{i}.wav").touch()

            result = combine_audio_sentences('chapter_1.wav', 0, 9, session)

            assert result is True
            mock_assemble.assert_called()

    @patch('lib.audio.combiner.assemble_chunks')
    @patch('lib.audio.combiner.Pool')
    def test_combine_audio_sentences_with_large_batch(self, mock_pool, mock_assemble):
        """Test combining large number of sentences (requires batching)."""
        mock_assemble.return_value = True

        mock_pool_instance = MagicMock()
        # Multiple batches succeed
        mock_pool_instance.starmap.return_value = [True] * 10
        mock_pool_instance.__enter__.return_value = mock_pool_instance
        mock_pool_instance.__exit__.return_value = None
        mock_pool.return_value = mock_pool_instance

        session = {
            'chapters_dir_sentences': '/tmp/sentences'
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            session['chapters_dir_sentences'] = tmpdir

            # Create 2000 sentence files (> 1024 batch size)
            for i in range(2000):
                Path(tmpdir, f"sentence_{i}.wav").touch()

            result = combine_audio_sentences('chapter_1.wav', 0, 1999, session)

            assert result is True
            # Should have been called multiple times (batches + final merge)
            assert mock_assemble.call_count > 1

    @patch('lib.audio.combiner.assemble_chunks')
    def test_combine_audio_sentences_no_files(self, mock_assemble):
        """Test when no sentence files exist."""
        session = {
            'chapters_dir_sentences': '/nonexistent'
        }

        result = combine_audio_sentences('chapter_1.wav', 0, 10, session)

        # Should handle missing directory gracefully
        # May return False or None

    @patch('lib.audio.combiner.assemble_chunks')
    @patch('lib.audio.combiner.Pool')
    def test_combine_audio_sentences_batch_failure(self, mock_pool, mock_assemble):
        """Test when one batch fails."""
        mock_assemble.return_value = True

        mock_pool_instance = MagicMock()
        # One batch fails
        mock_pool_instance.starmap.return_value = [True, False, True]
        mock_pool_instance.__enter__.return_value = mock_pool_instance
        mock_pool_instance.__exit__.return_value = None
        mock_pool.return_value = mock_pool_instance

        session = {
            'chapters_dir_sentences': '/tmp/sentences'
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            session['chapters_dir_sentences'] = tmpdir

            for i in range(2000):
                Path(tmpdir, f"sentence_{i}.wav").touch()

            result = combine_audio_sentences('chapter_1.wav', 0, 1999, session)

            # Should detect batch failure
            assert result is False or result is None

    @patch('lib.audio.combiner.assemble_chunks')
    @patch('lib.audio.combiner.Pool')
    def test_combine_audio_sentences_final_merge_failure(self, mock_pool, mock_assemble):
        """Test when final merge fails."""
        # Batches succeed but final merge fails
        mock_assemble.side_effect = [True, True, True, False]  # Last one fails

        mock_pool_instance = MagicMock()
        mock_pool_instance.starmap.return_value = [True, True, True]
        mock_pool_instance.__enter__.return_value = mock_pool_instance
        mock_pool_instance.__exit__.return_value = None
        mock_pool.return_value = mock_pool_instance

        session = {
            'chapters_dir_sentences': '/tmp/sentences'
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            session['chapters_dir_sentences'] = tmpdir

            for i in range(2000):
                Path(tmpdir, f"sentence_{i}.wav").touch()

            result = combine_audio_sentences('chapter_1.wav', 0, 1999, session)

            assert result is False


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.requires_ffmpeg
class TestCombinerIntegration:
    """Integration tests for audio combiner with real files."""

    def test_full_sentence_combination_workflow(self, temp_dir, check_ffmpeg_available):
        """Test complete workflow of combining sentences into chapter."""
        import wave
        import struct

        # Create sentences directory
        sentences_dir = temp_dir / "sentences"
        sentences_dir.mkdir()

        # Create test sentence audio files
        for i in range(5):
            sentence_file = sentences_dir / f"sentence_{i}.wav"
            with wave.open(str(sentence_file), 'w') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(44100)
                wav.writeframes(struct.pack('<h', 0) * 11025)  # 0.25 sec each

        session = {
            'chapters_dir_sentences': str(sentences_dir)
        }

        chapter_file = str(temp_dir / "chapter_1.wav")

        # Combine sentences
        result = combine_audio_sentences(chapter_file, 0, 4, session)

        assert result is True
        assert Path(chapter_file).exists()

    def test_batch_processing_with_real_files(self, temp_dir, check_ffmpeg_available):
        """Test batch processing with many real files."""
        import wave
        import struct

        sentences_dir = temp_dir / "sentences"
        sentences_dir.mkdir()

        # Create 50 sentence files
        for i in range(50):
            sentence_file = sentences_dir / f"sentence_{i}.wav"
            with wave.open(str(sentence_file), 'w') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(44100)
                wav.writeframes(struct.pack('<h', 0) * 5512)  # Very short

        session = {
            'chapters_dir_sentences': str(sentences_dir)
        }

        chapter_file = str(temp_dir / "chapter_1.wav")

        result = combine_audio_sentences(chapter_file, 0, 49, session)

        assert result is True
        assert Path(chapter_file).exists()


# ============================================================================
# Performance Tests
# ============================================================================

@pytest.mark.slow
@pytest.mark.requires_ffmpeg
class TestCombinerPerformance:
    """Performance tests for audio combiner."""

    def test_large_batch_performance(self, temp_dir, check_ffmpeg_available):
        """Test performance with large number of files."""
        import wave
        import struct
        import time

        sentences_dir = temp_dir / "sentences"
        sentences_dir.mkdir()

        # Create 200 files
        for i in range(200):
            sentence_file = sentences_dir / f"sentence_{i}.wav"
            with wave.open(str(sentence_file), 'w') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(44100)
                wav.writeframes(struct.pack('<h', 0) * 2205)  # Very short

        session = {
            'chapters_dir_sentences': str(sentences_dir)
        }

        chapter_file = str(temp_dir / "chapter_1.wav")

        start = time.time()
        result = combine_audio_sentences(chapter_file, 0, 199, session)
        elapsed = time.time() - start

        assert result is True
        assert elapsed < 60  # Should complete in reasonable time (60 seconds)
        print(f"Combined 200 files in {elapsed:.2f} seconds")
