"""
Audio Converter Module
Handles conversion of text chapters to audio using TTS.
"""

import os
import regex as re
from tqdm import tqdm
import gradio as gr

from lib.tts import TTSManager
from lib.core.session import context
from lib.core.exceptions import DependencyError
from lib.conf import default_audio_proc_format, TTS_SML
from lib.audio.combiner import combine_audio_sentences


def convert_chapters2audio(id: str) -> bool:
    """
    Convert all chapters in a session to audio files using TTS.

    This is the main orchestration function that:
    1. Initializes the TTS engine (TTSManager)
    2. Detects resume points for chapters and sentences
    3. Processes each sentence through TTS
    4. Combines sentences into chapter audio files
    5. Provides progress tracking via tqdm and Gradio

    Resume Capability:
        - Automatically detects existing chapter and sentence files
        - Resumes from the last completed sentence
        - Recovers missing files in the sequence

    Args:
        id: Session identifier

    Returns:
        bool: True if conversion succeeded, False otherwise

    Process Flow:
        1. Load session and initialize TTS engine
        2. Scan for existing audio files (chapters and sentences)
        3. Calculate resume points and missing files
        4. For each chapter:
            a. Process each sentence through TTS
            b. Save individual sentence audio files
            c. Combine sentences into chapter file
        5. Track progress with visual feedback

    Example:
        >>> convert_chapters2audio('session_123')
        Resuming from block 3
        Resuming from sentence 42
        --------------------------------------------------
        A total of 10 blocks and 234 sentences.
        --------------------------------------------------
        Block 3 containing 25 sentences...
        ...
        True

    Notes:
        - Uses multiprocessing for TTS (via TTSManager)
        - Supports cancellation via session['cancellation_requested']
        - Requires sufficient VRAM/RAM for TTS engine
        - Preserves SML (Speech Markup Language) tags
    """
    session = context.get_session(id)
    try:
        # Check for cancellation request
        if session['cancellation_requested']:
            print('Cancel requested')
            return False

        # Initialize TTS engine
        tts_manager = TTSManager(session)
        if not tts_manager:
            error = f"TTS engine {session['tts_engine']} could not be loaded!\nPossible reason can be not enough VRAM/RAM memory.\nTry to lower max_tts_in_memory in ./lib/models.py"
            print(error)
            return False

        # Resume detection for chapters
        resume_chapter = 0
        missing_chapters = []
        existing_chapters = sorted(
            [f for f in os.listdir(session['chapters_dir']) if f.endswith(f'.{default_audio_proc_format}')],
            key=lambda x: int(re.search(r'\d+', x).group())
        )
        if existing_chapters:
            resume_chapter = max(int(re.search(r'\d+', f).group()) for f in existing_chapters)
            msg = f'Resuming from block {resume_chapter}'
            print(msg)
            existing_chapter_numbers = {int(re.search(r'\d+', f).group()) for f in existing_chapters}
            missing_chapters = [
                i for i in range(1, resume_chapter) if i not in existing_chapter_numbers
            ]
            if resume_chapter not in missing_chapters:
                missing_chapters.append(resume_chapter)

        # Resume detection for sentences
        resume_sentence = 0
        missing_sentences = []
        existing_sentences = sorted(
            [f for f in os.listdir(session['chapters_dir_sentences']) if f.endswith(f'.{default_audio_proc_format}')],
            key=lambda x: int(re.search(r'\d+', x).group())
        )
        if existing_sentences:
            resume_sentence = max(int(re.search(r'\d+', f).group()) for f in existing_sentences)
            msg = f"Resuming from sentence {resume_sentence}"
            print(msg)
            existing_sentence_numbers = {int(re.search(r'\d+', f).group()) for f in existing_sentences}
            missing_sentences = [
                i for i in range(1, resume_sentence) if i not in existing_sentence_numbers
            ]
            if resume_sentence not in missing_sentences:
                missing_sentences.append(resume_sentence)

        # Validate chapters exist
        total_chapters = len(session['chapters'])
        if total_chapters == 0:
            error = 'No chapterrs found!'
            print(error)
            return False

        # Calculate totals
        total_iterations = sum(len(session['chapters'][x]) for x in range(total_chapters))
        total_sentences = sum(sum(1 for row in chapter if row.strip() not in TTS_SML.values()) for chapter in session['chapters'])
        if total_sentences == 0:
            error = 'No sentences found!'
            print(error)
            return False

        sentence_number = 0
        msg = f"--------------------------------------------------\nA total of {total_chapters} {'block' if total_chapters <= 1 else 'blocks'} and {total_sentences} {'sentence' if total_sentences <= 1 else 'sentences'}.\n--------------------------------------------------"
        print(msg)

        # Initialize progress tracking
        progress_bar = gr.Progress(track_tqdm=False)

        # Main conversion loop
        with tqdm(total=total_iterations, desc='0.00%', bar_format='{desc}: {n_fmt}/{total_fmt} ', unit='step', initial=0) as t:
            for x in range(0, total_chapters):
                chapter_num = x + 1
                chapter_audio_file = f'chapter_{chapter_num}.{default_audio_proc_format}'
                sentences = session['chapters'][x]
                sentences_count = sum(1 for row in sentences if row.strip() not in TTS_SML.values())
                start = sentence_number

                msg = f'Block {chapter_num} containing {sentences_count} sentences...'
                print(msg)

                # Process each sentence
                for i, sentence in enumerate(sentences):
                    # Check cancellation
                    if session['cancellation_requested']:
                        msg = 'Cancel requested'
                        print(msg)
                        return False

                    # Process sentence if needed (resume logic)
                    if sentence_number in missing_sentences or sentence_number > resume_sentence or (sentence_number == 0 and resume_sentence == 0):
                        if sentence_number <= resume_sentence and sentence_number > 0:
                            msg = f'**Recovering missing file sentence {sentence_number}'
                            print(msg)

                        sentence = sentence.strip()
                        success = tts_manager.convert_sentence2audio(sentence_number, sentence) if sentence else True

                        if success:
                            # Update progress
                            total_progress = (t.n + 1) / total_iterations
                            progress_bar(total_progress)
                            is_sentence = sentence.strip() not in TTS_SML.values()
                            percentage = total_progress * 100
                            t.set_description(f'{percentage:.2f}%')
                            msg = f" | {sentence}" if is_sentence else f" | {sentence}"
                            print(msg)
                        else:
                            return False

                    # Increment sentence counter (skip SML tags)
                    if sentence.strip() not in TTS_SML.values():
                        sentence_number += 1

                    t.update(1)  # advance for every iteration, including SML

                end = sentence_number - 1 if sentence_number > 1 else sentence_number
                msg = f"End of Block {chapter_num}"
                print(msg)

                # Combine sentences into chapter file
                if chapter_num in missing_chapters or sentence_number > resume_sentence:
                    if chapter_num <= resume_chapter:
                        msg = f'**Recovering missing file block {chapter_num}'
                        print(msg)

                    if combine_audio_sentences(chapter_audio_file, start, end, session):
                        msg = f'Combining block {chapter_num} to audio, sentence {start} to {end}'
                        print(msg)
                    else:
                        msg = 'combine_audio_sentences() failed!'
                        print(msg)
                        return False

        return True

    except Exception as e:
        DependencyError(e)
        return False
