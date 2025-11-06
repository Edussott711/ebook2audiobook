# Architecture du Mode Distribué - Diagrammes

## 1. Vue d'ensemble du système

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         MODE DISTRIBUÉ EBOOK2AUDIOBOOK                  │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐
│  User / CLI      │
│  docker-compose  │
└────────┬─────────┘
         │ convert_ebook(distributed=True)
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  COORDINATOR NODE (Master)                                              │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ DistributedCoordinator                                           │   │
│  │  • Découpage livre → chapitres                                   │   │
│  │  • Envoi tâches vers queue                                       │   │
│  │  • Agrégation résultats                                          │   │
│  │  • Gestion checkpoints                                           │   │
│  └──────────────┬───────────────────────────────┬───────────────────┘   │
│                 │                               │                       │
│                 ▼                               ▼                       │
│  ┌──────────────────────────┐   ┌─────────────────────────────────┐    │
│  │ CheckpointManager        │   │ SharedStorageHandler            │    │
│  │ (Redis sync)             │   │ (NFS/S3)                        │    │
│  └──────────────────────────┘   └─────────────────────────────────┘    │
└──────────────────┬──────────────────────────────────────────────────────┘
                   │
                   │ Celery Tasks
                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  REDIS (Message Broker + Result Backend)                               │
│  ┌────────────────┐  ┌────────────────┐  ┌─────────────────┐           │
│  │ Task Queue     │  │ Results Cache  │  │ Checkpoints KV  │           │
│  │ tts_queue      │  │ celery-results │  │ session:*       │           │
│  └────────────────┘  └────────────────┘  └─────────────────┘           │
└──────────────────┬────────────────┬────────────────┬────────────────────┘
                   │                │                │
      ┌────────────┘                │                └────────────┐
      │                             │                             │
      ▼                             ▼                             ▼
┌─────────────────┐       ┌─────────────────┐         ┌─────────────────┐
│ WORKER NODE 1   │       │ WORKER NODE 2   │   ...   │ WORKER NODE N   │
│ ┌─────────────┐ │       │ ┌─────────────┐ │         │ ┌─────────────┐ │
│ │Celery Worker│ │       │ │Celery Worker│ │         │ │Celery Worker│ │
│ └──────┬──────┘ │       │ └──────┬──────┘ │         │ └──────┬──────┘ │
│        │        │       │        │        │         │        │        │
│        ▼        │       │        ▼        │         │        ▼        │
│ ┌─────────────┐ │       │ ┌─────────────┐ │         │ ┌─────────────┐ │
│ │ TTS Engine  │ │       │ │ TTS Engine  │ │         │ │ TTS Engine  │ │
│ │ (XTTSv2)    │ │       │ │ (XTTSv2)    │ │         │ │ (XTTSv2)    │ │
│ │  GPU 0      │ │       │ │  GPU 1      │ │         │ │  GPU N      │ │
│ └─────────────┘ │       │ └─────────────┘ │         │ └─────────────┘ │
│        │        │       │        │        │         │        │        │
│        │ .mp3   │       │        │ .mp3   │         │        │ .mp3   │
│        ▼        │       │        ▼        │         │        ▼        │
└────────┼────────┘       └────────┼────────┘         └────────┼────────┘
         │                         │                           │
         └─────────────────────────┴───────────────────────────┘
                                   │
                                   ▼
                  ┌────────────────────────────────────┐
                  │ SHARED STORAGE                     │
                  │ ┌────────────────────────────────┐ │
                  │ │ /mnt/shared/session_id/        │ │
                  │ │  ├── chapter_1.mp3             │ │
                  │ │  ├── chapter_2.mp3             │ │
                  │ │  └── ...                       │ │
                  │ └────────────────────────────────┘ │
                  │ (NFS / S3 / MinIO)                 │
                  └────────────────────────────────────┘
                                   │
                                   │ Récupération
                                   ▼
                  ┌────────────────────────────────────┐
                  │ COORDINATOR (Combine Audio)        │
                  │  • Télécharge tous les chapitres   │
                  │  • Combine avec FFmpeg             │
                  │  • Génère audiobook.mp3 final      │
                  └────────────────────────────────────┘
