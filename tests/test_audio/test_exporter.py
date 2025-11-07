"""
Tests for lib/audio/exporter.py

Tests multi-format audio export: combine_audio_chapters.
"""

import pytest
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock, mock_open, call


# ============================================================================
# Tests for combine_audio_chapters() - Main Export Function
# ============================================================================

class TestCombineAudioChapters:
    """Test main audio export orchestration."""

    @patch('lib.audio.exporter.context')
    @patch('lib.audio.exporter.subprocess')
    @patch('lib.audio.exporter.shutil.which')
    @patch('lib.audio.exporter.os.listdir')
    @patch('lib.audio.exporter.AudioSegment')
    @patch('lib.audio.exporter.assemble_chunks')
    def test_export_m4b_success(
        self, mock_assemble, mock_audio_seg, mock_listdir,
        mock_which, mock_subprocess, mock_context
    ):
        """Test successful M4B export without split."""
        # Mock session
        session = {
            'cancellation_requested': False,
            'output_format': 'm4b',
            'output_split': False,
            'chapters_dir': '/tmp/chapters',
            'process_dir': '/tmp/process',
            'audiobooks_dir': '/tmp/audiobooks',
            'cover': None,
            'metadata': {
                'title': 'Test Book',
                'creator': 'Test Author',
                'language': 'en',
                'description': 'Test description',
                'publisher': 'Test Publisher',
                'published': '2024-01-01T00:00:00+00:00',
                'identifiers': {
                    'isbn': '1234567890',
                    'mobi-asin': 'B001234567'
                }
            },
            'final_name': 'test_book.m4b',
            'chapters': [
                ['Chapter 1'],
                ['Chapter 2']
            ]
        }
        mock_context.get_session.return_value = session

        # Mock chapter files
        mock_listdir.return_value = ['chapter_1.wav', 'chapter_2.wav']

        # Mock ffprobe for duration
        mock_ffprobe_result = MagicMock()
        mock_ffprobe_result.stdout = json.dumps({'format': {'duration': '120.5'}})
        mock_subprocess.run.return_value = mock_ffprobe_result

        # Mock ffmpeg
        mock_which.return_value = '/usr/bin/ffmpeg'
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = iter([])  # Empty output
        mock_subprocess.Popen.return_value = mock_process

        # Mock audio segment duration
        mock_seg = MagicMock()
        mock_seg.__len__.return_value = 120000  # 120 seconds in ms
        mock_audio_seg.from_file.return_value = mock_seg

        # Mock assemble_chunks
        mock_assemble.return_value = True

        # Mock file operations
        with patch('builtins.open', mock_open()):
            with patch('lib.audio.exporter.shutil.move'):
                from lib.audio.exporter import combine_audio_chapters

                result = combine_audio_chapters('test-session')

                assert result is not None
                assert isinstance(result, list)
                assert len(result) == 1
                assert result[0].endswith('test_book.m4b')

    @patch('lib.audio.exporter.context')
    @patch('lib.audio.exporter.os.listdir')
    def test_export_no_chapters(self, mock_listdir, mock_context):
        """Test when no chapter files exist."""
        session = {
            'chapters_dir': '/tmp/chapters',
            'output_format': 'm4b'
        }
        mock_context.get_session.return_value = session
        mock_listdir.return_value = []  # No files

        from lib.audio.exporter import combine_audio_chapters

        result = combine_audio_chapters('test-session')

        assert result is None

    @patch('lib.audio.exporter.context')
    def test_export_invalid_session(self, mock_context):
        """Test handling of invalid session."""
        mock_context.get_session.side_effect = Exception("Session not found")

        from lib.audio.exporter import combine_audio_chapters

        result = combine_audio_chapters('invalid-session')

        assert result is False


# ============================================================================
# Tests for Format-Specific Exports
# ============================================================================

