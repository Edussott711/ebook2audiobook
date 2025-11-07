"""
Audio Exporter Module
Handles export of audio chapters to various formats with FFmpeg metadata.

Supports multi-format export (AAC, FLAC, MP3, M4B, M4A, MP4, OGG, WAV, WebM)
with chapter timestamps, metadata, and cover art integration.
"""

import os
import re
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from multiprocessing import Pool, cpu_count

from pydub import AudioSegment

from lib.core.session import context
from lib.core.exceptions import DependencyError
from lib.conf import default_audio_proc_format, TTS_SML
from lib.system.utils import get_sanitized
from lib.audio.combiner import assemble_chunks


def combine_audio_chapters(id: str) -> list[str] | None:
    """
    Combine audio chapters and export to final audiobook format(s).

    This function orchestrates the complete audio export pipeline:
    1. Calculates total duration
    2. Splits into parts if needed (based on duration)
    3. Generates FFmpeg metadata (chapters, tags, cover)
    4. Exports to selected format (AAC, FLAC, MP3, M4B, etc.)
    5. Applies audio normalization and noise reduction
    6. Adds cover art (MP3, M4B, M4A, MP4)
    7. Moves VTT subtitle file

    Supported Output Formats:
        - **AAC**: 192k bitrate, 44.1kHz
        - **FLAC**: Lossless, compression level 5
        - **MP3**: libmp3lame, 192k bitrate
        - **M4B/M4A/MP4/MOV**: AAC in MP4 container with chapters
        - **OGG/WebM**: Opus codec with Vorbis metadata
        - **WAV**: Uncompressed PCM, 44.1kHz, 16-bit

    Split Functionality:
        - Automatically splits if total duration > (split_hours * 2)
        - Each part gets separate metadata and chapter list
        - Parts are numbered: filename_part1.ext, filename_part2.ext

    Args:
        id: Session identifier

    Returns:
        list[str]: List of exported file paths
        None: If export fails or no chapters found

    Example:
        >>> exported = combine_audio_chapters('session_123')
        >>> print(exported)
        ['/path/to/audiobooks/MyBook.m4b']

        >>> # With split
        >>> exported = combine_audio_chapters('session_456')
        >>> print(exported)
        ['/path/to/audiobooks/LongBook_part1.m4b',
         '/path/to/audiobooks/LongBook_part2.m4b']

    Process Flow:
        1. **Duration Calculation** - ffprobe each chapter
        2. **Split Decision** - Based on output_split setting
        3. **Batch Processing** - 1024 files per batch with multiprocessing
        4. **Metadata Generation** - FFmpeg metadata format
        5. **Audio Export** - Format-specific FFmpeg command
        6. **Cover Art** - Mutagen for MP3/M4B/M4A/MP4
        7. **File Moving** - VTT subtitle to final location

    Metadata Support:
        - **Vorbis** (OGG, WebM): Uppercase keys (TITLE, ARTIST, DATE)
        - **MP4** (M4B, M4A, MP4, MOV): Standard keys + faststart
        - **MP3**: ID3 tags + APIC cover art
        - **ISBN/ASIN**: Included for MP3 and MP4 formats

    Audio Processing:
        - **Loudness Normalization**: -16 LUFS integrated, LRA 11, TP -1.5
        - **Noise Reduction**: FFmpeg afftdn filter, -70dB floor

    Notes:
        - Uses multiprocessing (cpu_count()) for batch assembly
        - Temporary files managed with tempfile.TemporaryDirectory
        - Cover art embedded via mutagen (MP3, M4B, M4A, MP4)
        - VTT file automatically moved to final location
        - Respects cancellation_requested flag
    """

    def get_audio_duration(filepath: str) -> float:
        """
        Get audio file duration using ffprobe.

        Args:
            filepath: Path to audio file

        Returns:
            float: Duration in seconds
            0: If ffprobe fails
        """
        try:
            ffprobe_cmd = [
                shutil.which('ffprobe'),
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'json',
                filepath
            ]
            result = subprocess.run(ffprobe_cmd, capture_output=True, text=True)
            try:
                return float(json.loads(result.stdout)['format']['duration'])
            except Exception:
                return 0
        except subprocess.CalledProcessError as e:
            DependencyError(e)
            return 0
        except Exception as e:
            error = f"get_audio_duration() Error: Failed to process {filepath}: {e}"
            print(error)
            return 0

    def generate_ffmpeg_metadata(
        part_chapters: list[tuple[str, str]],
        session: dict,
        output_metadata_path: str,
        default_audio_proc_format: str
    ) -> str | bool:
        """
        Generate FFmpeg metadata file with chapters and tags.

        Creates FFMETADATA1 format file with:
        - Book metadata (title, artist, language, description, publisher)
        - Year/date from published field
        - ISBN/ASIN identifiers (MP3/MP4 only)
        - Chapter markers with timestamps

        Metadata Format Handling:
            - **Vorbis** (OGG, WebM): Uppercase keys, DATE field
            - **MP4/MP3**: Standard case keys, year field
            - **Publisher**: Only for MP4 and MP3

        Args:
            part_chapters: List of (filename, chapter_title) tuples
            session: Session dictionary with metadata
            output_metadata_path: Output path for metadata file
            default_audio_proc_format: Audio processing format

        Returns:
            str: Path to metadata file
            False: If generation fails
        """
        try:
            out_fmt = session['output_format']
            is_mp4_like = out_fmt in ['mp4', 'm4a', 'm4b', 'mov']
            is_vorbis = out_fmt in ['ogg', 'webm']
            is_mp3 = out_fmt == 'mp3'

            def tag(key: str) -> str:
                """Convert tag key to format-specific case."""
                return key.upper() if is_vorbis else key

            # Start metadata file
            ffmpeg_metadata = ';FFMETADATA1\n'

            # Add book metadata
            if session['metadata'].get('title'):
                ffmpeg_metadata += f"{tag('title')}={session['metadata']['title']}\n"
            if session['metadata'].get('creator'):
                ffmpeg_metadata += f"{tag('artist')}={session['metadata']['creator']}\n"
            if session['metadata'].get('language'):
                ffmpeg_metadata += f"{tag('language')}={session['metadata']['language']}\n"
            if session['metadata'].get('description'):
                ffmpeg_metadata += f"{tag('description')}={session['metadata']['description']}\n"
            if session['metadata'].get('publisher') and (is_mp4_like or is_mp3):
                ffmpeg_metadata += f"{tag('publisher')}={session['metadata']['publisher']}\n"

            # Parse published date for year
            if session['metadata'].get('published'):
                try:
                    if '.' in session['metadata']['published']:
                        year = datetime.strptime(session['metadata']['published'], '%Y-%m-%dT%H:%M:%S.%f%z').year
                    else:
                        year = datetime.strptime(session['metadata']['published'], '%Y-%m-%dT%H:%M:%S%z').year
                except Exception:
                    year = datetime.now().year
            else:
                year = datetime.now().year

            # Add year/date
            if is_vorbis:
                ffmpeg_metadata += f"{tag('date')}={year}\n"
            else:
                ffmpeg_metadata += f"{tag('year')}={year}\n"

            # Add identifiers (ISBN, ASIN)
            if session['metadata'].get('identifiers') and isinstance(session['metadata']['identifiers'], dict):
                if is_mp3 or is_mp4_like:
                    isbn = session['metadata']['identifiers'].get('isbn')
                    if isbn:
                        ffmpeg_metadata += f"{tag('isbn')}={isbn}\n"
                    asin = session['metadata']['identifiers'].get('mobi-asin')
                    if asin:
                        ffmpeg_metadata += f"{tag('asin')}={asin}\n"

            # Add chapter markers
            start_time = 0
            for filename, chapter_title in part_chapters:
                filepath = os.path.join(session['chapters_dir'], filename)
                duration_ms = len(AudioSegment.from_file(filepath, format=default_audio_proc_format))

                # Clean chapter title (escape special chars)
                clean_title = re.sub(
                    r'(^#)|[=\\]|(-$)',
                    lambda m: '\\' + (m.group(1) or m.group(0)),
                    chapter_title.replace(TTS_SML['pause'], '')
                )

                # Add chapter
                ffmpeg_metadata += '[CHAPTER]\nTIMEBASE=1/1000\n'
                ffmpeg_metadata += f'START={start_time}\nEND={start_time + duration_ms}\n'
                ffmpeg_metadata += f"{tag('title')}={clean_title}\n"
                start_time += duration_ms

            # Write metadata file
            with open(output_metadata_path, 'w', encoding='utf-8') as f:
                f.write(ffmpeg_metadata)

            return output_metadata_path

        except Exception as e:
            error = f"generate_ffmpeg_metadata() Error: {e}"
            print(error)
            return False

    def export_audio(
        ffmpeg_combined_audio: str,
        ffmpeg_metadata_file: str,
        ffmpeg_final_file: str
    ) -> bool:
        """
        Export combined audio to final format with metadata and cover art.

        Builds format-specific FFmpeg command with:
        - Audio codec and bitrate settings
        - Metadata mapping
        - Loudness normalization
        - Noise reduction
        - Cover art embedding (MP3, M4B, M4A, MP4)

        Format Settings:
            - **WAV**: PCM 44.1kHz, 16-bit
            - **AAC**: 192k, 44.1kHz
            - **FLAC**: Compression 5, 44.1kHz, 16-bit
            - **MP3**: libmp3lame 192k, 44.1kHz
            - **M4B/M4A/MP4**: AAC 192k, faststart, metadata tags
            - **WebM**: Opus 192k, 48kHz
            - **OGG**: Opus 192k, 48kHz, compression 0

        Args:
            ffmpeg_combined_audio: Path to combined audio file
            ffmpeg_metadata_file: Path to metadata file
            ffmpeg_final_file: Path to final output file

        Returns:
            bool: True if export succeeded, False otherwise
        """
        try:
            if session['cancellation_requested']:
                print('Cancel requested')
                return False

            cover_path = None
            ffmpeg_cmd = [shutil.which('ffmpeg'), '-hide_banner', '-nostats', '-i', ffmpeg_combined_audio]

            # Format-specific encoding
            if session['output_format'] == 'wav':
                ffmpeg_cmd += ['-map', '0:a', '-ar', '44100', '-sample_fmt', 's16']

            elif session['output_format'] == 'aac':
                ffmpeg_cmd += ['-c:a', 'aac', '-b:a', '192k', '-ar', '44100']

            elif session['output_format'] == 'flac':
                ffmpeg_cmd += ['-c:a', 'flac', '-compression_level', '5', '-ar', '44100', '-sample_fmt', 's16']

            else:
                # Formats with metadata support
                ffmpeg_cmd += ['-f', 'ffmetadata', '-i', ffmpeg_metadata_file, '-map', '0:a']

                if session['output_format'] in ['m4a', 'm4b', 'mp4', 'mov']:
                    ffmpeg_cmd += ['-c:a', 'aac', '-b:a', '192k', '-ar', '44100', '-movflags', '+faststart+use_metadata_tags']

                elif session['output_format'] == 'mp3':
                    ffmpeg_cmd += ['-c:a', 'libmp3lame', '-b:a', '192k', '-ar', '44100']

                elif session['output_format'] == 'webm':
                    ffmpeg_cmd += ['-c:a', 'libopus', '-b:a', '192k', '-ar', '48000']

                elif session['output_format'] == 'ogg':
                    ffmpeg_cmd += ['-c:a', 'libopus', '-compression_level', '0', '-b:a', '192k', '-ar', '48000']

                ffmpeg_cmd += ['-map_metadata', '1']

            # Audio filters: loudness normalization + noise reduction
            ffmpeg_cmd += [
                '-af', 'loudnorm=I=-16:LRA=11:TP=-1.5,afftdn=nf=-70',
                '-strict', 'experimental',
                '-threads', '1',
                '-y',
                ffmpeg_final_file
            ]

            # Execute FFmpeg
            process = subprocess.Popen(
                ffmpeg_cmd,
                env={},
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                encoding='utf-8',
                errors='ignore'
            )

            # Stream output
            for line in process.stdout:
                print(line, end='')

            process.wait()

            if process.returncode == 0:
                # Add cover art for supported formats
                if session['output_format'] in ['mp3', 'm4a', 'm4b', 'mp4']:
                    if session['cover'] is not None:
                        cover_path = session['cover']
                        msg = f'Adding cover {cover_path} into the final audiobook file...'
                        print(msg)

                        if session['output_format'] == 'mp3':
                            # MP3: ID3 APIC tag
                            from mutagen.mp3 import MP3
                            from mutagen.id3 import ID3, APIC, error

                            audio = MP3(ffmpeg_final_file, ID3=ID3)
                            try:
                                audio.add_tags()
                            except error:
                                pass

                            with open(cover_path, 'rb') as img:
                                audio.tags.add(
                                    APIC(
                                        encoding=3,
                                        mime='image/jpeg',
                                        type=3,
                                        desc='Cover',
                                        data=img.read()
                                    )
                                )

                        elif session['output_format'] in ['mp4', 'm4a', 'm4b']:
                            # MP4: covr atom
                            from mutagen.mp4 import MP4, MP4Cover

                            audio = MP4(ffmpeg_final_file)
                            with open(cover_path, 'rb') as f:
                                cover_data = f.read()
                            audio["covr"] = [MP4Cover(cover_data, imageformat=MP4Cover.FORMAT_JPEG)]

                        if audio:
                            audio.save()

                # Move VTT subtitle file
                final_vtt = f"{Path(ffmpeg_final_file).stem}.vtt"
                proc_vtt_path = os.path.join(session['process_dir'], final_vtt)
                final_vtt_path = os.path.join(session['audiobooks_dir'], final_vtt)
                shutil.move(proc_vtt_path, final_vtt_path)

                return True
            else:
                error = process.returncode
                print(error, ffmpeg_cmd)
                return False

        except Exception as e:
            DependencyError(e)
            return False

    # Main function body
    try:
        session = context.get_session(id)

        # Get all chapter files
        chapter_files = [f for f in os.listdir(session['chapters_dir']) if f.endswith(f'.{default_audio_proc_format}')]
        chapter_files = sorted(chapter_files, key=lambda x: int(re.search(r'\d+', x).group()))
        chapter_titles = [c[0] for c in session['chapters']]

        if len(chapter_files) == 0:
            print('No block files exists!')
            return None

        # Calculate total duration
        durations = []
        for file in chapter_files:
            filepath = os.path.join(session['chapters_dir'], file)
            durations.append(get_audio_duration(filepath))
        total_duration = sum(durations)

        exported_files = []

        # Split logic
        if session.get('output_split'):
            part_files = []
            part_chapter_indices = []
            cur_part = []
            cur_indices = []
            cur_duration = 0
            max_part_duration = session['output_split_hours'] * 3600
            needs_split = total_duration > (int(session['output_split_hours']) * 2) * 3600

            # Split into parts
            for idx, (file, dur) in enumerate(zip(chapter_files, durations)):
                if cur_part and (cur_duration + dur > max_part_duration):
                    part_files.append(cur_part)
                    part_chapter_indices.append(cur_indices)
                    cur_part = []
                    cur_indices = []
                    cur_duration = 0
                cur_part.append(file)
                cur_indices.append(idx)
                cur_duration += dur

            if cur_part:
                part_files.append(cur_part)
                part_chapter_indices.append(cur_indices)

            # Process each part
            for part_idx, (part_file_list, indices) in enumerate(zip(part_files, part_chapter_indices)):
                with tempfile.TemporaryDirectory() as tmpdir:
                    # Batch assembly (1024 files per batch)
                    batch_size = 1024
                    chunk_list = []

                    for i in range(0, len(part_file_list), batch_size):
                        batch = part_file_list[i:i + batch_size]
                        txt = os.path.join(tmpdir, f'chunk_{i:04d}.txt')
                        out = os.path.join(tmpdir, f'chunk_{i:04d}.{default_audio_proc_format}')

                        with open(txt, 'w') as f:
                            for file in batch:
                                path = os.path.join(session['chapters_dir'], file).replace("\\", "/")
                                f.write(f"file '{path}'\n")

                        chunk_list.append((txt, out))

                    # Parallel batch assembly
                    with Pool(cpu_count()) as pool:
                        results = pool.starmap(assemble_chunks, chunk_list)

                    if not all(results):
                        print(f"assemble_segments() One or more chunks failed for part {part_idx+1}.")
                        return None

                    # Final merge for this part
                    combined_chapters_file = os.path.join(
                        session['process_dir'],
                        f"{get_sanitized(session['metadata']['title'])}_part{part_idx+1}.{default_audio_proc_format}" if needs_split else f"{get_sanitized(session['metadata']['title'])}.{default_audio_proc_format}"
                    )

                    final_list = os.path.join(tmpdir, f'part_{part_idx+1:02d}_final.txt')
                    with open(final_list, 'w') as f:
                        for _, chunk_path in chunk_list:
                            f.write(f"file '{chunk_path.replace(os.sep, '/')}'\n")

                    if not assemble_chunks(final_list, combined_chapters_file):
                        print(f"assemble_segments() Final merge failed for part {part_idx+1}.")
                        return None

                    # Generate metadata for this part
                    metadata_file = os.path.join(session['process_dir'], f'metadata_part{part_idx+1}.txt')
                    part_chapters = [(chapter_files[i], chapter_titles[i]) for i in indices]
                    generate_ffmpeg_metadata(part_chapters, session, metadata_file, default_audio_proc_format)

                    # Export this part
                    final_file = os.path.join(
                        session['audiobooks_dir'],
                        f"{session['final_name'].rsplit('.', 1)[0]}_part{part_idx+1}.{session['output_format']}" if needs_split else session['final_name']
                    )

                    if export_audio(combined_chapters_file, metadata_file, final_file):
                        exported_files.append(final_file)

        else:
            # No split - export as single file
            with tempfile.TemporaryDirectory() as tmpdir:
                # Build single ffmpeg file list
                txt = os.path.join(tmpdir, 'all_chapters.txt')
                merged_tmp = os.path.join(tmpdir, f'all.{default_audio_proc_format}')

                with open(txt, 'w') as f:
                    for file in chapter_files:
                        path = os.path.join(session['chapters_dir'], file).replace("\\", "/")
                        f.write(f"file '{path}'\n")

                # Merge into one temp file
                if not assemble_chunks(txt, merged_tmp):
                    print("assemble_segments() Final merge failed.")
                    return None

                # Generate metadata for entire book
                metadata_file = os.path.join(session['process_dir'], 'metadata.txt')
                all_chapters = list(zip(chapter_files, chapter_titles))
                generate_ffmpeg_metadata(all_chapters, session, metadata_file, default_audio_proc_format)

                # Export in one go
                final_file = os.path.join(
                    session['audiobooks_dir'],
                    session['final_name']
                )

                if export_audio(merged_tmp, metadata_file, final_file):
                    exported_files.append(final_file)

        return exported_files if exported_files else None

    except Exception as e:
        DependencyError(e)
        return False
