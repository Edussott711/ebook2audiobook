# Plan d'implémentation : Mode de Parallélisme Distribué

## 📋 Vue d'ensemble

Ajout d'un mode de traitement distribué multi-machines pour paralléliser la conversion TTS de livres audio à grande échelle.

### Problème actuel
- **Bottleneck TTS** : Les phrases sont traitées séquentiellement (lib/functions.py:1498-1508)
- **Sous-utilisation GPU/CPU** : Un seul worker par instance
- **Scalabilité limitée** : Impossible d'utiliser plusieurs machines pour accélérer

### Objectif
Permettre la distribution du travail sur N machines pour réduire le temps de traitement de plusieurs heures à quelques minutes.

---

## 🏗️ Architecture proposée

### Option 1 : Celery + Redis (RECOMMANDÉ)
**Avantages** :
- ✅ Framework mature et battle-tested
- ✅ Retry automatique et gestion des pannes
- ✅ Monitoring intégré (Flower)
- ✅ Scaling horizontal facile
- ✅ Compatible avec l'écosystème Python existant

**Inconvénients** :
- ❌ Dépendance supplémentaire (Redis/RabbitMQ)
- ❌ Overhead pour petits jobs

**Stack technique** :
```
Master Node:
├── Celery Beat (optionnel - scheduling)
├── Redis (message broker + result backend)
└── Coordinator service (distribue les chapitres)

Worker Nodes (1-N):
├── Celery Worker
├── TTS Engine (XTTS chargé en mémoire)
└── Shared storage mount (NFS/S3)
```

### Option 2 : Ray Distributed
**Avantages** :
- ✅ Optimisé pour ML/AI workloads
- ✅ Gestion automatique des ressources GPU
- ✅ API Python native et simple
- ✅ Dashboard de monitoring intégré

**Inconvénients** :
- ❌ Overhead mémoire plus élevé
- ❌ Moins mature pour production

### Option 3 : Architecture custom avec ZeroMQ
**Avantages** :
- ✅ Contrôle total sur le système
- ✅ Légèreté maximale
- ✅ Pas de dépendances lourdes

**Inconvénients** :
- ❌ Développement complet de la logique de distribution
- ❌ Pas de retry/monitoring intégré
- ❌ Maintenance importante

---

## 🎯 Décision : Celery + Redis

### Justification
1. **Maturité** : Production-ready avec millions d'utilisateurs
2. **Intégration facile** : Compatible avec l'architecture actuelle
3. **Monitoring** : Flower pour visualiser les tâches en temps réel
4. **Fault tolerance** : Retry automatique + dead letter queues

---

## 📦 Composants à développer

### 1. Distributed Coordinator (`lib/distributed/coordinator.py`)
**Responsabilités** :
- Découper le livre en unités de travail (chapitres ou phrases)
- Envoyer les tâches à la queue Celery
- Agréger les résultats
- Mettre à jour les checkpoints distribués

**API** :
```python
class DistributedCoordinator:
    def __init__(self, session_id, num_workers):
        self.session_id = session_id
        self.redis_client = Redis(...)
        self.checkpoint_manager = DistributedCheckpointManager()

    def distribute_book(self, chapters: List[Chapter]):
        """Distribue les chapitres aux workers"""
        tasks = []
        for chapter in chapters:
            task = process_chapter.delay(
                chapter_id=chapter.id,
                sentences=chapter.sentences,
                session_id=self.session_id
            )
            tasks.append(task)
        return tasks

    def wait_and_aggregate(self, tasks):
        """Attend la fin et agrège les résultats"""
        results = [task.get() for task in tasks]
        return self.combine_audio_files(results)
```

### 2. Celery Tasks (`lib/distributed/tasks.py`)
**Tâches définies** :
```python
@celery_app.task(bind=True, max_retries=3)
def process_chapter(self, chapter_id, sentences, session_id, tts_config):
    """Traite un chapitre complet sur un worker"""
    try:
        # Charger le modèle TTS (mis en cache)
        tts_engine = get_cached_tts_engine(tts_config)

        # Traiter chaque phrase
        audio_files = []
        for sentence in sentences:
            audio_path = tts_engine.convert_sentence2audio(sentence)
            audio_files.append(audio_path)

        # Combiner les audios du chapitre
        combined_path = combine_chapter_audio(audio_files)

        # Uploader vers stockage partagé
        shared_path = upload_to_shared_storage(combined_path)

        # Mettre à jour checkpoint
        update_distributed_checkpoint(session_id, chapter_id, 'completed')

        return {
            'chapter_id': chapter_id,
            'audio_path': shared_path,
            'duration': get_audio_duration(shared_path)
        }
    except Exception as exc:
        # Retry avec backoff exponentiel
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)

@celery_app.task
def process_sentence(sentence_id, text, session_id, tts_config):
    """Traite une phrase unique (granularité fine)"""
    # Implémentation similaire mais niveau phrase
    pass
```

