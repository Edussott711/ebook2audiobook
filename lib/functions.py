# NOTE!!NOTE!!!NOTE!!NOTE!!!NOTE!!NOTE!!!NOTE!!NOTE!!!
# THE WORD "CHAPTER" IN THE CODE DOES NOT MEAN
# IT'S THE REAL CHAPTER OF THE EBOOK SINCE NO STANDARDS
# ARE DEFINING A CHAPTER ON .EPUB FORMAT. THE WORD "BLOCK"
# IS USED TO PRINT IT OUT TO THE TERMINAL, AND "CHAPTER" TO THE CODE
# WHICH IS LESS GENERIC FOR THE DEVELOPERS

import argparse, asyncio, csv, fnmatch, hashlib, io, json, math, os, platform, random, shutil, socket, subprocess, sys, tempfile, threading, time, traceback
import unicodedata, urllib.request, uuid, zipfile, ebooklib, gradio as gr, psutil, pymupdf4llm, regex as re, requests, stanza, torch, uvicorn

from soynlp.tokenizer import LTokenizer
from pythainlp.tokenize import word_tokenize
from sudachipy import dictionary, tokenizer
from PIL import Image
from tqdm import tqdm
from bs4 import BeautifulSoup, NavigableString, Tag
from collections import Counter
from collections.abc import Mapping
from collections.abc import MutableMapping
from datetime import datetime
from ebooklib import epub
from glob import glob
from iso639 import languages
from markdown import markdown
from multiprocessing import Pool, cpu_count
from multiprocessing import Manager, Event
from multiprocessing.managers import DictProxy, ListProxy
from num2words import num2words
from pathlib import Path
from pydub import AudioSegment
from pydub.utils import mediainfo
from queue import Queue, Empty
from types import MappingProxyType
from urllib.parse import urlparse
from starlette.requests import ClientDisconnect

from lib import *
from lib.classes.voice_extractor import VoiceExtractor
from lib.classes.tts_manager import TTSManager
from lib.checkpoint_manager import CheckpointManager
from lib.session_persistence import SessionPersistence
# Import refactored SRP modules - Audio processing
from lib.audio.converter import convert_chapters2audio
from lib.audio.combiner import combine_audio_sentences, assemble_chunks
from lib.audio.exporter import combine_audio_chapters
# Import refactored SRP modules - Text processing
from lib.text.processor import filter_chapter
from lib.text.sentence_splitter import get_sentences
from lib.text.number_converter import roman2number, set_formatted_number
from lib.text.date_converter import year2words, clock2words, get_date_entities
from lib.text.math_converter import math2words
from lib.text.normalizer import normalize_text
# Import refactored SRP modules - Ebook processing
from lib.ebook.extractor import get_chapters, get_cover
from lib.ebook.metadata import get_ebook_title
from lib.ebook.converter import convert2epub
# Import refactored SRP modules - Session utilities
from lib.core.session.session_utils import recursive_proxy
# Import refactored SRP modules - System utilities
from lib.system.utils import get_sanitized
# Import refactored SRP modules - File management
from lib.file import (
    prepare_dirs,
    delete_unused_tmp_dirs,
    analyze_uploaded_file,
    extract_custom_model,
    calculate_hash,
    compare_files_by_hash,
    hash_proxy_dict,
    compare_dict_keys,
    proxy2dict,
    compare_file_metadata
)
#from lib.classes.redirect_console import RedirectConsole
#from lib.classes.argos_translator import ArgosTranslator

# Import global context module (defined in lib.context to avoid circular imports)
# Use importlib to avoid conflict with 'context' variable exported from lib.__init__
import importlib
context_module = importlib.import_module('lib.context')

#import logging
#logging.basicConfig(
#    level=logging.INFO, # DEBUG for more verbosity
#    format="%(asctime)s [%(levelname)s] %(message)s"
#)

# Import DependencyError from the core exceptions module
from lib.core.exceptions import DependencyError

class SessionTracker:
    def __init__(self):
        self.lock = threading.Lock()

    def start_session(self, id):
        with self.lock:
            session = context_module.context.get_session(id)
            if session['status'] is None:
                session['status'] = 'ready'
                return True
        return False

    def end_session(self, id, socket_hash):
        context_module.active_sessions.discard(socket_hash)
        with self.lock:
            session = context_module.context.get_session(id)
            # Don't cancel the conversion process when Gradio disconnects
            # Only clean up UI-related session metadata
            # session['cancellation_requested'] = True  # Removed - process should continue
            session['tab_id'] = None
            # Keep status to allow process to continue
            # session['status'] = None  # Removed - maintain conversion state
            session[socket_hash] = None

class SessionContext:
    def __init__(self):
        self.manager = Manager()
        self.sessions = self.manager.dict()
        self.cancellation_events = {}

    def get_session(self, id):
        if id not in self.sessions:
            self.sessions[id] = recursive_proxy({
                "script_mode": NATIVE,
                "id": id,
                "tab_id": None,
                "process_id": None,
                "status": None,
                "event": None,
                "progress": 0,
                "cancellation_requested": False,
                "device": default_device,
                "system": None,
                "client": None,
                "language": default_language_code,
                "language_iso1": None,
                "audiobook": None,
                "audiobooks_dir": None,
                "process_dir": None,
                "ebook": None,
                "ebook_list": None,
                "ebook_mode": "single",
                "chapters_dir": None,
                "chapters_dir_sentences": None,
                "epub_path": None,
                "filename_noext": None,
                "tts_engine": default_tts_engine,
                "fine_tuned": default_fine_tuned,
                "voice": None,
                "voice_dir": None,
                "custom_model": None,
                "custom_model_dir": None,
                "temperature": default_engine_settings[TTS_ENGINES['XTTSv2']]['temperature'],
                "length_penalty": default_engine_settings[TTS_ENGINES['XTTSv2']]['length_penalty'],
                "num_beams": default_engine_settings[TTS_ENGINES['XTTSv2']]['num_beams'],
                "repetition_penalty": default_engine_settings[TTS_ENGINES['XTTSv2']]['repetition_penalty'],
                "top_k": default_engine_settings[TTS_ENGINES['XTTSv2']]['top_k'],
                "top_p": default_engine_settings[TTS_ENGINES['XTTSv2']]['top_p'],
                "speed": default_engine_settings[TTS_ENGINES['XTTSv2']]['speed'],
                "enable_text_splitting": default_engine_settings[TTS_ENGINES['XTTSv2']]['enable_text_splitting'],
                "text_temp": default_engine_settings[TTS_ENGINES['BARK']]['text_temp'],
                "waveform_temp": default_engine_settings[TTS_ENGINES['BARK']]['waveform_temp'],
                "final_name": None,
                "output_format": default_output_format,
                "output_split": default_output_split,
                "output_split_hours": default_output_split_hours,
                "metadata": {
                    "title": None, 
                    "creator": None,
                    "contributor": None,
                    "language": None,
                    "identifier": None,
                    "publisher": None,
                    "date": None,
                    "description": None,
                    "subject": None,
                    "rights": None,
                    "format": None,
                    "type": None,
                    "coverage": None,
                    "relation": None,
                    "Source": None,
                    "Modified": None,
                },
                "toc": None,
                "chapters": None,
                "cover": None,
                "duration": 0,
                "playback_time": 0,
                "created_at": datetime.now().isoformat()
            }, manager=self.manager)
        return self.sessions[id]

    def find_id_by_hash(self, socket_hash):
        for id, session in self.sessions.items():
            if socket_hash in session:
                return session.get('id')
        return None

ctx_tracker = SessionTracker()



def check_programs(prog_name, command, options):
    try:
        subprocess.run(
            [command, options],
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            check=True,
            text=True,
            encoding='utf-8'
        )
        return True, None
    except FileNotFoundError:
        e = f'''********** Error: {prog_name} is not installed! if your OS calibre package version 
        is not compatible you still can run ebook2audiobook.sh (linux/mac) or ebook2audiobook.cmd (windows) **********'''
        DependencyError(e)
        return False, None
    except subprocess.CalledProcessError:
        e = f'Error: There was an issue running {prog_name}.'
        DependencyError(e)
        return False, None


        










        
def get_ram():
    vm = psutil.virtual_memory()
    return vm.total // (1024 ** 3)

