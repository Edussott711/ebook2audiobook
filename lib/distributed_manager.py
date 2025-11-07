"""
Module de gestion du mode distribué - Interface unifiée.

Ce module sert de point d'entrée unique pour le mode distribué,
découplé du reste du code. Il gère:
- Détection des dépendances (redis, celery)
- Initialisation du mode distribué
- Coordination vs Worker mode
- Gestion gracieuse des erreurs
"""

import logging
import os
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class DistributedModeError(Exception):
    """Exception levée quand le mode distribué ne peut pas être activé."""
    pass


class DistributedManager:
    """
    Gestionnaire principal du mode distribué.

    Responsabilités:
    - Vérifier disponibilité des dépendances
    - Initialiser coordinator ou worker selon le mode
    - Fournir une API simple au code principal
    """

    def __init__(self):
        self._coordinator = None
        self._worker = None
        self._redis_client = None
        self._dependencies_checked = False
        self._dependencies_available = False

    def check_dependencies(self) -> bool:
        """
        Vérifie si les dépendances du mode distribué sont installées.

        Returns:
            bool: True si redis et celery sont disponibles
        """
        if self._dependencies_checked:
            return self._dependencies_available

        try:
            import redis
            import celery
            self._dependencies_available = True
            logger.info("Distributed mode dependencies available (redis, celery)")
        except ImportError as e:
            self._dependencies_available = False
            logger.warning(
                f"Distributed mode dependencies not available: {e}. "
                "Install with: pip install -r requirements-distributed.txt"
            )

        self._dependencies_checked = True
        return self._dependencies_available

    def initialize_coordinator(
        self,
        session_id: str,
        num_workers: int = 1,
        redis_url: str = None
    ):
        """
        Initialise le mode coordinator (master).

        Args:
            session_id: ID unique de la session
            num_workers: Nombre de workers attendus
            redis_url: URL de connexion Redis

        Raises:
            DistributedModeError: Si les dépendances manquent ou si Redis est inaccessible
        """
        if not self.check_dependencies():
            raise DistributedModeError(
                "Cannot initialize distributed mode: missing dependencies. "
                "Install with: pip install -r requirements-distributed.txt"
            )

        try:
            import redis
            from lib.distributed.coordinator import DistributedCoordinator

            # Tester connexion Redis
            redis_url = redis_url or os.getenv('REDIS_URL', 'redis://localhost:6379/0')
            self._redis_client = redis.from_url(redis_url, decode_responses=True)
            self._redis_client.ping()

            # Initialiser coordinator
            self._coordinator = DistributedCoordinator(
                session_id=session_id,
                num_workers=num_workers,
                redis_url=redis_url
            )

            logger.info(
                f"Coordinator initialized: session={session_id}, "
                f"workers={num_workers}, redis={redis_url}"
            )

        except redis.ConnectionError as e:
            raise DistributedModeError(
                f"Cannot connect to Redis at {redis_url}: {e}. "
                "Make sure Redis is running: docker run -d -p 6379:6379 redis:7-alpine"
            )
        except Exception as e:
            raise DistributedModeError(f"Failed to initialize coordinator: {e}")

    def initialize_worker(
        self,
        worker_id: str = None,
        gpu_id: str = None,
        redis_url: str = None
    ):
        """
        Initialise le mode worker.

        Args:
            worker_id: ID unique du worker
            gpu_id: ID du GPU à utiliser (None = auto-detect)
            redis_url: URL de connexion Redis

        Raises:
            DistributedModeError: Si les dépendances manquent
        """
        if not self.check_dependencies():
            raise DistributedModeError(
                "Cannot initialize worker: missing dependencies. "
                "Install with: pip install -r requirements-distributed.txt"
            )

        try:
            from lib.distributed.worker import start_worker

            worker_id = worker_id or os.getenv('WORKER_ID', 'worker_1')

            # Configurer variables d'environnement si nécessaire
            if redis_url:
                os.environ['REDIS_URL'] = redis_url
            if gpu_id is not None:
                os.environ['CUDA_VISIBLE_DEVICES'] = str(gpu_id)

            logger.info(
                f"Starting worker: id={worker_id}, "
                f"gpu={os.getenv('CUDA_VISIBLE_DEVICES', 'auto')}"
            )

            # Démarrer worker (bloquant)
            start_worker(worker_id=worker_id, gpu_id=gpu_id)

        except Exception as e:
            raise DistributedModeError(f"Failed to start worker: {e}")

    def distribute_conversion(
        self,
        chapters: List[List[str]],
        tts_config: Dict[str, Any],
        output_path: str,
        resume: bool = False
    ) -> str:
        """
        Distribue la conversion des chapitres aux workers.

        Args:
            chapters: Liste des chapitres (chaque chapitre = liste de phrases)
            tts_config: Configuration TTS (voice, language, device, etc.)
            output_path: Chemin du fichier audiobook final
            resume: Si True, reprend depuis checkpoint

        Returns:
            str: Chemin du fichier audiobook créé

        Raises:
            DistributedModeError: Si coordinator pas initialisé
        """
        if self._coordinator is None:
            raise DistributedModeError(
                "Coordinator not initialized. Call initialize_coordinator() first."
            )

        logger.info(
            f"Distributing {len(chapters)} chapters to workers "
            f"(resume={resume})"
        )

        # 1. Distribuer aux workers
        result = self._coordinator.distribute_chapters(
            chapters=chapters,
            tts_config=tts_config,
            resume=resume
        )

        # 2. Attendre et agréger résultats
        audio_paths = self._coordinator.wait_and_aggregate(result)

        # 3. Combiner en fichier final
        final_path = self._coordinator.combine_audio_files(
            audio_paths=audio_paths,
            output_path=output_path
        )

        logger.info(f"Distributed conversion completed: {final_path}")
        return final_path

    def get_progress(self) -> Dict[str, Any]:
        """
        Récupère la progression actuelle.

        Returns:
            Dict avec infos de progression

        Raises:
            DistributedModeError: Si coordinator pas initialisé
        """
        if self._coordinator is None:
            raise DistributedModeError("Coordinator not initialized")

        return self._coordinator.get_overall_progress()

    def is_available(self) -> bool:
        """Retourne True si le mode distribué est disponible."""
        return self.check_dependencies()

    def cleanup(self):
        """Nettoie les ressources."""
        if self._redis_client:
            try:
                self._redis_client.close()
            except Exception:
                pass

        self._coordinator = None
        self._worker = None
        self._redis_client = None


