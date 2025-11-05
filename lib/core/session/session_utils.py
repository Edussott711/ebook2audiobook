"""
Session Utilities Module
Provides utility functions for session management.
"""

from typing import Any
from multiprocessing import Manager


def recursive_proxy(data: Any, manager: Manager = None) -> Any:
    """
    Recursively convert a data structure to multiprocessing proxy objects.

    Converts regular Python dicts and lists to Manager-backed proxy
    objects that can be safely shared between processes.

    Args:
        data: Data structure to convert (dict, list, or primitive)
        manager: Multiprocessing Manager instance (creates one if None)

    Returns:
        Any: Proxy object (dict, list, or primitive)
    """
    if manager is None:
        manager = Manager()

    if isinstance(data, dict):
        proxy_dict = manager.dict()
        for key, value in data.items():
            proxy_dict[key] = recursive_proxy(value, manager)
        return proxy_dict

    elif isinstance(data, list):
        proxy_list = manager.list()
        for item in data:
            proxy_list.append(recursive_proxy(item, manager))
        return proxy_list

    elif isinstance(data, (str, int, float, bool, type(None))):
        return data

    else:
        error = f"Unsupported data type: {type(data)}"
        print(error)
        return None