def get_vram():
    os_name = platform.system()
    # NVIDIA (Cross-Platform: Windows, Linux, macOS)
    try:
        from pynvml import nvmlInit, nvmlDeviceGetHandleByIndex, nvmlDeviceGetMemoryInfo
        nvmlInit()
        handle = nvmlDeviceGetHandleByIndex(0)  # First GPU
        info = nvmlDeviceGetMemoryInfo(handle)
        vram = info.total
        return int(vram // (1024 ** 3))  # Convert to GB
    except ImportError:
        pass
    except Exception as e:
        pass
    # AMD (Windows)
    if os_name == "Windows":
        try:
            cmd = 'wmic path Win32_VideoController get AdapterRAM'
            output = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            lines = output.stdout.splitlines()
            vram_values = [int(line.strip()) for line in lines if line.strip().isdigit()]
            if vram_values:
                return int(vram_values[0] // (1024 ** 3))
        except Exception as e:
            pass
    # AMD (Linux)
    if os_name == "Linux":
        try:
            cmd = "lspci -v | grep -i 'VGA' -A 12 | grep -i 'preallocated' | awk '{print $2}'"
            output = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            if output.stdout.strip().isdigit():
                return int(output.stdout.strip()) // 1024
        except Exception as e:
            pass
    # Intel (Linux Only)
    intel_vram_paths = [
        "/sys/kernel/debug/dri/0/i915_vram_total",  # Intel dedicated GPUs
        "/sys/class/drm/card0/device/resource0"  # Some integrated GPUs
    ]
    for path in intel_vram_paths:
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    vram = int(f.read().strip()) // (1024 ** 3)
                    return vram
            except Exception as e:
                pass
    # macOS (OpenGL Alternative)
    if os_name == "Darwin":
        try:
            from OpenGL.GL import glGetIntegerv
            from OpenGL.GLX import GLX_RENDERER_VIDEO_MEMORY_MB_MESA
            vram = int(glGetIntegerv(GLX_RENDERER_VIDEO_MEMORY_MB_MESA) // 1024)
            return vram
        except ImportError:
            pass
        except Exception as e:
            pass
    msg = 'Could not detect GPU VRAM Capacity!'
    return 0

    

def get_num2words_compat(lang_iso1):
    try:
        test = num2words(1, lang=lang_iso1.replace('zh', 'zh_CN'))
        return True
    except NotImplementedError:
        return False
    except Exception as e:
        return False






def filter_sml(text):
    for key, value in TTS_SML.items():
        pattern = re.escape(key) if key == '###' else r'\[' + re.escape(key) + r'\]'
        text = re.sub(pattern, f" {value} ", text)
    return text







    
def get_compatible_tts_engines(language):
    compatible_engines = [
        tts for tts in models.keys()
        if language in language_tts.get(tts, {})
    ]
    return compatible_engines

def convert_ebook_batch(args, ctx=None):
    if isinstance(args['ebook_list'], list):
        ebook_list = args['ebook_list'][:]
        for file in ebook_list: # Use a shallow copy
            if any(file.endswith(ext) for ext in ebook_formats):
                args['ebook'] = file
                print(f'Processing eBook file: {os.path.basename(file)}')
                progress_status, passed = convert_ebook(args, ctx)
                if passed is False:
                    print(f'Conversion failed: {progress_status}')
                    sys.exit(1)
                args['ebook_list'].remove(file) 
        reset_ebook_session(args['session'])
        return progress_status, passed
    else:
        print(f'the ebooks source is not a list!')
        sys.exit(1)       

def convert_ebook(args, ctx=None):
    try:
        error = None
        id = None
        info_session = None
        if args['language'] is not None:
            if not os.path.splitext(args['ebook'])[1]:
                error = f"{args['ebook']} needs a format extension."
                print(error)
                return error, false
            if not os.path.exists(args['ebook']):
                error = 'File does not exist or Directory empty.'
                print(error)
                return error, false
            try:
                if len(args['language']) == 2:
                    lang_array = languages.get(part1=args['language'])
                    if lang_array:
                        args['language'] = lang_array.part3
                        args['language_iso1'] = lang_array.part1
                elif len(args['language']) == 3:
                    lang_array = languages.get(part3=args['language'])
                    if lang_array:
                        args['language'] = lang_array.part3
                        args['language_iso1'] = lang_array.part1
                else:
                    args['language_iso1'] = None
            except Exception as e:
                pass

            if args['language'] not in language_mapping.keys():
                error = 'The language you provided is not (yet) supported'
                print(error)
                return error, false

            if ctx is not None:
                context_module.context = ctx

            context_module.is_gui_process = args['is_gui_process']
            id = args['session'] if args['session'] is not None else str(uuid.uuid4())

            session = context_module.context.get_session(id)
            session['script_mode'] = args['script_mode'] if args['script_mode'] is not None else NATIVE
            session['ebook'] = args['ebook']
            session['ebook_list'] = args['ebook_list']
            session['device'] = args['device']
            session['language'] = args['language']
            session['language_iso1'] = args['language_iso1']
            session['tts_engine'] = args['tts_engine'] if args['tts_engine'] is not None else get_compatible_tts_engines(args['language'])[0]

            # Initialize custom_model_dir BEFORE using it
            if not context_module.is_gui_process:
                session['custom_model_dir'] = os.path.join(models_dir, '__sessions',f"model-{session['id']}")
                session['voice_dir'] = os.path.join(voices_dir, '__sessions', f"voice-{session['id']}", session['language'])

            session['custom_model'] = args['custom_model'] if not context_module.is_gui_process or args['custom_model'] is None else os.path.join(session['custom_model_dir'], args['custom_model'])
            session['fine_tuned'] = args['fine_tuned']
            session['voice'] = args['voice']
            session['temperature'] =  args['temperature']
            session['length_penalty'] = args['length_penalty']
            session['num_beams'] = args['num_beams']
            session['repetition_penalty'] = args['repetition_penalty']
            session['top_k'] =  args['top_k']
            session['top_p'] = args['top_p']
            session['speed'] = args['speed']
            session['enable_text_splitting'] = args['enable_text_splitting']
            session['text_temp'] =  args['text_temp']
            session['waveform_temp'] =  args['waveform_temp']
            session['audiobooks_dir'] = args['audiobooks_dir']
            session['output_format'] = args['output_format']
            session['output_split'] = args['output_split']    
            session['output_split_hours'] = args['output_split_hours'] if args['output_split_hours'] is not None else default_output_split_hours

            info_session = f"\n*********** Session: {id} **************\nStore it in case of interruption, crash, reuse of custom model or custom voice,\nyou can resume the conversion with --session {id}\n\n💾 Checkpoint System Active:\n  - Progress is automatically saved at key stages\n  - If interrupted, simply restart with the same session ID to resume\n  - Use --force_restart to ignore checkpoints and start fresh"

            if not context_module.is_gui_process:
                # voice_dir and custom_model_dir already initialized above
                os.makedirs(session['voice_dir'], exist_ok=True)
                # As now uploaded voice files are in their respective language folder so check if no wav and bark folder are on the voice_dir root from previous versions
                [shutil.move(src, os.path.join(session['voice_dir'], os.path.basename(src))) for src in glob(os.path.join(os.path.dirname(session['voice_dir']), '*.wav')) + ([os.path.join(os.path.dirname(session['voice_dir']), 'bark')] if os.path.isdir(os.path.join(os.path.dirname(session['voice_dir']), 'bark')) and not os.path.exists(os.path.join(session['voice_dir'], 'bark')) else [])]
                if session['custom_model'] is not None:
                    if not os.path.exists(session['custom_model_dir']):
                        os.makedirs(session['custom_model_dir'], exist_ok=True)
                    src_path = Path(session['custom_model'])
                    src_name = src_path.stem
                    if not os.path.exists(os.path.join(session['custom_model_dir'], src_name)):
                        required_files = models[session['tts_engine']]['internal']['files']
                        if analyze_uploaded_file(session['custom_model'], required_files):
                            model = extract_custom_model(session['custom_model'], session)
                            if model is not None:
                                session['custom_model'] = model
                            else:
                                error = f"{model} could not be extracted or mandatory files are missing"
                        else:
                            error = f'{os.path.basename(f)} is not a valid model or some required files are missing'
                if session['voice'] is not None:                  
                    voice_name = get_sanitized(os.path.splitext(os.path.basename(session['voice']))[0])
                    final_voice_file = os.path.join(session['voice_dir'], f'{voice_name}.wav')
                    if not os.path.exists(final_voice_file):
                        extractor = VoiceExtractor(session, session['voice'], voice_name)
                        status, msg = extractor.extract_voice()
                        if status:
                            session['voice'] = final_voice_file
                        else:
                            error = f'VoiceExtractor.extract_voice() failed! {msg}'
                            print(error)
            if error is None:
                if session['script_mode'] == NATIVE:
                    bool, e = check_programs('Calibre', 'ebook-convert', '--version')
                    if not bool:
                        error = f'check_programs() Calibre failed: {e}'
                    bool, e = check_programs('FFmpeg', 'ffmpeg', '-version')
                    if not bool:
                        error = f'check_programs() FFMPEG failed: {e}'
                if error is None:
                    old_session_dir = os.path.join(tmp_dir, f"ebook-{session['id']}")
                    session['session_dir'] = os.path.join(tmp_dir, f"proc-{session['id']}")
                    if os.path.isdir(old_session_dir):
                        os.rename(old_session_dir, session['session_dir'])
                    session['process_dir'] = os.path.join(session['session_dir'], f"{hashlib.md5(session['ebook'].encode()).hexdigest()}")
                    session['chapters_dir'] = os.path.join(session['process_dir'], "chapters")
                    session['chapters_dir_sentences'] = os.path.join(session['chapters_dir'], 'sentences')
                    if prepare_dirs(args['ebook'], session):
                        # Initialize checkpoint manager
                        checkpoint_mgr = CheckpointManager(session)

                        # Handle force restart - delete checkpoint if requested
                        if args.get('force_restart', False):
                            checkpoint_mgr.delete_checkpoint()
                            checkpoint_info = None
                            print("\n✓ Force restart requested - starting from beginning\n")
                        else:
                            # Check for existing checkpoint
                            checkpoint_info = checkpoint_mgr.get_checkpoint_info()

                        if checkpoint_info:
                            checkpoint_stage = checkpoint_info.get('stage', 'unknown')
                            checkpoint_time = checkpoint_info.get('timestamp', 'unknown')
                            resume_msg = f"\n{'='*60}\n✓ Found existing checkpoint!\n  Stage: {checkpoint_stage}\n  Time: {checkpoint_time}\n  Resuming from last checkpoint...\n{'='*60}\n"
                            print(resume_msg)
                            if context_module.is_gui_process:
                                show_alert({"type": "info", "msg": f"Resuming from checkpoint: {checkpoint_stage}"})
                            checkpoint_mgr.restore_from_checkpoint()

                        session['filename_noext'] = os.path.splitext(os.path.basename(session['ebook']))[0]
                        msg = ''
                        msg_extra = ''
                        vram_avail = get_vram()
                        if vram_avail <= 4:
                            msg_extra += 'VRAM capacity could not be detected. -' if vram_avail == 0 else 'VRAM under 4GB - '
                            if session['tts_engine'] == TTS_ENGINES['BARK']:
                                os.environ['SUNO_USE_SMALL_MODELS'] = 'True'
                                msg_extra += f"Switching BARK to SMALL models - "
                        else:
                            if session['tts_engine'] == TTS_ENGINES['BARK']:
                                os.environ['SUNO_USE_SMALL_MODELS'] = 'False'                        
                        if session['device'] == 'cuda':
                            session['device'] = session['device'] if torch.cuda.is_available() else 'cpu'
                            if session['device'] == 'cpu':
                                msg += f"GPU not recognized by torch! Read {default_gpu_wiki} - Switching to CPU - "
                        elif session['device'] == 'mps':
                            session['device'] = session['device'] if torch.backends.mps.is_available() else 'cpu'
                            if session['device'] == 'cpu':
                                msg += f"MPS not recognized by torch! Read {default_gpu_wiki} - Switching to CPU - "
                        if session['device'] == 'cpu':
                            if session['tts_engine'] == TTS_ENGINES['BARK']:
                                os.environ['SUNO_OFFLOAD_CPU'] = 'True'
                        if default_engine_settings[TTS_ENGINES['XTTSv2']]['use_deepspeed'] == True:
                            try:
                                import deepspeed
                            except:
                                default_engine_settings[TTS_ENGINES['XTTSv2']]['use_deepspeed'] = False
                                msg_extra += 'deepseed not installed or package is broken. set to False - '
                            else: 
                                msg_extra += 'deepspeed detected and ready!'
                        if msg == '':
                            msg = f"Using {session['device'].upper()} - "
                        msg += msg_extra
                        if context_module.is_gui_process:
                            show_alert({"type": "warning", "msg": msg})
                        print(msg)
                        session['epub_path'] = os.path.join(session['process_dir'], '__' + session['filename_noext'] + '.epub')

                        # Skip EPUB conversion if checkpoint exists and epub file is present
                        skip_epub_conversion = checkpoint_info and os.path.exists(session['epub_path'])
                        if skip_epub_conversion or convert2epub(id):
                            if not skip_epub_conversion:
                                checkpoint_mgr.save_checkpoint('epub_converted')
                            epubBook = epub.read_epub(session['epub_path'], {'ignore_ncx': True})       
                            metadata = dict(session['metadata'])
                            for key, value in metadata.items():
                                data = epubBook.get_metadata('DC', key)
                                if data:
                                    for value, attributes in data:
                                        metadata[key] = value
                            metadata['language'] = session['language']
                            metadata['title'] = metadata['title'] = metadata['title'] or Path(session['ebook']).stem.replace('_',' ')
                            metadata['creator'] =  False if not metadata['creator'] or metadata['creator'] == 'Unknown' else metadata['creator']
                            session['metadata'] = metadata                  
                            try:
                                if len(session['metadata']['language']) == 2:
                                    lang_array = languages.get(part1=session['language'])
                                    if lang_array:
                                        session['metadata']['language'] = lang_array.part3
                            except Exception as e:
                                pass                         
                            if session['metadata']['language'] != session['language']:
                                error = f"WARNING!!! language selected {session['language']} differs from the EPUB file language {session['metadata']['language']}"
                                print(error)
                            session['cover'] = get_cover(epubBook, session)
                            if session['cover']:
                                # Skip chapter extraction if checkpoint exists and chapters are loaded
                                skip_chapter_extraction = checkpoint_info and checkpoint_info.get('stage') in ['chapters_extracted', 'audio_conversion_in_progress', 'audio_converted', 'chapters_combined', 'completed']
                                if not skip_chapter_extraction or session.get('chapters') is None:
                                    session['toc'], session['chapters'] = get_chapters(epubBook, session)
                                    checkpoint_mgr.save_checkpoint('chapters_extracted')
                                session['final_name'] = get_sanitized(session['metadata']['title'] + '.' + session['output_format'])
                                if session['chapters'] is not None:
                                    if convert_chapters2audio(id):
                                        checkpoint_mgr.save_checkpoint('audio_converted')
                                        msg = 'Conversion successful. Combining sentences and chapters...'
                                        show_alert({"type": "info", "msg": msg})
                                        exported_files = combine_audio_chapters(id)               
                                        if exported_files is not None:
                                            chapters_dirs = [
                                                dir_name for dir_name in os.listdir(session['process_dir'])
                                                if fnmatch.fnmatch(dir_name, "chapters_*") and os.path.isdir(os.path.join(session['process_dir'], dir_name))
                                            ]
                                            shutil.rmtree(os.path.join(session['voice_dir'], 'proc'), ignore_errors=True)
                                            if context_module.is_gui_process:
                                                if len(chapters_dirs) > 1:
                                                    if os.path.exists(session['chapters_dir']):
                                                        shutil.rmtree(session['chapters_dir'], ignore_errors=True)
                                                    if os.path.exists(session['epub_path']):
                                                        os.remove(session['epub_path'])
                                                    if os.path.exists(session['cover']):
                                                        os.remove(session['cover'])
                                                else:
                                                    if os.path.exists(session['process_dir']):
                                                        shutil.rmtree(session['process_dir'], ignore_errors=True)
                                            else:
                                                if os.path.exists(session['voice_dir']):
                                                    if not any(os.scandir(session['voice_dir'])):
                                                        shutil.rmtree(session['voice_dir'], ignore_errors=True)
                                                if os.path.exists(session['custom_model_dir']):
                                                    if not any(os.scandir(session['custom_model_dir'])):
                                                        shutil.rmtree(session['custom_model_dir'], ignore_errors=True)
                                                if os.path.exists(session['session_dir']):
                                                    shutil.rmtree(session['session_dir'], ignore_errors=True)
                                            progress_status = f'Audiobook(s) {", ".join(os.path.basename(f) for f in exported_files)} created!'
                                            session['audiobook'] = exported_files[-1]
                                            checkpoint_mgr.save_checkpoint('completed')
                                            # Delete checkpoint on successful completion
                                            checkpoint_mgr.delete_checkpoint()
                                            print(info_session)
                                            return progress_status, True
                                        else:
                                            error = 'combine_audio_chapters() error: exported_files not created!'
                                    else:
                                        error = 'convert_chapters2audio() failed!'
                                else:
                                    error = 'get_chapters() failed!'
                            else:
                                error = 'get_cover() failed!'
                        else:
                            error = 'convert2epub() failed!'
                    else:
                        error = f"Temporary directory {session['process_dir']} not removed due to failure."
        else:
            error = f"Language {args['language']} is not supported."
        if session['cancellation_requested']:
            error = 'Cancelled'
        else:
            if not context_module.is_gui_process and id is not None:
                error += info_session
        print(error)
        return error, False
    except Exception as e:
        print(f'convert_ebook() Exception: {e}')
        return e, False

def restore_session_from_data(data, session):
    try:
        for key, value in data.items():
            if key in session:  # Check if the key exists in session
                if isinstance(value, dict) and isinstance(session[key], dict):
                    restore_session_from_data(value, session[key])
                else:
                    session[key] = value
    except Exception as e:
        DependencyError(e)

def reset_ebook_session(id):
    session = context_module.context.get_session(id)
    # FIX: Clear active_session when conversion completes
    # This is called after successful conversion
    from lib.session_persistence import SessionPersistence
    sp = SessionPersistence()
    sp.set_active_session(None)

    data = {
        "ebook": None,
        "chapters_dir": None,
        "chapters_dir_sentences": None,
        "epub_path": None,
        "filename_noext": None,
        "chapters": None,
        "cover": None,
        "status": None,
        "progress": 0,
        "duration": 0,
        "playback_time": 0,
        "cancellation_requested": False,
        "event": None,
        "metadata": {
            "title": None, 
            "creator": None,
            "contributor": None,
            "language": None,
            "identifier": None,
            "publisher": None,
            "date": None,
            "description": None,
            "subject": None,
            "rights": None,
            "format": None,
            "type": None,
            "coverage": None,
            "relation": None,
            "Source": None,
            "Modified": None
        }
    }
    restore_session_from_data(data, session)

def get_all_ip_addresses():
    ip_addresses = []
    for interface, addresses in psutil.net_if_addrs().items():
        for address in addresses:
            if address.family == socket.AF_INET:
                ip_addresses.append(address.address)
            elif address.family == socket.AF_INET6:
                ip_addresses.append(address.address)  
    return ip_addresses

def show_alert(state):
    if isinstance(state, dict):
        if state['type'] is not None:
            if state['type'] == 'error':
                gr.Error(state['msg'])
            elif state['type'] == 'warning':
                gr.Warning(state['msg'])
            elif state['type'] == 'info':
                gr.Info(state['msg'])
            elif state['type'] == 'success':
                gr.Success(state['msg'])

def web_interface(args, ctx):
    context_module.context = ctx
    context_module.is_gui_process = True  # Always True in web interface

    # Initialize session persistence
    session_persistence = SessionPersistence()

    # Session management helper functions
    def load_session_choices():
        """Load session list for dropdown choices."""
        try:
            sessions = session_persistence.list_sessions(include_completed=False)
            choices = ['New Session']
            for session in sessions:
                display_name = session_persistence.get_session_display_name(session['id'])
                choices.append(display_name)
            return choices
        except Exception as e:
            print(f"Error loading session choices: {e}")
            return ['New Session']

    def get_session_id_from_display_name(display_name):
        """Get session ID from display name."""
        if display_name == 'New Session':
            return None
        try:
            sessions = session_persistence.list_sessions(include_completed=False)
            for session in sessions:
                if session_persistence.get_session_display_name(session['id']) == display_name:
                    return session['id']
            return None
        except Exception as e:
            print(f"Error getting session ID: {e}")
            return None

    def save_session_to_disk(id):
        """Save current session to disk."""
        try:
            session = context_module.context.get_session(id)
            if session and session.get('id'):
                # Add created_at timestamp if not present
                if 'created_at' not in session:
                    session['created_at'] = datetime.now().isoformat()

                session_persistence.save_session(session['id'], dict(session))
                return True
        except Exception as e:
            print(f"Error saving session to disk: {e}")
        return False

    def load_session_from_disk(session_id):
        """Load session from disk."""
        try:
            if not session_id:
                return None
            session_data = session_persistence.load_session(session_id)
            return session_data
        except Exception as e:
            print(f"Error loading session from disk: {e}")
            return None

    script_mode = args['script_mode']
    is_gui_process = args['is_gui_process']
    is_gui_shared = args['share']
    title = 'Ebook2Audiobook'
    glass_mask_msg = 'Initialization, please wait...'
    ebook_src = None
    language_options = [
        (
            f"{details['name']} - {details['native_name']}" if details['name'] != details['native_name'] else details['name'],
            lang
        )
        for lang, details in language_mapping.items()
    ]
    voice_options = []
    tts_engine_options = []
    custom_model_options = []
    fine_tuned_options = []
    audiobook_options = []
    options_output_split_hours = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12']
    
    src_label_file = 'Select a File'
    src_label_dir = 'Select a Directory'
    
    visible_gr_tab_xtts_params = interface_component_options['gr_tab_xtts_params']
    visible_gr_tab_bark_params = interface_component_options['gr_tab_bark_params']
    visible_gr_group_custom_model = interface_component_options['gr_group_custom_model']
    visible_gr_group_voice_file = interface_component_options['gr_group_voice_file']

    theme = gr.themes.Origin(
        primary_hue='green',
        secondary_hue='amber',
        neutral_hue='gray',
        radius_size='lg',
        font_mono=['JetBrains Mono', 'monospace', 'Consolas', 'Menlo', 'Liberation Mono']
    )

    header_css = '''
        <style>
            /* Global Scrollbar Customization */
            /* The entire scrollbar */
            ::-webkit-scrollbar {
                width: 6px !important;
                height: 6px !important;
                cursor: pointer !important;;
            }
            /* The scrollbar track (background) */
            ::-webkit-scrollbar-track {
                background: none transparent !important;
                border-radius: 6px !important;
            }
            /* The scrollbar thumb (scroll handle) */
            ::-webkit-scrollbar-thumb {
                background: #c09340 !important;
                border-radius: 6px !important;
            }
            /* The scrollbar thumb on hover */
            ::-webkit-scrollbar-thumb:hover {
                background: #ff8c00 !important;
            }
            /* Firefox scrollbar styling */
            html {
                scrollbar-width: thin !important;
                scrollbar-color: #c09340 none !important;
            }
            .svelte-1xyfx7i.center.boundedheight.flex{
                height: 120px !important;
            }
            .wrap-inner {
                border: 1px solid #666666;
            }
            .block.svelte-5y6bt2 {
                padding: 10px !important;
                margin: 0 !important;
                height: auto !important;
                font-size: 16px !important;
            }
            .wrap.svelte-12ioyct {
                padding: 0 !important;
                margin: 0 !important;
                font-size: 12px !important;
            }
            .block.svelte-5y6bt2.padded {
                height: auto !important;
                padding: 10px !important;
            }
            .block.svelte-5y6bt2.padded.hide-container {
                height: auto !important;
                padding: 0 !important;
            }
            .waveform-container.svelte-19usgod {
                height: 58px !important;
                overflow: hidden !important;
                padding: 0 !important;
                margin: 0 !important;
            }
            .component-wrapper.svelte-19usgod {
                height: 110px !important;
            }
            .timestamps.svelte-19usgod {
                display: none !important;
            }
            .controls.svelte-ije4bl {
                padding: 0 !important;
                margin: 0 !important;
            }
            .icon-btn {
                font-size: 30px !important;
            }
            .small-btn {
                font-size: 22px !important;
                width: 60px !important;
                height: 60px !important;
                margin: 0 !important;
                padding: 0 !important;
            }
            .file-preview-holder {
                height: 116px !important;
                overflow: auto !important;
            }
            .selected {
                color: orange !important;
            }
            .progress-bar.svelte-ls20lj {
                background: orange !important;
            }
            #glass-mask {
                position: fixed !important;
                top: 0 !important;
                left: 0 !important;
                width: 100vw !important; 
                height: 100vh !important;
                background: rgba(0,0,0,0.6) !important;
                display: flex !important;
                text-align: center;
                align-items: center !important;
                justify-content: center !important;
                font-size: 1.2rem !important;
                color: #fff !important;
                z-index: 9999 !important;
                transition: opacity 2s ease-out 2s !important;
                pointer-events: all !important;
            }
            #glass-mask.hide {
                opacity: 0 !important;
                pointer-events: none !important;
            }
            #gr_markdown_logo {
                position: absolute !important; 
                text-align: right !important;
            }
            #gr_ebook_file, #gr_custom_model_file, #gr_voice_file {
                height: 140px !important;
            }
            #gr_custom_model_file [aria-label="Clear"], #gr_voice_file [aria-label="Clear"] {
                display: none !important;
            }               
            #gr_tts_engine_list, #gr_fine_tuned_list, #gr_session, #gr_output_format_list {
                height: 95px !important;
            }
            #gr_voice_list {
                height: 60px !important;
            }
            #gr_voice_list span[data-testid="block-info"],
            #gr_audiobook_list span[data-testid="block-info"]{
                display: none !important;
            }
            ///////////////
            #gr_voice_player {
                margin: 0 !important;
                padding: 0 !important;
                width: 60px !important;
                height: 60px !important;
            }
            #gr_row_voice_player {
                height: 60px !important;
            }
            #gr_voice_player :is(#waveform, .rewind, .skip, .playback, label, .volume, .empty) {
                display: none !important;
            }
            #gr_voice_player .controls {
                display: block !important;
                position: absolute !important;
                left: 15px !important;
                top: 0 !important;
            }
            ///////////
            #gr_audiobook_player :is(.volume, .empty, .source-selection, .control-wrapper, .settings-wrapper) {
                display: none !important;
            }
            #gr_audiobook_player label{
                display: none !important;
            }
            #gr_audiobook_player audio {
                width: 100% !important;
                padding-top: 10px !important;
                padding-bottom: 10px !important;
                border-radius: 0px !important;
                background-color: #ebedf0 !important;
                color: #ffffff !important;
            }
            #gr_audiobook_player audio::-webkit-media-controls-panel {
                width: 100% !important;
                padding-top: 10px !important;
                padding-bottom: 10px !important;
                border-radius: 0px !important;
                background-color: #ebedf0 !important;
                color: #ffffff !important;
            }
            ////////////
            .fade-in {
                animation: fadeIn 1s ease-in;
                display: inline-block;
            }
            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }
        </style>
    '''
    
    with gr.Blocks(theme=theme, title=title, css=header_css, delete_cache=(86400, 86400)) as app:
        with gr.Tabs(elem_id='gr_tabs'):
            gr_tab_main = gr.TabItem('Main Parameters', elem_id='gr_tab_main', elem_classes='tab_item')
            with gr_tab_main:
                # Session selector at the top
                with gr.Group(elem_id='gr_group_session_selector'):
                    gr_session_selector = gr.Dropdown(
                        label='Active Session',
                        elem_id='gr_session_selector',
                        choices=['New Session'],
                        value='New Session',
                        type='value',
                        interactive=True,
                        info='Select an existing session to resume or start a new one'
                    )
                with gr.Row(elem_id='gr_row_tab_main'):
                    with gr.Column(elem_id='gr_col_1', scale=3):
                        with gr.Group(elem_id='gr1'):
                            gr_ebook_file = gr.File(label=src_label_file, elem_id='gr_ebook_file', file_types=ebook_formats, file_count='single', allow_reordering=True, height=140)
                            gr_ebook_mode = gr.Radio(label='', elem_id='gr_ebook_mode', choices=[('File','single'), ('Directory','directory')], value='single', interactive=True)
                        with gr.Group(elem_id='gr_group_language'):
                            gr_language = gr.Dropdown(label='Language', elem_id='gr_language', choices=language_options, value=default_language_code, type='value', interactive=True)
                        gr_group_voice_file = gr.Group(elem_id='gr_group_voice_file', visible=visible_gr_group_voice_file)
                        with gr_group_voice_file:
                            gr_voice_file = gr.File(label='*Cloning Voice Audio Fiie', elem_id='gr_voice_file', file_types=voice_formats, value=None, height=140)
                            gr_row_voice_player = gr.Row(elem_id='gr_row_voice_player')
                            with gr_row_voice_player:
                                gr_voice_player = gr.Audio(elem_id='gr_voice_player', type='filepath', interactive=False, show_download_button=False, container=False, visible=False, show_share_button=False, show_label=False, waveform_options=gr.WaveformOptions(show_controls=False), scale=0, min_width=60)
                                gr_voice_list = gr.Dropdown(label='', elem_id='gr_voice_list', choices=voice_options, type='value', interactive=True, scale=2)
                                gr_voice_del_btn = gr.Button('🗑', elem_id='gr_voice_del_btn', elem_classes=['small-btn'], variant='secondary', interactive=True, visible=False, scale=0, min_width=60)
                            gr_optional_markdown = gr.Markdown(elem_id='gr_markdown_optional', value='<p>&nbsp;&nbsp;* Optional</p>')
                        with gr.Group(elem_id='gr_group_device'):
                            gr_device = gr.Dropdown(label='Processor Unit', elem_id='gr_device', choices=[('CPU','cpu'), ('GPU','cuda'), ('MPS','mps')], type='value', value=default_device, interactive=True)
                            gr_logo_markdown = gr.Markdown(elem_id='gr_logo_markdown', value=f'''
                                <div style="right:0;margin:auto;padding:10px;text-align:right">
                                    <a href="https://github.com/DrewThomasson/ebook2audiobook" style="text-decoration:none;font-size:14px" target="_blank">
                                    <b>{title}</b>&nbsp;<b style="color:orange">{prog_version}</b></a>
                                </div>
                                '''
                            )
                    with gr.Column(elem_id='gr_col_2', scale=3):
                        with gr.Group(elem_id='gr_group_engine'):
                            gr_tts_engine_list = gr.Dropdown(label='TTS Engine', elem_id='gr_tts_engine_list', choices=tts_engine_options, type='value', interactive=True)
                            gr_tts_rating = gr.HTML()
                            gr_fine_tuned_list = gr.Dropdown(label='Fine Tuned Models (Presets)', elem_id='gr_fine_tuned_list', choices=fine_tuned_options, type='value', interactive=True)
                            gr_group_custom_model = gr.Group(visible=visible_gr_group_custom_model)
                            with gr_group_custom_model:
                                gr_custom_model_file = gr.File(label=f"Upload Fine Tuned Model", elem_id='gr_custom_model_file', value=None, file_types=['.zip'], height=140)
                                with gr.Row(elem_id='gr_row_custom_model'):
                                    gr_custom_model_list = gr.Dropdown(label='', elem_id='gr_custom_model_list', choices=custom_model_options, type='value', interactive=True, scale=2)
                                    gr_custom_model_del_btn = gr.Button('🗑', elem_id='gr_custom_model_del_btn', elem_classes=['small-btn'], variant='secondary', interactive=True, visible=False, scale=0, min_width=60)
                                gr_custom_model_markdown = gr.Markdown(elem_id='gr_markdown_custom_model', value='<p>&nbsp;&nbsp;* Optional</p>')
                        with gr.Group(elem_id='gr_group_output_format'):
                            with gr.Row(elem_id='gr_row_output_format'):
                                gr_output_format_list = gr.Dropdown(label='Output Format', elem_id='gr_output_format_list', choices=output_formats, type='value', value=default_output_format, interactive=True, scale=2)
                                gr_output_split = gr.Checkbox(label='Split Output File', elem_id='gr_output_split', value=default_output_split, interactive=True, scale=1)
                                gr_output_split_hours = gr.Dropdown(label='Max hours / part', elem_id='gr_output_split_hours', choices=options_output_split_hours, type='value', value=default_output_split_hours, interactive=True, visible=False, scale=2)
                        gr_session = gr.Textbox(label='Session', elem_id='gr_session', interactive=False)
            gr_tab_xtts_params = gr.TabItem('XTTSv2 Fine Tuned Parameters', elem_id='gr_tab_xtts_params', elem_classes='tab_item', visible=visible_gr_tab_xtts_params)           
            with gr_tab_xtts_params:
                gr.Markdown(
                    elem_id='gr_markdown_tab_xtts_params',
                    value='''
                    ### Customize XTTSv2 Parameters
                    Adjust the settings below to influence how the audio is generated. You can control the creativity, speed, repetition, and more.
                    '''
                )
                gr_xtts_temperature = gr.Slider(
                    label='Temperature',
                    minimum=0.05,
                    maximum=10.0,
                    step=0.05,
                    value=float(default_engine_settings[TTS_ENGINES['XTTSv2']]['temperature']),
                    elem_id='gr_xtts_temperature',
                    info='Higher values lead to more creative, unpredictable outputs. Lower values make it more monotone.'
                )
                gr_xtts_length_penalty = gr.Slider(
                    label='Length Penalty',
                    minimum=0.3,
                    maximum=5.0,
                    step=0.1,
                    value=float(default_engine_settings[TTS_ENGINES['XTTSv2']]['length_penalty']),
                    elem_id='gr_xtts_length_penalty',
                    info='Adjusts how much longer sequences are preferred. Higher values encourage the model to produce longer and more natural speech.',
                    visible=False
                )
                gr_xtts_num_beams = gr.Slider(
                    label='Number Beams',
                    minimum=1,
                    maximum=10,
                    step=1,
                    value=int(default_engine_settings[TTS_ENGINES['XTTSv2']]['num_beams']),
                    elem_id='gr_xtts_num_beams',
                    info='Controls how many alternative sequences the model explores. Higher values improve speech coherence and pronunciation but increase inference time.',
                    visible=False
                )
                gr_xtts_repetition_penalty = gr.Slider(
                    label='Repetition Penalty',
                    minimum=1.0,
                    maximum=10.0,
                    step=0.1,
                    value=float(default_engine_settings[TTS_ENGINES['XTTSv2']]['repetition_penalty']),
                    elem_id='gr_xtts_repetition_penalty',
                    info='Penalizes repeated phrases. Higher values reduce repetition.'
                )
                gr_xtts_top_k = gr.Slider(
                    label='Top-k Sampling',
                    minimum=10,
                    maximum=100,
                    step=1,
                    value=int(default_engine_settings[TTS_ENGINES['XTTSv2']]['top_k']),
                    elem_id='gr_xtts_top_k',
                    info='Lower values restrict outputs to more likely words and increase speed at which audio generates.'
                )
                gr_xtts_top_p = gr.Slider(
                    label='Top-p Sampling',
                    minimum=0.1,
                    maximum=1.0, 
                    step=0.01,
                    value=float(default_engine_settings[TTS_ENGINES['XTTSv2']]['top_p']),
                    elem_id='gr_xtts_top_p',
                    info='Controls cumulative probability for word selection. Lower values make the output more predictable and increase speed at which audio generates.'
                )
                gr_xtts_speed = gr.Slider(
                    label='Speed', 
                    minimum=0.5, 
                    maximum=3.0, 
                    step=0.1, 
                    value=float(default_engine_settings[TTS_ENGINES['XTTSv2']]['speed']),
                    elem_id='gr_xtts_speed',
                    info='Adjusts how fast the narrator will speak.'
                )
                gr_xtts_enable_text_splitting = gr.Checkbox(
                    label='Enable Text Splitting', 
                    value=default_engine_settings[TTS_ENGINES['XTTSv2']]['enable_text_splitting'],
                    elem_id='gr_xtts_enable_text_splitting',
                    info='Coqui-tts builtin text splitting. Can help against hallucinations bu can also be worse.',
                    visible=False
                )
            gr_tab_bark_params = gr.TabItem('BARK fine Tuned Parameters', elem_id='gr_tab_bark_params', elem_classes='tab_item', visible=visible_gr_tab_bark_params)           
            with gr_tab_bark_params:
                gr.Markdown(
                    elem_id='gr_markdown_tab_bark_params',
                    value='''
                    ### Customize BARK Parameters
                    Adjust the settings below to influence how the audio is generated, emotional and voice behavior random or more conservative
                    '''
                )
                gr_bark_text_temp = gr.Slider(
                    label='Text Temperature', 
                    minimum=0.0,
                    maximum=1.0,
                    step=0.01,
                    value=float(default_engine_settings[TTS_ENGINES['BARK']]['text_temp']),
                    elem_id='gr_bark_text_temp',
                    info='Higher values lead to more creative, unpredictable outputs. Lower values make it more conservative.'
                )
                gr_bark_waveform_temp = gr.Slider(
                    label='Waveform Temperature', 
                    minimum=0.0,
                    maximum=1.0,
                    step=0.01,
                    value=float(default_engine_settings[TTS_ENGINES['BARK']]['waveform_temp']),
                    elem_id='gr_bark_waveform_temp',
                    info='Higher values lead to more creative, unpredictable outputs. Lower values make it more conservative.'
                )
        gr_state_update = gr.State(value={"hash": None})
        gr_read_data = gr.JSON(visible=False, elem_id='gr_read_data')
        gr_write_data = gr.JSON(visible=False, elem_id='gr_write_data')
        gr_tab_progress = gr.Textbox(elem_id='gr_tab_progress', label='Progress', interactive=False)
        gr_group_audiobook_list = gr.Group(elem_id='gr_group_audiobook_list', visible=False)
        with gr_group_audiobook_list:
            gr_audiobook_vtt = gr.Textbox(elem_id='gr_audiobook_vtt', label='', interactive=False, visible=False)
            gr_audiobook_sentence = gr.Textbox(elem_id='gr_audiobook_sentence', label='Audiobook', value='...', interactive=False, visible=True, lines=3, max_lines=3)
            gr_audiobook_player = gr.Audio(elem_id='gr_audiobook_player', label='',type='filepath', autoplay=False, waveform_options=gr.WaveformOptions(show_recording_waveform=False), show_download_button=False, show_share_button=False, container=True, interactive=False, visible=True)
            gr_audiobook_player_playback_time = gr.Number(label='', interactive=False, visible=True, elem_id="gr_audiobook_player_playback_time", value=0.0)
            with gr.Row(elem_id='gr_row_audiobook_list'):
                gr_audiobook_download_btn = gr.DownloadButton(elem_id='gr_audiobook_download_btn', label='↧', elem_classes=['small-btn'], variant='secondary', interactive=True, visible=True, scale=0, min_width=60)
                gr_audiobook_list = gr.Dropdown(elem_id='gr_audiobook_list', label='', choices=audiobook_options, type='value', interactive=True, visible=True, scale=2)
                gr_audiobook_del_btn = gr.Button(elem_id='gr_audiobook_del_btn', value='🗑', elem_classes=['small-btn'], variant='secondary', interactive=True, visible=True, scale=0, min_width=60)

        # Convert button and chapter migration checkbox
        gr_convert_btn = gr.Button(elem_id='gr_convert_btn', value='📚', elem_classes='icon-btn', variant='primary', interactive=False)
        gr_scan_chapters_checkbox = gr.Checkbox(
            label='📂 I moved chapter files - Scan and update checkpoint before converting',
            elem_id='gr_scan_chapters_checkbox',
            value=False,
            interactive=True,
            info='Check this if you copied chapter files from another session. The system will detect them and resume from where they left off.'
        )

        gr_modal = gr.HTML(visible=False)
        gr_glass_mask = gr.HTML(f'<div id="glass-mask">{glass_mask_msg}</div>')
        gr_confirm_field_hidden = gr.Textbox(elem_id='confirm_hidden', visible=False)
        gr_confirm_yes_btn = gr.Button(elem_id='confirm_yes_btn', value='', visible=False)
        gr_confirm_no_btn = gr.Button(elem_id='confirm_no_btn', value='', visible=False)

        def cleanup_session(req: gr.Request):
            socket_hash = req.session_hash
            if any(socket_hash in session for session in context_module.context.sessions.values()):
                session_id = context_module.context.find_id_by_hash(socket_hash)
                ctx_tracker.end_session(session_id, socket_hash)

        def load_vtt_data(path):
            if not path or not os.path.exists(path):
                return None
            try:
                vtt_path = Path(path).with_suffix('.vtt')
                if not os.path.exists(vtt_path):
                    return None
                with open(vtt_path, "r", encoding="utf-8-sig", errors="replace") as f:
                    content = f.read()
                return content
            except Exception:
                return None

        def show_modal(type, msg):
            return f'''
            <style>
                .modal {{
                    display: none; /* Hidden by default */
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background-color: rgba(0, 0, 0, 0.5);
                    z-index: 9999;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                }}
                .modal-content {{
                    background-color: #333;
                    padding: 20px;
                    border-radius: 8px;
                    text-align: center;
                    max-width: 300px;
                    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.5);
                    border: 2px solid #FFA500;
                    color: white;
                    position: relative;
                }}
                .modal-content p {{
                    margin: 10px 0;
                }}
                .confirm-buttons {{
                    display: flex;
                    justify-content: space-evenly;
                    margin-top: 20px;
                }}
                .confirm-buttons button {{
                    padding: 10px 20px;
                    border: none;
                    border-radius: 5px;
                    font-size: 16px;
                    cursor: pointer;
                }}
                .confirm-buttons .confirm_yes_btn {{
                    background-color: #28a745;
                    color: white;
                }}
                .confirm-buttons .confirm_no_btn {{
                    background-color: #dc3545;
                    color: white;
                }}
                .confirm-buttons .confirm_yes_btn:hover {{
                    background-color: #34d058;
                }}
                .confirm-buttons .confirm_no_btn:hover {{
                    background-color: #ff6f71;
                }}
                /* Spinner */
                .spinner {{
                    margin: 15px auto;
                    border: 4px solid rgba(255, 255, 255, 0.2);
                    border-top: 4px solid #FFA500;
                    border-radius: 50%;
                    width: 30px;
                    height: 30px;
                    animation: spin 1s linear infinite;
                }}
                @keyframes spin {{
                    0% {{ transform: rotate(0deg); }}
                    100% {{ transform: rotate(360deg); }}
                }}
            </style>
            <div id="custom-modal" class="modal">
                <div class="modal-content">
                    <p style="color:#ffffff">{msg}</p>            
                    {show_confirm() if type == 'confirm' else '<div class="spinner"></div>'}
                </div>
            </div>
            '''

        def show_confirm():
            return '''
            <div class="confirm-buttons">
                <button class="confirm_yes_btn" onclick="document.querySelector('#confirm_yes_btn').click()">✔</button>
                <button class="confirm_no_btn" onclick="document.querySelector('#confirm_no_btn').click()">⨉</button>
            </div>
            '''

        def show_rating(tts_engine):

            def yellow_stars(n):
                return "".join(
                    "<span style='color:#f0bc00; font-size:12px'>★</span>" for _ in range(n)
                )

            def color_box(value):
                if value <= 4:
                    color = "#4CAF50"  # Green = low
                elif value <= 8:
                    color = "#FF9800"  # Orange = medium
                else:
                    color = "#F44336"  # Red = high
                return f"<span style='background:{color};color:white;padding:1px 5px;border-radius:3px;font-size:11px'>{value} GB</span>"
            
            rating = default_engine_settings[tts_engine]['rating']

            return f"""
            <div style='margin:0; padding:0; font-size:12px; line-height:1.2; height:auto; display:flex; flex-wrap:wrap; align-items:center; gap:6px 12px;'>
              <span style='display:inline-flex; white-space:nowrap; padding:0 10px'><b>GPU VRAM:</b> {color_box(rating["GPU VRAM"])}</span>
              <span style='display:inline-flex; white-space:nowrap; padding:0 10px'><b>CPU:</b> {yellow_stars(rating["CPU"])}</span>
              <span style='display:inline-flex; white-space:nowrap; padding:0 10px'><b>RAM:</b> {color_box(rating["RAM"])}</span>
              <span style='display:inline-flex; white-space:nowrap; padding:0 10px'><b>Realism:</b> {yellow_stars(rating["Realism"])}</span>
            </div>
            """

        def alert_exception(error):
            """Display error in Gradio UI without crashing the server."""
            print(f"ERROR: {error}")  # Log to console
            gr.Error(error)  # Show in UI
            # Note: Do NOT use DependencyError here as it calls sys.exit() which crashes Gradio

        def update_session_selector(id):
            """Update session selector dropdown with current session."""
            try:
                if not id:
                    return gr.update(choices=['New Session'], value='New Session')

                choices = load_session_choices()
                # Check if this session exists in saved sessions
                if session_persistence.session_exists(id):
                    display_name = session_persistence.get_session_display_name(id)
                    # Only set value if it exists in choices
                    if display_name in choices:
                        return gr.update(choices=choices, value=display_name)

                # Default to New Session if not found
                return gr.update(choices=choices, value='New Session')
            except Exception as e:
                print(f"Error updating session selector: {e}")
                return gr.update(choices=['New Session'], value='New Session')

        def handle_session_selector_change(selected_session, current_id, req: gr.Request):
            """Handle session selection from dropdown."""
            try:
                if selected_session == 'New Session':
                    # Create a new session
                    new_id = str(uuid.uuid4())
                    session = context_module.context.get_session(new_id)
                    # Add created_at timestamp
                    session['created_at'] = datetime.now().isoformat()

                    # FIX PROBLEM 6: Save new session to disk immediately
                    save_session_to_disk(new_id)

                    # Clear active session in persistence (new session not yet active)
                    session_persistence.set_active_session(None)

                    print(f"✓ Created and saved new session: {new_id[:8]}")
                    # Return new session ID and refresh choices
                    return new_id, gr.update(choices=load_session_choices(), value='New Session')
                else:
                    # Load existing session
                    session_id = get_session_id_from_display_name(selected_session)
                    if session_id:
                        # Check if another session is active (block multiple active sessions)
                        active_session_id = session_persistence.get_active_session()
                        if active_session_id and active_session_id != session_id:
                            # Check if active session is actually converting
                            active_disk = load_session_from_disk(active_session_id)
                            if active_disk and active_disk.get('status') == 'converting':
                                gr.Warning(f"Another session is currently converting. Please wait for it to complete.")
                                return current_id, gr.update(value=selected_session)
                            else:
                                # Active session not really converting, clear it
                                session_persistence.set_active_session(None)

                        # Load session from disk
                        disk_session = load_session_from_disk(session_id)
                        if disk_session:
                            # Get or create session in memory
                            session = context_module.context.get_session(session_id)
                            # Restore all fields from disk
                            for key, value in disk_session.items():
                                if key not in ['tab_id', 'process_id', 'cancellation_requested']:
                                    # Don't restore runtime-only fields
                                    session[key] = value

                            # FIX PROBLEM 5: Save session to disk after switching
                            # This updates last_access and ensures sync
                            save_session_to_disk(session_id)

                            # Set as active session only if it's converting
                            if session.get('status') == 'converting':
                                session_persistence.set_active_session(session_id)

                            print(f"✓ Switched to session: {session_id[:8]}")
                            return session_id, gr.update(value=selected_session)

                    gr.Warning("Failed to load selected session")
                    return current_id, gr.update(value=selected_session)
            except Exception as e:
                print(f"Error in handle_session_selector_change: {e}")
                gr.Warning(f"Error switching session: {e}")
                return current_id, gr.update()

        def restore_interface(id, req: gr.Request):
            try:
                session = context_module.context.get_session(id)
                socket_hash = req.session_hash
                # Don't check socket_hash - it may not exist yet during reconnection
                # The session itself is enough to restore the interface
                # if not session.get(socket_hash):
                #     outputs = tuple([gr.update() for _ in range(24)])
                #     return outputs
                ebook_data = None
                file_count = session['ebook_mode']
                if isinstance(session['ebook_list'], list) and file_count == 'directory':
                    #ebook_data = session['ebook_list']
                    ebook_data = None
                elif isinstance(session['ebook'], str) and file_count == 'single':
                    ebook_data = session['ebook']
                else:
                    ebook_data = None
                ### XTTSv2 Params
                session['temperature'] = session['temperature'] if session['temperature'] else default_engine_settings[TTS_ENGINES['XTTSv2']]['temperature']
                session['length_penalty'] = default_engine_settings[TTS_ENGINES['XTTSv2']]['length_penalty']
                session['num_beams'] = default_engine_settings[TTS_ENGINES['XTTSv2']]['num_beams']
                session['repetition_penalty'] = session['repetition_penalty'] if session['repetition_penalty'] else default_engine_settings[TTS_ENGINES['XTTSv2']]['repetition_penalty']
                session['top_k'] = session['top_k'] if session['top_k'] else default_engine_settings[TTS_ENGINES['XTTSv2']]['top_k']
                session['top_p'] = session['top_p'] if session['top_p'] else default_engine_settings[TTS_ENGINES['XTTSv2']]['top_p']
                session['speed'] = session['speed'] if session['speed'] else default_engine_settings[TTS_ENGINES['XTTSv2']]['speed']
                session['enable_text_splitting'] = default_engine_settings[TTS_ENGINES['XTTSv2']]['enable_text_splitting']
                ### BARK Params
                session['text_temp'] = session['text_temp'] if session['text_temp'] else default_engine_settings[TTS_ENGINES['BARK']]['text_temp']
                session['waveform_temp'] = session['waveform_temp'] if session['waveform_temp'] else default_engine_settings[TTS_ENGINES['BARK']]['waveform_temp']
                return (
                    gr.update(value=ebook_data), gr.update(value=session['ebook_mode']), gr.update(value=session['device']),
                    gr.update(value=session['language']), update_gr_tts_engine_list(id), update_gr_custom_model_list(id),
                    update_gr_fine_tuned_list(id), gr.update(value=session['output_format']), update_gr_audiobook_list(id), gr.update(value=load_vtt_data(session['audiobook'])),
                    gr.update(value=float(session['temperature'])), gr.update(value=float(session['length_penalty'])), gr.update(value=int(session['num_beams'])),
                    gr.update(value=float(session['repetition_penalty'])), gr.update(value=int(session['top_k'])), gr.update(value=float(session['top_p'])), gr.update(value=float(session['speed'])), 
                    gr.update(value=bool(session['enable_text_splitting'])), gr.update(value=float(session['text_temp'])), gr.update(value=float(session['waveform_temp'])), update_gr_voice_list(id),
                    gr.update(value=session['output_split']), gr.update(value=session['output_split_hours']), gr.update(active=True)
                )
            except Exception as e:
                error = f'restore_interface(): {e}'
                alert_exception(error)
                outputs = tuple([gr.update() for _ in range(24)])
                return outputs

        def refresh_interface(id):
            session = context_module.context.get_session(id)
            return (
                    gr.update(interactive=False), gr.update(value=None), update_gr_audiobook_list(id), 
                    gr.update(value=session['audiobook']), gr.update(visible=False), update_gr_voice_list(id)
            )

        def change_gr_audiobook_list(selected, id):
            session = context_module.context.get_session(id)
            session['audiobook'] = selected
            if selected is not None:
                audio_info = mediainfo(selected)
                session['duration'] = float(audio_info['duration'])
            visible = True if len(audiobook_options) else False
            return gr.update(value=selected), gr.update(value=selected), gr.update(value=load_vtt_data(selected)), gr.update(visible=visible)
        
        def update_gr_glass_mask(str=glass_mask_msg, attr=''):
            return gr.update(value=f'<div id="glass-mask" {attr}>{str}</div>')
        
        def state_convert_btn(upload_file=None, upload_file_mode=None, custom_model_file=None, session=None):
            try:
                if session is None:
                    return gr.update(variant='primary', interactive=False)
                else:
                    if hasattr(upload_file, 'name') and not hasattr(custom_model_file, 'name'):
                        return gr.update(variant='primary', interactive=True)
                    elif isinstance(upload_file, list) and len(upload_file) > 0 and upload_file_mode == 'directory' and not hasattr(custom_model_file, 'name'):
                        return gr.update(variant='primary', interactive=True)
                    else:
                        return gr.update(variant='primary', interactive=False)
            except Exception as e:
                error = f'state_convert_btn(): {e}'
                alert_exception(error)
        
        def disable_components():
            outputs = tuple([gr.update(interactive=False) for _ in range(9)])
            return outputs
        
        def enable_components():
            outputs = tuple([gr.update(interactive=True) for _ in range(9)])
            return outputs

        def change_gr_ebook_file(data, id):
            import time
            try:
                session = context_module.context.get_session(id)
                session['ebook'] = None
                session['ebook_list'] = None
                if data is None:
                    if session['status'] == 'converting':
                        session['cancellation_requested'] = True
                        msg = 'Cancellation requested, please wait...'
                        yield gr.update(value=show_modal('wait', msg),visible=True)

                        # Wait for conversion to actually stop
                        max_wait = 30  # Maximum 30 seconds
                        waited = 0
                        while session['status'] == 'converting' and waited < max_wait:
                            time.sleep(0.5)
                            waited += 0.5
                            session = context_module.context.get_session(id)  # Refresh session

                        # Ensure status is reset
                        if session['status'] == 'converting':
                            session['status'] = 'ready'

                        yield gr.update(visible=False)
                        return
                if isinstance(data, list):
                    session['ebook_list'] = data
                else:
                    session['ebook'] = data
                session['cancellation_requested'] = False
            except Exception as e:
                error = f'change_gr_ebook_file(): {e}'
                alert_exception(error)
            return gr.update(visible=False)
            
        def change_gr_ebook_mode(val, id):
            session = context_module.context.get_session(id)
            session['ebook_mode'] = val
            if val == 'single':
                return gr.update(label=src_label_file, value=None, file_count='single')
            else:
                return gr.update(label=src_label_dir, value=None, file_count='directory')

        def change_gr_voice_file(f, id):
            if f is not None:
                state = {}
                if len(voice_options) > max_custom_voices:
                    error = f'You are allowed to upload a max of {max_custom_voices} voices'
                    state['type'] = 'warning'
                    state['msg'] = error
                elif os.path.splitext(f.name)[1] not in voice_formats:
                    error = f'The audio file format selected is not valid.'
                    state['type'] = 'warning'
                    state['msg'] = error
                else:                  
                    session = context_module.context.get_session(id)
                    voice_name = os.path.splitext(os.path.basename(f))[0].replace('&', 'And')
                    voice_name = get_sanitized(voice_name)
                    final_voice_file = os.path.join(session['voice_dir'], f'{voice_name}.wav')
                    extractor = VoiceExtractor(session, f, voice_name)
                    status, msg = extractor.extract_voice()
                    if status:
                        session['voice'] = final_voice_file
                        msg = f"Voice {voice_name} added to the voices list"
                        state['type'] = 'success'
                        state['msg'] = msg
                    else:
                        error = 'failed! Check if you audio file is compatible.'
                        state['type'] = 'warning'
                        state['msg'] = error
                show_alert(state)
                return gr.update(value=None)
            return gr.update()

        def change_gr_voice_list(selected, id):
            session = context_module.context.get_session(id)
            session['voice'] = next((value for label, value in voice_options if value == selected), None)
            visible = True if session['voice'] is not None else False
            min_width = 60 if session['voice'] is not None else 0
            return gr.update(value=session['voice'], visible=visible, min_width=min_width), gr.update(visible=visible)

        def click_gr_voice_del_btn(selected, id):
            try:
                if selected is not None:
                    session = context_module.context.get_session(id)
                    speaker_path = os.path.abspath(selected)
                    speaker = re.sub(r'\.wav$|\.npz$', '', os.path.basename(selected))
                    builtin_root = os.path.join(voices_dir, session['language'])
                    sessions_root = os.path.join(voices_dir, '__sessions')
                    is_in_sessions = os.path.commonpath([speaker_path, os.path.abspath(sessions_root)]) == os.path.abspath(sessions_root)
                    is_in_builtin = os.path.commonpath([speaker_path, os.path.abspath(builtin_root)]) == os.path.abspath(builtin_root)
                    # Check if voice is built-in
                    is_builtin = any(
                        speaker in settings.get('voices', {})
                        for settings in (default_engine_settings[engine] for engine in TTS_ENGINES.values())
                    )
                    if is_builtin and is_in_builtin:
                        error = f'Voice file {speaker} is a builtin voice and cannot be deleted.'
                        show_alert({"type": "warning", "msg": error})
                        return gr.update(), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)
                    try:
                        selected_path = Path(selected).resolve()
                        parent_path = Path(session['voice_dir']).parent.resolve()
                        if parent_path in selected_path.parents:
                            msg = f'Are you sure to delete {speaker}...'
                            return (
                                gr.update(value='confirm_voice_del'),
                                gr.update(value=show_modal('confirm', msg), visible=True),
                                gr.update(visible=True),
                                gr.update(visible=True)
                            )
                        else:
                            error = f'{speaker} is part of the global voices directory. Only your own custom uploaded voices can be deleted!'
                            show_alert({"type": "warning", "msg": error})
                            return gr.update(), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)
                    except Exception as e:
                        error = f'Could not delete the voice file {selected}!\n{e}'
                        alert_exception(error)
                        return gr.update(), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)
                # Fallback/default return if not selected or after errors
                return gr.update(), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)
            except Exception as e:
                error = f'click_gr_voice_del_btn(): {e}'
                alert_exception(error)
                return gr.update(), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)

        def click_gr_custom_model_del_btn(selected, id):
            try:
                if selected is not None:
                    session = context_module.context.get_session(id)
                    selected_name = os.path.basename(selected)
                    msg = f'Are you sure to delete {selected_name}...'
                    return gr.update(value='confirm_custom_model_del'), gr.update(value=show_modal('confirm', msg),visible=True), gr.update(visible=True), gr.update(visible=True)
            except Exception as e:
                error = f'Could not delete the custom model {selected_name}!'
                alert_exception(error)
            return gr.update(), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)

        def click_gr_audiobook_del_btn(selected, id):
            try:
                if selected is not None:
                    session = context_module.context.get_session(id)
                    selected_name = Path(selected).stem
                    msg = f'Are you sure to delete {selected_name}...'
                    return gr.update(value='confirm_audiobook_del'), gr.update(value=show_modal('confirm', msg),visible=True), gr.update(visible=True), gr.update(visible=True)
            except Exception as e:
                error = f'Could not delete the audiobook {selected_name}!'
                alert_exception(error)
            return gr.update(), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)

        def confirm_deletion(voice_path, custom_model, audiobook, id, method=None):
            try:
                if method is not None:
                    session = context_module.context.get_session(id)
                    if method == 'confirm_voice_del':
                        selected_name = Path(voice_path).stem
                        pattern = re.sub(r'\.wav$', '*.wav', voice_path)
                        files2remove = glob(pattern)
                        for file in files2remove:
                            os.remove(file)
                        shutil.rmtree(os.path.join(os.path.dirname(voice_path), 'bark', selected_name), ignore_errors=True)
                        msg = f"Voice file {re.sub(r'.wav$', '', selected_name)} deleted!"
                        session['voice'] = None
                        show_alert({"type": "warning", "msg": msg})
                        return gr.update(), gr.update(), gr.update(visible=False), update_gr_voice_list(id), gr.update(visible=False), gr.update(visible=False)
                    elif method == 'confirm_custom_model_del':
                        selected_name = os.path.basename(custom_model)
                        shutil.rmtree(custom_model, ignore_errors=True)                           
                        msg = f'Custom model {selected_name} deleted!'
                        session['custom_model'] = None
                        show_alert({"type": "warning", "msg": msg})
                        return update_gr_custom_model_list(id), gr.update(), gr.update(visible=False), gr.update(), gr.update(visible=False), gr.update(visible=False)
                    elif method == 'confirm_audiobook_del':
                        selected_name = Path(audiobook).stem
                        if os.path.isdir(audiobook):
                            shutil.rmtree(selected, ignore_errors=True)
                        elif os.path.exists(audiobook):
                            os.remove(audiobook)
                        vtt_path = Path(audiobook).with_suffix('.vtt')
                        if os.path.exists(vtt_path):
                            os.remove(vtt_path)
                        msg = f'Audiobook {selected_name} deleted!'
                        session['audiobook'] = None
                        show_alert({"type": "warning", "msg": msg})
                        return gr.update(), update_gr_audiobook_list(id), gr.update(visible=False), gr.update(), gr.update(visible=False), gr.update(visible=False)
                return gr.update(), gr.update(), gr.update(visible=False), gr.update(), gr.update(visible=False), gr.update(visible=False)
            except Exception as e:
                error = f'confirm_deletion(): {e}!'
                alert_exception(error)
            return gr.update(), gr.update(), gr.update(visible=False), gr.update(), gr.update(visible=False), gr.update(visible=False)
                
        def prepare_audiobook_download(selected):
            if os.path.exists(selected):
                return selected
            return None           

        def update_gr_voice_list(id):
            try:
                nonlocal voice_options
                session = context_module.context.get_session(id)
                lang_dir = session['language'] if session['language'] != 'con' else 'con-'  # Bypass Windows CON reserved name
                file_pattern = "*.wav"
                eng_options = []
                bark_options = []
                builtin_options = [
                    (os.path.splitext(f.name)[0], str(f))
                    for f in Path(os.path.join(voices_dir, lang_dir)).rglob(file_pattern)
                ]
                if session['language'] in language_tts[TTS_ENGINES['XTTSv2']]:
                    builtin_names = {t[0]: None for t in builtin_options}
                    eng_dir = Path(os.path.join(voices_dir, "eng"))
                    eng_options = [
                        (base, str(f))
                        for f in eng_dir.rglob(file_pattern)
                        for base in [os.path.splitext(f.name)[0]]
                        if base not in builtin_names
                    ]
                if session['tts_engine'] == TTS_ENGINES['BARK']:
                    lang_array = languages.get(part3=session['language'])
                    if lang_array:
                        lang_iso1 = lang_array.part1 
                        lang = lang_iso1.lower()
                        speakers_path = Path(default_engine_settings[TTS_ENGINES['BARK']]['speakers_path'])
                        pattern_speaker = re.compile(r"^.*?_speaker_(\d+)$")
                        bark_options = [
                            (pattern_speaker.sub(r"Speaker \1", f.stem), str(f.with_suffix(".wav")))
                            for f in speakers_path.rglob(f"{lang}_speaker_*.npz")
                        ]
                voice_options = builtin_options + eng_options + bark_options
                session['voice_dir'] = os.path.join(voices_dir, '__sessions', f"voice-{session['id']}", session['language'])
                os.makedirs(session['voice_dir'], exist_ok=True)
                if session['voice_dir'] is not None:
                    parent_dir = Path(session['voice_dir']).parent
                    voice_options += [
                        (os.path.splitext(f.name)[0], str(f))
                        for f in parent_dir.rglob(file_pattern)
                        if f.is_file()
                    ]
                if session['tts_engine'] in [TTS_ENGINES['VITS'], TTS_ENGINES['FAIRSEQ'], TTS_ENGINES['TACOTRON2'], TTS_ENGINES['YOURTTS']]:
                    voice_options = [('Default', None)] + sorted(voice_options, key=lambda x: x[0].lower())
                else:
                    voice_options = sorted(voice_options, key=lambda x: x[0].lower())                           
                default_voice_path = models[session['tts_engine']][session['fine_tuned']]['voice']
                if session['voice'] is None:
                    if voice_options[0][1] is not None:
                        default_name = Path(default_voice_path).stem
                        for name, value in voice_options:
                            if name == default_name:
                                session['voice'] = value
                                break
                        else:
                            values = [v for _, v in voice_options]
                            if default_voice_path in values:
                                session['voice'] = default_voice_path
                            else:
                                session['voice'] = voice_options[0][1]
                else:
                    current_voice_name = Path(session['voice']).stem
                    current_voice_path = next(
                        (path for name, path in voice_options if name == current_voice_name and path == session['voice']), False
                    )
                    if current_voice_path:
                        session['voice'] = current_voice_path
                    else:
                        session['voice'] = default_voice_path
                return gr.update(choices=voice_options, value=session['voice'])
            except Exception as e:
                error = f'update_gr_voice_list(): {e}!'
                alert_exception(error)
                return gr.update()

        def update_gr_tts_engine_list(id):
            try:
                nonlocal tts_engine_options
                session = context_module.context.get_session(id)
                # Ensure language is set, use default if not
                if not session.get('language'):
                    session['language'] = default_language_code
                tts_engine_options = get_compatible_tts_engines(session['language'])
                # Only update tts_engine if options are available
                if len(tts_engine_options) > 0:
                    session['tts_engine'] = session['tts_engine'] if session['tts_engine'] in tts_engine_options else tts_engine_options[0]
                    return gr.update(choices=tts_engine_options, value=session['tts_engine'])
                else:
                    # Fallback to default if no options
                    return gr.update(choices=[], value=None)
            except Exception as e:
                error = f'update_gr_tts_engine_list(): {e}!'
                alert_exception(error)
                return gr.update()

        def update_gr_custom_model_list(id):
            try:
                nonlocal custom_model_options
                session = context_module.context.get_session(id)
                custom_model_tts_dir = check_custom_model_tts(session['custom_model_dir'], session['tts_engine'])

                # Handle case where custom_model_tts_dir is None
                if custom_model_tts_dir is None:
                    custom_model_options = [('None', None)]
                else:
                    custom_model_options = [('None', None)] + [
                        (
                            str(dir),
                            os.path.join(custom_model_tts_dir, dir)
                        )
                        for dir in os.listdir(custom_model_tts_dir)
                        if os.path.isdir(os.path.join(custom_model_tts_dir, dir))
                    ]

                session['custom_model'] = session['custom_model'] if session['custom_model'] in [option[1] for option in custom_model_options] else custom_model_options[0][1]
                return gr.update(choices=custom_model_options, value=session['custom_model'])
            except Exception as e:
                error = f'update_gr_custom_model_list(): {e}!'
                print(error)  # Log the error
                gr.Warning(error)  # Show warning to user
                custom_model_options = [('None', None)]
                return gr.update(choices=custom_model_options, value=None)

        def update_gr_fine_tuned_list(id):
            try:
                nonlocal fine_tuned_options
                session = context_module.context.get_session(id)
                fine_tuned_options = [
                    name for name, details in models.get(session['tts_engine'],{}).items()
                    if details.get('lang') == 'multi' or details.get('lang') == session['language']
                ]
                session['fine_tuned'] = session['fine_tuned'] if session['fine_tuned'] in fine_tuned_options else default_fine_tuned
                return gr.update(choices=fine_tuned_options, value=session['fine_tuned'])
            except Exception as e:
                error = f'update_gr_fine_tuned_list(): {e}!'
                alert_exception(error)              
                return gr.update()

        def change_gr_device(device, id):
            session = context_module.context.get_session(id)
            session['device'] = device

        def change_gr_language(selected, id):
            if selected:
                session = context_module.context.get_session(id)
                prev = session['language']      
                session['language'] = selected
                return[
                    gr.update(value=session['language']),
                    update_gr_tts_engine_list(id),
                    update_gr_custom_model_list(id),
                    update_gr_fine_tuned_list(id)
                ]
            return (gr.update(), gr.update(), gr.update(), gr.update())

        def check_custom_model_tts(custom_model_dir, tts_engine):
            dir_path = None
            if custom_model_dir is not None and tts_engine is not None:
                dir_path = os.path.join(custom_model_dir, tts_engine)
                if not os.path.isdir(dir_path):
                    os.makedirs(dir_path, exist_ok=True)
            return dir_path

        def change_gr_custom_model_file(f, t, id):
            if f is not None:
                state = {}
                try:
                    if len(custom_model_options) > max_custom_model:
                        error = f'You are allowed to upload a max of {max_custom_models} models'   
                        state['type'] = 'warning'
                        state['msg'] = error
                    else:
                        session = context_module.context.get_session(id)
                        session['tts_engine'] = t
                        required_files = models[session['tts_engine']]['internal']['files']
                        if analyze_uploaded_file(f, required_files):
                            model = extract_custom_model(f, session)
                            if model is None:
                                error = f'Cannot extract custom model zip file {os.path.basename(f)}'
                                state['type'] = 'warning'
                                state['msg'] = error
                            else:
                                session['custom_model'] = model
                                msg = f'{os.path.basename(model)} added to the custom models list'
                                state['type'] = 'success'
                                state['msg'] = msg
                        else:
                            error = f'{os.path.basename(f)} is not a valid model or some required files are missing'
                            state['type'] = 'warning'
                            state['msg'] = error
                except ClientDisconnect:
                    error = 'Client disconnected during upload. Operation aborted.'
                    state['type'] = 'error'
                    state['msg'] = error
                except Exception as e:
                    error = f'change_gr_custom_model_file() exception: {str(e)}'
                    state['type'] = 'error'
                    state['msg'] = error
                show_alert(state)
                return gr.update(value=None)
            return gr.update()

        def change_gr_tts_engine_list(engine, id):
            session = context_module.context.get_session(id)
            session['tts_engine'] = engine
            default_voice_path = models[session['tts_engine']][session['fine_tuned']]['voice']
            if default_voice_path is None:
                session['voice'] = default_voice_path
            bark_visible = False
            if session['tts_engine'] == TTS_ENGINES['XTTSv2']:
                visible_custom_model = True
                if session['fine_tuned'] != 'internal':
                    visible_custom_model = False
                return (
                       gr.update(value=show_rating(session['tts_engine'])), 
                       gr.update(visible=visible_gr_tab_xtts_params), gr.update(visible=False), gr.update(visible=visible_custom_model), update_gr_fine_tuned_list(id),
                       gr.update(label=f"*Upload {session['tts_engine']} Model (Should be a ZIP file with {', '.join(models[session['tts_engine']][default_fine_tuned]['files'])})"),
                       gr.update(label=f"My {session['tts_engine']} custom models")
                )
            else:
                if session['tts_engine'] == TTS_ENGINES['BARK']:
                    bark_visible = visible_gr_tab_bark_params
                return (
                        gr.update(value=show_rating(session['tts_engine'])), gr.update(visible=False), gr.update(visible=bark_visible), 
                        gr.update(visible=False), update_gr_fine_tuned_list(id), gr.update(label=f"*Upload Fine Tuned Model not available for {session['tts_engine']}"), gr.update(label='')
                )
                
        def change_gr_fine_tuned_list(selected, id):
            if selected:
                session = context_module.context.get_session(id)
                visible = False
                if session['tts_engine'] == TTS_ENGINES['XTTSv2']:
                    if selected == 'internal':
                        visible = visible_gr_group_custom_model
                session['fine_tuned'] = selected
                return gr.update(visible=visible)
            return gr.update()

        def change_gr_custom_model_list(selected, id):
            session = context_module.context.get_session(id)
            session['custom_model'] = next((value for label, value in custom_model_options if value == selected), None)
            visible = True if session['custom_model'] is not None else False
            return gr.update(visible=not visible), gr.update(visible=visible)
        
        def change_gr_output_format_list(val, id):
            session = context_module.context.get_session(id)
            session['output_format'] = val
            return
            
        def change_gr_output_split(bool, id):
            session = context_module.context.get_session(id)
            session['output_split'] = bool
            return gr.update(visible=bool)

        def change_gr_output_split_hours(selected, id):
            session = context_module.context.get_session(id)
            session['output_split_hours'] = selected
            return

        def change_gr_audiobook_player_playback_time(str, id):
            session = context_module.context.get_session(id)
            session['playback_time'] = float(str)
            return

        def change_param(key, val, id, val2=None):
            session = context_module.context.get_session(id)
            session[key] = val
            state = {}
            if key == 'length_penalty':
                if val2 is not None:
                    if float(val) > float(val2):
                        error = 'Length penalty must be always lower than num beams if greater than 1.0 or equal if 1.0'   
                        state['type'] = 'warning'
                        state['msg'] = error
                        show_alert(state)
            elif key == 'num_beams':
                if val2 is not None:
                    if float(val) < float(val2):
                        error = 'Num beams must be always higher than length penalty or equal if its value is 1.0'   
                        state['type'] = 'warning'
                        state['msg'] = error
                        show_alert(state)
            return

        def submit_convert_btn(
                id, device, ebook_file, tts_engine, language, voice, custom_model, fine_tuned, output_format, temperature,
                length_penalty, num_beams, repetition_penalty, top_k, top_p, speed, enable_text_splitting, text_temp, waveform_temp,
                output_split, output_split_hours, scan_chapters
            ):
            try:
                session = context_module.context.get_session(id)
                args = {
                    "is_gui_process": is_gui_process,
                    "session": id,
                    "script_mode": script_mode,
                    "device": device.lower(),
                    "tts_engine": tts_engine,
                    "ebook": ebook_file if isinstance(ebook_file, str) else None,
                    "ebook_list": ebook_file if isinstance(ebook_file, list) else None,
                    "audiobooks_dir": session['audiobooks_dir'],
                    "voice": voice,
                    "language": language,
                    "custom_model": custom_model,
                    "fine_tuned": fine_tuned,
                    "output_format": output_format,
                    "temperature": float(temperature),
                    "length_penalty": float(length_penalty),
                    "num_beams": session['num_beams'],
                    "repetition_penalty": float(repetition_penalty),
                    "top_k": int(top_k),
                    "top_p": float(top_p),
                    "speed": float(speed),
                    "enable_text_splitting": enable_text_splitting,
                    "text_temp": float(text_temp),
                    "waveform_temp": float(waveform_temp),
                    "output_split": output_split,
                    "output_split_hours": output_split_hours
                }
                error = None
                if args['ebook'] is None and args['ebook_list'] is None:
                    error = 'Error: a file or directory is required.'
                    show_alert({"type": "warning", "msg": error})
                elif args['num_beams'] < args['length_penalty']:
                    error = 'Error: num beams must be greater or equal than length penalty.'
                    show_alert({"type": "warning", "msg": error})
                else:
                    # NEW FEATURE: Scan and detect moved chapters if checkbox is checked
                    if scan_chapters:
                        print("🔍 Scanning for existing chapter files...")
                        from lib.checkpoint_manager import CheckpointManager
                        checkpoint_mgr = CheckpointManager(session)
                        scan_success = checkpoint_mgr.update_checkpoint_from_scan()
                        if scan_success:
                            show_alert({"type": "success", "msg": "✅ Chapters scanned successfully! Will resume from last completed chapter."})
                        else:
                            show_alert({"type": "warning", "msg": "⚠️ Chapter scan completed but found no existing files."})

                    session['status'] = 'converting'
                    # FIX: Mark this session as active when conversion starts
                    session_persistence.set_active_session(session['id'])
                    session['progress'] = len(audiobook_options)
                    if isinstance(args['ebook_list'], list):
                        ebook_list = args['ebook_list'][:]
                        for file in ebook_list:
                            if any(file.endswith(ext) for ext in ebook_formats):
                                print(f'Processing eBook file: {os.path.basename(file)}')
                                args['ebook'] = file
                                progress_status, passed = convert_ebook(args)
                                if passed is False:
                                    if session['status'] == 'converting':
                                        error = 'Conversion cancelled.'
                                        break
                                    else:
                                        error = 'Conversion failed.'
                                        break
                                else:
                                    show_alert({"type": "success", "msg": progress_status})
                                    args['ebook_list'].remove(file)
                                    reset_ebook_session(args['session'])
                                    count_file = len(args['ebook_list'])
                                    if count_file > 0:
                                        msg = f"{len(args['ebook_list'])} remaining..."
                                    else:
                                        msg = 'Conversion successful!'
                                    yield gr.update(value=msg)
                        session['status'] = 'ready'
                        # FIX: Clear active_session after batch conversion completes
                        session_persistence.set_active_session(None)
                    else:
                        print(f"Processing eBook file: {os.path.basename(args['ebook'])}")
                        progress_status, passed = convert_ebook(args)
                        if passed is False:
                            if session['status'] == 'converting':
                                error = 'Conversion cancelled.'
                            else:
                                error = 'Conversion failed.'
                            session['status'] = 'ready'
                            # FIX: Clear active_session after failed conversion
                            session_persistence.set_active_session(None)
                        else:
                            show_alert({"type": "success", "msg": progress_status})
                            reset_ebook_session(args['session'])
                            msg = 'Conversion successful!'
                            return gr.update(value=msg)
                if error is not None:
                    show_alert({"type": "warning", "msg": error})
            except Exception as e:
                error = f'submit_convert_btn(): {e}'
                alert_exception(error)
            return gr.update(value='')

        def update_gr_audiobook_list(id):
            try:
                nonlocal audiobook_options
                session = context_module.context.get_session(id)
                # Check if audiobooks_dir is initialized before using it
                if not session.get('audiobooks_dir') or not os.path.exists(session['audiobooks_dir']):
                    return gr.update(choices=[], value=None)
                audiobook_options = [
                    (f, os.path.join(session['audiobooks_dir'], str(f)))
                    for f in os.listdir(session['audiobooks_dir'])
                    if not f.lower().endswith(".vtt")  # exclude VTT files
                ]
                audiobook_options.sort(
                    key=lambda x: os.path.getmtime(x[1]),
                    reverse=True
                )
                session['audiobook'] = (
                    session['audiobook']
                    if session['audiobook'] in [option[1] for option in audiobook_options]
                    else None
                )
                if len(audiobook_options) > 0:
                    if session['audiobook'] is not None:
                        return gr.update(choices=audiobook_options, value=session['audiobook'])
                    else:
                        return gr.update(choices=audiobook_options, value=audiobook_options[0][1])
                gr.update(choices=audiobook_options)
            except Exception as e:
                error = f'update_gr_audiobook_list(): {e}!'
                alert_exception(error)              
                return gr.update()

        def change_gr_read_data(data, state, req: gr.Request):
            try:
                msg = 'Error while loading saved session. Please try to delete your cookies and refresh the page'

                # FIX PROBLEM 1: Create new session and save immediately
                if data is None or not isinstance(data, dict) or 'id' not in data:
                    new_session = context_module.context.get_session(str(uuid.uuid4()))
                    # Save new session to disk immediately
                    save_session_to_disk(new_session['id'])
                    print(f"✓ Created and saved new session: {new_session['id'][:8]}")
                    data = new_session

                # Check if this session existed before (to detect fresh server start after Docker restart)
                session_existed_in_memory = data['id'] in context_module.context.sessions

                # Get or create session in memory
                session = context_module.context.get_session(data['id'])

                # FIX PROBLEM 11: Load from disk FIRST, before any other restoration
                # This ensures disk data takes precedence over potentially stale localStorage data
                disk_session = None
                if data['id']:
                    disk_session = load_session_from_disk(data['id'])
                    if disk_session and not session_existed_in_memory:
                        # Restore session from disk to memory (only if not in memory)
                        for key, value in disk_session.items():
                            if key not in ['tab_id', 'process_id', 'cancellation_requested']:
                                # Don't restore runtime-only fields
                                session[key] = value
                        print(f"✓ Session {data['id'][:8]} restored from disk")

                # FIX PROBLEM 7 & 10: Use disk status as source of truth, not localStorage
                # This prevents false positives when localStorage is stale
                was_converting = False
                if disk_session:
                    # Trust disk status over localStorage
                    was_converting = disk_session.get('status') == 'converting'
                else:
                    # Fallback to localStorage only if no disk session
                    was_converting = data.get('status') == 'converting'

                # Detect if this is a reconnection from the same browser tab
                same_tab_reconnecting = data.get('tab_id') == session.get('tab_id') and session.get('tab_id') is not None

                # FIX PROBLEM 10: Better reconnection detection
                # Check if this socket hash already exists for this session (true reconnect)
                is_existing_socket = req.session_hash in session.keys() and req.session_hash in context_module.active_sessions

                # Count active socket connections for this session
                active_socket_count = sum(1 for hash_key in context_module.active_sessions if hash_key in session.keys())
                has_no_active_sockets = active_socket_count == 0

                # Only restore from localStorage if it's a same-tab reconnect or no active sessions
                if same_tab_reconnecting or len(context_module.active_sessions) == 0 or has_no_active_sockets:
                    restore_session_from_data(data, session)

                # FIX PROBLEM 3: Don't reset status if conversion is in progress
                # CRITICAL: Never interrupt an active conversion
                if was_converting and session.get('status') == 'converting':
                    # Conversion is actively running, DO NOT reset status
                    print(f"✓ Preserving active conversion for session {session['id'][:8]}")
                elif not was_converting and has_no_active_sockets:
                    # No conversion and no active connections = safe to reset
                    session['status'] = None

                # Block only if it's NOT a reconnection AND start_session fails
                if not same_tab_reconnecting and not is_existing_socket and not has_no_active_sockets:
                    if not ctx_tracker.start_session(session['id']):
                        error = "Your session is already active.<br>If it's not the case please close your browser and relaunch it."
                        return gr.update(), gr.update(), gr.update(value=''), update_gr_glass_mask(str=error)

                # Register this socket connection
                context_module.active_sessions.add(req.session_hash)
                session[req.session_hash] = req.session_hash
                session['cancellation_requested'] = False
                if isinstance(session['ebook'], str):
                    if not os.path.exists(session['ebook']):
                        session['ebook'] = None
                if session['voice'] is not None:
                    if not os.path.exists(session['voice']):
                        session['voice'] = None
                if session['custom_model'] is not None:
                    if not os.path.exists(session['custom_model_dir']):
                        session['custom_model'] = None
                if session['fine_tuned'] is not None:
                    if session['tts_engine'] is not None:
                        if session['tts_engine'] in models.keys():
                            if session['fine_tuned'] not in models[session['tts_engine']].keys():
                                session['fine_tuned'] = default_fine_tuned
                        else:
                            session['tts_engine'] = default_tts_engine
                            session['fine_tuned'] = default_fine_tuned
                if session['audiobook'] is not None:
                    if not os.path.exists(session['audiobook']):
                        session['audiobook'] = None
                # If conversion was in progress and is still ongoing, keep it as 'converting'
                # If it completed while disconnected, it will already be 'ready' from the conversion process
                if was_converting and session['status'] == 'converting':
                    # Conversion is still in progress, keep status
                    pass
                elif was_converting and session['status'] != 'converting':
                    # Conversion completed while disconnected, ensure status is correct
                    if session['status'] != 'ready':
                        session['status'] = 'ready'
                session['system'] = (f"{platform.system()}-{platform.release()}").lower()
                session['custom_model_dir'] = os.path.join(models_dir, '__sessions', f"model-{session['id']}")
                session['voice_dir'] = os.path.join(voices_dir, '__sessions', f"voice-{session['id']}", session['language'])
                os.makedirs(session['custom_model_dir'], exist_ok=True)
                os.makedirs(session['voice_dir'], exist_ok=True)
                # As now uploaded voice files are in their respective language folder so check if no wav and bark folder are on the voice_dir root from previous versions
                [shutil.move(src, os.path.join(session['voice_dir'], os.path.basename(src))) for src in glob(os.path.join(os.path.dirname(session['voice_dir']), '*.wav')) + ([os.path.join(os.path.dirname(session['voice_dir']), 'bark')] if os.path.isdir(os.path.join(os.path.dirname(session['voice_dir']), 'bark')) and not os.path.exists(os.path.join(session['voice_dir'], 'bark')) else [])]                
                if is_gui_shared:
                    msg = f' Note: access limit time: {interface_shared_tmp_expire} days'
                    session['audiobooks_dir'] = os.path.join(audiobooks_gradio_dir, f"web-{session['id']}")
                    delete_unused_tmp_dirs(audiobooks_gradio_dir, interface_shared_tmp_expire, session)
                else:
                    msg = f' Note: if no activity is detected after {tmp_expire} days, your session will be cleaned up.'
                    session['audiobooks_dir'] = os.path.join(audiobooks_host_dir, f"web-{session['id']}")
                    delete_unused_tmp_dirs(audiobooks_host_dir, tmp_expire, session)
                if not os.path.exists(session['audiobooks_dir']):
                    os.makedirs(session['audiobooks_dir'], exist_ok=True)
                previous_hash = state['hash']
                new_hash = hash_proxy_dict(MappingProxyType(session))
                state['hash'] = new_hash
                session_dict = proxy2dict(session)
                show_alert({"type": "info", "msg": msg})
                return gr.update(value=session_dict), gr.update(value=state), gr.update(value=session['id']), gr.update()
            except Exception as e:
                error = f'change_gr_read_data(): {e}'
                alert_exception(error)
                return gr.update(), gr.update(), gr.update(), gr.update()

        def save_session(id, state):
            try:
                if id:
                    if id in context_module.context.sessions:
                        session = context_module.context.get_session(id)
                        if session:
                            if session['event'] == 'clear':
                                session_dict = proxy2dict(session)  # Must convert proxy to dict for JSON serialization
                            else:
                                previous_hash = state['hash']
                                new_hash = hash_proxy_dict(MappingProxyType(session))
                                if previous_hash == new_hash:
                                    return gr.update(), gr.update(), gr.update()
                                else:
                                    state['hash'] = new_hash
                                    session_dict = proxy2dict(session)

                            # Save session to disk
                            save_session_to_disk(id)

                            if session['status'] == 'converting':
                                if session['progress'] != len(audiobook_options):
                                    session['progress'] = len(audiobook_options)
                                    return gr.update(value=session_dict), gr.update(value=state), update_gr_audiobook_list(id)
                            return gr.update(value=session_dict), gr.update(value=state), gr.update()
                return gr.update(), gr.update(), gr.update()
            except Exception as e:
                error = f'save_session(): {e}!'
                alert_exception(error)
                return gr.update(), gr.update(value=e), gr.update()
        
        def clear_event(id):
            if id:
                session = context_module.context.get_session(id)
                if session['event'] is not None:
                    session['event'] = None

        gr_ebook_file.change(
            fn=state_convert_btn,
            inputs=[gr_ebook_file, gr_ebook_mode, gr_custom_model_file, gr_session],
            outputs=[gr_convert_btn]
        ).then(
            fn=change_gr_ebook_file,
            inputs=[gr_ebook_file, gr_session],
            outputs=[gr_modal]
        )
        gr_ebook_mode.change(
            fn=change_gr_ebook_mode,
            inputs=[gr_ebook_mode, gr_session],
            outputs=[gr_ebook_file]
        )
        gr_voice_file.upload(
            fn=change_gr_voice_file,
            inputs=[gr_voice_file, gr_session],
            outputs=[gr_voice_file]
        ).then(
            fn=update_gr_voice_list,
            inputs=[gr_session],
            outputs=[gr_voice_list]
        )
        gr_voice_list.change(
            fn=change_gr_voice_list,
            inputs=[gr_voice_list, gr_session],
            outputs=[gr_voice_player, gr_voice_del_btn]
        )
        gr_voice_del_btn.click(
            fn=click_gr_voice_del_btn,
            inputs=[gr_voice_list, gr_session],
            outputs=[gr_confirm_field_hidden, gr_modal, gr_confirm_yes_btn, gr_confirm_no_btn]
        )
        gr_device.change(
            fn=change_gr_device,
            inputs=[gr_device, gr_session],
            outputs=None
        )
        # FIX PROBLEM 9: Session selector change handler
        # Note: req: gr.Request is auto-injected by Gradio, don't include in inputs
        gr_session_selector.change(
            fn=handle_session_selector_change,
            inputs=[gr_session_selector, gr_session],
            outputs=[gr_session, gr_session_selector]
        ).then(
            fn=refresh_interface,
            inputs=[gr_session],
            outputs=None
        )

        gr_language.change(
            fn=change_gr_language,
            inputs=[gr_language, gr_session],
            outputs=[gr_language, gr_tts_engine_list, gr_custom_model_list, gr_fine_tuned_list]
        ).then(
            fn=update_gr_voice_list,
            inputs=[gr_session],
            outputs=[gr_voice_list]
        )
        gr_tts_engine_list.change(
            fn=change_gr_tts_engine_list,
            inputs=[gr_tts_engine_list, gr_session],
            outputs=[gr_tts_rating, gr_tab_xtts_params, gr_tab_bark_params, gr_group_custom_model, gr_fine_tuned_list, gr_custom_model_file, gr_custom_model_list] 
        ).then(
            fn=update_gr_voice_list,
            inputs=[gr_session],
            outputs=[gr_voice_list]        
        )
        gr_fine_tuned_list.change(
            fn=change_gr_fine_tuned_list,
            inputs=[gr_fine_tuned_list, gr_session],
            outputs=[gr_group_custom_model]
        ).then(
            fn=update_gr_voice_list,
            inputs=[gr_session],
            outputs=[gr_voice_list]        
        )
        gr_custom_model_file.upload(
            fn=change_gr_custom_model_file,
            inputs=[gr_custom_model_file, gr_tts_engine_list, gr_session],
            outputs=[gr_custom_model_file]
        ).then(
            fn=update_gr_custom_model_list,
            inputs=[gr_session],
            outputs=[gr_custom_model_list]
        )
        gr_custom_model_list.change(
            fn=change_gr_custom_model_list,
            inputs=[gr_custom_model_list, gr_session],
            outputs=[gr_fine_tuned_list, gr_custom_model_del_btn]
        )
        gr_custom_model_del_btn.click(
            fn=click_gr_custom_model_del_btn,
            inputs=[gr_custom_model_list, gr_session],
            outputs=[gr_confirm_field_hidden, gr_modal, gr_confirm_yes_btn, gr_confirm_no_btn]
        )
        gr_output_format_list.change(
            fn=change_gr_output_format_list,
            inputs=[gr_output_format_list, gr_session],
            outputs=None
        )
        gr_output_split.change(
            fn=change_gr_output_split,
            inputs=[gr_output_split, gr_session],
            outputs=gr_output_split_hours
        )
        gr_output_split_hours.change(
            fn=change_gr_output_split_hours,
            inputs=[gr_output_split_hours, gr_session],
            outputs=None
        )
        gr_audiobook_vtt.change(
            fn=lambda: gr.update(value=''),
            inputs=[],
            outputs=[gr_audiobook_sentence]
        ).then(
            fn=None,
            inputs=[gr_audiobook_vtt],
            js='(data)=>{window.load_vtt?.(URL.createObjectURL(new Blob([data],{type: "text/vtt"})));}'         
        )
        gr_tab_progress.change(
            fn=None,
            inputs=[gr_tab_progress],
            outputs=[],
            js=f'() => {{ document.title = "{title}"; }}'
        )
        gr_audiobook_player_playback_time.change(
            fn=change_gr_audiobook_player_playback_time,
            inputs=[gr_audiobook_player_playback_time, gr_session],
            outputs=[]
        )
        gr_audiobook_download_btn.click(
            fn=lambda audiobook: show_alert({"type": "info", "msg": f'Downloading {os.path.basename(audiobook)}'}),
            inputs=[gr_audiobook_list],
            outputs=None,
            show_progress='minimal'
        )
        gr_audiobook_list.change(
            fn=change_gr_audiobook_list,
            inputs=[gr_audiobook_list, gr_session],
            outputs=[gr_audiobook_download_btn, gr_audiobook_player, gr_audiobook_vtt, gr_group_audiobook_list]
        )
        gr_audiobook_del_btn.click(
            fn=click_gr_audiobook_del_btn,
            inputs=[gr_audiobook_list, gr_session],
            outputs=[gr_confirm_field_hidden, gr_modal, gr_confirm_yes_btn, gr_confirm_no_btn]
        )
        ########### XTTSv2 Params
        gr_xtts_temperature.change(
            fn=lambda val, id: change_param('temperature', val, id),
            inputs=[gr_xtts_temperature, gr_session],
            outputs=None
        )
        gr_xtts_length_penalty.change(
            fn=lambda val, id, val2: change_param('length_penalty', val, id, val2),
            inputs=[gr_xtts_length_penalty, gr_session, gr_xtts_num_beams],
            outputs=None,
        )
        gr_xtts_num_beams.change(
            fn=lambda val, id, val2: change_param('num_beams', val, id, val2),
            inputs=[gr_xtts_num_beams, gr_session, gr_xtts_length_penalty],
            outputs=None,
        )
        gr_xtts_repetition_penalty.change(
            fn=lambda val, id: change_param('repetition_penalty', val, id),
            inputs=[gr_xtts_repetition_penalty, gr_session],
            outputs=None
        )
        gr_xtts_top_k.change(
            fn=lambda val, id: change_param('top_k', val, id),
            inputs=[gr_xtts_top_k, gr_session],
            outputs=None
        )
        gr_xtts_top_p.change(
            fn=lambda val, id: change_param('top_p', val, id),
            inputs=[gr_xtts_top_p, gr_session],
            outputs=None
        )
        gr_xtts_speed.change(
            fn=lambda val, id: change_param('speed', val, id),
            inputs=[gr_xtts_speed, gr_session],
            outputs=None
        )
        gr_xtts_enable_text_splitting.change(
            fn=lambda val, id: change_param('enable_text_splitting', val, id),
            inputs=[gr_xtts_enable_text_splitting, gr_session],
            outputs=None
        )
        ########### BARK Params
        gr_bark_text_temp.change(
            fn=lambda val, id: change_param('text_temp', val, id),
            inputs=[gr_bark_text_temp, gr_session],
            outputs=None
        )
        gr_bark_waveform_temp.change(
            fn=lambda val, id: change_param('waveform_temp', val, id),
            inputs=[gr_bark_waveform_temp, gr_session],
            outputs=None
        )
        ############ Timer to save session to localStorage
        gr_timer = gr.Timer(9, active=False)
        gr_timer.tick(
            fn=save_session,
            inputs=[gr_session, gr_state_update],
            outputs=[gr_write_data, gr_state_update, gr_audiobook_list]
        ).then(
            fn=clear_event,
            inputs=[gr_session],
            outputs=None
        )
        gr_convert_btn.click(
            fn=state_convert_btn,
            inputs=None,
            outputs=[gr_convert_btn]
        ).then(
            fn=disable_components,
            inputs=[],
            outputs=[gr_ebook_mode, gr_language, gr_voice_file, gr_voice_list, gr_device, gr_tts_engine_list, gr_fine_tuned_list, gr_custom_model_file, gr_custom_model_list]
        ).then(
            fn=submit_convert_btn,
            inputs=[
                gr_session, gr_device, gr_ebook_file, gr_tts_engine_list, gr_language, gr_voice_list,
                gr_custom_model_list, gr_fine_tuned_list, gr_output_format_list,
                gr_xtts_temperature, gr_xtts_length_penalty, gr_xtts_num_beams, gr_xtts_repetition_penalty, gr_xtts_top_k, gr_xtts_top_p, gr_xtts_speed, gr_xtts_enable_text_splitting,
                gr_bark_text_temp, gr_bark_waveform_temp, gr_output_split, gr_output_split_hours, gr_scan_chapters_checkbox
            ],
            outputs=[gr_tab_progress]
        ).then(
            fn=enable_components,
            inputs=[],
            outputs=[gr_ebook_mode, gr_language, gr_voice_file, gr_voice_list, gr_device, gr_tts_engine_list, gr_fine_tuned_list, gr_custom_model_file, gr_custom_model_list]
        ).then(
            fn=refresh_interface,
            inputs=[gr_session],
            outputs=[gr_convert_btn, gr_ebook_file, gr_audiobook_list, gr_audiobook_player, gr_modal, gr_voice_list]
        )
        gr_write_data.change(
            fn=None,
            inputs=[gr_write_data],
            js="""
                (data)=>{
                    try{
                        if(data){
                            localStorage.clear();
                            if(data['event'] != 'clear'){
                                //console.log('save: ', data);
                                window.localStorage.setItem('data', JSON.stringify(data));
                            }
                        }
                    }catch(e){
                        console.log('gr_write_data.change error: '+e)
                    }
                }
            """
        )       
        gr_read_data.change(
            fn=change_gr_read_data,
            inputs=[gr_read_data, gr_state_update],
            outputs=[gr_write_data, gr_state_update, gr_session, gr_glass_mask]
        ).then(
            fn=restore_interface,
            inputs=[gr_session],
            outputs=[
                gr_ebook_file, gr_ebook_mode, gr_device, gr_language,
                gr_tts_engine_list, gr_custom_model_list, gr_fine_tuned_list,
                gr_output_format_list, gr_audiobook_list, gr_audiobook_vtt,
                gr_xtts_temperature, gr_xtts_length_penalty, gr_xtts_num_beams, gr_xtts_repetition_penalty,
                gr_xtts_top_k, gr_xtts_top_p, gr_xtts_speed, gr_xtts_enable_text_splitting, gr_bark_text_temp,
                gr_bark_waveform_temp, gr_voice_list, gr_output_split, gr_output_split_hours, gr_timer
            ]
        ).then(
            fn=update_session_selector,
            inputs=[gr_session],
            outputs=[gr_session_selector]
        ).then(
            fn=lambda session: update_gr_glass_mask(attr='class="hide"') if session else gr.update(),
            inputs=[gr_session],
            outputs=[gr_glass_mask]
        )
        gr_confirm_yes_btn.click(
            fn=confirm_deletion,
            inputs=[gr_voice_list, gr_custom_model_list, gr_audiobook_list, gr_session, gr_confirm_field_hidden],
            outputs=[gr_custom_model_list, gr_audiobook_list, gr_modal, gr_voice_list, gr_confirm_yes_btn, gr_confirm_no_btn]
        )
        gr_confirm_no_btn.click(
            fn=confirm_deletion,
            inputs=[gr_voice_list, gr_custom_model_list, gr_audiobook_list, gr_session],
            outputs=[gr_custom_model_list, gr_audiobook_list, gr_modal, gr_voice_list, gr_confirm_yes_btn, gr_confirm_no_btn]
        )
        app.load(
            fn=None,
            js=r'''
                ()=>{
                    try {
                        if (typeof(window.init_elements) !== "function") {
                            window.init_elements = () => {
                                try {
                                    let lastCue = null;
                                    let fade_timeout = null;
                                    let last_time = 0;
                                    if (gr_root && gr_checkboxes && gr_radios && gr_audiobook_player_playback_time && gr_audiobook_sentence && gr_tab_progress) {
                                        let set_playback_time = false;
                                        gr_audiobook_player.addEventListener("loadedmetadata", () => {
                                            //console.log("loadedmetadata:", window.playback_time);
                                            if (window.playback_time > 0) {
                                                gr_audiobook_player.currentTime = window.playback_time;
                                            }
                                            set_playback_time = true;
                                        },{once: true});
                                        gr_audiobook_player.addEventListener("timeupdate", () => {
                                            if (set_playback_time == true) {
                                                window.playback_time = gr_audiobook_player.currentTime;
                                                const cue = findCue(window.playback_time);
                                                if (cue && cue !== lastCue) {
                                                    if (fade_timeout) {
                                                        gr_audiobook_sentence.style.opacity = "1";
                                                    } else {
                                                        gr_audiobook_sentence.style.opacity = "0";
                                                    }
                                                    gr_audiobook_sentence.style.transition = "none";
                                                    gr_audiobook_sentence.value = cue.text;
                                                    clearTimeout(fade_timeout);
                                                    fade_timeout = setTimeout(() => {
                                                        gr_audiobook_sentence.style.transition = "opacity 0.1s ease-in";
                                                        gr_audiobook_sentence.style.opacity = "1";
                                                        fade_timeout = null;
                                                    }, 33);
                                                    lastCue = cue;
                                                } else if (!cue && lastCue !== null) {
                                                    gr_audiobook_sentence.value = "...";
                                                    lastCue = null;
                                                }
                                                const now = performance.now();
                                                if (now - last_time > 1000) {
                                                    //console.log("timeupdate", window.playback_time);
                                                    gr_audiobook_player_playback_time.value = String(window.playback_time);
                                                    gr_audiobook_player_playback_time.dispatchEvent(new Event("input", { bubbles: true }));
                                                    last_time = now;
                                                }
                                            }
                                        });
                                        gr_audiobook_player.addEventListener("ended", () => {
                                            gr_audiobook_sentence.value = "...";
                                            lastCue = null;
                                        });
                                        
                                        ///////////////
                                        
                                        // Observe programmatic changes
                                        new MutationObserver(tab_progress).observe(gr_tab_progress, { attributes: true, childList: true, subtree: true, characterData: true });
                                        // Also catch user edits
                                        gr_tab_progress.addEventListener("input", tab_progress);
                                        
                                        ///////////////
                                        
                                        const url = new URL(window.location);
                                        const theme = url.searchParams.get("__theme");
                                        let osTheme;
                                        let audioFilter = "";
                                        let elColor = "#666666";
                                        if (theme) {
                                            if (theme === "dark") {
                                                if (gr_audiobook_player) {
                                                    audioFilter = "invert(1) hue-rotate(180deg)";
                                                }
                                                elColor = "#fff";
                                            }
                                            gr_checkboxes.forEach(cb => { cb.style.border = "1px solid " + elColor; });
                                            gr_radios.forEach(cb => { cb.style.border = "1px solid " + elColor; });
                                        } else {
                                            osTheme = window.matchMedia?.("(prefers-color-scheme: dark)").matches;
                                            if (osTheme) {
                                                if (gr_audiobook_player) {
                                                    audioFilter = "invert(1) hue-rotate(180deg)";
                                                }
                                                elColor = "#fff";
                                            }
                                            gr_checkboxes.forEach(cb => { cb.style.border = "1px solid " + elColor; });
                                            gr_radios.forEach(cb => { cb.style.border = "1px solid " + elColor; });
                                        }
                                        if (!gr_audiobook_player.style.transition) {
                                            gr_audiobook_player.style.transition = "filter 1s ease";
                                        }
                                        gr_audiobook_player.style.filter = audioFilter;
                                    }
                                } catch (e) {
                                    console.log("init_elements error:", e);
                                }
                            };
                        }
                        if (typeof(window.load_vtt) !== "function") {
                            window.load_vtt_timeout = null;
                            window.load_vtt = (path) => {
                                try {
                                    if (gr_audiobook_player && gr_audiobook_player_playback_time && gr_audiobook_sentence) {
                                        // Remove any <track> to bypass browser subtitle engine
                                        let existing = gr_root.querySelector("#gr_audiobook_track");
                                        if (existing) {
                                            existing.remove();
                                        }
                                        gr_audiobook_sentence.style.fontSize = "14px";
                                        gr_audiobook_sentence.style.fontWeight = "bold";
                                        gr_audiobook_sentence.style.width = "100%";
                                        gr_audiobook_sentence.style.height = "auto";
                                        gr_audiobook_sentence.style.textAlign = "center";
                                        gr_audiobook_sentence.style.margin = "0";
                                        gr_audiobook_sentence.style.padding = "7px 0 7px 0";
                                        gr_audiobook_sentence.style.lineHeight = "14px";
                                        gr_audiobook_sentence.value = "...";
                                        if (path) {
                                            fetch(path).then(res => res.text()).then(vttText => {
                                                parseVTTFast(vttText);
                                            });
                                        }
                                        gr_audiobook_player.load();
                                    } else {
                                        clearTimeout(window.load_vtt_timeout);
                                        window.load_vtt_timeout = setTimeout(window.load_vtt, 500, path);
                                    }
                                } catch (e) {
                                    console.log("load_vtt error:", e);
                                }
                            };
                        }
                        if (typeof(window.tab_progress) !== "function") {
                            window.tab_progress = () => {
                                const val = gr_tab_progress?.value || gr_tab_progress?.textContent || "";
                                const prct = val.trim().split(" ")[4];
                                if (prct && /^\d+(\.\d+)?%$/.test(prct)) {
                                    document.title = "Ebook2Audiobook: " + prct;
                                }
                            };
                        }
                        function parseVTTFast(vtt) {
                            const lines = vtt.split(/\r?\n/);
                            const timePattern = /(\d{2}:)?\d{2}:\d{2}\.\d{3}/;
                            let start = null, end = null, textBuffer = [];
                            cues = [];

                            function pushCue() {
                                if (start !== null && end !== null && textBuffer.length) {
                                    cues.push({ start, end, text: textBuffer.join("\n") });
                                }
                                start = end = null;
                                textBuffer.length = 0;
                            }

                            for (let i = 0, len = lines.length; i < len; i++) {
                                const line = lines[i];
                                if (!line.trim()) { pushCue(); continue; }
                                if (line.includes("-->")) {
                                    const [s, e] = line.split("-->").map(l => l.trim().split(" ")[0]);
                                    if (timePattern.test(s) && timePattern.test(e)) {
                                        start = toSeconds(s);
                                        end = toSeconds(e);
                                    }
                                } else if (!timePattern.test(line)) {
                                    textBuffer.push(line);
                                }
                            }
                            pushCue();
                        }
                        
                        function toSeconds(ts) {
                            const parts = ts.split(":");
                            if (parts.length === 3) {
                                return parseInt(parts[0], 10) * 3600 +
                                       parseInt(parts[1], 10) * 60 +
                                       parseFloat(parts[2]);
                            }
                            return parseInt(parts[0], 10) * 60 + parseFloat(parts[1]);
                        }

                        function findCue(time) {
                            let lo = 0, hi = cues.length - 1;
                            while (lo <= hi) {
                                const mid = (lo + hi) >> 1;
                                const cue = cues[mid];
                                if (time < cue.start) {
                                    hi = mid - 1;
                                } else if (time >= cue.end) {
                                    lo = mid + 1;
                                } else {
                                    return cue;
                                }
                            }
                            return null;
                        }
                        
                        //////////////////////
                        
                        let gr_root;
                        let gr_checkboxes;
                        let gr_radios;
                        let gr_audiobook_player_playback_time;
                        let gr_audiobook_sentence;
                        let gr_audiobook_player;
                        let gr_tab_progress;
                        let load_timeout;
                        let cues = [];

                        function init() {
                            try {
                                gr_root = (window.gradioApp && window.gradioApp()) || document;
                                if (!gr_root) {
                                    clearTimeout(load_timeout);
                                    load_timeout = setTimeout(init, 1000);
                                    return;
                                }
                                gr_audiobook_player = gr_root.querySelector("#gr_audiobook_player");
                                gr_audiobook_player_playback_time = gr_root.querySelector("#gr_audiobook_player_playback_time input");
                                gr_audiobook_sentence = gr_root.querySelector("#gr_audiobook_sentence textarea");
                                gr_tab_progress = gr_root.querySelector("#gr_tab_progress");
                                gr_checkboxes = gr_root.querySelectorAll("input[type='checkbox']");
                                gr_radios = gr_root.querySelectorAll("input[type='radio']");
                                // If key elements aren’t mounted yet, retry
                                if (!gr_audiobook_player || !gr_audiobook_player_playback_time) {
                                    clearTimeout(load_timeout);
                                    //console.log("Componenents not ready... retrying");
                                    load_timeout = setTimeout(init, 1000);
                                    return;
                                }
                                // if container, get inner <audio>/<video>
                                if (gr_audiobook_player && !gr_audiobook_player.matches?.("audio,video")) {
                                    const real = gr_audiobook_player.querySelector?.("audio,video");
                                    if (real) gr_audiobook_player = real;
                                }
                                //console.log("Componenents ready!");
                                window.init_elements();
                            } catch (e) {
                                console.log("init error:", e);
                                clearTimeout(load_timeout);
                                load_timeout = setTimeout(init, 1000);
                            }
                        }
                        
                        init();

                        window.addEventListener("beforeunload", () => {
                            try {
                                const saved = JSON.parse(localStorage.getItem("data") || "{}");
                                if (saved.tab_id == window.tab_id || !saved.tab_id) {
                                    saved.tab_id = undefined;
                                    // Don't clear status if conversion is in progress
                                    // This allows the process to continue and resync on reconnect
                                    if (saved.status !== 'converting') {
                                        saved.status = undefined;
                                    }
                                    localStorage.setItem("data", JSON.stringify(saved));
                                }
                            } catch (e) {
                                console.log("Error updating status on unload:", e);
                            }
                        });

                        window.playback_time = 0;
                        const stored = window.localStorage.getItem("data");
                        if (stored) {
                            const parsed = JSON.parse(stored);
                            parsed.tab_id = "tab-" + performance.now().toString(36) + "-" + Math.random().toString(36).substring(2, 10);
                            window.playback_time = parsed.playback_time;
                            //console.log("window.playback_time", window.playback_time);
                            return parsed;
                        }
                    } catch (e) {
                        console.log("gr_raed_data js error:", e);
                    }
                    return null;
                }
            ''',
            outputs=[gr_read_data],
        )
        app.unload(cleanup_session)
    try:
        all_ips = get_all_ip_addresses()
        msg = f'IPs available for connection:\n{all_ips}\nNote: 0.0.0.0 is not the IP to connect. Instead use an IP above to connect.'
        print(msg)
        os.environ['no_proxy'] = ' ,'.join(all_ips)
        app.queue(default_concurrency_limit=interface_concurrency_limit).launch(debug=bool(int(os.environ.get('GRADIO_DEBUG', '0'))),show_error=debug_mode, favicon_path='./favicon.ico', server_name=interface_host, server_port=interface_port, share=is_gui_shared, max_file_size=max_upload_size)
    except OSError as e:
        error = f'Connection error: {e}'
        alert_exception(error)
    except socket.error as e:
        error = f'Socket error: {e}'
        alert_exception(error)
    except KeyboardInterrupt:
        error = 'Server interrupted by user. Shutting down...'
        alert_exception(error)
    except Exception as e:
        error = f'An unexpected error occurred: {e}'
        alert_exception(error)
