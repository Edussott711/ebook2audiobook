"""
System Module
Provides system-level utilities and resource detection.
"""

from .resources import get_ram, get_vram
from .programs import check_programs
from .utils import get_sanitized

__all__ = [
    'get_ram',
    'get_vram',
    'check_programs',
    'get_sanitized',
]