```

---

## 2. Flux de traitement d'un chapitre

```
COORDINATOR                REDIS                 WORKER                 STORAGE
     │                       │                      │                       │
     │ 1. Enqueue task       │                      │                       │
     ├──────────────────────>│                      │                       │
     │   process_chapter(    │                      │                       │
     │     chapter_id=5,     │                      │                       │
     │     sentences=[...]   │                      │                       │
     │   )                   │                      │                       │
     │                       │                      │                       │
     │                       │ 2. Dequeue task      │                       │
     │                       │<─────────────────────┤                       │
     │                       │                      │                       │
     │                       │                      │ 3. Load TTS model     │
     │                       │                      │    (from cache)       │
     │                       │                      │                       │
     │                       │                      │ 4. For each sentence: │
     │                       │                      │    - TTS conversion   │
     │                       │                      │    - Save temp .mp3   │
     │                       │                      │                       │
     │                       │ 5. Update progress   │                       │
     │                       │<─────────────────────┤                       │
     │<──────────────────────┤                      │                       │
     │ (Redis pub/sub)       │                      │                       │
     │                       │                      │                       │
     │                       │                      │ 6. Combine sentences  │
     │                       │                      │    (FFmpeg)           │
     │                       │                      │                       │
     │                       │                      │ 7. Upload chapter     │
     │                       │                      ├──────────────────────>│
     │                       │                      │                       │
     │                       │ 8. Save checkpoint   │                       │
     │                       │<─────────────────────┤                       │
     │                       │  chapter_5: done     │                       │
     │                       │                      │                       │
     │                       │ 9. Return result     │                       │
     │                       │<─────────────────────┤                       │
     │<──────────────────────┤                      │                       │
     │ {chapter_id: 5,       │                      │                       │
     │  audio_path: "...",   │                      │                       │
     │  duration: 1200}      │                      │                       │
     │                       │                      │                       │
     │ 10. Download chapter  │                      │                       │
     ├───────────────────────────────────────────────────────────────────>│
     │<──────────────────────────────────────────────────────────────────┤
     │ chapter_5.mp3         │                      │                       │
     │                       │                      │                       │
```

---

## 3. Architecture réseau Docker

```
┌─────────────────────────────────────────────────────────────────────────┐
│  docker-compose.distributed.yml                                        │
└─────────────────────────────────────────────────────────────────────────┘

Network: ebook2audiobook_distributed_network (bridge)

┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│  ┌────────────────┐    ┌──────────────────────────────────────────┐    │
│  │  redis:6379    │◄───┤ coordinator                              │    │
│  │  (broker)      │    │  • Port: 7860 (Gradio UI)                │    │
│  └────────┬───────┘    │  • Volume: ./input:/app/input            │    │
│           │            │  • Volume: ./output:/app/output          │    │
│           │            │  • Volume: shared_audio:/mnt/shared      │    │
│           │            │  • Env: DISTRIBUTED_MODE=true            │    │
│           │            │  • Command: python app.py --distributed  │    │
│           │            └──────────────────────────────────────────┘    │
│           │                                                             │
│           │                                                             │
│           │            ┌──────────────────────────────────────────┐    │
│           └───────────>│ worker_1                                 │    │
│                        │  • GPU: 0                                │    │
│                        │  • Volume: shared_audio:/mnt/shared      │    │
│                        │  • Env: CUDA_VISIBLE_DEVICES=0           │    │
│                        │  • Command: celery worker                │    │
│                        └──────────────────────────────────────────┘    │
│           │                                                             │
│           │            ┌──────────────────────────────────────────┐    │
│           └───────────>│ worker_2                                 │    │
│                        │  • GPU: 1                                │    │
│                        │  • Volume: shared_audio:/mnt/shared      │    │
│                        │  • Env: CUDA_VISIBLE_DEVICES=1           │    │
│                        │  • Command: celery worker                │    │
│                        └──────────────────────────────────────────┘    │
│           │                                                             │
│           │            ┌──────────────────────────────────────────┐    │
│           └───────────>│ worker_N                                 │    │
│                        │  • GPU: auto                             │    │
│                        │  • Scalable: --scale worker=N            │    │
│                        └──────────────────────────────────────────┘    │
│           │                                                             │
│           │            ┌──────────────────────────────────────────┐    │
│           └───────────>│ flower:5555                              │    │
│                        │  • Monitoring dashboard                  │    │
│                        │  • Real-time task visualization          │    │
│                        └──────────────────────────────────────────┘    │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘

