# Spécifications techniques détaillées - Mode Distribué

## 📋 Table des matières

1. [Composants Python](#composants-python)
2. [Configuration Celery](#configuration-celery)
3. [Schéma de données Redis](#schéma-de-données-redis)
4. [API des composants](#api-des-composants)
5. [Gestion des erreurs](#gestion-des-erreurs)
6. [Performance et optimisations](#performance-et-optimisations)
7. [Sécurité](#sécurité)

---

## 1. Composants Python

### 1.1 `lib/distributed/__init__.py`

```python
"""
Module de parallélisme distribué pour ebook2audiobook.

Fournit les composants pour distribuer le traitement TTS sur plusieurs machines:
- Coordinator: Orchestre la distribution des tâches
- Worker: Exécute les conversions TTS
- Celery tasks: Définit les tâches distribuables
- Checkpoint manager: Synchronise l'état distribué
- Storage handler: Gère le stockage partagé
"""

__version__ = '1.0.0'

from .coordinator import DistributedCoordinator
from .worker import DistributedWorker
from .checkpoint_manager import DistributedCheckpointManager
from .storage import SharedStorageHandler
from .celery_app import celery_app

__all__ = [
    'DistributedCoordinator',
    'DistributedWorker',
    'DistributedCheckpointManager',
    'SharedStorageHandler',
    'celery_app'
]
```

---

### 1.2 `lib/distributed/celery_app.py`

```python
"""Configuration de l'application Celery."""

import os
from celery import Celery
from kombu import Queue, Exchange

# URL Redis depuis environnement ou défaut
REDIS_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')

# Instance Celery
celery_app = Celery(
    'ebook2audiobook_distributed',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['lib.distributed.tasks']
)

# Configuration
celery_app.conf.update(
    # Sérialisation
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='UTC',
    enable_utc=True,

    # Résultats
    result_expires=3600 * 24,  # 24h
    result_backend_transport_options={
        'master_name': 'mymaster',
        'visibility_timeout': 3600,
    },

    # Retry et timeout
    task_acks_late=True,  # ACK après succès seulement
    task_reject_on_worker_lost=True,
    task_time_limit=3600,  # 1h max par tâche
    task_soft_time_limit=3300,  # Warning à 55min
    task_track_started=True,

    # Workers
    worker_prefetch_multiplier=1,  # 1 tâche à la fois (GPU isolation)
    worker_max_tasks_per_child=50,  # Restart après 50 tâches (libère mémoire)
    worker_disable_rate_limits=True,

    # Queues
    task_default_queue='tts_queue',
    task_queues=(
        Queue('tts_queue', Exchange('tts_queue'), routing_key='tts'),
        Queue('priority_queue', Exchange('priority_queue'), routing_key='priority'),
    ),

    # Monitoring
    task_send_sent_event=True,
    worker_send_task_events=True,

    # Retry
    task_autoretry_for=(Exception,),
    task_max_retries=3,
    task_default_retry_delay=60,  # 1min entre retries
    retry_backoff=True,
    retry_backoff_max=600,  # Max 10min
    retry_jitter=True,
)

# Route des tâches
celery_app.conf.task_routes = {
    'lib.distributed.tasks.process_chapter': {'queue': 'tts_queue'},
    'lib.distributed.tasks.process_sentence': {'queue': 'tts_queue'},
    'lib.distributed.tasks.health_check': {'queue': 'priority_queue'},
}

# Beat schedule (optionnel - tâches périodiques)
celery_app.conf.beat_schedule = {
    'cleanup-old-sessions': {
        'task': 'lib.distributed.tasks.cleanup_old_sessions',
        'schedule': 3600 * 6,  # Tous les 6h
    },
}
```

**Explication des paramètres critiques** :

| Paramètre | Valeur | Raison |
|-----------|--------|--------|
| `worker_prefetch_multiplier` | 1 | Évite que worker prenne plusieurs tâches GPU |
| `task_acks_late` | True | Retry si worker crash avant fin |
| `task_time_limit` | 3600 | Protection contre tâches infinies |
| `worker_max_tasks_per_child` | 50 | Évite fuites mémoire GPU |

---

### 1.3 `lib/distributed/coordinator.py`

```python
"""
Coordinator principal pour la distribution des tâches.
"""

import logging
import redis
from typing import List, Dict, Any, Optional
from celery import group
from celery.result import GroupResult

from .tasks import process_chapter
from .checkpoint_manager import DistributedCheckpointManager
from .storage import SharedStorageHandler

logger = logging.getLogger(__name__)


class DistributedCoordinator:
    """
    Coordonne la distribution d'un livre sur plusieurs workers.

    Responsabilités:
    - Découper le livre en unités de travail
    - Envoyer les tâches à Celery
    - Agréger les résultats
    - Mettre à jour les checkpoints
    - Gérer les pannes et retries
    """

    def __init__(
        self,
        session_id: str,
        num_workers: int = 1,
        redis_url: str = 'redis://localhost:6379/0',
        storage_type: str = 'nfs',
        storage_path: str = '/mnt/shared'
    ):
        """
        Initialise le coordinator.

        Args:
            session_id: ID unique de la session de conversion
            num_workers: Nombre de workers attendus
            redis_url: URL de connexion Redis
            storage_type: Type de stockage ('nfs', 's3', 'local')
            storage_path: Chemin du stockage partagé
        """
        self.session_id = session_id
        self.num_workers = num_workers
        self.redis_client = redis.from_url(redis_url)
        self.checkpoint_manager = DistributedCheckpointManager(
            session_id, self.redis_client
        )
        self.storage_handler = SharedStorageHandler(storage_type, storage_path)

        logger.info(
            f"Coordinator initialized for session {session_id} "
            f"with {num_workers} workers"
        )

    def distribute_book(
        self,
        chapters: List[Dict[str, Any]],
        tts_config: Dict[str, Any],
        resume: bool = False
    ) -> GroupResult:
        """
        Distribue les chapitres aux workers.

        Args:
            chapters: Liste des chapitres avec leurs phrases
            tts_config: Configuration TTS (voice, language, etc.)
            resume: Si True, ne traite que les chapitres non terminés

        Returns:
            GroupResult: Objet Celery pour suivre la progression

        Example:
            chapters = [
                {'id': 1, 'sentences': ['Hello.', 'World.']},
                {'id': 2, 'sentences': ['Chapter', 'two.']},
            ]
            result = coordinator.distribute_book(chapters, tts_config)
        """
        # 1. Charger checkpoint existant si resume
        if resume:
            checkpoint = self.checkpoint_manager.load_checkpoint()
            completed = set(checkpoint.get('converted_chapters', []))
            pending_chapters = [ch for ch in chapters if ch['id'] not in completed]
            logger.info(
                f"Resume mode: {len(completed)} completed, "
                f"{len(pending_chapters)} pending"
            )
        else:
            pending_chapters = chapters
            # Initialiser checkpoint
            self.checkpoint_manager.save_checkpoint('audio_conversion_in_progress', {
                'total_chapters': len(chapters),
                'converted_chapters': [],
                'failed_chapters': [],
            })

        # 2. Créer groupe de tâches Celery
        tasks = []
        for chapter in pending_chapters:
            task = process_chapter.s(
                chapter_id=chapter['id'],
                sentences=chapter['sentences'],
                session_id=self.session_id,
                tts_config=tts_config
            )
            tasks.append(task)

        # 3. Envoyer en parallèle avec group()
        job = group(tasks)
        result = job.apply_async()

        logger.info(f"Distributed {len(tasks)} chapters to workers")
        self._publish_progress(0, len(pending_chapters))

        return result

    def wait_and_aggregate(
        self,
        result: GroupResult,
        timeout: Optional[int] = None
    ) -> List[str]:
        """
        Attend la fin de toutes les tâches et agrège les résultats.

        Args:
            result: GroupResult de distribute_book()
            timeout: Timeout en secondes (None = infini)

        Returns:
            Liste des chemins audio des chapitres (ordonnés par chapter_id)

        Raises:
            TimeoutError: Si timeout dépassé
            Exception: Si une tâche échoue après tous les retries
        """
        logger.info("Waiting for all chapters to complete...")

        # Attendre avec progression
        total = len(result)
        completed_paths = {}

        while not result.ready():
            completed = result.completed_count()
            self._publish_progress(completed, total)

            # Attendre un peu
            result.join(timeout=5, propagate=False)

        # Récupérer tous les résultats
        try:
            results = result.get(timeout=timeout, propagate=True)
        except Exception as e:
            logger.error(f"Error getting results: {e}")
            # Identifier les tâches échouées
            failed = self._identify_failed_tasks(result)
            raise Exception(f"Failed chapters: {failed}") from e

        # Trier par chapter_id
        for res in results:
            completed_paths[res['chapter_id']] = res['audio_path']

        sorted_paths = [
            completed_paths[i] for i in sorted(completed_paths.keys())
        ]

        logger.info(f"All {total} chapters completed successfully")
        return sorted_paths

    def combine_audio_files(
        self,
        audio_paths: List[str],
        output_path: str
    ) -> str:
        """
        Combine les chapitres audio en un fichier final.

        Args:
            audio_paths: Chemins des audios de chapitres (ordonnés)
            output_path: Chemin du fichier de sortie

        Returns:
            Chemin du fichier combiné
        """
        logger.info(f"Combining {len(audio_paths)} audio files...")

        # 1. Télécharger depuis stockage partagé
        local_paths = []
        for i, shared_path in enumerate(audio_paths):
            local_path = f'/tmp/{self.session_id}_chapter_{i}.mp3'
            self.storage_handler.download_audio(shared_path, local_path)
            local_paths.append(local_path)

        # 2. Utiliser la fonction existante combine_audio_files
        # (import depuis lib.functions)
        from lib.functions import combine_audio_files as combine_ffmpeg

        final_path = combine_ffmpeg(local_paths, output_path)

        logger.info(f"Final audiobook created at {final_path}")
        return final_path

    def get_overall_progress(self) -> Dict[str, Any]:
        """
        Récupère la progression globale depuis Redis.

        Returns:
            Dict avec:
            - total_chapters: int
            - converted_chapters: int
            - failed_chapters: int
            - progress_percent: float
            - estimated_time_remaining: int (seconds)
        """
        checkpoint = self.checkpoint_manager.load_checkpoint()

        total = checkpoint.get('total_chapters', 0)
        converted = len(checkpoint.get('converted_chapters', []))
        failed = len(checkpoint.get('failed_chapters', []))

        progress_percent = (converted / total * 100) if total > 0 else 0

        # Estimation temps restant (basée sur temps moyen par chapitre)
        start_time = checkpoint.get('start_time', 0)
        if start_time and converted > 0:
            elapsed = time.time() - start_time
            avg_time_per_chapter = elapsed / converted
            remaining_chapters = total - converted
            estimated_time = avg_time_per_chapter * remaining_chapters
        else:
            estimated_time = None

        return {
            'total_chapters': total,
            'converted_chapters': converted,
            'failed_chapters': failed,
            'progress_percent': progress_percent,
            'estimated_time_remaining': estimated_time
        }

    def _publish_progress(self, completed: int, total: int):
        """Publie la progression sur Redis pub/sub."""
        progress = (completed / total * 100) if total > 0 else 0
        self.redis_client.publish(
            f'progress:{self.session_id}',
            json.dumps({
                'completed': completed,
                'total': total,
                'progress': progress
            })
        )

    def _identify_failed_tasks(self, result: GroupResult) -> List[int]:
        """Identifie les chapter_ids des tâches échouées."""
        failed = []
        for i, task in enumerate(result.results):
            if task.failed():
                # Extraire chapter_id depuis task args
                chapter_id = task.args[0] if task.args else i
                failed.append(chapter_id)
        return failed
```

**Points clés** :
- Utilise `celery.group()` pour parallélisme
- Gère le resume via checkpoints
- Publie la progression en temps réel
- Télécharge et combine les audios à la fin

---

### 1.4 `lib/distributed/tasks.py`

```python
"""
Tâches Celery pour le traitement distribué.
"""

import logging
import time
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
            - voice_name: str
            - language: str
            - model_name: str
            - custom_model: Optional[str]
            - ...

    Returns:
        Dict avec:
        - chapter_id: int
        - audio_path: str (chemin dans stockage partagé)
        - duration: float (secondes)
        - num_sentences: int

    Raises:
        Exception: Si erreur après tous les retries
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
            audio_file = tts_engine.convert_sentence2audio(
                sentence=sentence,
                output_file=f'/tmp/{session_id}_ch{chapter_id}_s{i}.mp3'
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
        combined_path = _combine_chapter_sentences(
            sentence_audio_files,
            f'/tmp/{session_id}_chapter_{chapter_id}.mp3'
        )

        # 4. Uploader vers stockage partagé
        storage_handler = SharedStorageHandler(
            storage_type=os.getenv('SHARED_STORAGE_TYPE', 'nfs'),
            storage_path=os.getenv('SHARED_STORAGE_PATH', '/mnt/shared')
        )
        shared_path = storage_handler.upload_audio(
            combined_path,
            session_id,
            f'chapter_{chapter_id}'
        )

        # 5. Mettre à jour checkpoint
        checkpoint_manager = DistributedCheckpointManager(
            session_id,
            redis_client=None  # Will create internally
        )
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
        checkpoint_manager = DistributedCheckpointManager(session_id, None)
        checkpoint_manager.mark_chapter_failed(chapter_id, str(exc))

        # Retry avec backoff exponentiel
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(name='lib.distributed.tasks.health_check')
def health_check() -> Dict[str, Any]:
    """
    Vérifie la santé du worker.

    Returns:
        Dict avec:
        - status: 'ok' | 'degraded' | 'error'
        - gpu_available: bool
        - gpu_memory_free: int (MB)
        - tts_model_loaded: bool
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
    cache_key = f"{tts_config['model_name']}_{tts_config.get('voice_name', 'default')}"

    if cache_key not in _TTS_ENGINE_CACHE:
        logger.info(f"Loading TTS model: {cache_key}")

        # Import dynamique pour éviter charge au démarrage
        from lib.classes.tts_manager import TTSManager

        # Créer le TTS engine
        tts_manager = TTSManager(
            model_name=tts_config['model_name'],
            voice_name=tts_config['voice_name'],
            language=tts_config['language'],
            device=tts_config.get('device', 'cuda'),
            custom_model_path=tts_config.get('custom_model')
        )

        _TTS_ENGINE_CACHE[cache_key] = tts_manager
        logger.info(f"TTS model loaded and cached: {cache_key}")

    return _TTS_ENGINE_CACHE[cache_key]


def _combine_chapter_sentences(audio_files: List[str], output_path: str) -> str:
    """Combine les phrases d'un chapitre avec FFmpeg."""
    import subprocess

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
        output_path
    ]

    subprocess.run(cmd, check=True, capture_output=True)
    os.remove(list_file)

    return output_path


def _get_audio_duration(audio_path: str) -> float:
    """Récupère la durée d'un fichier audio avec ffprobe."""
    import subprocess
    import json

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
    import os
    for f in files:
        try:
            os.remove(f)
        except Exception:
            pass
```

**Points clés** :
- Cache global du modèle TTS par worker
- Retry automatique avec backoff exponentiel
- Mise à jour checkpoint après chaque chapitre
- Health check pour monitoring

---

### 1.5 `lib/distributed/checkpoint_manager.py`

```python
"""
Gestionnaire de checkpoints distribués.
"""

import json
import time
import logging
from typing import Dict, Any, List, Optional
import redis
from contextlib import contextmanager

from lib.checkpoint_manager import CheckpointManager

logger = logging.getLogger(__name__)


class DistributedCheckpointManager(CheckpointManager):
    """
    Extension du CheckpointManager pour le mode distribué.

    Utilise Redis pour synchroniser l'état entre les workers.
    Garantit la cohérence avec des locks Redis.
    """

    def __init__(
        self,
        session_id: str,
        redis_client: Optional[redis.Redis] = None,
        redis_url: str = 'redis://localhost:6379/0'
    ):
        """
        Args:
            session_id: ID de la session
            redis_client: Client Redis (ou None pour créer)
            redis_url: URL Redis si redis_client non fourni
        """
        super().__init__(session_id)

        if redis_client is None:
            self.redis = redis.from_url(redis_url)
        else:
            self.redis = redis_client

        self.lock_key = f'checkpoint_lock:{session_id}'
        self.checkpoint_key = f'checkpoint:{session_id}'
        self.lock_timeout = 10  # secondes

    def save_checkpoint(self, stage: str, data: Dict[str, Any]):
        """
        Sauvegarde atomique du checkpoint avec lock Redis.

        Args:
            stage: Stage actuel (epub_converted, audio_conversion_in_progress, etc.)
            data: Données à sauvegarder
        """
        with self._acquire_lock():
            # 1. Lire checkpoint existant depuis Redis
            existing = self._load_from_redis()

            # 2. Merger avec nouvelles données
            merged = {**existing, **data, 'stage': stage, 'last_update': time.time()}

            # 3. Sauvegarder dans Redis
            self.redis.set(
                self.checkpoint_key,
                json.dumps(merged),
                ex=3600 * 24 * 7  # Expire après 7 jours
            )

            # 4. Sauvegarder aussi localement (backup)
            super().save_checkpoint(stage, merged)

            logger.debug(f"Checkpoint saved for session {self.session_id}: {stage}")

    def load_checkpoint(self) -> Dict[str, Any]:
        """
        Charge le checkpoint depuis Redis (ou local en fallback).

        Returns:
            Dict avec les données du checkpoint
        """
        # Essayer Redis d'abord
        checkpoint = self._load_from_redis()

        # Fallback sur local si Redis vide
        if not checkpoint:
            logger.warning("Redis checkpoint empty, loading from local file")
            checkpoint = super().load_checkpoint()

            # Re-sync vers Redis
            if checkpoint:
                self.redis.set(
                    self.checkpoint_key,
                    json.dumps(checkpoint),
                    ex=3600 * 24 * 7
                )

        return checkpoint

    def mark_chapter_complete(self, chapter_id: int):
        """
        Marque un chapitre comme terminé (thread-safe).

        Args:
            chapter_id: ID du chapitre
        """
        with self._acquire_lock():
            checkpoint = self._load_from_redis()

            # Ajouter à la liste des chapitres convertis
            converted = checkpoint.get('converted_chapters', [])
            if chapter_id not in converted:
                converted.append(chapter_id)
                converted.sort()  # Garder trié

            # Retirer des failed si présent
            failed = checkpoint.get('failed_chapters', [])
            if chapter_id in failed:
                failed.remove(chapter_id)

            # Mettre à jour
            checkpoint['converted_chapters'] = converted
            checkpoint['failed_chapters'] = failed
            checkpoint['last_update'] = time.time()

            self.redis.set(self.checkpoint_key, json.dumps(checkpoint))

            logger.info(
                f"Chapter {chapter_id} marked complete "
                f"({len(converted)}/{checkpoint.get('total_chapters', 0)})"
            )

    def mark_chapter_failed(self, chapter_id: int, error: str):
        """
        Marque un chapitre comme échoué.

        Args:
            chapter_id: ID du chapitre
            error: Message d'erreur
        """
        with self._acquire_lock():
            checkpoint = self._load_from_redis()

            failed = checkpoint.get('failed_chapters', [])
            if chapter_id not in failed:
                failed.append(chapter_id)

            errors = checkpoint.get('chapter_errors', {})
            errors[str(chapter_id)] = error

            checkpoint['failed_chapters'] = failed
            checkpoint['chapter_errors'] = errors

            self.redis.set(self.checkpoint_key, json.dumps(checkpoint))

            logger.error(f"Chapter {chapter_id} marked failed: {error}")

    def get_pending_chapters(self) -> List[int]:
        """
        Retourne la liste des chapitres non traités.

        Returns:
            Liste des chapter_ids à traiter
        """
        checkpoint = self.load_checkpoint()

        total = checkpoint.get('total_chapters', 0)
        converted = set(checkpoint.get('converted_chapters', []))

        # Tous les chapitres - convertis
        pending = [i for i in range(1, total + 1) if i not in converted]

        return pending

    @contextmanager
    def _acquire_lock(self):
        """
        Context manager pour acquérir un lock Redis.

        Utilise SETNX avec timeout pour éviter deadlocks.
        """
        lock_acquired = False
        lock_value = f'{time.time()}_{os.getpid()}'

        try:
            # Tentative d'acquisition (avec retry)
            for attempt in range(30):  # Max 30 secondes
                lock_acquired = self.redis.set(
                    self.lock_key,
                    lock_value,
                    nx=True,  # Only if not exists
                    ex=self.lock_timeout
                )

                if lock_acquired:
                    break

                # Attendre un peu avant retry
                time.sleep(1)

            if not lock_acquired:
                raise TimeoutError(
                    f"Could not acquire lock for {self.session_id} "
                    f"after 30 seconds"
                )

            yield

        finally:
            # Libérer le lock seulement si on l'a acquis
            if lock_acquired:
                # Vérifier que c'est bien notre lock avant de supprimer
                current_value = self.redis.get(self.lock_key)
                if current_value and current_value.decode() == lock_value:
                    self.redis.delete(self.lock_key)

    def _load_from_redis(self) -> Dict[str, Any]:
        """Charge le checkpoint depuis Redis."""
        data = self.redis.get(self.checkpoint_key)
        if data:
            return json.loads(data)
        return {}
```

**Points clés** :
- Locks Redis pour updates atomiques
- Fallback sur fichier local si Redis down
- Méthodes thread-safe pour multi-workers
- TTL de 7 jours sur les checkpoints

---

### 1.6 `lib/distributed/storage.py`

```python
"""
Gestionnaire de stockage partagé pour les fichiers audio.
"""

import os
import shutil
import logging
from typing import List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class SharedStorageHandler:
    """
    Gère le stockage partagé des fichiers audio entre workers.

    Supporte:
    - NFS: Montage réseau partagé
    - S3: Amazon S3 ou compatible (MinIO)
    - Local: Système de fichiers local (dev/test uniquement)
    """

    def __init__(
        self,
        storage_type: str = 'nfs',
        storage_path: str = '/mnt/shared'
    ):
        """
        Args:
            storage_type: 'nfs', 's3', ou 'local'
            storage_path: Chemin de base du stockage
        """
        self.storage_type = storage_type
        self.base_path = storage_path

        if storage_type == 's3':
            self._init_s3()
        elif storage_type in ['nfs', 'local']:
            self._init_filesystem()
        else:
            raise ValueError(f"Unknown storage type: {storage_type}")

        logger.info(f"Storage handler initialized: {storage_type} @ {storage_path}")

    def _init_s3(self):
        """Initialise le client S3."""
        import boto3

        self.s3_client = boto3.client(
            's3',
            endpoint_url=os.getenv('S3_ENDPOINT_URL'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        self.bucket_name = os.getenv('S3_BUCKET_NAME', 'ebook2audiobook')

    def _init_filesystem(self):
        """Initialise le système de fichiers."""
        Path(self.base_path).mkdir(parents=True, exist_ok=True)

    def upload_audio(
        self,
        local_path: str,
        session_id: str,
        filename: str
    ) -> str:
        """
        Upload un fichier audio vers le stockage partagé.

        Args:
            local_path: Chemin local du fichier
            session_id: ID de session
            filename: Nom du fichier (sans extension)

        Returns:
            Chemin dans le stockage partagé

        Example:
            shared_path = handler.upload_audio(
                '/tmp/ch1.mp3',
                'session_abc',
                'chapter_1'
            )
            # Returns: '/mnt/shared/session_abc/chapter_1.mp3'
        """
        if self.storage_type == 's3':
            return self._upload_to_s3(local_path, session_id, filename)
        else:
            return self._upload_to_filesystem(local_path, session_id, filename)

    def _upload_to_filesystem(
        self,
        local_path: str,
        session_id: str,
        filename: str
    ) -> str:
        """Upload vers NFS ou local filesystem."""
        # Créer répertoire session
        session_dir = Path(self.base_path) / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        # Chemin de destination
        ext = Path(local_path).suffix
        dest_path = session_dir / f"{filename}{ext}"

        # Copier le fichier
        shutil.copy2(local_path, dest_path)

        logger.debug(f"Uploaded {local_path} -> {dest_path}")
        return str(dest_path)

    def _upload_to_s3(
        self,
        local_path: str,
        session_id: str,
        filename: str
    ) -> str:
        """Upload vers S3."""
        ext = Path(local_path).suffix
        s3_key = f"{session_id}/{filename}{ext}"

        self.s3_client.upload_file(
            local_path,
            self.bucket_name,
            s3_key
        )

        logger.debug(f"Uploaded {local_path} -> s3://{self.bucket_name}/{s3_key}")
        return f"s3://{self.bucket_name}/{s3_key}"

    def download_audio(self, shared_path: str, local_path: str):
        """
        Télécharge un fichier depuis le stockage partagé.

        Args:
            shared_path: Chemin dans le stockage partagé
            local_path: Chemin local de destination
        """
        if shared_path.startswith('s3://'):
            self._download_from_s3(shared_path, local_path)
        else:
            self._download_from_filesystem(shared_path, local_path)

    def _download_from_filesystem(self, shared_path: str, local_path: str):
        """Download depuis filesystem."""
        shutil.copy2(shared_path, local_path)

    def _download_from_s3(self, s3_path: str, local_path: str):
        """Download depuis S3."""
        # Parse s3://bucket/key
        s3_path = s3_path.replace('s3://', '')
        bucket, key = s3_path.split('/', 1)

        self.s3_client.download_file(bucket, key, local_path)

    def list_session_files(self, session_id: str) -> List[str]:
        """
        Liste tous les fichiers d'une session.

        Args:
            session_id: ID de session

        Returns:
            Liste des chemins des fichiers
        """
        if self.storage_type == 's3':
            return self._list_s3_files(session_id)
        else:
            return self._list_filesystem_files(session_id)

    def _list_filesystem_files(self, session_id: str) -> List[str]:
        """Liste les fichiers filesystem."""
        session_dir = Path(self.base_path) / session_id
        if not session_dir.exists():
            return []

        return [str(f) for f in session_dir.glob('*') if f.is_file()]

    def _list_s3_files(self, session_id: str) -> List[str]:
        """Liste les fichiers S3."""
        response = self.s3_client.list_objects_v2(
            Bucket=self.bucket_name,
            Prefix=f"{session_id}/"
        )

        files = []
        for obj in response.get('Contents', []):
            files.append(f"s3://{self.bucket_name}/{obj['Key']}")

        return files

    def cleanup_session(self, session_id: str):
        """
        Supprime tous les fichiers d'une session.

        Args:
            session_id: ID de session à nettoyer
        """
        if self.storage_type == 's3':
            self._cleanup_s3_session(session_id)
        else:
            self._cleanup_filesystem_session(session_id)

        logger.info(f"Cleaned up session {session_id}")

    def _cleanup_filesystem_session(self, session_id: str):
        """Cleanup filesystem."""
        session_dir = Path(self.base_path) / session_id
        if session_dir.exists():
            shutil.rmtree(session_dir)

    def _cleanup_s3_session(self, session_id: str):
        """Cleanup S3."""
        # Lister et supprimer tous les objets
        objects = self._list_s3_files(session_id)
        for obj_path in objects:
            key = obj_path.replace(f's3://{self.bucket_name}/', '')
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
```

**Points clés** :
- Support NFS, S3, et local
- API unifiée quel que soit le backend
- Méthodes de cleanup pour libérer espace

---

## 2. Configuration Celery

Voir section 1.2 pour la configuration complète.

---

## 3. Schéma de données Redis

### 3.1 Clés utilisées

| Clé | Type | Description | TTL |
|-----|------|-------------|-----|
| `checkpoint:{session_id}` | String (JSON) | État du checkpoint | 7 jours |
| `checkpoint_lock:{session_id}` | String | Lock pour updates atomiques | 10s |
| `progress:{session_id}` | PubSub | Canal pour progression temps réel | N/A |
| `celery-task-meta-{task_id}` | String (JSON) | Métadonnées des tâches | 24h |

### 3.2 Structure checkpoint

```json
{
  "stage": "audio_conversion_in_progress",
  "total_chapters": 25,
  "converted_chapters": [1, 2, 5, 7, 10, 12],
  "failed_chapters": [3],
  "in_progress_chapters": {
    "4": "worker_2@host1",
    "6": "worker_1@host2"
  },
  "chapter_metadata": {
    "1": {
      "duration": 1200.5,
      "size_mb": 15.3,
      "num_sentences": 145
    }
  },
  "start_time": 1699287600,
  "last_update": 1699289400,
  "tts_config": {
    "voice_name": "en_US/female/jenny",
    "language": "en",
    "model_name": "xtts"
  }
}
```

---

## 4. API des composants

Voir sections précédentes pour les signatures complètes.

---

## 5. Gestion des erreurs

### 5.1 Retry strategy

```python
# Tâche avec retry exponentiel
@celery_app.task(
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=3
)
```

**Comportement** :
- Tentative 1: Immédiate
- Tentative 2: 2^1 = 2s (+ jitter aléatoire)
- Tentative 3: 2^2 = 4s (+ jitter)
- Tentative 4: 2^3 = 8s (+ jitter)
- Échec final: Exception propagée

### 5.2 Dead Letter Queue

```python
# Configuration Celery
celery_app.conf.task_reject_on_worker_lost = True
celery_app.conf.task_acks_late = True
```

Si un worker crash, la tâche retourne dans la queue.

### 5.3 Circuit breaker (optionnel)

```python
# Pour éviter de retry indéfiniment un service HS
from celery.exceptions import Reject

@celery_app.task
def process_chapter(...):
    if is_service_down():
        raise Reject('Service unavailable', requeue=False)
```

---

## 6. Performance et optimisations

### 6.1 Métriques cibles

| Métrique | Valeur actuelle | Cible |
|----------|-----------------|-------|
| Throughput GPU | ~30% | >80% |
| Temps/chapitre | 120s | 120s (pas de régression) |
| Temps total (5 workers) | 1x | 0.2x (5x plus rapide) |
| Overhead coordination | N/A | <10% |

### 6.2 Optimisations implémentées

1. **Cache TTS model** : Chargé 1 fois par worker
2. **Prefetch = 1** : Évite contention GPU
3. **FFmpeg batch** : Combine par lots de 1024 fichiers
4. **Compression audio** : MP3 128kbps au lieu de WAV
5. **Cleanup proactif** : Supprime temp files immédiatement

---

## 7. Sécurité

### 7.1 Redis

- **Password** : Utiliser `REDIS_URL=redis://:password@host:6379/0`
- **Network** : Limiter accès avec firewall
- **TLS** : Pour production, utiliser `rediss://` (Redis over TLS)

### 7.2 Stockage S3

- **IAM** : Utiliser rôles IAM au lieu de credentials
- **Encryption** : Activer server-side encryption (SSE-S3)
- **Bucket policy** : Restreindre accès par IP/VPC

### 7.3 Celery

- **Signature** : Utiliser `task_serializer='json'` (évite pickle = RCE)
- **Rate limiting** : Limiter taux de tâches par worker
- **Authentication** : Utiliser Redis AUTH

---

**Date**: 2025-11-06
**Version**: 1.0