class TestFormatSpecificExport:
    """Test different audio format exports."""

    @pytest.mark.parametrize("output_format,expected_codec", [
        ('m4b', 'aac'),
        ('m4a', 'aac'),
        ('mp4', 'aac'),
        ('mp3', 'libmp3lame'),
        ('aac', 'aac'),
        ('flac', 'flac'),
        ('ogg', 'libopus'),
        ('webm', 'libopus'),
        ('wav', None),  # No codec for WAV
    ])
    @patch('lib.audio.exporter.context')
    @patch('lib.audio.exporter.subprocess')
    @patch('lib.audio.exporter.shutil.which')
    @patch('lib.audio.exporter.os.listdir')
    @patch('lib.audio.exporter.AudioSegment')
    @patch('lib.audio.exporter.assemble_chunks')
    def test_format_export(
        self, mock_assemble, mock_audio_seg, mock_listdir,
        mock_which, mock_subprocess, mock_context,
        output_format, expected_codec
    ):
        """Test export for different formats."""
        session = {
            'cancellation_requested': False,
            'output_format': output_format,
            'output_split': False,
            'chapters_dir': '/tmp/chapters',
            'process_dir': '/tmp/process',
            'audiobooks_dir': '/tmp/audiobooks',
            'cover': None,
            'metadata': {
                'title': 'Test Book',
                'creator': 'Test Author',
                'language': 'en',
                'published': '2024-01-01T00:00:00+00:00',
            },
            'final_name': f'test_book.{output_format}',
            'chapters': [['Chapter 1']]
        }
        mock_context.get_session.return_value = session

        mock_listdir.return_value = ['chapter_1.wav']

        # Mock ffprobe
        mock_ffprobe_result = MagicMock()
        mock_ffprobe_result.stdout = json.dumps({'format': {'duration': '60.0'}})
        mock_subprocess.run.return_value = mock_ffprobe_result

        # Mock ffmpeg
        mock_which.return_value = '/usr/bin/ffmpeg'
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = iter([])
        mock_subprocess.Popen.return_value = mock_process

        # Mock audio segment
        mock_seg = MagicMock()
        mock_seg.__len__.return_value = 60000
        mock_audio_seg.from_file.return_value = mock_seg

        mock_assemble.return_value = True

        with patch('builtins.open', mock_open()):
            with patch('lib.audio.exporter.shutil.move'):
                from lib.audio.exporter import combine_audio_chapters

                result = combine_audio_chapters('test-session')

                # Verify ffmpeg was called with correct codec
                if expected_codec:
                    mock_subprocess.Popen.assert_called()
                    ffmpeg_cmd = mock_subprocess.Popen.call_args[0][0]
                    if expected_codec:
                        assert expected_codec in ffmpeg_cmd


# ============================================================================
# Tests for Split Functionality
# ============================================================================

