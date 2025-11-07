"""
Session Manager Module
Provides centralized session management and context.
"""

from typing import Dict, Any, Optional
from multiprocessing import Manager
from .session_utils import recursive_proxy
from lib.conf import (
    NATIVE, default_device,
    default_output_format, default_output_split,
    default_output_split_hours
)
from lib.lang import default_language_code
from lib.models import (
    TTS_ENGINES, default_engine_settings,
    default_tts_engine, default_fine_tuned
)


class SessionContext:
    """
    Manages session contexts for ebook conversion processes.

    Provides centralized storage and retrieval of session data using
    multiprocessing-safe proxy objects.
    """

    def __init__(self):
        """Initialize the session context with a multiprocessing Manager."""
        self.manager = Manager()
        self.sessions = self.manager.dict()
        self.cancellation_events = {}

    def get_session(self, session_id: str) -> Dict[str, Any]:
        """
        Get or create a session by ID.

        If the session doesn't exist, creates a new one with default values.

        Args:
            session_id: Unique session identifier

        Returns:
            Dict[str, Any]: Session data dictionary (multiprocessing proxy)
        """
        if session_id not in self.sessions:
            self.sessions[session_id] = self._create_session(session_id)
        return self.sessions[session_id]

    def _create_session(self, session_id: str) -> Dict[str, Any]:
        """
        Create a new session with default values.

        Args:
            session_id: Unique session identifier

        Returns:
            Dict[str, Any]: New session data dictionary
        """
        session_data = {
            "script_mode": NATIVE,
            "id": session_id,
            "tab_id": None,
            "process_id": None,
            "status": None,
            "event": None,
            "progress": 0,
            "cancellation_requested": False,
            "device": default_device,
            "system": None,
            "client": None,
            "language": default_language_code,
            "language_iso1": None,
            "audiobook": None,
            "audiobooks_dir": None,
            "process_dir": None,
            "ebook": None,
            "ebook_list": None,
            "ebook_mode": "single",
            "chapters_dir": None,
            "chapters_dir_sentences": None,
            "epub_path": None,
            "filename_noext": None,
            "tts_engine": default_tts_engine,
            "fine_tuned": default_fine_tuned,
            "voice": None,
            "voice_dir": None,
            "custom_model": None,
            "custom_model_dir": None,
            "temperature": default_engine_settings[TTS_ENGINES['XTTSv2']]['temperature'],
            "length_penalty": default_engine_settings[TTS_ENGINES['XTTSv2']]['length_penalty'],
            "num_beams": default_engine_settings[TTS_ENGINES['XTTSv2']]['num_beams'],
            "repetition_penalty": default_engine_settings[TTS_ENGINES['XTTSv2']]['repetition_penalty'],
            "top_k": default_engine_settings[TTS_ENGINES['XTTSv2']]['top_k'],
            "top_p": default_engine_settings[TTS_ENGINES['XTTSv2']]['top_p'],
            "speed": default_engine_settings[TTS_ENGINES['XTTSv2']]['speed'],
            "enable_text_splitting": default_engine_settings[TTS_ENGINES['XTTSv2']]['enable_text_splitting'],
            "text_temp": default_engine_settings[TTS_ENGINES['BARK']]['text_temp'],
            "waveform_temp": default_engine_settings[TTS_ENGINES['BARK']]['waveform_temp'],
            "final_name": None,
            "output_format": default_output_format,
            "output_split": default_output_split,
            "output_split_hours": default_output_split_hours,
            "metadata": {
                "title": None,
                "creator": None,
                "contributor": None,
                "language": None,
                "identifier": None,
                "publisher": None,
                "date": None,
                "description": None,
                "subject": None,
                "rights": None,
                "format": None,
                "type": None,
                "coverage": None,
                "relation": None,
                "Source": None,
                "Modified": None,
            },
            "toc": None,
            "chapters": None,
            "cover": None,
            "duration": 0,
            "playback_time": 0
        }

        return recursive_proxy(session_data, manager=self.manager)

    def find_id_by_hash(self, socket_hash: str) -> Optional[str]:
        """
        Find a session ID by socket hash.

        Args:
            socket_hash: Socket hash identifier to search for

        Returns:
            str | None: Session ID if found, None otherwise
        """
        for session_id, session in self.sessions.items():
            if socket_hash in session:
                return session.get('id')
        return None

    def session_exists(self, session_id: str) -> bool:
        """
        Check if a session exists.

        Args:
            session_id: Unique session identifier

        Returns:
            bool: True if session exists, False otherwise
        """
        return session_id in self.sessions

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session by ID.

        Args:
            session_id: Unique session identifier

        Returns:
            bool: True if session was deleted, False if it didn't exist
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            if session_id in self.cancellation_events:
                del self.cancellation_events[session_id]
            return True
        return False

    def get_all_session_ids(self) -> list:
        """
        Get all active session IDs.

        Returns:
            list: List of session IDs
        """
        return list(self.sessions.keys())
