"""
EPUB Converter Module
Handles conversion of various ebook formats to EPUB.
"""

import os
import re
import shutil
import subprocess
from typing import Dict, Any, Optional
from lib.core.exceptions import DependencyError
from lib.conf import ebook_formats


def convert2epub(session: Dict[str, Any]) -> bool:
    """
    Convert an ebook file to EPUB format using Calibre's ebook-convert utility.

    Supports PDF, MOBI, AZW3, and other formats. For PDFs, performs special
    processing to flatten the content to Markdown before conversion.

    Args:
        session: Session context dictionary containing:
            - ebook: Path to the input ebook file
            - epub_path: Path where the EPUB output should be saved
            - process_dir: Working directory for temporary files
            - cancellation_requested: Flag to check for cancellation

    Returns:
        bool: True if conversion succeeded, False otherwise
    """
    if session.get('cancellation_requested'):
        print('Cancel requested')
        return False

    try:
        title = False
        author = False

        # Check if ebook-convert utility is available
        util_app = shutil.which('ebook-convert')
        if not util_app:
            error = "The 'ebook-convert' utility is not installed or not found."
            print(error)
            return False

        file_input = session['ebook']

        # Validate input file
        if os.path.getsize(file_input) == 0:
            error = f"Input file is empty: {file_input}"
            print(error)
            return False

        file_ext = os.path.splitext(file_input)[1].lower()
        if file_ext not in ebook_formats:
            error = f'Unsupported file format: {file_ext}'
            print(error)
            return False

        # Special handling for PDF files
        if file_ext == '.pdf':
            import fitz
            import pymupdf4llm

            msg = 'File input is a PDF. Flatten it to Markdown...'
            print(msg)

            # Extract PDF metadata
            doc = fitz.open(session['ebook'])
            pdf_metadata = doc.metadata
            filename_no_ext = os.path.splitext(os.path.basename(session['ebook']))[0]

            title = pdf_metadata.get('title') or filename_no_ext
            author = pdf_metadata.get('author') or False

            # Convert PDF to Markdown
            markdown_text = pymupdf4llm.to_markdown(session['ebook'])

            # Remove single asterisks for italics (but not bold **)
            markdown_text = re.sub(r'(?<!\*)\*(?!\*)(.*?)\*(?!\*)', r'\1', markdown_text)

            # Remove single underscores for italics (but not bold __)
            markdown_text = re.sub(r'(?<!_)_(?!_)(.*?)_(?!_)', r'\1', markdown_text)

            # Save as Markdown file
            file_input = os.path.join(session['process_dir'], f'{filename_no_ext}.md')
            with open(file_input, "w", encoding="utf-8") as md_file:
                md_file.write(markdown_text)

        # Build ebook-convert command
        msg = f"Running command: {util_app} {file_input} {session['epub_path']}"
        print(msg)

        cmd = [
            util_app, file_input, session['epub_path'],
            '--input-encoding=utf-8',
            '--output-profile=generic_eink',
            '--epub-version=3',
            '--flow-size=0',
            '--chapter-mark=pagebreak',
            '--page-breaks-before', "//*[name()='h1' or name()='h2' or name()='h3' or name()='h4' or name()='h5']",
            '--disable-font-rescaling',
            '--pretty-print',
            '--smarten-punctuation',
            '--verbose'
        ]

        # Add optional title and author if available
        if title:
            cmd += ['--title', title]
        if author:
            cmd += ['--authors', author]

        # Execute conversion
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )

        print(result.stdout)
        return True

    except subprocess.CalledProcessError as e:
        print(f"Subprocess error: {e.stderr}")
        DependencyError(str(e))
        return False

    except FileNotFoundError as e:
        print(f"Utility not found: {e}")
        DependencyError(str(e))
        return False