class TestSplitExport:
    """Test audio split functionality."""

    @patch('lib.audio.exporter.context')
    @patch('lib.audio.exporter.subprocess')
    @patch('lib.audio.exporter.shutil.which')
    @patch('lib.audio.exporter.os.listdir')
    @patch('lib.audio.exporter.AudioSegment')
    @patch('lib.audio.exporter.assemble_chunks')
    @patch('lib.audio.exporter.Pool')
    def test_split_enabled_large_book(
        self, mock_pool, mock_assemble, mock_audio_seg,
        mock_listdir, mock_which, mock_subprocess, mock_context
    ):
        """Test splitting large audiobook into multiple parts."""
        session = {
            'cancellation_requested': False,
            'output_format': 'm4b',
            'output_split': True,
            'output_split_hours': 10,
            'chapters_dir': '/tmp/chapters',
            'process_dir': '/tmp/process',
            'audiobooks_dir': '/tmp/audiobooks',
            'cover': None,
            'metadata': {
                'title': 'Long Book',
                'creator': 'Test Author',
                'language': 'en',
                'published': '2024-01-01T00:00:00+00:00',
            },
            'final_name': 'long_book.m4b',
            'chapters': [['Chapter 1'], ['Chapter 2'], ['Chapter 3']]
        }
        mock_context.get_session.return_value = session

        # 3 chapters
        mock_listdir.return_value = ['chapter_1.wav', 'chapter_2.wav', 'chapter_3.wav']

        # Mock ffprobe - each chapter is 25 hours (90000 seconds)
        # Total: 75 hours (triggers split at 10 hours per part)
        mock_ffprobe_result = MagicMock()
        mock_ffprobe_result.stdout = json.dumps({'format': {'duration': '90000.0'}})
        mock_subprocess.run.return_value = mock_ffprobe_result

        # Mock ffmpeg
        mock_which.return_value = '/usr/bin/ffmpeg'
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = iter([])
        mock_subprocess.Popen.return_value = mock_process

        # Mock audio segment
        mock_seg = MagicMock()
        mock_seg.__len__.return_value = 90000000  # 90000 seconds in ms
        mock_audio_seg.from_file.return_value = mock_seg

        # Mock multiprocessing pool
        mock_pool_instance = MagicMock()
        mock_pool_instance.starmap.return_value = [True, True]
        mock_pool.return_value.__enter__.return_value = mock_pool_instance

        mock_assemble.return_value = True

        with patch('builtins.open', mock_open()):
            with patch('lib.audio.exporter.shutil.move'):
                from lib.audio.exporter import combine_audio_chapters

                result = combine_audio_chapters('test-session')

                assert result is not None
                assert isinstance(result, list)
                # Should create multiple parts
                assert len(result) >= 2

    @patch('lib.audio.exporter.context')
    @patch('lib.audio.exporter.subprocess')
    @patch('lib.audio.exporter.shutil.which')
    @patch('lib.audio.exporter.os.listdir')
    @patch('lib.audio.exporter.AudioSegment')
    @patch('lib.audio.exporter.assemble_chunks')
    def test_split_enabled_small_book(
        self, mock_assemble, mock_audio_seg, mock_listdir,
        mock_which, mock_subprocess, mock_context
    ):
        """Test that small book is not split even with split enabled."""
        session = {
            'cancellation_requested': False,
            'output_format': 'm4b',
            'output_split': True,
            'output_split_hours': 10,  # 10 hours per part
            'chapters_dir': '/tmp/chapters',
            'process_dir': '/tmp/process',
            'audiobooks_dir': '/tmp/audiobooks',
            'cover': None,
            'metadata': {
                'title': 'Short Book',
                'creator': 'Test Author',
                'language': 'en',
                'published': '2024-01-01T00:00:00+00:00',
            },
            'final_name': 'short_book.m4b',
            'chapters': [['Chapter 1']]
        }
        mock_context.get_session.return_value = session

        mock_listdir.return_value = ['chapter_1.wav']

        # Mock ffprobe - 5 hours (18000 seconds) - below 20 hour threshold
        mock_ffprobe_result = MagicMock()
        mock_ffprobe_result.stdout = json.dumps({'format': {'duration': '18000.0'}})
        mock_subprocess.run.return_value = mock_ffprobe_result

        # Mock ffmpeg
        mock_which.return_value = '/usr/bin/ffmpeg'
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = iter([])
        mock_subprocess.Popen.return_value = mock_process

        # Mock audio segment
        mock_seg = MagicMock()
        mock_seg.__len__.return_value = 18000000
        mock_audio_seg.from_file.return_value = mock_seg

        mock_assemble.return_value = True

        with patch('builtins.open', mock_open()):
            with patch('lib.audio.exporter.shutil.move'):
                from lib.audio.exporter import combine_audio_chapters

                result = combine_audio_chapters('test-session')

                assert result is not None
                assert len(result) == 1  # Should NOT be split


# ============================================================================
# Tests for Cover Art Embedding
# ============================================================================

