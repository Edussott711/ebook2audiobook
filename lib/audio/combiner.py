"""
Audio Combiner Module
Handles combining audio sentences into chapters using FFmpeg.
"""

import os
import shutil
import subprocess
import tempfile
from typing import Dict, Any
from multiprocessing import Pool, cpu_count

from lib.core.exceptions import DependencyError
from lib.conf import default_audio_proc_format


def assemble_chunks(txt_file: str, out_file: str) -> bool:
    """
    Assemble audio chunks using FFmpeg concat demuxer.

    Uses FFmpeg's concat protocol to merge multiple audio files listed
    in a text file into a single output file.

    Args:
        txt_file: Path to text file containing list of audio files to concatenate
                  Format: file '/path/to/audio1.flac'
        out_file: Path to output audio file

    Returns:
        bool: True if assembly succeeded, False otherwise

    Example:
        >>> assemble_chunks('chunks.txt', 'output.flac')
        True
    """
    try:
        # Build FFmpeg command for concatenation
        ffmpeg_cmd = [
            shutil.which('ffmpeg'),
            '-hide_banner',
            '-nostats',
            '-y',  # Overwrite output file
            '-safe', '0',  # Allow unsafe file paths
            '-f', 'concat',  # Use concat demuxer
            '-i', txt_file,  # Input file list
            '-c:a', default_audio_proc_format,  # Audio codec
            '-map_metadata', '-1',  # Strip metadata
            '-threads', '1',  # Single thread (faster for small files)
            out_file
        ]

        # Execute FFmpeg process
        process = subprocess.Popen(
            ffmpeg_cmd,
            env={},
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding='utf-8',
            errors='ignore'
        )

        # Print stdout in real-time
        for line in process.stdout:
            print(line, end='')

        # Wait for completion
        process.wait()

        if process.returncode == 0:
            return True
        else:
            error = f"FFmpeg failed with return code {process.returncode}"
            print(error, ffmpeg_cmd)
            return False

    except subprocess.CalledProcessError as e:
        DependencyError(str(e))
        return False

    except Exception as e:
        error = f"assemble_chunks() Error: Failed to process {txt_file} → {out_file}: {e}"
        print(error)
        return False


def combine_audio_sentences(
    chapter_audio_file: str,
    start: int,
    end: int,
    session: Dict[str, Any]
) -> bool:
    """
    Combine audio sentence files into a single chapter file.

    Processes sentence audio files in batches for efficiency, then merges
    all batches into the final chapter file. Uses multiprocessing to
    parallelize batch assembly.

    Args:
        chapter_audio_file: Output chapter filename (will be placed in chapters_dir)
        start: Starting sentence number (inclusive)
        end: Ending sentence number (inclusive)
        session: Session context dictionary containing:
            - chapters_dir: Directory for chapter audio files
            - chapters_dir_sentences: Directory containing sentence audio files

    Returns:
        bool: True if combination succeeded, False otherwise

    Process:
        1. List all sentence audio files in range [start, end]
        2. Split into batches of 1024 files
        3. Assemble each batch in parallel (multiprocessing)
        4. Merge all batches into final chapter file

    Example:
        >>> combine_audio_sentences('chapter_1.flac', 0, 100, session)
        ********* Combined block audio file saved in /path/chapter_1.flac
        True
    """
    try:
        # Build full output path
        chapter_audio_file = os.path.join(session['chapters_dir'], chapter_audio_file)
        chapters_dir_sentences = session['chapters_dir_sentences']

        # Configuration
        batch_size = 1024  # Files per batch

        # List all sentence audio files
        sentence_files = [
            f for f in os.listdir(chapters_dir_sentences)
            if f.endswith(f'.{default_audio_proc_format}')
        ]

        # Sort by sentence number (filename without extension)
        sentences_ordered = sorted(
            sentence_files,
            key=lambda x: int(os.path.splitext(x)[0])
        )

        # Select files in range [start, end]
        selected_files = [
            os.path.join(chapters_dir_sentences, f)
            for f in sentences_ordered
            if start <= int(os.path.splitext(f)[0]) <= end
        ]

        if not selected_files:
            print('No audio files found in the specified range.')
            return False

        # Use temporary directory for intermediate files
        with tempfile.TemporaryDirectory() as tmpdir:
            chunk_list = []

            # Step 1: Create batches
            for i in range(0, len(selected_files), batch_size):
                batch = selected_files[i:i + batch_size]

                # Create file list for this batch
                txt = os.path.join(tmpdir, f'chunk_{i:04d}.txt')
                out = os.path.join(tmpdir, f'chunk_{i:04d}.{default_audio_proc_format}')

                with open(txt, 'w') as f:
                    for file in batch:
                        # Normalize path separators for FFmpeg
                        f.write(f"file '{file.replace(os.sep, '/')}'\n")

                chunk_list.append((txt, out))

            # Step 2: Assemble batches in parallel
            try:
                with Pool(cpu_count()) as pool:
                    results = pool.starmap(assemble_chunks, chunk_list)
            except Exception as e:
                error = f"combine_audio_sentences() multiprocessing error: {e}"
                print(error)
                return False

            # Check all batches succeeded
            if not all(results):
                error = "combine_audio_sentences() One or more chunks failed."
                print(error)
                return False

            # Step 3: Final merge of all batches
            final_list = os.path.join(tmpdir, 'sentences_final.txt')
            with open(final_list, 'w') as f:
                for _, chunk_path in chunk_list:
                    f.write(f"file '{chunk_path.replace(os.sep, '/')}'\n")

            # Assemble final chapter file
            if assemble_chunks(final_list, chapter_audio_file):
                msg = f'********* Combined block audio file saved in {chapter_audio_file}'
                print(msg)
                return True
            else:
                error = "combine_audio_sentences() Final merge failed."
                print(error)
                return False

    except Exception as e:
        DependencyError(str(e))
        return False
