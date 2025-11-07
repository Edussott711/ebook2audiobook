"""
Coordinator principal pour la distribution des tâches via Celery.
"""

import logging
import time
import os
from typing import List, Dict, Any, Optional
from celery import group
from celery.result import GroupResult

from .tasks import process_chapter
from .checkpoint_manager import DistributedCheckpointManager
# Note: SharedStorageHandler n'est plus utilisé (audio transféré via Redis)

logger = logging.getLogger(__name__)


class DistributedCoordinator:
    """
    Coordonne la distribution d'un livre sur plusieurs workers via Celery.

    Responsabilités:
    - Découper le livre en unités de travail (chapitres)
    - Envoyer les tâches à Celery
    - Agréger les résultats
    - Mettre à jour les checkpoints
    - Gérer les pannes et retries
    """

    def __init__(
        self,
        session_id: str,
        num_workers: int = 1,
        redis_url: str = None
    ):
        """
        Initialise le coordinator.

        Args:
            session_id: ID unique de la session de conversion
            num_workers: Nombre de workers attendus
            redis_url: URL de connexion Redis
        """
        self.session_id = session_id
        self.num_workers = num_workers

        # Importer redis seulement si nécessaire
        try:
            import redis
            redis_url = redis_url or os.getenv('REDIS_URL', 'redis://localhost:6379/0')
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
        except ImportError:
            raise ImportError("redis-py is required for distributed mode. Install with: pip install redis")

        self.checkpoint_manager = DistributedCheckpointManager(
            session_id, self.redis_client
        )

        logger.info(
            f"Coordinator initialized for session {session_id} "
            f"with {num_workers} workers (no shared storage required)"
        )

    def distribute_chapters(
        self,
        chapters: List[List[str]],
        tts_config: Dict[str, Any],
        resume: bool = False
    ) -> GroupResult:
        """
        Distribue les chapitres aux workers.

        Args:
            chapters: Liste des chapitres (chaque chapitre = liste de phrases)
            tts_config: Configuration TTS (voice, language, etc.)
            resume: Si True, ne traite que les chapitres non terminés

        Returns:
            GroupResult: Objet Celery pour suivre la progression
        """
        # 1. Charger checkpoint existant si resume
        if resume:
            checkpoint = self.checkpoint_manager.load_checkpoint()
            completed = set(checkpoint.get('converted_chapters', []))
            pending_chapter_ids = [i for i in range(len(chapters)) if i not in completed]
            logger.info(
                f"Resume mode: {len(completed)} completed, "
                f"{len(pending_chapter_ids)} pending"
            )
        else:
            pending_chapter_ids = list(range(len(chapters)))
            # Initialiser checkpoint
            self.checkpoint_manager.save_checkpoint('audio_conversion_in_progress', {
                'total_chapters': len(chapters),
                'converted_chapters': [],
                'failed_chapters': [],
            })

        # 2. Créer groupe de tâches Celery
        tasks = []
        for chapter_id in pending_chapter_ids:
            task = process_chapter.s(
                chapter_id=chapter_id,
                sentences=chapters[chapter_id],
                session_id=self.session_id,
                tts_config=tts_config
            )
            tasks.append(task)

        # 3. Envoyer en parallèle avec group()
        job = group(tasks)
        result = job.apply_async()

        logger.info(f"Distributed {len(tasks)} chapters to workers")
        self._publish_progress(0, len(pending_chapter_ids))

        return result

    def wait_and_aggregate(
        self,
        result: GroupResult,
        timeout: Optional[int] = None
    ) -> List[str]:
        """
        Attend la fin de toutes les tâches et agrège les résultats.

        Args:
            result: GroupResult de distribute_chapters()
            timeout: Timeout en secondes (None = infini)

        Returns:
            Liste des chemins audio des chapitres (ordonnés par chapter_id)
        """
        logger.info("Waiting for all chapters to complete...")

        # Attendre avec progression
        total = len(result)
        completed_paths = {}

        while not result.ready():
            completed = result.completed_count()
            self._publish_progress(completed, total)

            # Attendre un peu
            try:
                result.join(timeout=5, propagate=False)
            except Exception:
                pass
            time.sleep(1)

        # Récupérer tous les résultats
        try:
            results = result.get(timeout=timeout, propagate=True)
        except Exception as e:
            logger.error(f"Error getting results: {e}")
            # Identifier les tâches échouées
            failed = self._identify_failed_tasks(result)
            raise Exception(f"Failed chapters: {failed}") from e

        # Décoder les audios base64 et sauvegarder localement
        import base64
        import os

        os.makedirs('/tmp/distributed_audio', exist_ok=True)

        for res in results:
            chapter_id = res['chapter_id']

            # Décoder audio base64
            audio_bytes = base64.b64decode(res['audio_base64'])

            # Sauvegarder localement
            audio_path = f'/tmp/distributed_audio/{self.session_id}_chapter_{chapter_id}.mp3'
            with open(audio_path, 'wb') as f:
                f.write(audio_bytes)

            completed_paths[chapter_id] = audio_path

            logger.info(
                f"Chapter {chapter_id} received ({res.get('audio_size_mb', 0):.2f} MB, "
                f"{res.get('duration', 0):.1f}s)"
            )

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
            audio_paths: Chemins des audios de chapitres (ordonnés, déjà en local)
            output_path: Chemin du fichier de sortie

        Returns:
            Chemin du fichier combiné
        """
        logger.info(f"Combining {len(audio_paths)} audio files...")

        import subprocess

        # Créer fichier liste pour FFmpeg
        list_file = f'/tmp/{self.session_id}_chapters.txt'
        with open(list_file, 'w') as f:
            for path in audio_paths:
                f.write(f"file '{path}'\n")

        # FFmpeg concat
        cmd = [
            'ffmpeg', '-f', 'concat', '-safe', '0',
            '-i', list_file,
            '-c', 'copy',
            output_path,
            '-y'
        ]

        subprocess.run(cmd, check=True, capture_output=True)

        # Cleanup
        os.remove(list_file)
        for path in audio_paths:
            try:
                os.remove(path)
            except Exception:
                pass

        logger.info(f"Final audiobook created at {output_path}")
        return output_path

    def get_overall_progress(self) -> Dict[str, Any]:
        """
        Récupère la progression globale depuis Redis.

        Returns:
            Dict avec progress info
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
        import json
        progress = (completed / total * 100) if total > 0 else 0
        try:
            self.redis_client.publish(
                f'progress:{self.session_id}',
                json.dumps({
                    'completed': completed,
                    'total': total,
                    'progress': progress
                })
            )
        except Exception:
            pass  # Pub/sub est optionnel

    def _identify_failed_tasks(self, result: GroupResult) -> List[int]:
        """Identifie les chapter_ids des tâches échouées."""
        failed = []
        for i, task in enumerate(result.results):
            if task.failed():
                # Extraire chapter_id depuis task args
                try:
                    chapter_id = task.args[0] if task.args else i
                    failed.append(chapter_id)
                except Exception:
                    failed.append(i)
        return failed