### 3. Distributed Checkpoint Manager (`lib/distributed/checkpoint_manager.py`)
**Extensions au CheckpointManager actuel** :
```python
class DistributedCheckpointManager(CheckpointManager):
    def __init__(self, session_id, redis_client):
        super().__init__(session_id)
        self.redis = redis_client
        self.lock_key = f"checkpoint_lock:{session_id}"

    def save_checkpoint(self, stage, data):
        """Sauvegarde atomique avec Redis lock"""
        with redis_lock(self.redis, self.lock_key):
            # Fusion des données de tous les workers
            existing = self.redis.hgetall(f"checkpoint:{self.session_id}")
            merged = {**existing, **data}

            # Sauvegarde locale + Redis
            super().save_checkpoint(stage, merged)
            self.redis.hset(f"checkpoint:{self.session_id}", mapping=merged)

    def get_pending_chapters(self):
        """Retourne les chapitres non traités pour resume"""
        checkpoint = self.load_checkpoint()
        all_chapters = checkpoint.get('total_chapters', [])
        completed = checkpoint.get('converted_chapters', [])
        return [ch for ch in all_chapters if ch not in completed]
```

### 4. Worker Service (`lib/distributed/worker.py`)
**Responsabilités** :
- Démarrer un worker Celery
- Pré-charger le modèle TTS en mémoire GPU
- Traiter les tâches de la queue
- Reporter l'état au coordinator

**Démarrage** :
```python
class DistributedWorker:
    def __init__(self, worker_id, gpu_id=None):
        self.worker_id = worker_id
        self.gpu_id = gpu_id
        self.tts_engine = None

    def start(self):
        """Lance le worker Celery"""
        # Pré-charge le modèle TTS
        self.tts_engine = initialize_tts_engine(gpu_id=self.gpu_id)

        # Cache global pour éviter recharges
        set_global_tts_engine(self.tts_engine)

        # Démarre Celery worker
        celery_app.worker_main([
            'worker',
            f'--hostname=worker_{self.worker_id}@%h',
            '--loglevel=info',
            '--concurrency=1',  # 1 tâche/worker pour GPU isolation
            f'--queues=tts_queue',
        ])
```

### 5. Shared Storage Handler (`lib/distributed/storage.py`)
**Options de stockage** :
```python
class SharedStorageHandler:
    def __init__(self, storage_type='nfs'):
        # storage_type: 'nfs', 's3', 'local' (pour testing)
        self.storage_type = storage_type
        self.base_path = self._get_base_path()

    def upload_audio(self, local_path, session_id, chapter_id):
        """Upload vers stockage partagé"""
        if self.storage_type == 'nfs':
            # Simple copy vers mount NFS
            shared_path = f"{self.base_path}/{session_id}/{chapter_id}.mp3"
            shutil.copy2(local_path, shared_path)
        elif self.storage_type == 's3':
            # Upload vers S3
            s3_client.upload_file(local_path, bucket, key)
        return shared_path

    def download_audio(self, shared_path, local_path):
        """Récupère depuis stockage partagé"""
        # Implémentation inverse
        pass
```

---

## 🔧 Modifications du code existant

### 1. `lib/functions.py` - convert_ebook()
**Changements** :
```python
def convert_ebook(ebook_file, voice_name, language, ..., distributed_mode=False, num_workers=1):
    # ... code existant ...

    if distributed_mode:
        from lib.distributed.coordinator import DistributedCoordinator

        coordinator = DistributedCoordinator(
            session_id=session_id,
            num_workers=num_workers,
            redis_url=os.getenv('REDIS_URL', 'redis://localhost:6379')
        )

        # Distribution des chapitres
        tasks = coordinator.distribute_book(chapters)

        # Attente et agrégation
        audio_files = coordinator.wait_and_aggregate(tasks)

    else:
        # Mode séquentiel actuel (pas de changement)
        audio_files = convert_chapters2audio(...)

    # ... suite du code ...
```