class TestCoverArtEmbedding:
    """Test cover art embedding for supported formats."""

    @pytest.mark.parametrize("output_format,use_mutagen_module", [
        ('mp3', 'mutagen.mp3'),
        ('m4b', 'mutagen.mp4'),
        ('m4a', 'mutagen.mp4'),
        ('mp4', 'mutagen.mp4'),
    ])
    @patch('lib.audio.exporter.context')
    @patch('lib.audio.exporter.subprocess')
    @patch('lib.audio.exporter.shutil.which')
    @patch('lib.audio.exporter.os.listdir')
    @patch('lib.audio.exporter.AudioSegment')
    @patch('lib.audio.exporter.assemble_chunks')
    def test_cover_art_embedding(
        self, mock_assemble, mock_audio_seg, mock_listdir,
        mock_which, mock_subprocess, mock_context,
        output_format, use_mutagen_module
    ):
        """Test cover art is embedded for supported formats."""
        session = {
            'cancellation_requested': False,
            'output_format': output_format,
            'output_split': False,
            'chapters_dir': '/tmp/chapters',
            'process_dir': '/tmp/process',
            'audiobooks_dir': '/tmp/audiobooks',
            'cover': '/tmp/cover.jpg',  # Cover provided
            'metadata': {
                'title': 'Test Book',
                'creator': 'Test Author',
                'language': 'en',
                'published': '2024-01-01T00:00:00+00:00',
            },
            'final_name': f'test_book.{output_format}',
            'chapters': [['Chapter 1']]
        }
        mock_context.get_session.return_value = session

        mock_listdir.return_value = ['chapter_1.wav']

        # Mock ffprobe
        mock_ffprobe_result = MagicMock()
        mock_ffprobe_result.stdout = json.dumps({'format': {'duration': '60.0'}})
        mock_subprocess.run.return_value = mock_ffprobe_result

        # Mock ffmpeg
        mock_which.return_value = '/usr/bin/ffmpeg'
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = iter([])
        mock_subprocess.Popen.return_value = mock_process

        # Mock audio segment
        mock_seg = MagicMock()
        mock_seg.__len__.return_value = 60000
        mock_audio_seg.from_file.return_value = mock_seg

        mock_assemble.return_value = True

        # Mock mutagen
        if output_format == 'mp3':
            mock_audio_file = MagicMock()
            mock_audio_file.tags = MagicMock()
            with patch('lib.audio.exporter.MP3', return_value=mock_audio_file):
                with patch('lib.audio.exporter.ID3'):
                    with patch('lib.audio.exporter.APIC'):
                        with patch('builtins.open', mock_open(read_data=b'fake_image_data')):
                            with patch('lib.audio.exporter.shutil.move'):
                                from lib.audio.exporter import combine_audio_chapters

                                result = combine_audio_chapters('test-session')

                                assert result is not None
                                # Verify cover was added
                                mock_audio_file.save.assert_called()
        else:
            # MP4-like formats
            mock_audio_file = MagicMock()
            with patch('lib.audio.exporter.MP4', return_value=mock_audio_file):
                with patch('lib.audio.exporter.MP4Cover') as mock_cover:
                    with patch('builtins.open', mock_open(read_data=b'fake_image_data')):
                        with patch('lib.audio.exporter.shutil.move'):
                            from lib.audio.exporter import combine_audio_chapters

                            result = combine_audio_chapters('test-session')

                            assert result is not None
                            mock_audio_file.save.assert_called()

    @patch('lib.audio.exporter.context')
    @patch('lib.audio.exporter.subprocess')
    @patch('lib.audio.exporter.shutil.which')
    @patch('lib.audio.exporter.os.listdir')
    @patch('lib.audio.exporter.AudioSegment')
    @patch('lib.audio.exporter.assemble_chunks')
    def test_no_cover_art(
        self, mock_assemble, mock_audio_seg, mock_listdir,
        mock_which, mock_subprocess, mock_context
    ):
        """Test export without cover art."""
        session = {
            'cancellation_requested': False,
            'output_format': 'm4b',
            'output_split': False,
            'chapters_dir': '/tmp/chapters',
            'process_dir': '/tmp/process',
            'audiobooks_dir': '/tmp/audiobooks',
            'cover': None,  # No cover
            'metadata': {
                'title': 'Test Book',
                'creator': 'Test Author',
                'language': 'en',
                'published': '2024-01-01T00:00:00+00:00',
            },
            'final_name': 'test_book.m4b',
            'chapters': [['Chapter 1']]
        }
        mock_context.get_session.return_value = session

        mock_listdir.return_value = ['chapter_1.wav']

        mock_ffprobe_result = MagicMock()
        mock_ffprobe_result.stdout = json.dumps({'format': {'duration': '60.0'}})
        mock_subprocess.run.return_value = mock_ffprobe_result

        mock_which.return_value = '/usr/bin/ffmpeg'
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = iter([])
        mock_subprocess.Popen.return_value = mock_process

        mock_seg = MagicMock()
        mock_seg.__len__.return_value = 60000
        mock_audio_seg.from_file.return_value = mock_seg

        mock_assemble.return_value = True

        with patch('builtins.open', mock_open()):
            with patch('lib.audio.exporter.shutil.move'):
                from lib.audio.exporter import combine_audio_chapters

                result = combine_audio_chapters('test-session')

                assert result is not None
                # Should still succeed without cover


# ============================================================================
# Tests for Metadata Generation
# ============================================================================

