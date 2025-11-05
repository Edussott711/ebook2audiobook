"""
File Hashing Module
Provides utilities for calculating and comparing file hashes.
"""

import hashlib
from typing import Dict
from collections.abc import Mapping


def calculate_hash(filepath: str, hash_algorithm: str = 'sha256') -> str:
    """
    Calculate the hash of a file.

    Args:
        filepath: Path to the file to hash
        hash_algorithm: Hash algorithm to use (default: 'sha256')

    Returns:
        str: Hexadecimal hash digest of the file
    """
    hash_func = hashlib.new(hash_algorithm)
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):  # Read in chunks to handle large files
            hash_func.update(chunk)
    return hash_func.hexdigest()


def compare_files_by_hash(file1: str, file2: str, hash_algorithm: str = 'sha256') -> bool:
    """
    Compare two files by their hash values.

    Args:
        file1: Path to the first file
        file2: Path to the second file
        hash_algorithm: Hash algorithm to use for comparison (default: 'sha256')

    Returns:
        bool: True if files have the same hash, False otherwise
    """
    return calculate_hash(file1, hash_algorithm) == calculate_hash(file2, hash_algorithm)


def hash_proxy_dict(proxy_dict: dict) -> str:
    """
    Calculate MD5 hash of a proxy dictionary.

    Args:
        proxy_dict: Dictionary to hash (typically a multiprocessing proxy dict)

    Returns:
        str: MD5 hash of the dictionary's string representation
    """
    return hashlib.md5(str(proxy_dict).encode('utf-8')).hexdigest()


def compare_dict_keys(d1: Mapping, d2: Mapping) -> Dict[str, set] | None:
    """
    Compare keys between two dictionaries recursively.

    Args:
        d1: First dictionary to compare
        d2: Second dictionary to compare

    Returns:
        dict | None: Dictionary showing missing keys, or None if keys match
    """
    if not isinstance(d1, Mapping) or not isinstance(d2, Mapping):
        return d1 == d2

    d1_keys = set(d1.keys())
    d2_keys = set(d2.keys())

    missing_in_d2 = d1_keys - d2_keys
    missing_in_d1 = d2_keys - d1_keys

    if missing_in_d2 or missing_in_d1:
        return {
            "missing_in_d2": missing_in_d2,
            "missing_in_d1": missing_in_d1,
        }

    for key in d1_keys.intersection(d2_keys):
        nested_result = compare_dict_keys(d1[key], d2[key])
        if nested_result:
            return {key: nested_result}

    return None
