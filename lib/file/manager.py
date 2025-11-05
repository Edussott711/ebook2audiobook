"""
File Manager Module
Provides utilities for directory and file management operations.
"""

import os
import shutil
from typing import Dict, Any
from .hasher import compare_files_by_hash
from lib.core.exceptions import DependencyError
from lib.conf import models_dir


def prepare_dirs(src: str, session: Dict[str, Any]) -> bool:
    """
    Prepare all necessary directories for the conversion process.

    Creates required directories and copies the source ebook file to the
    process directory. Detects if resuming an existing conversion.

    Args:
        src: Path to the source ebook file
        session: Session context dictionary containing directory paths

    Returns:
        bool: True if preparation was successful, False otherwise
    """
    try:
        resume = False

        # Create necessary directories
        os.makedirs(os.path.join(models_dir, 'tts'), exist_ok=True)
        os.makedirs(session['session_dir'], exist_ok=True)
        os.makedirs(session['process_dir'], exist_ok=True)
        os.makedirs(session['custom_model_dir'], exist_ok=True)
        os.makedirs(session['voice_dir'], exist_ok=True)
        os.makedirs(session['audiobooks_dir'], exist_ok=True)

        # Set ebook path in session
        session['ebook'] = os.path.join(session['process_dir'], os.path.basename(src))

        # Check if we can resume (file exists and matches source)
        if os.path.exists(session['ebook']):
            if compare_files_by_hash(session['ebook'], src):
                resume = True

        # If not resuming, clean up previous chapters
        if not resume:
            shutil.rmtree(session['chapters_dir'], ignore_errors=True)

        # Create chapter directories
        os.makedirs(session['chapters_dir'], exist_ok=True)
        os.makedirs(session['chapters_dir_sentences'], exist_ok=True)

        # Copy source ebook to process directory
        shutil.copy(src, session['ebook'])

        return True

    except Exception as e:
        DependencyError(str(e))
        return False


def delete_unused_tmp_dirs(web_dir: str, days: int, session: Dict[str, Any]) -> None:
    """
    Delete temporary directories older than specified number of days.

    Args:
        web_dir: Path to the web temporary directory
        days: Number of days threshold for deletion
        session: Session context dictionary (for current session exclusion)
    """
    import time
    from pathlib import Path

    try:
        if not os.path.exists(web_dir):
            return

        current_time = time.time()
        threshold = days * 24 * 60 * 60  # Convert days to seconds

        for item in os.listdir(web_dir):
            item_path = os.path.join(web_dir, item)

            # Skip if not a directory
            if not os.path.isdir(item_path):
                continue

            # Skip current session directory
            if 'session_dir' in session and item_path == session['session_dir']:
                continue

            # Check directory age
            try:
                dir_stat = os.stat(item_path)
                age = current_time - dir_stat.st_mtime

                if age > threshold:
                    shutil.rmtree(item_path, ignore_errors=True)
                    print(f"Deleted old temporary directory: {item_path}")
            except Exception as e:
                print(f"Warning: Could not delete {item_path}: {e}")

    except Exception as e:
        print(f"Warning: Error cleaning up temporary directories: {e}")