Volumes:
  • redis_data (persistent)
  • shared_audio (NFS mount ou volume Docker partagé)

Ports exposés:
  • 6379: Redis (interne uniquement)
  • 7860: Gradio UI (coordinator)
  • 5555: Flower monitoring
```

---

## 4. Hiérarchie des classes Python

```
lib/
├── distributed/
│   ├── __init__.py
│   │
│   ├── celery_app.py
│   │   └── celery_app (instance Celery)
│   │       • broker: Redis
│   │       • backend: Redis
│   │       • imports: ['lib.distributed.tasks']
│   │
│   ├── coordinator.py
│   │   └── class DistributedCoordinator
│   │       ├── __init__(session_id, num_workers, redis_url)
│   │       ├── distribute_book(chapters: List[Chapter]) -> List[AsyncResult]
│   │       ├── wait_and_aggregate(tasks) -> List[str]
│   │       ├── combine_audio_files(audio_paths) -> str
│   │       └── get_overall_progress() -> float
│   │
│   ├── tasks.py
│   │   ├── @celery_app.task
│   │   │   process_chapter(chapter_id, sentences, session_id, tts_config)
│   │   │       • Charge TTS engine
│   │   │       • Traite chaque phrase
│   │   │       • Combine audios
│   │   │       • Upload vers storage
│   │   │       • Update checkpoint
│   │   │       • Return result dict
│   │   │
│   │   └── @celery_app.task
│   │       process_sentence(sentence_id, text, ...) [Option granularité fine]
│   │
│   ├── checkpoint_manager.py
│   │   └── class DistributedCheckpointManager(CheckpointManager)
│   │       ├── __init__(session_id, redis_client)
│   │       ├── save_checkpoint(stage, data)  # Thread-safe avec Redis lock
│   │       ├── load_checkpoint() -> dict
│   │       ├── get_pending_chapters() -> List[int]
│   │       └── mark_chapter_complete(chapter_id)
│   │
│   ├── storage.py
│   │   └── class SharedStorageHandler
│   │       ├── __init__(storage_type='nfs')
│   │       ├── upload_audio(local_path, session_id, chapter_id) -> str
│   │       ├── download_audio(shared_path, local_path)
│   │       ├── list_session_files(session_id) -> List[str]
│   │       └── cleanup_session(session_id)
│   │
│   └── worker.py
│       └── class DistributedWorker
│           ├── __init__(worker_id, gpu_id=None)
│           ├── start()  # Lance Celery worker
│           ├── preload_tts_model()
│           └── health_check() -> dict
│
└── functions.py (modifié)
    └── convert_ebook(..., distributed_mode=False, num_workers=1)
        • Si distributed_mode:
            - Instancie DistributedCoordinator
            - distribute_book(chapters)
            - wait_and_aggregate(tasks)
        • Sinon:
            - Mode séquentiel actuel (inchangé)
