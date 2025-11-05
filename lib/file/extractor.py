"""
File Extractor Module
Provides utilities for extracting files from archives.
"""

import os
import shutil
import zipfile
import regex as re
import asyncio
from typing import Dict, Any, List, Optional
from tqdm import tqdm
from lib.core.exceptions import DependencyError
from lib.models import models, default_fine_tuned
from lib.system.utils import get_sanitized


def extract_custom_model(
    file_src: str,
    session: Dict[str, Any],
    required_files: Optional[List[str]] = None,
    is_gui_process: bool = False
) -> Optional[str]:
    """
    Extract a custom TTS model from a ZIP archive.

    Args:
        file_src: Path to the ZIP file containing the custom model
        session: Session context dictionary containing extraction paths
        required_files: List of required files to extract (default: from models config)
        is_gui_process: Whether running in GUI mode (affects cleanup behavior)

    Returns:
        str | None: Path to the extracted model directory, or None if extraction failed
    """
    try:
        model_path = None

        # Use default required files if not specified
        if required_files is None:
            required_files = models[session['tts_engine']][default_fine_tuned]['files']

        # Sanitize model name from filename
        model_name = re.sub('.zip', '', os.path.basename(file_src), flags=re.IGNORECASE)
        model_name = get_sanitized(model_name)

        # Open ZIP and extract files
        with zipfile.ZipFile(file_src, 'r') as zip_ref:
            files = zip_ref.namelist()
            files_length = len(files)
            tts_dir = session['tts_engine']
            model_path = os.path.join(session['custom_model_dir'], tts_dir, model_name)

            # Skip extraction if model already exists
            if os.path.exists(model_path):
                print(f'{model_path} already exists, bypassing files extraction')
                return model_path

            # Create model directory
            os.makedirs(model_path, exist_ok=True)

            # Convert required files to lowercase for comparison
            required_files_lc = set(x.lower() for x in required_files)

            # Extract only required files with progress bar
            with tqdm(total=files_length, unit='files') as t:
                for f in files:
                    base_f = os.path.basename(f).lower()
                    if base_f in required_files_lc:
                        out_path = os.path.join(model_path, base_f)
                        with zip_ref.open(f) as src, open(out_path, 'wb') as dst:
                            shutil.copyfileobj(src, dst)
                    t.update(1)

        # Clean up source ZIP in GUI mode
        if is_gui_process:
            os.remove(file_src)

        if model_path is not None:
            msg = f'Extracted files to {model_path}'
            print(msg)
            return model_path
        else:
            error = f'An error occurred when unzip {file_src}'
            print(error)
            return None

    except asyncio.exceptions.CancelledError as e:
        DependencyError(str(e))
        if is_gui_process:
            os.remove(file_src)
        return None

    except Exception as e:
        DependencyError(str(e))
        if is_gui_process:
            os.remove(file_src)
        return None
