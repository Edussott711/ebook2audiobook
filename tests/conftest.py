"""
Pytest configuration and fixtures
"""
import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_ebook_path(temp_dir: Path) -> Path:
    """Create a sample ebook file for testing"""
    ebook_path = temp_dir / "test_book.txt"
    ebook_path.write_text("Chapter 1\n\nThis is a test book.\n\nChapter 2\n\nAnother chapter.")
    return ebook_path


@pytest.fixture
def audiobooks_dir(temp_dir: Path) -> Path:
    """Create audiobooks output directory"""
    audiobooks = temp_dir / "audiobooks"
    audiobooks.mkdir(exist_ok=True)
    return audiobooks


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up test environment variables"""
    test_vars = {
        "PYTHONUNBUFFERED": "1",
        "TESTING": "1",
    }
    for key, value in test_vars.items():
        monkeypatch.setenv(key, value)
    return test_vars


@pytest.fixture(autouse=True)
def reset_imports():
    """Reset imports before each test"""
    import sys
    # Store original modules
    original_modules = sys.modules.copy()
    yield
    # Restore original modules
    sys.modules.clear()
    sys.modules.update(original_modules)