### 2. `app.py` - Nouveaux arguments CLI
```python
parser.add_argument(
    '--distributed',
    action='store_true',
    help='Enable distributed processing mode'
)
parser.add_argument(
    '--num-workers',
    type=int,
    default=1,
    help='Number of distributed workers to use'
)
parser.add_argument(
    '--redis-url',
    type=str,
    default='redis://localhost:6379',
    help='Redis URL for distributed coordination'
)
parser.add_argument(
    '--worker-mode',
    action='store_true',
    help='Start as a worker node (not coordinator)'
)
```

### 3. Nouvelle configuration (`lib/conf.py`)
```python
# Distributed mode settings
DISTRIBUTED_MODE_ENABLED = os.getenv('DISTRIBUTED_MODE', 'false').lower() == 'true'
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', REDIS_URL)
SHARED_STORAGE_TYPE = os.getenv('SHARED_STORAGE_TYPE', 'nfs')  # nfs, s3, local
SHARED_STORAGE_PATH = os.getenv('SHARED_STORAGE_PATH', '/mnt/shared')
```

---

## 🐳 Déploiement Docker

### 1. Docker Compose pour cluster distribué
**`docker-compose.distributed.yml`** :
```yaml
version: '3.8'

services:
  # Redis broker
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  # Coordinator (master)
  coordinator:
    build: .
    environment:
      - DISTRIBUTED_MODE=true
      - REDIS_URL=redis://redis:6379
      - SHARED_STORAGE_PATH=/mnt/shared
    volumes:
      - ./input:/app/input
      - ./output:/app/output
      - shared_audio:/mnt/shared
    depends_on:
      - redis
    command: python app.py --distributed --num-workers 3 --script_mode headless

  # Workers (scalable)
  worker:
    build: .
    environment:
      - DISTRIBUTED_MODE=true
      - REDIS_URL=redis://redis:6379
      - SHARED_STORAGE_PATH=/mnt/shared
    volumes:
      - shared_audio:/mnt/shared
    depends_on:
      - redis
    deploy:
      replicas: 3  # Nombre de workers
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    command: python app.py --worker-mode

  # Monitoring Flower
  flower:
    image: mher/flower
    environment:
      - CELERY_BROKER_URL=redis://redis:6379
    ports:
      - "5555:5555"
    depends_on:
      - redis

volumes:
  redis_data:
  shared_audio:
```

### 2. Dockerfile multi-stage pour workers
```dockerfile
# Utiliser le Dockerfile existant comme base
FROM <base_image> as worker

# Installer Celery et dépendances
RUN pip install celery[redis] flower

# Copier le code de distribution
COPY lib/distributed /app/lib/distributed

# Point d'entrée configuré pour worker/coordinator
COPY entrypoint-distributed.sh /app/
RUN chmod +x /app/entrypoint-distributed.sh
ENTRYPOINT ["/app/entrypoint-distributed.sh"]
```

**`entrypoint-distributed.sh`** :
```bash
#!/bin/bash
if [ "$WORKER_MODE" = "true" ]; then
    echo "Starting worker node..."
    celery -A lib.distributed.celery_app worker --loglevel=info
else
    echo "Starting coordinator node..."
    exec python app.py "$@"
fi
```

---

## 📊 Stratégie de distribution

### Granularité : Chapitre vs Phrase

#### Option A : Distribution par chapitre (RECOMMANDÉ)
**Avantages** :
- ✅ Moins d'overhead de communication
- ✅ Checkpoints naturels (par chapitre)
- ✅ Load balancing acceptable (livres = 20-50 chapitres)

**Inconvénients** :
- ❌ Déséquilibre si chapitres de tailles variables

**Implémentation** :
```python
# 1 tâche = 1 chapitre complet
for chapter in chapters:
    process_chapter.delay(chapter)
```

#### Option B : Distribution par phrase
**Avantages** :
- ✅ Load balancing optimal
- ✅ Granularité maximale

**Inconvénients** :
- ❌ Overhead élevé (milliers de tâches)
- ❌ Gestion complexe des checkpoints

**Implémentation** :
```python
# 1 tâche = 1 phrase
for sentence in all_sentences:
    process_sentence.delay(sentence)
```