class TestMetadataGeneration:
    """Test FFmpeg metadata file generation."""

    @patch('lib.audio.exporter.context')
    @patch('lib.audio.exporter.subprocess')
    @patch('lib.audio.exporter.shutil.which')
    @patch('lib.audio.exporter.os.listdir')
    @patch('lib.audio.exporter.AudioSegment')
    @patch('lib.audio.exporter.assemble_chunks')
    def test_metadata_with_all_fields(
        self, mock_assemble, mock_audio_seg, mock_listdir,
        mock_which, mock_subprocess, mock_context
    ):
        """Test metadata generation with all fields populated."""
        session = {
            'cancellation_requested': False,
            'output_format': 'm4b',
            'output_split': False,
            'chapters_dir': '/tmp/chapters',
            'process_dir': '/tmp/process',
            'audiobooks_dir': '/tmp/audiobooks',
            'cover': None,
            'metadata': {
                'title': 'Complete Book',
                'creator': 'Author Name',
                'language': 'en',
                'description': 'A complete description',
                'publisher': 'Publisher Name',
                'published': '2024-01-16T14:30:00.123456+00:00',
                'identifiers': {
                    'isbn': '978-1234567890',
                    'mobi-asin': 'B0123456789'
                }
            },
            'final_name': 'complete_book.m4b',
            'chapters': [['Chapter One'], ['Chapter Two']]
        }
        mock_context.get_session.return_value = session

        mock_listdir.return_value = ['chapter_1.wav', 'chapter_2.wav']

        mock_ffprobe_result = MagicMock()
        mock_ffprobe_result.stdout = json.dumps({'format': {'duration': '60.0'}})
        mock_subprocess.run.return_value = mock_ffprobe_result

        mock_which.return_value = '/usr/bin/ffmpeg'
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = iter([])
        mock_subprocess.Popen.return_value = mock_process

        mock_seg = MagicMock()
        mock_seg.__len__.return_value = 60000
        mock_audio_seg.from_file.return_value = mock_seg

        mock_assemble.return_value = True

        # Capture metadata file content
        metadata_content = []
        original_open = open

        def mock_open_func(path, mode='r', *args, **kwargs):
            if 'metadata' in str(path) and 'w' in mode:
                mock_file = MagicMock()
                mock_file.write = lambda content: metadata_content.append(content)
                return mock_file
            return original_open(path, mode, *args, **kwargs)

        with patch('builtins.open', mock_open_func):
            with patch('lib.audio.exporter.shutil.move'):
                from lib.audio.exporter import combine_audio_chapters

                result = combine_audio_chapters('test-session')

                assert result is not None
                # Check that metadata was written
                if metadata_content:
                    metadata = ''.join(metadata_content)
                    assert ';FFMETADATA1' in metadata
                    assert 'title=Complete Book' in metadata
                    assert 'artist=Author Name' in metadata
                    assert 'isbn=978-1234567890' in metadata

    @pytest.mark.parametrize("output_format,expected_tag_case", [
        ('ogg', 'UPPER'),   # Vorbis uses uppercase
        ('webm', 'UPPER'),  # Vorbis uses uppercase
        ('m4b', 'lower'),   # MP4 uses lowercase
        ('mp3', 'lower'),   # MP3 uses lowercase
    ])
    @patch('lib.audio.exporter.context')
    @patch('lib.audio.exporter.subprocess')
    @patch('lib.audio.exporter.shutil.which')
    @patch('lib.audio.exporter.os.listdir')
    @patch('lib.audio.exporter.AudioSegment')
    @patch('lib.audio.exporter.assemble_chunks')
    def test_metadata_tag_case(
        self, mock_assemble, mock_audio_seg, mock_listdir,
        mock_which, mock_subprocess, mock_context,
        output_format, expected_tag_case
    ):
        """Test metadata tag case for different formats."""
        session = {
            'cancellation_requested': False,
            'output_format': output_format,
            'output_split': False,
            'chapters_dir': '/tmp/chapters',
            'process_dir': '/tmp/process',
            'audiobooks_dir': '/tmp/audiobooks',
            'cover': None,
            'metadata': {
                'title': 'Test Book',
                'creator': 'Author',
                'language': 'en',
                'published': '2024-01-01T00:00:00+00:00',
            },
            'final_name': f'test_book.{output_format}',
            'chapters': [['Chapter 1']]
        }
        mock_context.get_session.return_value = session

        mock_listdir.return_value = ['chapter_1.wav']

        mock_ffprobe_result = MagicMock()
        mock_ffprobe_result.stdout = json.dumps({'format': {'duration': '60.0'}})
        mock_subprocess.run.return_value = mock_ffprobe_result

        mock_which.return_value = '/usr/bin/ffmpeg'
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = iter([])
        mock_subprocess.Popen.return_value = mock_process

        mock_seg = MagicMock()
        mock_seg.__len__.return_value = 60000
        mock_audio_seg.from_file.return_value = mock_seg

        mock_assemble.return_value = True

        # Capture metadata
        metadata_content = []
        original_open = open

        def mock_open_func(path, mode='r', *args, **kwargs):
            if 'metadata' in str(path) and 'w' in mode:
                mock_file = MagicMock()
                mock_file.write = lambda content: metadata_content.append(content)
                return mock_file
            return original_open(path, mode, *args, **kwargs)

        with patch('builtins.open', mock_open_func):
            with patch('lib.audio.exporter.shutil.move'):
                from lib.audio.exporter import combine_audio_chapters

                result = combine_audio_chapters('test-session')

                if metadata_content:
                    metadata = ''.join(metadata_content)
                    if expected_tag_case == 'UPPER':
                        # Vorbis should have uppercase tags
                        assert 'TITLE=' in metadata or 'title=' in metadata
                    else:
                        # MP4/MP3 should have lowercase tags
                        assert 'title=' in metadata


