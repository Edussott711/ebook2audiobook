"""
Session Tracker Module
Provides tracking and lifecycle management for active sessions.
"""

import threading
from typing import Set


class SessionTracker:
    """
    Tracks active sessions and manages their lifecycle.

    Uses thread locking to ensure thread-safe session state transitions.
    """

    def __init__(self, context=None):
        """
        Initialize the session tracker.

        Args:
            context: SessionContext instance to track sessions from
        """
        self.lock = threading.Lock()
        self.context = context
        self.active_sessions: Set[str] = set()

    def set_context(self, context):
        """
        Set the session context to track.

        Args:
            context: SessionContext instance
        """
        self.context = context

    def start_session(self, session_id: str) -> bool:
        """
        Start a session by marking it as ready.

        Args:
            session_id: Unique session identifier

        Returns:
            bool: True if session was started, False if already active
        """
        with self.lock:
            if self.context is None:
                return False

            session = self.context.get_session(session_id)
            if session['status'] is None:
                session['status'] = 'ready'
                return True
        return False

    def end_session(self, session_id: str, socket_hash: str = None):
        """
        End a session and clean up UI-related metadata.

        Note: Does not cancel the conversion process, only cleans up
        UI-related session data when the client disconnects.

        Args:
            session_id: Unique session identifier
            socket_hash: Socket hash to remove from active sessions
        """
        if socket_hash:
            self.active_sessions.discard(socket_hash)

        with self.lock:
            if self.context is None:
                return

            session = self.context.get_session(session_id)

            # Clean up UI-related session metadata
            # Don't cancel the conversion process when Gradio disconnects
            session['tab_id'] = None

            if socket_hash:
                session[socket_hash] = None

    def is_session_active(self, session_id: str) -> bool:
        """
        Check if a session is currently active.

        Args:
            session_id: Unique session identifier

        Returns:
            bool: True if session exists and has a status, False otherwise
        """
        with self.lock:
            if self.context is None:
                return False

            session = self.context.get_session(session_id)
            return session.get('status') is not None

    def add_active_socket(self, socket_hash: str):
        """
        Add a socket hash to the active sessions set.

        Args:
            socket_hash: Socket hash identifier
        """
        self.active_sessions.add(socket_hash)

    def remove_active_socket(self, socket_hash: str):
        """
        Remove a socket hash from the active sessions set.

        Args:
            socket_hash: Socket hash identifier
        """
        self.active_sessions.discard(socket_hash)
