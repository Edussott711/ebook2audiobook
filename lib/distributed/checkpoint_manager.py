"""
Gestionnaire de checkpoints distribués avec synchronisation Redis.
"""

import json
import time
import logging
import os
from typing import Dict, Any, List, Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DistributedCheckpointManager:
    """
    Gestionnaire de checkpoints pour le mode distribué.

    Utilise Redis pour synchroniser l'état entre les workers.
    Garantit la cohérence avec des locks Redis.
    """

    def __init__(
        self,
        session_id: str,
        redis_client=None,
        redis_url: str = None
    ):
        """
        Args:
            session_id: ID de la session
            redis_client: Client Redis (ou None pour créer)
            redis_url: URL Redis si redis_client non fourni
        """
        self.session_id = session_id

        if redis_client is None:
            try:
                import redis
                redis_url = redis_url or os.getenv('REDIS_URL', 'redis://localhost:6379/0')
                self.redis = redis.from_url(redis_url, decode_responses=True)
            except ImportError:
                raise ImportError("redis-py is required for distributed mode. Install with: pip install redis")
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

            logger.debug(f"Checkpoint saved for session {self.session_id}: {stage}")

    def load_checkpoint(self) -> Dict[str, Any]:
        """
        Charge le checkpoint depuis Redis.

        Returns:
            Dict avec les données du checkpoint
        """
        checkpoint = self._load_from_redis()
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

            self.redis.set(self.checkpoint_key, json.dumps(checkpoint), ex=3600 * 24 * 7)

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

            self.redis.set(self.checkpoint_key, json.dumps(checkpoint), ex=3600 * 24 * 7)

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
        pending = [i for i in range(total) if i not in converted]

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
                if current_value and current_value == lock_value:
                    self.redis.delete(self.lock_key)

    def _load_from_redis(self) -> Dict[str, Any]:
        """Charge le checkpoint depuis Redis."""
        data = self.redis.get(self.checkpoint_key)
        if data:
            return json.loads(data)
        return {}
