"""
Core Exceptions Module
Defines custom exceptions for the ebook2audiobook application.
"""

import sys
import traceback


class DependencyError(Exception):
    """
    Exception raised when a required dependency is missing or incompatible.

    This exception automatically handles itself by printing the traceback
    and exiting the script if not in GUI mode.
    """

    def __init__(self, message: str = None):
        """
        Initialize the DependencyError.

        Args:
            message: Error message describing the dependency issue
        """
        super().__init__(message)
        self.message = message
        print(message)
        self.handle_exception()

    def handle_exception(self):
        """
        Handle the exception by printing traceback and potentially exiting.

        Automatically exits the script if not running in GUI mode.
        """
        # Print the full traceback of the exception
        traceback.print_exc()

        # Print the exception message
        error_msg = f'Caught DependencyError: {self}'
        print(error_msg)

        # Exit the script if it's not a web process
        # Note: is_gui_process should be injected or retrieved from context
        from lib.functions import is_gui_process
        if not is_gui_process:
            sys.exit(1)


class ConversionError(Exception):
    """
    Exception raised when ebook conversion fails.
    """
    pass


class ValidationError(Exception):
    """
    Exception raised when input validation fails.
    """
    pass


class AudioProcessingError(Exception):
    """
    Exception raised when audio processing fails.
    """
    pass


class SessionError(Exception):
    """
    Exception raised when session operations fail.
    """
    pass
