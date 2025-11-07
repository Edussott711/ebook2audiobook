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

        # 4. Calculer durée
        duration = _get_audio_duration(combined_path)

        # 5. Encoder l'audio en base64 pour transfert via Redis
        import base64
        with open(combined_path, 'rb') as f:
            audio_bytes = f.read()
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        audio_size_mb = len(audio_bytes) / (1024 * 1024)

        logger.info(f"Chapter {chapter_id} audio size: {audio_size_mb:.2f} MB")

        # 6. Mettre à jour checkpoint
        checkpoint_manager = DistributedCheckpointManager(session_id)
        checkpoint_manager.mark_chapter_complete(chapter_id)

        # 7. Cleanup fichiers temporaires
        _cleanup_temp_files(sentence_audio_files + [combined_path])

        elapsed = time.time() - start_time
        logger.info(
            f"Chapter {chapter_id} completed in {elapsed:.1f}s "
            f"(duration: {duration:.1f}s)"
        )

        return {
            'chapter_id': chapter_id,
            'audio_base64': audio_base64,
            'audio_size_mb': audio_size_mb,
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
        Dict avec status, gpu_available, device_type, etc.
    """
    import torch
    import os

    status = 'ok'
    gpu_available = torch.cuda.is_available()
    gpu_memory_free = 0
    gpu_count = 0
    device_type = 'cpu'
    tts_loaded = len(_TTS_ENGINE_CACHE) > 0

    # Déterminer le device utilisé
    cuda_visible = os.getenv('CUDA_VISIBLE_DEVICES', '')

    if gpu_available and cuda_visible != '':
        device_type = 'cuda'
        try:
            gpu_count = torch.cuda.device_count()
            gpu_memory_free = torch.cuda.mem_get_info()[0] // (1024 ** 2)  # MB
            if gpu_memory_free < 1000:  # < 1GB libre
                status = 'degraded'
        except Exception:
            status = 'error'
    elif gpu_available and cuda_visible == '':
        # GPU disponible mais CUDA_VISIBLE_DEVICES vide = mode CPU forcé
        device_type = 'cpu (GPU available but disabled)'
    else:
        device_type = 'cpu'

    return {
        'status': status,
        'device_type': device_type,
        'gpu_available': gpu_available,
        'gpu_count': gpu_count,
        'gpu_memory_free_mb': gpu_memory_free,
        'tts_model_loaded': tts_loaded,
        'cached_models': list(_TTS_ENGINE_CACHE.keys())
    }


def _get_or_create_tts_engine(tts_config: Dict[str, Any]):
    """Récupère le TTS engine depuis le cache ou le crée."""
    global _TTS_ENGINE_CACHE

    # Détecter le device à utiliser
    requested_device = tts_config.get('device')
    gpu_available = _is_gpu_available()

    # Déterminer le device final
    if requested_device:
        # Device explicitement demandé
        device = requested_device
    else:
        # Auto-détection : GPU si disponible, sinon CPU
        device = 'cuda' if gpu_available else 'cpu'

    # Validation : si GPU demandé mais pas disponible, fallback CPU
    if device == 'cuda' and not gpu_available:
        logger.warning("GPU requested but not available, falling back to CPU")
        device = 'cpu'

    # Clé de cache basée sur config + device
    cache_key = f"{tts_config.get('model_name', 'xtts')}_{tts_config.get('voice_name', 'default')}_{device}"

    if cache_key not in _TTS_ENGINE_CACHE:
        logger.info(
            f"Loading TTS model: {cache_key} "
            f"(device: {device}, GPU available: {gpu_available})"
        )

        # Import dynamique pour éviter charge au démarrage
        from lib.classes.tts_manager import TTSManager

        # Créer le TTS engine
        tts_manager = TTSManager(
            model_name=tts_config.get('model_name', 'xtts'),
            voice_name=tts_config.get('voice_name'),
            language=tts_config.get('language', 'en'),
            device=device,
            custom_model_path=tts_config.get('custom_model')
        )

        _TTS_ENGINE_CACHE[cache_key] = tts_manager
        logger.info(f"TTS model loaded and cached: {cache_key} on {device}")

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
