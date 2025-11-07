"""Configuration de l'application Celery pour ebook2audiobook."""

import os
from celery import Celery
from kombu import Queue, Exchange

# URL Redis depuis environnement ou défaut
REDIS_URL = os.getenv('CELERY_BROKER_URL', os.getenv('REDIS_URL', 'redis://localhost:6379/0'))

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
    'lib.distributed.tasks.health_check': {'queue': 'priority_queue'},
}