# Instance globale (singleton pattern)
_distributed_manager = None


def get_distributed_manager() -> DistributedManager:
    """
    Retourne l'instance globale du DistributedManager.

    Returns:
        DistributedManager: Instance singleton
    """
    global _distributed_manager
    if _distributed_manager is None:
        _distributed_manager = DistributedManager()
    return _distributed_manager


def is_distributed_mode_available() -> bool:
    """
    Vérifie rapidement si le mode distribué est disponible.

    Returns:
        bool: True si redis et celery sont installés
    """
    manager = get_distributed_manager()
    return manager.is_available()


# API simplifiée pour le code principal
def initialize_coordinator(session_id: str, num_workers: int = 1, redis_url: str = None):
    """Initialise le coordinator. Voir DistributedManager.initialize_coordinator()."""
    manager = get_distributed_manager()
    manager.initialize_coordinator(session_id, num_workers, redis_url)


def initialize_worker(worker_id: str = None, gpu_id: str = None, redis_url: str = None):
    """Initialise le worker. Voir DistributedManager.initialize_worker()."""
    manager = get_distributed_manager()
    manager.initialize_worker(worker_id, gpu_id, redis_url)


def distribute_conversion(
    chapters: List[List[str]],
    tts_config: Dict[str, Any],
    output_path: str,
    resume: bool = False
) -> str:
    """Distribue la conversion. Voir DistributedManager.distribute_conversion()."""
    manager = get_distributed_manager()
    return manager.distribute_conversion(chapters, tts_config, output_path, resume)


def get_progress() -> Dict[str, Any]:
    """Récupère la progression. Voir DistributedManager.get_progress()."""
    manager = get_distributed_manager()
    return manager.get_progress()
