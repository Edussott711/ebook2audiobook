"""
Global Context Module
Provides the global session context instance shared across the application.

This module exists to avoid circular imports when modules need to access
the global session context.
"""

# Global session context instance
# Initialized by app.py or convert_ebook functions
context = None

# Global process flag
is_gui_process = False

# Active sessions set
active_sessions = set()
