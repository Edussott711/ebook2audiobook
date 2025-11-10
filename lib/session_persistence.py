"""
Session Persistence Module
Manages persistent sessions that survive Docker restarts.

Features:
- Thread-safe file operations with file locking
- Atomic writes to prevent corruption
- Schema validation and versioning
- Automatic cleanup of old sessions
- Session index management
"""

import os
import json
import time
import fcntl
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path


class SessionPersistence:
    """
    Manages persistent storage of user sessions.

    Best Practices Implemented:
    - Thread-safe operations with file locking
    - Atomic writes (write to temp, then rename)
    - Schema validation
    - Version migration support
    - Structured error handling
    - Automatic cleanup
    """

    VERSION = "1.0"
    SESSIONS_DIR = "/app/sessions"
    INDEX_FILE = "sessions.json"
    MAX_INCOMPLETE_SESSIONS = 4
    CLEANUP_COMPLETED_AFTER_HOURS = 24

    def __init__(self, sessions_dir: str = None):
        """Initialize session persistence manager."""
        self.sessions_dir = Path(sessions_dir or self.SESSIONS_DIR)
        self.index_path = self.sessions_dir / self.INDEX_FILE
        self.lock = threading.RLock()  # Reentrant lock for thread safety

        # Ensure directories exist
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        # Initialize index if doesn't exist
        if not self.index_path.exists():
            self._create_index()

    def _create_index(self):
        """Create initial index file."""
        index = {
            "version": self.VERSION,
            "active_session": None,
            "sessions": []
        }
        self._atomic_write(self.index_path, index)

    def _atomic_write(self, path: Path, data: dict):
        """
        Atomic write to prevent corruption.
        Writes to temp file first, then renames.
        """
        temp_path = path.with_suffix('.tmp')
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                # Acquire exclusive lock
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                    f.flush()
                    os.fsync(f.fileno())  # Ensure written to disk
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

            # Atomic rename
            temp_path.replace(path)
        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            raise IOError(f"Failed to write {path}: {e}")

    def _read_with_lock(self, path: Path) -> dict:
        """Read file with shared lock."""
        if not path.exists():
            return {}

        try:
            with open(path, 'r', encoding='utf-8') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    return json.load(f)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except Exception as e:
            print(f"Warning: Failed to read {path}: {e}")
            return {}

    def _get_index(self) -> dict:
        """Get current session index."""
        with self.lock:
            index = self._read_with_lock(self.index_path)

            # Validate and migrate if needed
            if not index or index.get('version') != self.VERSION:
                self._create_index()
                index = self._read_with_lock(self.index_path)

            return index

    def _update_index(self, index: dict):
        """Update session index atomically."""
        with self.lock:
            index['version'] = self.VERSION
            self._atomic_write(self.index_path, index)

    def _get_session_dir(self, session_id: str) -> Path:
        """Get directory path for a session."""
        return self.sessions_dir / f"session-{session_id}"

    def _get_session_file(self, session_id: str) -> Path:
        """Get session data file path."""
        return self._get_session_dir(session_id) / "session_data.json"

    def _get_metadata_file(self, session_id: str) -> Path:
        """Get session metadata file path."""
        return self._get_session_dir(session_id) / "metadata.json"

    def save_session(self, session_id: str, session_data: dict) -> bool:
        """
        Save session to disk.

        Args:
            session_id: Unique session identifier
            session_data: Complete session state

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            with self.lock:
                session_dir = self._get_session_dir(session_id)
                session_dir.mkdir(parents=True, exist_ok=True)

                # Save session data
                session_file = self._get_session_file(session_id)
                self._atomic_write(session_file, session_data)

                # Update metadata
                metadata = {
                    "id": session_id,
                    "status": session_data.get('status', 'ready'),
                    # Use 'or' to handle None values: if get() returns None, use default
                    "ebook_name": os.path.basename(session_data.get('ebook') or 'Unknown'),
                    "progress": session_data.get('progress', 0),
                    "tts_engine": session_data.get('tts_engine', 'Unknown'),
                    "voice": os.path.basename(session_data.get('voice', 'Default')) if session_data.get('voice') else 'Default',
                    "language": session_data.get('language', 'eng'),
                    "last_access": datetime.now().isoformat(),
                    "completed": session_data.get('status') == 'ready' and session_data.get('audiobook') is not None,
                    "created_at": session_data.get('created_at', datetime.now().isoformat())
                }

                metadata_file = self._get_metadata_file(session_id)
                self._atomic_write(metadata_file, metadata)

                # Update index
                self._update_session_index(metadata)

                return True
        except Exception as e:
            print(f"Error saving session {session_id}: {e}")
            return False

    def load_session(self, session_id: str) -> Optional[dict]:
        """
        Load session from disk.

        Args:
            session_id: Session identifier

        Returns:
            Session data dict or None if not found
        """
        try:
            with self.lock:
                session_file = self._get_session_file(session_id)
                if not session_file.exists():
                    return None

                session_data = self._read_with_lock(session_file)

                # Update last access time
                metadata_file = self._get_metadata_file(session_id)
                if metadata_file.exists():
                    metadata = self._read_with_lock(metadata_file)
                    metadata['last_access'] = datetime.now().isoformat()
                    self._atomic_write(metadata_file, metadata)
                    self._update_session_index(metadata)

                return session_data
        except Exception as e:
            print(f"Error loading session {session_id}: {e}")
            return None

    def _update_session_index(self, metadata: dict):
        """Update or add session in index."""
        index = self._get_index()

        # Find and update existing session
        found = False
        for i, session in enumerate(index['sessions']):
            if session['id'] == metadata['id']:
                index['sessions'][i] = metadata
                found = True
                break

        # Add new session if not found
        if not found:
            index['sessions'].append(metadata)

        # Sort by last_access (most recent first)
        index['sessions'].sort(
            key=lambda s: s.get('last_access', ''),
            reverse=True
        )

        self._update_index(index)

    def list_sessions(self, include_completed: bool = False) -> List[dict]:
        """
        List all available sessions.

        Args:
            include_completed: Include completed sessions

        Returns:
            List of session metadata dicts
        """
        try:
            with self.lock:
                index = self._get_index()
                sessions = index.get('sessions', [])

                if not include_completed:
                    sessions = [s for s in sessions if not s.get('completed', False)]

                return sessions
        except Exception as e:
            print(f"Error listing sessions: {e}")
            return []

    def get_active_session(self) -> Optional[str]:
        """Get currently active session ID."""
        try:
            with self.lock:
                index = self._get_index()
                return index.get('active_session')
        except Exception as e:
            print(f"Error getting active session: {e}")
            return None

    def set_active_session(self, session_id: Optional[str]) -> bool:
        """
        Set active session (only one allowed at a time).

        Args:
            session_id: Session to activate, or None to clear

        Returns:
            True if set successfully
        """
        try:
            with self.lock:
                index = self._get_index()
                index['active_session'] = session_id
                self._update_index(index)
                return True
        except Exception as e:
            print(f"Error setting active session: {e}")
            return False

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session from disk.

        Args:
            session_id: Session to delete

        Returns:
            True if deleted successfully
        """
        try:
            with self.lock:
                # Remove from index
                index = self._get_index()
                index['sessions'] = [s for s in index['sessions'] if s['id'] != session_id]

                if index['active_session'] == session_id:
                    index['active_session'] = None

                self._update_index(index)

                # Delete files
                import shutil
                session_dir = self._get_session_dir(session_id)
                if session_dir.exists():
                    shutil.rmtree(session_dir, ignore_errors=True)

                return True
        except Exception as e:
            print(f"Error deleting session {session_id}: {e}")
            return False

    def cleanup_old_sessions(self, keep_incomplete: int = None):
        """
        Clean up old sessions.
        Keeps only the N most recent incomplete sessions.
        Removes completed sessions older than CLEANUP_COMPLETED_AFTER_HOURS.

        FIX PROBLEM 8: Never delete sessions that are actively converting.

        Args:
            keep_incomplete: Number of incomplete sessions to keep (default: MAX_INCOMPLETE_SESSIONS)
        """
        try:
            with self.lock:
                keep_incomplete = keep_incomplete or self.MAX_INCOMPLETE_SESSIONS
                index = self._get_index()
                sessions = index['sessions']

                # Separate sessions by status
                converting = []
                incomplete = []
                completed = []

                for s in sessions:
                    session_id = s.get('id')
                    if not session_id:
                        continue

                    # FIX PROBLEM 8: Load actual session data to check real status
                    # Metadata can be stale, session_data.json is source of truth
                    session_file = self._get_session_file(session_id)
                    if session_file.exists():
                        session_data = self._read_with_lock(session_file)
                        actual_status = session_data.get('status')

                        # CRITICAL: Never delete converting sessions
                        if actual_status == 'converting':
                            converting.append(s)
                            continue

                    # Categorize by completed flag
                    if s.get('completed', False):
                        completed.append(s)
                    else:
                        incomplete.append(s)

                # Keep all converting sessions (NEVER delete them)
                sessions_to_keep = converting.copy()

                # Keep only most recent N incomplete sessions (excluding converting)
                sessions_to_keep.extend(incomplete[:keep_incomplete])
                sessions_to_delete = incomplete[keep_incomplete:]

                # Remove old completed sessions
                cutoff_time = datetime.now() - timedelta(hours=self.CLEANUP_COMPLETED_AFTER_HOURS)
                for session in completed:
                    try:
                        last_access = datetime.fromisoformat(session.get('last_access', ''))
                        if last_access < cutoff_time:
                            sessions_to_delete.append(session)
                        else:
                            sessions_to_keep.append(session)
                    except (ValueError, TypeError):
                        # Invalid date format, keep it to be safe
                        sessions_to_keep.append(session)

                # Delete sessions
                for session in sessions_to_delete:
                    session_name = session.get('ebook_name', 'Unknown')
                    session_id = session['id']
                    print(f"Cleaning up old session: {session_id[:8]} - {session_name}")
                    self.delete_session(session_id)

                print(f"Cleanup complete: Kept {len(sessions_to_keep)} sessions ({len(converting)} converting), removed {len(sessions_to_delete)} sessions")
        except Exception as e:
            print(f"Error during cleanup: {e}")
            import traceback
            traceback.print_exc()

    def session_exists(self, session_id: str) -> bool:
        """Check if session exists on disk."""
        session_file = self._get_session_file(session_id)
        return session_file.exists()

    def get_session_display_name(self, session_id: str) -> str:
        """
        Get display name for session.
        Format: "Ebook Name (Progress%) - Model: xtts, Voice: filename"
        """
        try:
            metadata_file = self._get_metadata_file(session_id)
            if not metadata_file.exists():
                return f"Session {session_id[:8]}"

            metadata = self._read_with_lock(metadata_file)

            ebook_name = metadata.get('ebook_name', 'Unknown')
            # Remove extension for display
            ebook_name = os.path.splitext(ebook_name)[0]

            progress = metadata.get('progress', 0)
            tts_engine = metadata.get('tts_engine', 'Unknown')
            voice = metadata.get('voice', 'Default')
            status = metadata.get('status', 'ready')

            # Build display name
            name = f"{ebook_name}"

            if status == 'converting':
                name += f" ({progress}%)"
            elif metadata.get('completed'):
                name += " (✓)"

            name += f" - Model: {tts_engine}"

            if voice and voice != 'Default':
                # Remove extension from voice filename
                voice = os.path.splitext(voice)[0]
                name += f", Voice: {voice}"

            return name
        except Exception as e:
            print(f"Error getting display name for {session_id}: {e}")
            return f"Session {session_id[:8]}"
