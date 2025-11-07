"""
Pytest configuration and shared fixtures for ebook2audiobook tests.

This module provides common fixtures and test utilities used across
all test modules.
"""

import os
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any
import pytest
from unittest.mock import MagicMock, Mock

# Add project root to path
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# ============================================================================
# Session Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def test_data_dir():
    """Path to test data directory."""
    return Path(__file__).parent / "test_data"


@pytest.fixture(scope="session")
def sample_epub_path(test_data_dir):
    """Path to sample EPUB file for testing."""
    epub_dir = test_data_dir / "sample_books"
    epub_dir.mkdir(parents=True, exist_ok=True)

    # Return path where sample EPUB should be placed
    # In real tests, you'd have actual EPUB files here
    return epub_dir / "sample_book.epub"


# ============================================================================
# Function-scoped Fixtures
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_session():
    """
    Create a mock session dictionary with common test values.

    Returns a session dict that mimics the structure used in the application.
    """
    return {
        'id': 'test-session-12345',
        'ebook': '/path/to/test.epub',
        'ebook_list': [],
        'language': 'eng',
        'language_iso1': 'en',
        'tts_engine': 'xtts',
        'device': 'cpu',
        'voice': 'default',
        'custom_model': None,
        'fine_tuned': False,
        'temperature': 0.7,
        'length_penalty': 1.0,
        'num_beams': 1,
        'repetition_penalty': 2.0,
        'top_k': 50,
        'top_p': 0.8,
        'speed': 1.0,
        'enable_text_splitting': True,
        'text_temp': None,
        'output_format': 'm4b',
        'output_split': False,
        'output_split_hours': 10,
        'cancellation_requested': False,
        'chapters': [],
        'chapters_dir': '/tmp/test_chapters',
        'chapters_dir_sentences': '/tmp/test_sentences',
        'process_dir': '/tmp/test_process',
        'audiobooks_dir': '/tmp/test_audiobooks',
        'cover': None,
        'metadata': {
            'title': 'Test Book',
            'creator': 'Test Author',
            'language': 'en',
            'description': 'A test book for unit testing',
            'publisher': 'Test Publisher',
            'published': '2024-01-01T00:00:00+00:00',
            'identifiers': {
                'isbn': '1234567890',
                'mobi-asin': 'B001234567'
            }
        },
        'final_name': 'test_book.m4b'
    }


@pytest.fixture
def mock_session_manager():
    """Mock session manager (SessionContext)."""
    manager = MagicMock()
    manager.get_session = MagicMock(return_value={})
    manager.session_exists = MagicMock(return_value=True)
    return manager


# ============================================================================
# Text Processing Fixtures
# ============================================================================

@pytest.fixture
def sample_text_english():
    """Sample English text for testing."""
    return """
    Chapter One: The Beginning

    It was the best of times, it was the worst of times. The year was 1984,
    and on January 16th at 14:30, everything changed. The equation 2 + 2 = 4
    became questioned. Numbers like 1,234,567 seemed infinite.

    "What is happening?" asked John. The 1st, 2nd, and 3rd attempts failed.
    Only Chapter XIV (14) remained unread.
    """


@pytest.fixture
def sample_text_french():
    """Sample French text for testing."""
    return """
    Chapitre Un : Le Début

    C'était le meilleur des temps, c'était le pire des temps. L'année était 1984,
    et le 16 janvier à 14h30, tout a changé. Les nombres comme 1.234.567 semblaient infinis.
    """


@pytest.fixture
def sample_html_chapter():
    """Sample HTML chapter content for testing filter_chapter."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Chapter 1</title></head>
    <body>
        <h1>Chapter One</h1>
        <p>This is the first paragraph with some text.</p>
        <p>This is the second paragraph.</p>

        <table>
            <tr><th>Name</th><th>Age</th></tr>
            <tr><td>Alice</td><td>30</td></tr>
            <tr><td>Bob</td><td>25</td></tr>
        </table>

        <div>Some content in a div</div>
        <br/>
        <p>Final paragraph after break.</p>
    </body>
    </html>
    """


# ============================================================================
# Audio Processing Fixtures
# ============================================================================

@pytest.fixture
def sample_audio_file(temp_dir):
    """
    Create a sample audio file for testing.

    Note: This creates a minimal valid audio file.
    For real tests, you'd use actual audio samples.
    """
    audio_path = temp_dir / "sample.wav"

    # Create a minimal WAV file (silence, 1 second, 44100 Hz, mono)
    # WAV header for 1 second of silence
    import wave
    import struct

    with wave.open(str(audio_path), 'w') as wav:
        wav.setnchannels(1)  # mono
        wav.setsampwidth(2)  # 16-bit
        wav.setframerate(44100)  # 44.1kHz
        # 1 second of silence
        wav.writeframes(struct.pack('<h', 0) * 44100)

    return audio_path


@pytest.fixture
def mock_tts_manager():
    """Mock TTS Manager for testing."""
    manager = MagicMock()
    manager.convert_sentence2audio = MagicMock(return_value=True)
    return manager


# ============================================================================
# EPUB Processing Fixtures
# ============================================================================

@pytest.fixture
def mock_epub_book():
    """Mock EPUB book object."""
    from unittest.mock import MagicMock

    book = MagicMock()
    book.get_items_of_type = MagicMock(return_value=[])
    return book


@pytest.fixture
def mock_epub_item():
    """Mock EPUB document item."""
    from unittest.mock import MagicMock

    item = MagicMock()
    item.get_body_content = MagicMock(return_value=b"<html><body><p>Test content</p></body></html>")
    return item


# ============================================================================
# FFmpeg Fixtures
# ============================================================================

@pytest.fixture
def check_ffmpeg_available():
    """
    Check if FFmpeg is available on the system.

    Skip tests requiring FFmpeg if not available.
    """
    import shutil
    ffmpeg = shutil.which('ffmpeg')
    ffprobe = shutil.which('ffprobe')

    if not ffmpeg or not ffprobe:
        pytest.skip("FFmpeg not available on this system")

    return True


# ============================================================================
# Utility Functions
# ============================================================================

def create_test_chapters(session_dir: Path, num_chapters: int = 3):
    """
    Create test chapter audio files.

    Args:
        session_dir: Directory to create chapter files in
        num_chapters: Number of chapter files to create

    Returns:
        List of created file paths
    """
    import wave
    import struct

    chapters_dir = session_dir / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)

    created_files = []

    for i in range(1, num_chapters + 1):
        chapter_file = chapters_dir / f"chapter_{i}.wav"

        # Create a minimal WAV file
        with wave.open(str(chapter_file), 'w') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(44100)
            # Half second of silence per chapter
            wav.writeframes(struct.pack('<h', 0) * 22050)

        created_files.append(chapter_file)

    return created_files


# ============================================================================
# Pytest Hooks
# ============================================================================

def pytest_configure(config):
    """Pytest configuration hook."""
    # Add custom markers
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as an end-to-end test"
    )


def pytest_collection_modifyitems(config, items):
    """
    Modify test collection to add markers based on test location.
    """
    for item in items:
        # Add markers based on test file location
        if "test_e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        else:
            item.add_marker(pytest.mark.unit)
