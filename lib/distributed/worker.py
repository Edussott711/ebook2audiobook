"""
Utilitaires pour démarrer et gérer les workers Celery.
"""

import os
import sys
import logging

logger = logging.getLogger(__name__)


def start_worker(worker_id: str = None, gpu_id: str = None, concurrency: int = 1):
    """
    Démarre un worker Celery.

    Args:
        worker_id: ID unique du worker
        gpu_id: ID du GPU à utiliser (None = auto-detect)
        concurrency: Nombre de tâches simultanées (généralement 1 pour GPU)
    """
    from .celery_app import celery_app

    worker_id = worker_id or os.getenv('WORKER_ID', 'worker_1')

    # Configurer GPU si spécifié
    if gpu_id is not None:
        os.environ['CUDA_VISIBLE_DEVICES'] = str(gpu_id)
        logger.info(f"Worker {worker_id} using GPU {gpu_id}")
    elif 'CUDA_VISIBLE_DEVICES' in os.environ:
        logger.info(f"Worker {worker_id} using GPU {os.environ['CUDA_VISIBLE_DEVICES']}")
    else:
        logger.info(f"Worker {worker_id} using CPU")

    # Pré-charger le modèle TTS (optionnel)
    # Ceci peut être fait ici pour éviter le chargement à chaque tâche
    # Mais pour plus de flexibilité, on laisse le chargement dans la tâche

    logger.info(f"Starting Celery worker: {worker_id}")

    # Démarrer le worker
    argv = [
        'worker',
        f'--hostname={worker_id}@%h',
        '--loglevel=info',
        f'--concurrency={concurrency}',
        '--queues=tts_queue',
        '--max-tasks-per-child=50',  # Restart après 50 tâches
    ]

    celery_app.worker_main(argv)


if __name__ == '__main__':
    # Permettre de démarrer directement: python -m lib.distributed.worker
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    worker_id = os.getenv('WORKER_ID', 'worker_1')
    gpu_id = os.getenv('CUDA_VISIBLE_DEVICES')

    start_worker(worker_id=worker_id, gpu_id=gpu_id)