```

---

## 5. Diagramme de séquence - Conversion distribuée complète

```
User  Coordinator  Redis  Worker1  Worker2  Storage  FFmpeg
 │         │         │       │        │        │       │
 │ Start   │         │       │        │        │       │
 ├────────>│         │       │        │        │       │
 │         │         │       │        │        │       │
 │         │ Parse   │       │        │        │       │
 │         │ ebook   │       │        │        │       │
 │         │ →chaps  │       │        │        │       │
 │         │         │       │        │        │       │
 │         │ Enqueue │       │        │        │       │
 │         │ Ch1-3   │       │        │        │       │
 │         ├────────>│       │        │        │       │
 │         │         │       │        │        │       │
 │         │         │ Ch1   │        │        │       │
 │         │         ├──────>│        │        │       │
 │         │         │       │        │        │       │
 │         │         │ Ch2          │        │       │
 │         │         ├──────────────>│        │       │
 │         │         │       │        │        │       │
 │         │         │       │ TTS    │        │       │
 │         │         │       │ loop   │ TTS    │       │
 │         │         │       │        │ loop   │       │
 │         │         │       │        │        │       │
 │         │         │       │ FFmpeg │        │       │
 │         │         │       │ combine│ FFmpeg │       │
 │         │         │       ├───────────────────────>│
 │         │         │       │        ├───────────────>│
 │         │         │       │        │        │       │
 │         │         │       │ Upload │        │       │
 │         │         │       ├───────────────>│       │
 │         │         │       │        │ Upload │       │
 │         │         │       │        ├───────>│       │
 │         │         │       │        │        │       │
 │         │         │ Done  │        │        │       │
 │         │         │<──────┤        │        │       │
 │         │         │       │ Done   │        │       │
 │         │         │<───────────────┤        │       │
 │         │         │       │        │        │       │
 │         │ Results │       │        │        │       │
 │         │<────────┤       │        │        │       │
 │         │         │       │        │        │       │
 │         │ Download│       │        │        │       │
 │         │ all chap│       │        │        │       │
 │         ├────────────────────────────────>│       │
 │         │<───────────────────────────────┤       │
 │         │         │       │        │        │       │
 │         │ Final   │       │        │        │       │
 │         │ combine │       │        │        │       │
 │         ├───────────────────────────────────────>│
 │         │<────────────────────────────────────────┤
 │         │         │       │        │        │       │
 │ Done    │         │       │        │        │       │
 │<────────┤         │       │        │        │       │
 │         │         │       │        │        │       │
```

---

## 6. Stratégie de checkpoint distribué

```
┌─────────────────────────────────────────────────────────────────┐
│  CHECKPOINT STATE IN REDIS                                      │
│                                                                 │
│  Key: checkpoint:session_abc123                                 │
│                                                                 │
│  {                                                              │
│    "stage": "audio_conversion_in_progress",                     │
│    "total_chapters": 25,                                        │
│    "converted_chapters": [1, 2, 5, 7, 10],  ← Workers update   │
│    "failed_chapters": [3],                   ← Retry needed     │
│    "in_progress_chapters": {                                    │
│      "4": "worker_2",           ← Currently processing          │
│      "6": "worker_1"                                            │
│    },                                                           │
│    "chapter_metadata": {                                        │
│      "1": {"duration": 1200, "size_mb": 15},                   │
│      "2": {"duration": 1400, "size_mb": 18}                    │
│    },                                                           │
│    "start_time": 1699287600,                                    │
│    "last_update": 1699289400                                    │
│  }                                                              │
│                                                                 │
│  REDIS LOCK pour updates atomiques:                             │
│  Key: checkpoint_lock:session_abc123                            │
│  TTL: 10 seconds                                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

WORKFLOW DE MISE À JOUR:

Worker 1                                    Redis
   │                                          │
   │ 1. Acquire lock                          │
   ├─────────────────────────────────────────>│
   │   SETNX checkpoint_lock:session_abc123 1 │
   │                                          │
   │ 2. Read current checkpoint               │
   ├─────────────────────────────────────────>│
   │   HGETALL checkpoint:session_abc123      │
   │<─────────────────────────────────────────┤
   │   {converted_chapters: [1, 2]}           │
   │                                          │
   │ 3. Update locally                        │
   │   converted_chapters.append(5)           │
   │                                          │
   │ 4. Write back                            │
   ├─────────────────────────────────────────>│
   │   HSET checkpoint:session_abc123         │
   │   converted_chapters [1,2,5]             │
   │                                          │
   │ 5. Release lock                          │
   ├─────────────────────────────────────────>│
   │   DEL checkpoint_lock:session_abc123     │
   │                                          │

