"""
File Module
Provides file management, validation, and extraction utilities.
"""

from .manager import prepare_dirs, delete_unused_tmp_dirs
from .validator import analyze_uploaded_file
from .extractor import extract_custom_model
from .hasher import (
    calculate_hash,
    compare_files_by_hash,
    hash_proxy_dict,
    compare_dict_keys
)
from .utils import proxy2dict, compare_file_metadata

__all__ = [
    # Manager
    'prepare_dirs',
    'delete_unused_tmp_dirs',
    # Validator
    'analyze_uploaded_file',
    # Extractor
    'extract_custom_model',
    # Hasher
    'calculate_hash',
    'compare_files_by_hash',
    'hash_proxy_dict',
    'compare_dict_keys',
    # Utils
    'proxy2dict',
    'compare_file_metadata',
]