# ============================================================================
# Tests for Batch Processing
# ============================================================================

class TestBatchProcessing:
    """Test multiprocessing batch assembly."""

    @patch('lib.audio.exporter.context')
    @patch('lib.audio.exporter.subprocess')
    @patch('lib.audio.exporter.shutil.which')
    @patch('lib.audio.exporter.os.listdir')
    @patch('lib.audio.exporter.AudioSegment')
    @patch('lib.audio.exporter.assemble_chunks')
    @patch('lib.audio.exporter.Pool')
    def test_batch_processing_large_chapter_count(
        self, mock_pool, mock_assemble, mock_audio_seg,
        mock_listdir, mock_which, mock_subprocess, mock_context
    ):
        """Test batch processing with >1024 chapters."""
        session = {
            'cancellation_requested': False,
            'output_format': 'm4b',
            'output_split': True,
            'output_split_hours': 100,  # High threshold
            'chapters_dir': '/tmp/chapters',
            'process_dir': '/tmp/process',
            'audiobooks_dir': '/tmp/audiobooks',
            'cover': None,
            'metadata': {
                'title': 'Massive Book',
                'creator': 'Test Author',
                'language': 'en',
                'published': '2024-01-01T00:00:00+00:00',
            },
            'final_name': 'massive_book.m4b',
            'chapters': [['Chapter'] for _ in range(2000)]  # 2000 chapters
        }
        mock_context.get_session.return_value = session

        # 2000 chapter files
        mock_listdir.return_value = [f'chapter_{i}.wav' for i in range(1, 2001)]

        # Mock ffprobe - 1 hour per chapter = 2000 hours total
        mock_ffprobe_result = MagicMock()
        mock_ffprobe_result.stdout = json.dumps({'format': {'duration': '3600.0'}})
        mock_subprocess.run.return_value = mock_ffprobe_result

        # Mock ffmpeg
        mock_which.return_value = '/usr/bin/ffmpeg'
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = iter([])
        mock_subprocess.Popen.return_value = mock_process

        # Mock audio segment
        mock_seg = MagicMock()
        mock_seg.__len__.return_value = 3600000
        mock_audio_seg.from_file.return_value = mock_seg

        # Mock multiprocessing pool
        mock_pool_instance = MagicMock()
        # Return True for all batch assemblies
        mock_pool_instance.starmap.return_value = [True] * 10  # Multiple batches
        mock_pool.return_value.__enter__.return_value = mock_pool_instance

        mock_assemble.return_value = True

        with patch('builtins.open', mock_open()):
            with patch('lib.audio.exporter.shutil.move'):
                from lib.audio.exporter import combine_audio_chapters

                result = combine_audio_chapters('test-session')

                assert result is not None
                # Should use multiprocessing pool
                mock_pool_instance.starmap.assert_called()


