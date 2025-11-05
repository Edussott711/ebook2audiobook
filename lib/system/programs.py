"""
System Programs Module
Provides utilities for checking system program availability.
"""

import subprocess
from lib.core.exceptions import DependencyError


def check_programs(prog_name: str, command: str, options: str) -> tuple[bool, None]:
    """
    Check if a system program is installed and available.

    Args:
        prog_name: Name of the program for error messages
        command: Command to execute
        options: Command-line options to pass

    Returns:
        tuple[bool, None]: (True, None) if program is available, (False, None) otherwise
    """
    try:
        subprocess.run(
            [command, options],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True,
            encoding='utf-8'
        )
        return True, None
    except FileNotFoundError:
        error_msg = (
            f'********** Error: {prog_name} is not installed! '
            f'If your OS calibre package version is not compatible, '
            f'you can still run ebook2audiobook.sh (linux/mac) or '
            f'ebook2audiobook.cmd (windows) **********'
        )
        DependencyError(error_msg)
        return False, None
    except subprocess.CalledProcessError:
        error_msg = f'Error: There was an issue running {prog_name}.'
        DependencyError(error_msg)
        return False, None
