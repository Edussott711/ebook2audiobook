"""
Module de parallélisme distribué pour ebook2audiobook.

Fournit les composants pour distribuer le traitement TTS sur plusieurs machines:
- Coordinator: Orchestre la distribution des tâches via Celery
- Worker: Exécute les conversions TTS
- Celery tasks: Définit les tâches distribuables
- Checkpoint manager: Synchronise l'état distribué
- Storage handler: Gère le stockage partagé
"""

__version__ = '1.0.0'

from .celery_app import celery_app
from .coordinator import DistributedCoordinator
from .checkpoint_manager import DistributedCheckpointManager
from .storage import SharedStorageHandler

__all__ = [
    'celery_app',
    'DistributedCoordinator',
    'DistributedCheckpointManager',
    'SharedStorageHandler',
]
