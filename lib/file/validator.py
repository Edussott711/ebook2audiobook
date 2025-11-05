"""
File Validator Module
Provides utilities for validating files and archives.
"""

import os
import zipfile
from typing import List


def analyze_uploaded_file(zip_path: str, required_files: List[str]) -> bool:
    """
    Analyze a ZIP file to verify it contains all required files.

    Checks that:
    1. The ZIP file exists and is valid
    2. All required files are present
    3. No required files are empty (0 KB)

    Args:
        zip_path: Path to the ZIP file to analyze
        required_files: List of required file names (case-insensitive)

    Returns:
        bool: True if all requirements are met, False otherwise

    Raises:
        ValueError: If the file is not a valid ZIP archive
        RuntimeError: If an error occurs during analysis
    """
    try:
        # Check if file exists
        if not os.path.exists(zip_path):
            error = f"The file does not exist: {os.path.basename(zip_path)}"
            print(error)
            return False

        files_in_zip = {}
        empty_files = set()

        # Open and analyze the ZIP file
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for file_info in zf.infolist():
                file_name = file_info.filename

                # Skip directories
                if file_info.is_dir():
                    continue

                # Extract base filename and store size
                base_name = os.path.basename(file_name)
                files_in_zip[base_name.lower()] = file_info.file_size

                # Track empty files
                if file_info.file_size == 0:
                    empty_files.add(base_name.lower())

        # Convert required files to lowercase for case-insensitive comparison
        required_files = [file.lower() for file in required_files]

        # Check for missing files
        missing_files = [f for f in required_files if f not in files_in_zip]

        # Check for empty required files
        required_empty_files = [f for f in required_files if f in empty_files]

        # Report issues
        if missing_files:
            print(f"Missing required files: {missing_files}")

        if required_empty_files:
            print(f"Required files with 0 KB: {required_empty_files}")

        # Return True only if no missing or empty required files
        return not missing_files and not required_empty_files

    except zipfile.BadZipFile:
        error = "The file is not a valid ZIP archive."
        raise ValueError(error)
    except Exception as e:
        error = f"An error occurred: {e}"
        raise RuntimeError(error)