#### Option C : Hybride (Best of both)
**Distribution par chapitre + parallélisme local des phrases** :
```python
@celery_app.task
def process_chapter(chapter):
    # Sur le worker, utiliser multiprocessing local pour les phrases
    with ProcessPoolExecutor(max_workers=4) as executor:
        audio_files = executor.map(process_sentence_local, chapter.sentences)
    return combine_chapter(audio_files)
```

**Recommandation** : Commencer avec **Option A** (par chapitre) pour simplicité.

---

## 🔐 Gestion des pannes

### 1. Retry automatique
```python
@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 5},
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True
)
def process_chapter(self, ...):
    # Celery gère automatiquement les retries
    pass
```

### 2. Dead Letter Queue
```python
# Configuration Celery
celery_app.conf.task_reject_on_worker_lost = True
celery_app.conf.task_acks_late = True  # ACK après succès seulement
```

### 3. Health checks
```python
# Monitoring périodique des workers
@celery_app.task
def health_check():
    return {'status': 'ok', 'gpu_available': torch.cuda.is_available()}

# Ping depuis coordinator
for worker in active_workers:
    health_check.apply_async(queue=worker.queue)
```

### 4. Graceful shutdown
```python
# Capture SIGTERM pour sauvegarde checkpoint
import signal

def save_checkpoint_and_exit(signum, frame):
    checkpoint_manager.save_checkpoint('interrupted', current_state)
    sys.exit(0)

signal.signal(signal.SIGTERM, save_checkpoint_and_exit)
```

---

## 📈 Monitoring et observabilité

### 1. Flower Dashboard
- **URL** : http://localhost:5555
- **Fonctionnalités** :
  - Visualisation des tâches en temps réel
  - Statistiques par worker
  - Retry history
  - Logs centralisés

### 2. Métriques custom
```python
from celery.signals import task_success, task_failure

@task_success.connect
def task_success_handler(sender=None, result=None, **kwargs):
    # Log vers Prometheus/Grafana
    metrics.increment('tts.chapters.completed')
    metrics.timing('tts.chapter.duration', result['duration'])

@task_failure.connect
def task_failure_handler(sender=None, exception=None, **kwargs):
    metrics.increment('tts.chapters.failed')
    logger.error(f"Task failed: {exception}")
```

### 3. Progress tracking
```python
# Update Redis avec progression en temps réel
def update_progress(session_id, completed_chapters, total_chapters):
    progress = (completed_chapters / total_chapters) * 100
    redis_client.set(f"progress:{session_id}", progress)
    redis_client.publish(f"progress_updates", json.dumps({
        'session_id': session_id,
        'progress': progress
    }))
```

---

## 🧪 Tests

### 1. Tests unitaires
```python
# tests/test_distributed_coordinator.py
def test_distribute_chapters():
    coordinator = DistributedCoordinator(session_id='test', num_workers=2)
    chapters = [Chapter(id=1, sentences=['Hello']), Chapter(id=2, sentences=['World'])]

    tasks = coordinator.distribute_book(chapters)
    assert len(tasks) == 2

def test_checkpoint_sync():
    manager = DistributedCheckpointManager('test', redis_client)
    manager.save_checkpoint('audio_conversion_in_progress', {'chapter': 1})

    loaded = manager.load_checkpoint()
    assert loaded['chapter'] == 1
```

### 2. Tests d'intégration
```python
# tests/test_distributed_integration.py
@pytest.mark.integration
def test_full_distributed_conversion():
    # Démarre cluster test (Redis + 2 workers)
    with DistributedTestCluster(num_workers=2):
        result = convert_ebook(
            'test.epub',
            distributed_mode=True,
            num_workers=2
        )
        assert os.path.exists(result['output_file'])
```

### 3. Tests de charge
```python
# Simuler 10 conversions simultanées
@pytest.mark.stress
def test_concurrent_books():
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(convert_ebook, f'book_{i}.epub', distributed_mode=True)
            for i in range(10)
        ]
        results = [f.result() for f in futures]
    assert all(r['status'] == 'completed' for r in results)
```

---

## 📚 Documentation utilisateur

### Démarrage rapide

#### Mode local (testing)
```bash
# Démarrer Redis
docker run -d -p 6379:6379 redis:alpine

# Terminal 1 : Démarrer workers
python app.py --worker-mode --num-workers 2

# Terminal 2 : Lancer conversion
python app.py --distributed --num-workers 2 --script_mode headless \
  --ebook input/book.epub --voice en_US/female
```