RESUME APRÈS PANNE:

1. Coordinator démarre
2. Charge checkpoint depuis Redis
3. Identifie chapitres non terminés:
   all_chapters - converted_chapters = [3, 4, 6, 8, 9, ...]
4. Re-enqueue uniquement ces chapitres
5. Continue normalement
```

---

## 7. Gestion de la mémoire GPU

```
┌─────────────────────────────────────────────────────────────────┐
│  STRATÉGIE GPU PAR WORKER                                       │
└─────────────────────────────────────────────────────────────────┘

CONFIG DOCKER COMPOSE:
  worker:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ['0']  ← Pin worker 1 → GPU 0
              capabilities: [gpu]

ISOLATION GPU:
  • Un worker = un GPU dédié
  • Variable: CUDA_VISIBLE_DEVICES
  • Évite contention mémoire

WORKER INIT:

┌─────────────────────────────────────────────────────────────┐
│ Worker 1 (GPU 0)                                            │
│                                                             │
│  1. Set CUDA_VISIBLE_DEVICES=0                              │
│  2. Load TTS model → GPU 0                                  │
│  3. Cache global: MODEL_CACHE['xtts'] = model               │
│  4. Process tasks séquentiellement (concurrency=1)          │
│     ├─ Task 1: Use cached model                            │
│     ├─ Task 2: Use cached model                            │
│     └─ Task N: Use cached model                            │
│                                                             │
│  Memory:                                                    │
│  ┌──────────────────────────────┐                           │
│  │ GPU 0 VRAM (24 GB)           │                           │
│  │ ┌──────────────────────────┐ │                           │
│  │ │ XTTSv2 Model: 8 GB       │ │  ← Loaded once           │
│  │ └──────────────────────────┘ │                           │
│  │ ┌──────────────────────────┐ │                           │
│  │ │ Inference buffers: 2 GB  │ │  ← Per task              │
│  │ └──────────────────────────┘ │                           │
│  │ Free: 14 GB                  │                           │
│  └──────────────────────────────┘                           │
└─────────────────────────────────────────────────────────────┘

MULTI-GPU SCALING:

Machine avec 4 GPUs:
  worker_1: CUDA_VISIBLE_DEVICES=0
  worker_2: CUDA_VISIBLE_DEVICES=1
  worker_3: CUDA_VISIBLE_DEVICES=2
  worker_4: CUDA_VISIBLE_DEVICES=3

  = 4x parallélisme sans contention