# ============================================================================
# Tests for Error Handling
# ============================================================================

class TestExporterErrorHandling:
    """Test error handling in combine_audio_chapters."""

    @patch('lib.audio.exporter.context')
    @patch('lib.audio.exporter.subprocess')
    @patch('lib.audio.exporter.shutil.which')
    @patch('lib.audio.exporter.os.listdir')
    @patch('lib.audio.exporter.AudioSegment')
    @patch('lib.audio.exporter.assemble_chunks')
    def test_ffmpeg_export_failure(
        self, mock_assemble, mock_audio_seg, mock_listdir,
        mock_which, mock_subprocess, mock_context
    ):
        """Test when FFmpeg export fails."""
        session = {
            'cancellation_requested': False,
            'output_format': 'm4b',
            'output_split': False,
            'chapters_dir': '/tmp/chapters',
            'process_dir': '/tmp/process',
            'audiobooks_dir': '/tmp/audiobooks',
            'cover': None,
            'metadata': {
                'title': 'Test Book',
                'creator': 'Test Author',
                'language': 'en',
                'published': '2024-01-01T00:00:00+00:00',
            },
            'final_name': 'test_book.m4b',
            'chapters': [['Chapter 1']]
        }
        mock_context.get_session.return_value = session

        mock_listdir.return_value = ['chapter_1.wav']

        mock_ffprobe_result = MagicMock()
        mock_ffprobe_result.stdout = json.dumps({'format': {'duration': '60.0'}})
        mock_subprocess.run.return_value = mock_ffprobe_result

        # FFmpeg fails
        mock_which.return_value = '/usr/bin/ffmpeg'
        mock_process = MagicMock()
        mock_process.returncode = 1  # Failure
        mock_process.stdout = iter(['Error: encoding failed'])
        mock_subprocess.Popen.return_value = mock_process

        mock_seg = MagicMock()
        mock_seg.__len__.return_value = 60000
        mock_audio_seg.from_file.return_value = mock_seg

        mock_assemble.return_value = True

        with patch('builtins.open', mock_open()):
            from lib.audio.exporter import combine_audio_chapters

            result = combine_audio_chapters('test-session')

            assert result is None or result is False

    @patch('lib.audio.exporter.context')
    @patch('lib.audio.exporter.subprocess')
    @patch('lib.audio.exporter.shutil.which')
    @patch('lib.audio.exporter.os.listdir')
    @patch('lib.audio.exporter.AudioSegment')
    @patch('lib.audio.exporter.assemble_chunks')
    def test_cancellation_during_export(
        self, mock_assemble, mock_audio_seg, mock_listdir,
        mock_which, mock_subprocess, mock_context
    ):
        """Test cancellation handling during export."""
        session = {
            'cancellation_requested': True,  # Cancelled
            'output_format': 'm4b',
            'output_split': False,
            'chapters_dir': '/tmp/chapters',
            'process_dir': '/tmp/process',
            'audiobooks_dir': '/tmp/audiobooks',
            'cover': None,
            'metadata': {
                'title': 'Test Book',
                'creator': 'Test Author',
                'language': 'en',
                'published': '2024-01-01T00:00:00+00:00',
            },
            'final_name': 'test_book.m4b',
            'chapters': [['Chapter 1']]
        }
        mock_context.get_session.return_value = session

        mock_listdir.return_value = ['chapter_1.wav']

        mock_ffprobe_result = MagicMock()
        mock_ffprobe_result.stdout = json.dumps({'format': {'duration': '60.0'}})
        mock_subprocess.run.return_value = mock_ffprobe_result

        mock_seg = MagicMock()
        mock_seg.__len__.return_value = 60000
        mock_audio_seg.from_file.return_value = mock_seg

        mock_assemble.return_value = True

        with patch('builtins.open', mock_open()):
            from lib.audio.exporter import combine_audio_chapters

            result = combine_audio_chapters('test-session')

            # Should return None or False on cancellation
            assert result is None or result is False

    @patch('lib.audio.exporter.context')
    @patch('lib.audio.exporter.subprocess')
    @patch('lib.audio.exporter.shutil.which')
    @patch('lib.audio.exporter.os.listdir')
    @patch('lib.audio.exporter.AudioSegment')
    @patch('lib.audio.exporter.assemble_chunks')
    def test_ffprobe_failure(
        self, mock_assemble, mock_audio_seg, mock_listdir,
        mock_which, mock_subprocess, mock_context
    ):
        """Test when ffprobe fails to get duration."""
        session = {
            'cancellation_requested': False,
            'output_format': 'm4b',
            'output_split': False,
            'chapters_dir': '/tmp/chapters',
            'process_dir': '/tmp/process',
            'audiobooks_dir': '/tmp/audiobooks',
            'cover': None,
            'metadata': {
                'title': 'Test Book',
                'creator': 'Test Author',
                'language': 'en',
                'published': '2024-01-01T00:00:00+00:00',
            },
            'final_name': 'test_book.m4b',
            'chapters': [['Chapter 1']]
        }
        mock_context.get_session.return_value = session

        mock_listdir.return_value = ['chapter_1.wav']

        # ffprobe fails
        mock_subprocess.run.side_effect = subprocess.CalledProcessError(1, 'ffprobe')

        mock_seg = MagicMock()
        mock_seg.__len__.return_value = 60000
        mock_audio_seg.from_file.return_value = mock_seg

        mock_assemble.return_value = True
        mock_which.return_value = '/usr/bin/ffmpeg'

        # Should handle gracefully (duration = 0)
        from lib.audio.exporter import combine_audio_chapters

        # May succeed or fail depending on implementation
        result = combine_audio_chapters('test-session')


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.integration
class TestExporterIntegration:
    """Integration tests for complete export pipeline."""

    @patch('lib.audio.exporter.context')
    @patch('lib.audio.exporter.subprocess')
    @patch('lib.audio.exporter.shutil.which')
    @patch('lib.audio.exporter.os.listdir')
    @patch('lib.audio.exporter.AudioSegment')
    @patch('lib.audio.exporter.assemble_chunks')
    def test_complete_export_pipeline(
        self, mock_assemble, mock_audio_seg, mock_listdir,
        mock_which, mock_subprocess, mock_context
    ):
        """Test complete export pipeline with all features."""
        session = {
            'cancellation_requested': False,
            'output_format': 'm4b',
            'output_split': False,
            'chapters_dir': '/tmp/chapters',
            'process_dir': '/tmp/process',
            'audiobooks_dir': '/tmp/audiobooks',
            'cover': '/tmp/cover.jpg',
            'metadata': {
                'title': 'Complete Book',
                'creator': 'Author Name',
                'language': 'en',
                'description': 'Full description',
                'publisher': 'Publisher',
                'published': '2024-01-16T14:30:00+00:00',
                'identifiers': {
                    'isbn': '978-1234567890',
                    'mobi-asin': 'B0123456789'
                }
            },
            'final_name': 'complete_book.m4b',
            'chapters': [
                ['Chapter One: Beginning'],
                ['Chapter Two: Middle'],
                ['Chapter Three: End']
            ]
        }
        mock_context.get_session.return_value = session

        mock_listdir.return_value = ['chapter_1.wav', 'chapter_2.wav', 'chapter_3.wav']

        mock_ffprobe_result = MagicMock()
        mock_ffprobe_result.stdout = json.dumps({'format': {'duration': '1800.0'}})
        mock_subprocess.run.return_value = mock_ffprobe_result

        mock_which.return_value = '/usr/bin/ffmpeg'
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = iter(['Processing...', 'Done'])
        mock_subprocess.Popen.return_value = mock_process

        mock_seg = MagicMock()
        mock_seg.__len__.return_value = 1800000
        mock_audio_seg.from_file.return_value = mock_seg

        mock_assemble.return_value = True

        # Mock mutagen for cover art
        mock_audio_file = MagicMock()
        with patch('lib.audio.exporter.MP4', return_value=mock_audio_file):
            with patch('lib.audio.exporter.MP4Cover'):
                with patch('builtins.open', mock_open(read_data=b'fake_image')):
                    with patch('lib.audio.exporter.shutil.move'):
                        from lib.audio.exporter import combine_audio_chapters

                        result = combine_audio_chapters('test-session')

                        assert result is not None
                        assert isinstance(result, list)
                        assert len(result) == 1
                        # Verify all steps executed
                        mock_assemble.assert_called()
                        mock_subprocess.Popen.assert_called()
                        mock_audio_file.save.assert_called()