#### Mode cluster Docker
```bash
# Lancer cluster complet (coordinator + 3 workers + Redis)
docker-compose -f docker-compose.distributed.yml up --scale worker=3

# Monitoring
open http://localhost:5555  # Flower dashboard
```

### Configuration avancée

#### Variables d'environnement
```bash
# Coordination
export DISTRIBUTED_MODE=true
export REDIS_URL=redis://my-redis-server:6379
export NUM_WORKERS=5

# Stockage partagé
export SHARED_STORAGE_TYPE=s3
export AWS_S3_BUCKET=my-audiobooks-bucket

# Tuning
export CELERY_WORKER_CONCURRENCY=1  # Tâches simultanées/worker
export CELERY_TASK_TIME_LIMIT=3600  # Timeout 1h par chapitre
```

---

## 🚀 Feuille de route d'implémentation

### Phase 1 : Infrastructure de base (Semaine 1-2)
1. ✅ Installation et configuration Celery + Redis
2. ✅ Création de `lib/distributed/coordinator.py`
3. ✅ Création de `lib/distributed/tasks.py` avec task basique
4. ✅ Tests unitaires pour coordinator

### Phase 2 : Intégration TTS (Semaine 3)
1. ✅ Adaptation de `convert_chapters2audio()` pour mode distribué
2. ✅ Implémentation de `process_chapter` task complet
3. ✅ Gestion du cache TTS sur workers
4. ✅ Tests d'intégration bout-en-bout

### Phase 3 : Checkpoint distribué (Semaine 4)
1. ✅ Extension de `CheckpointManager` → `DistributedCheckpointManager`
2. ✅ Synchronisation Redis des états
3. ✅ Tests de resume après panne
4. ✅ Validation de la cohérence des données

### Phase 4 : Stockage partagé (Semaine 5)
1. ✅ Implémentation `SharedStorageHandler` (NFS + S3)
2. ✅ Intégration avec workers
3. ✅ Tests de performance stockage
4. ✅ Fallback sur stockage local si partagé indisponible

### Phase 5 : Docker et déploiement (Semaine 6)
1. ✅ Création `docker-compose.distributed.yml`
2. ✅ Script `entrypoint-distributed.sh`
3. ✅ Configuration multi-GPU
4. ✅ Documentation déploiement

### Phase 6 : Monitoring (Semaine 7)
1. ✅ Intégration Flower
2. ✅ Métriques custom Prometheus
3. ✅ Dashboard Grafana pour visualisation
4. ✅ Alertes sur pannes workers

### Phase 7 : Optimisations (Semaine 8)
1. ✅ Load balancing dynamique
2. ✅ Compression des résultats intermédiaires
3. ✅ Auto-scaling workers selon charge
4. ✅ Benchmarks performance

---

## 📊 Métriques de succès

| Métrique | Cible |
|----------|-------|
| **Temps de conversion** | 5-10x plus rapide avec 5 workers |
| **Utilisation GPU** | >80% (vs <30% actuel) |
| **Taux de pannes** | <1% avec retry |
| **Overhead coordination** | <10% du temps total |
| **Scalabilité** | Linéaire jusqu'à 10 workers |

---

## 🔍 Risques et mitigation

| Risque | Impact | Probabilité | Mitigation |
|--------|--------|-------------|------------|
| Contention GPU sur workers | Élevé | Moyenne | 1 tâche/worker, CUDA_VISIBLE_DEVICES |
| Échec synchronisation checkpoints | Élevé | Faible | Redis locks + validation |
| Saturation réseau (NFS) | Moyen | Moyenne | Compression audio, batch uploads |
| Complexité debugging distribué | Moyen | Élevée | Logs centralisés, tracing distribué |
| Coût infrastructure | Faible | Élevée | Auto-scaling, mode hybride cloud |

---

## 💡 Améliorations futures

1. **Auto-scaling dynamique** : Ajouter/retirer workers selon la charge
2. **Support cloud natif** : AWS ECS/Fargate, K8s
3. **Optimisation réseau** : Compression audio en transit
4. **Pré-chargement intelligent** : Prédire chapitres suivants
5. **Multi-tenancy** : Plusieurs livres simultanés sur même cluster

---

## 📞 Support et contribution

- **Issues** : GitHub Issues pour bugs
- **Discussions** : GitHub Discussions pour questions
- **PR** : Contributions bienvenues !

---

**Date de création** : 2025-11-06
**Auteur** : Claude (Assistant IA)
**Version** : 1.0 - Plan initial
