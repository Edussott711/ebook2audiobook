"""
Tâches Celery pour le traitement distribué.
"""

import logging
import time
import os
import subprocess
import json
from typing import List, Dict, Any

from .celery_app import celery_app
from .checkpoint_manager import DistributedCheckpointManager
from .storage import SharedStorageHandler

logger = logging.getLogger(__name__)

# Cache global du modèle TTS (par worker)
_TTS_ENGINE_CACHE = {}


@celery_app.task(
    bind=True,
    name='lib.distributed.tasks.process_chapter',
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    acks_late=True
)
def process_chapter(
    self,
    chapter_id: int,
    sentences: List[str],
    session_id: str,
    tts_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Traite un chapitre complet : TTS + combine + upload.

    Args:
        self: Instance de la tâche (bind=True)
        chapter_id: ID du chapitre
        sentences: Liste des phrases à convertir
        session_id: ID de session
        tts_config: Configuration TTS

    Returns:
        Dict avec chapter_id, audio_path, duration, etc.
    """
    start_time = time.time()

    logger.info(
        f"[Worker {self.request.hostname}] Processing chapter {chapter_id} "
        f"({len(sentences)} sentences) for session {session_id}"
    )

    try:
        # 1. Charger/récupérer TTS engine depuis cache
        tts_engine = _get_or_create_tts_engine(tts_config)

        # 2. Traiter chaque phrase
        sentence_audio_files = []
        for i, sentence in enumerate(sentences):
            logger.debug(f"Chapter {chapter_id}, sentence {i+1}/{len(sentences)}")

            # Conversion TTS
            output_file = f'/tmp/{session_id}_ch{chapter_id}_s{i}.mp3'
            audio_file = tts_engine.convert_sentence2audio(
                sentence=sentence,
                output_file=output_file
            )
            sentence_audio_files.append(audio_file)

            # Update progress (optionnel)
            self.update_state(
                state='PROGRESS',
                meta={
                    'chapter_id': chapter_id,
                    'sentence': i + 1,
                    'total_sentences': len(sentences)
                }
            )

        # 3. Combiner les phrases du chapitre avec FFmpeg
        combined_path = f'/tmp/{session_id}_chapter_{chapter_id}.mp3'
        _combine_chapter_sentences(sentence_audio_files, combined_path)

        # 4. Uploader vers stockage partagé
        storage_handler = SharedStorageHandler(
            storage_type=os.getenv('SHARED_STORAGE_TYPE', 'local'),
            storage_path=os.getenv('SHARED_STORAGE_PATH', '/tmp/shared')
        )
        shared_path = storage_handler.upload_audio(
            combined_path,
            session_id,
            f'chapter_{chapter_id}'
        )

        # 5. Mettre à jour checkpoint
        checkpoint_manager = DistributedCheckpointManager(session_id)
        checkpoint_manager.mark_chapter_complete(chapter_id)

        # 6. Calculer durée
        duration = _get_audio_duration(combined_path)

        # 7. Cleanup fichiers temporaires
        _cleanup_temp_files(sentence_audio_files + [combined_path])

        elapsed = time.time() - start_time
        logger.info(
            f"Chapter {chapter_id} completed in {elapsed:.1f}s "
            f"(duration: {duration:.1f}s)"
        )

        return {
            'chapter_id': chapter_id,
            'audio_path': shared_path,
            'duration': duration,
            'num_sentences': len(sentences),
            'processing_time': elapsed
        }

    except Exception as exc:
        logger.error(
            f"Error processing chapter {chapter_id}: {exc}",
            exc_info=True
        )

        # Marquer comme échec dans checkpoint
        try:
            checkpoint_manager = DistributedCheckpointManager(session_id)
            checkpoint_manager.mark_chapter_failed(chapter_id, str(exc))
        except Exception:
            pass

        # Retry avec backoff exponentiel
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(name='lib.distributed.tasks.health_check')
def health_check() -> Dict[str, Any]:
    """
    Vérifie la santé du worker.

    Returns:
        Dict avec status, gpu_available, etc.
    """
    import torch

    status = 'ok'
    gpu_available = torch.cuda.is_available()
    gpu_memory_free = 0
    tts_loaded = len(_TTS_ENGINE_CACHE) > 0

    if gpu_available:
        try:
            gpu_memory_free = torch.cuda.mem_get_info()[0] // (1024 ** 2)
            if gpu_memory_free < 1000:  # < 1GB libre
                status = 'degraded'
        except Exception:
            status = 'error'

    return {
        'status': status,
        'gpu_available': gpu_available,
        'gpu_memory_free': gpu_memory_free,
        'tts_model_loaded': tts_loaded
    }


def _get_or_create_tts_engine(tts_config: Dict[str, Any]):
    """Récupère le TTS engine depuis le cache ou le crée."""
    global _TTS_ENGINE_CACHE

    # Clé de cache basée sur config
    cache_key = f"{tts_config.get('model_name', 'xtts')}_{tts_config.get('voice_name', 'default')}"

    if cache_key not in _TTS_ENGINE_CACHE:
        logger.info(f"Loading TTS model: {cache_key}")

        # Import dynamique pour éviter charge au démarrage
        from lib.classes.tts_manager import TTSManager

        # Créer le TTS engine
        tts_manager = TTSManager(
            model_name=tts_config.get('model_name', 'xtts'),
            voice_name=tts_config.get('voice_name'),
            language=tts_config.get('language', 'en'),
            device=tts_config.get('device', 'cuda' if _is_gpu_available() else 'cpu'),
            custom_model_path=tts_config.get('custom_model')
        )

        _TTS_ENGINE_CACHE[cache_key] = tts_manager
        logger.info(f"TTS model loaded and cached: {cache_key}")

    return _TTS_ENGINE_CACHE[cache_key]


def _is_gpu_available() -> bool:
    """Vérifie si GPU est disponible."""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


def _combine_chapter_sentences(audio_files: List[str], output_path: str) -> str:
    """Combine les phrases d'un chapitre avec FFmpeg."""
    # Créer fichier liste pour FFmpeg
    list_file = output_path + '.txt'
    with open(list_file, 'w') as f:
        for audio_file in audio_files:
            f.write(f"file '{audio_file}'\n")

    # FFmpeg concat
    cmd = [
        'ffmpeg', '-f', 'concat', '-safe', '0',
        '-i', list_file,
        '-c', 'copy',
        output_path,
        '-y'  # Overwrite
    ]

    subprocess.run(cmd, check=True, capture_output=True)
    os.remove(list_file)

    return output_path


def _get_audio_duration(audio_path: str) -> float:
    """Récupère la durée d'un fichier audio avec ffprobe."""
    cmd = [
        'ffprobe', '-v', 'quiet',
        '-print_format', 'json',
        '-show_format',
        audio_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)
    return float(data['format']['duration'])


def _cleanup_temp_files(files: List[str]):
    """Supprime les fichiers temporaires."""
    for f in files:
        try:
            if os.path.exists(f):
                os.remove(f)
        except Exception:
            pass