```

---

## 8. Monitoring avec Flower

```
┌──────────────────────────────────────────────────────────────┐
│  FLOWER DASHBOARD (http://localhost:5555)                    │
└──────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ WORKERS                                                     │
│ ┌─────────────┬─────────┬──────────┬──────────┬──────────┐ │
│ │ Hostname    │ Status  │ Active   │ Success  │ Failed   │ │
│ ├─────────────┼─────────┼──────────┼──────────┼──────────┤ │
│ │ worker_1@h1 │ Online  │ 1        │ 42       │ 0        │ │
│ │ worker_2@h2 │ Online  │ 1        │ 38       │ 1        │ │
│ │ worker_3@h3 │ Offline │ 0        │ 15       │ 3        │ │
│ └─────────────┴─────────┴──────────┴──────────┴──────────┘ │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ TASKS                                                       │
│ ┌────────────┬──────────────┬────────┬──────────┬────────┐ │
│ │ Task ID    │ Name         │ State  │ Runtime  │ Worker │ │
│ ├────────────┼──────────────┼────────┼──────────┼────────┤ │
│ │ abc123...  │ process_ch.. │ SUCCESS│ 125.3s   │ work_1 │ │
│ │ def456...  │ process_ch.. │ RUNNING│ 45.2s    │ work_2 │ │
│ │ ghi789...  │ process_ch.. │ PENDING│ -        │ -      │ │
│ │ jkl012...  │ process_ch.. │ RETRY  │ -        │ work_3 │ │
│ └────────────┴──────────────┴────────┴──────────┴────────┘ │
└─────────────────────────────────────────────────────────────┘

MÉTRIQUES TEMPS RÉEL:
  • Throughput: 2.5 tasks/min
  • Avg task time: 120s
  • Queue length: 15 pending
  • Total processed: 95/120 chapters (79%)

GRAPHIQUES:
  • Task timeline (Gantt chart)
  • Worker utilization
  • Task duration histogram
```

---

## 9. Exemples de déploiement

### Déploiement local (testing)

```
┌─────────────────────────────────────────────┐
│  LAPTOP / WORKSTATION                       │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │ Terminal 1: Redis                   │   │
│  │ $ docker run -p 6379:6379 redis     │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │ Terminal 2: Worker                  │   │
│  │ $ python app.py --worker-mode       │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │ Terminal 3: Coordinator             │   │
│  │ $ python app.py --distributed \     │   │
│  │   --ebook book.epub                 │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  Stockage: Local filesystem                │
└─────────────────────────────────────────────┘
```

### Déploiement cluster Docker

```
┌──────────────────────────────────────────────────────────────┐
│  DOCKER HOST (server avec 4 GPUs)                           │
│                                                              │
│  $ docker-compose -f docker-compose.distributed.yml up \    │
│    --scale worker=4                                          │
│                                                              │
│  ┌────────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Redis      │  │ Worker 1 │  │ Worker 2 │  │ Worker 3 │  │
│  │ Container  │  │ GPU 0    │  │ GPU 1    │  │ GPU 2    │  │
│  └────────────┘  └──────────┘  └──────────┘  └──────────┘  │
│                                                              │
│  ┌────────────┐  ┌──────────┐  ┌──────────┐                │
│  │ Coordinator│  │ Worker 4 │  │ Flower   │                │
│  │ + Gradio   │  │ GPU 3    │  │ Monitor  │                │
│  └────────────┘  └──────────┘  └──────────┘                │
│                                                              │
│  Stockage: Docker volume 'shared_audio'                     │
└──────────────────────────────────────────────────────────────┘
```

### Déploiement multi-serveurs

```
┌──────────────────────────────────────────────────────────────┐
│  SERVER 1 (Coordinator)                                      │
│  ┌────────────────┐  ┌──────────────┐                        │
│  │ Redis          │  │ Coordinator  │                        │
│  │ (exposed port) │  │              │                        │
│  └────────────────┘  └──────────────┘                        │
│  IP: 192.168.1.10                                            │
└──────────────────────────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│ SERVER 2      │ │ SERVER 3      │ │ SERVER 4      │
│ (Worker)      │ │ (Worker)      │ │ (Worker)      │
│               │ │               │ │               │
│ ┌───────────┐ │ │ ┌───────────┐ │ │ ┌───────────┐ │
│ │ Worker 1  │ │ │ │ Worker 2  │ │ │ │ Worker 3  │ │
│ │ 8x GPU    │ │ │ │ 8x GPU    │ │ │ │ 8x GPU    │ │
│ └───────────┘ │ │ └───────────┘ │ │ └───────────┘ │
│               │ │               │ │               │
│ IP:           │ │ IP:           │ │ IP:           │
│ 192.168.1.11  │ │ 192.168.1.12  │ │ 192.168.1.13  │
└───────────────┘ └───────────────┘ └───────────────┘

Stockage: NFS mount @ 192.168.1.10:/mnt/shared
Tous les workers montent le même NFS

Configuration:
  REDIS_URL=redis://192.168.1.10:6379
  SHARED_STORAGE_TYPE=nfs
  SHARED_STORAGE_PATH=/mnt/shared
```

---

Cette architecture permet:
- ✅ Scaling horizontal illimité
- ✅ Fault tolerance via retry automatique
- ✅ Resume après panne
- ✅ Monitoring temps réel
- ✅ Utilisation optimale GPU (80%+ vs 30% actuel)
- ✅ Temps de conversion divisé par N (nombre de workers)
