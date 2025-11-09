"""
File Utilities Module
Provides general file utility functions.
"""

from typing import Any


def proxy2dict(proxy_obj: Any) -> Any:
    """
    Convert a multiprocessing proxy object to a regular Python dict/list.

    Handles circular references by tracking visited objects.

    Args:
        proxy_obj: Proxy object to convert (dict, list, or primitive type)

    Returns:
        Any: Regular Python object (dict, list, or primitive)
    """
    def recursive_copy(source: Any, visited: set) -> Any:
        # Handle circular references by tracking visited objects
        if id(source) in visited:
            return None  # Stop processing circular references
        visited.add(id(source))  # Mark as visited

        # Check for dict-like objects (including DictProxy)
        # Use duck typing: if it has 'items' method, treat it as a dict
        if hasattr(source, 'items') and callable(getattr(source, 'items')):
            result = {}
            for key, value in source.items():
                result[key] = recursive_copy(value, visited)
            return result
        # Check for list-like objects (including ListProxy)
        # Use duck typing: if it's not dict-like and is iterable (but not string)
        elif hasattr(source, '__iter__') and not isinstance(source, (str, bytes)):
            try:
                return [recursive_copy(item, visited) for item in source]
            except (TypeError, AttributeError):
                # If iteration fails, fall through to other checks
                pass

        # Handle primitive types
        if isinstance(source, (int, float, str, bool, type(None))):
            return source
        elif isinstance(source, set):
            return list(source)
        else:
            # For unsupported types, return string representation
            return str(source)

    visited_set = set()
    return recursive_copy(proxy_obj, visited_set)


def compare_file_metadata(f1: str, f2: str) -> bool:
    """
    Compare metadata of two files.

    Args:
        f1: Path to first file
        f2: Path to second file

    Returns:
        bool: True if metadata matches, False otherwise
    """
    import os

    try:
        stat1 = os.stat(f1)
        stat2 = os.stat(f2)

        # Compare file size and modification time
        return (stat1.st_size == stat2.st_size and
                stat1.st_mtime == stat2.st_mtime)
    except Exception:
        return False
