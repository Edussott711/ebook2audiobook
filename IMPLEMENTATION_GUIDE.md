# Guide d'implémentation - Mode Parallélisme Distribué

## 📅 Planning d'implémentation (8 semaines)

Ce guide détaille l'implémentation étape par étape du mode distribué, avec tests et validation à chaque étape.

---

## Phase 1 : Infrastructure de base (Semaine 1-2)

### Étape 1.1 : Installer les dépendances Celery et Redis

**Durée estimée** : 2 heures

#### Actions :

1. **Ajouter Celery aux dépendances**

Éditer `requirements.txt` :
```bash
celery[redis]==5.3.4
redis==5.0.1
flower==2.0.1  # Pour monitoring
```

2. **Installer localement pour tests**
```bash
pip install -r requirements.txt
```

3. **Démarrer Redis en local**
```bash
docker run -d -p 6379:6379 --name ebook2audio-redis redis:7-alpine
```

4. **Vérifier connexion Redis**
```python
import redis
client = redis.from_url('redis://localhost:6379/0')
client.ping()  # Doit retourner True
```

#### Tests :
- ✅ Redis démarré et accessible
- ✅ Celery installé sans erreur
- ✅ `redis-cli ping` retourne `PONG`

---

### Étape 1.2 : Créer la structure du module distribué

**Durée estimée** : 1 heure

#### Actions :

1. **Créer l'arborescence**
```bash
mkdir -p lib/distributed
touch lib/distributed/__init__.py
touch lib/distributed/celery_app.py
touch lib/distributed/coordinator.py
touch lib/distributed/tasks.py
touch lib/distributed/checkpoint_manager.py
touch lib/distributed/storage.py
touch lib/distributed/worker.py
```

2. **Implémenter `lib/distributed/__init__.py`**
```python
"""Module de parallélisme distribué pour ebook2audiobook."""

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

#### Tests :
- ✅ Import du module fonctionne : `python -c "import lib.distributed"`

---

### Étape 1.3 : Configurer Celery

**Durée estimée** : 3 heures

#### Actions :

1. **Implémenter `lib/distributed/celery_app.py`**

Copier le code complet depuis `TECHNICAL_SPECIFICATIONS.md` section 1.2.

2. **Tester configuration Celery**
```bash
# Démarrer un worker de test
celery -A lib.distributed.celery_app worker --loglevel=info

# Dans un autre terminal, tester une tâche simple
python -c "
from lib.distributed.celery_app import celery_app

@celery_app.task
def add(x, y):
    return x + y

result = add.delay(4, 6)
print(f'Task ID: {result.id}')
print(f'Result: {result.get(timeout=10)}')
"
```

#### Tests :
- ✅ Worker démarre sans erreur
- ✅ Tâche de test s'exécute et retourne 10
- ✅ Logs Celery affichent la tâche

---

### Étape 1.4 : Implémenter DistributedCheckpointManager

**Durée estimée** : 4 heures

#### Actions :

1. **Implémenter `lib/distributed/checkpoint_manager.py`**

Copier le code depuis `TECHNICAL_SPECIFICATIONS.md` section 1.5.

2. **Écrire tests unitaires**

Créer `tests/test_distributed_checkpoint.py` :
```python
import pytest
import redis
from lib.distributed.checkpoint_manager import DistributedCheckpointManager


@pytest.fixture
def redis_client():
    """Client Redis de test."""
    client = redis.from_url('redis://localhost:6379/1')  # DB 1 pour tests
    yield client
    # Cleanup
    client.flushdb()


def test_save_and_load_checkpoint(redis_client):
    """Test sauvegarde et chargement."""
    manager = DistributedCheckpointManager('test_session', redis_client)

    # Sauvegarder
    manager.save_checkpoint('audio_conversion_in_progress', {
        'total_chapters': 10,
        'converted_chapters': [1, 2, 3]
    })

    # Charger
    checkpoint = manager.load_checkpoint()
    assert checkpoint['stage'] == 'audio_conversion_in_progress'
    assert checkpoint['total_chapters'] == 10
    assert checkpoint['converted_chapters'] == [1, 2, 3]


def test_mark_chapter_complete(redis_client):
    """Test marquage chapitre complété."""
    manager = DistributedCheckpointManager('test_session', redis_client)

    manager.save_checkpoint('audio_conversion_in_progress', {
        'total_chapters': 5,
        'converted_chapters': [1, 2]
    })

    manager.mark_chapter_complete(3)

    checkpoint = manager.load_checkpoint()
    assert 3 in checkpoint['converted_chapters']
    assert checkpoint['converted_chapters'] == [1, 2, 3]


def test_concurrent_updates(redis_client):
    """Test updates concurrentes (simule multi-workers)."""
    import threading

    manager = DistributedCheckpointManager('test_session', redis_client)
    manager.save_checkpoint('audio_conversion_in_progress', {
        'total_chapters': 20,
        'converted_chapters': []
    })

    # Simuler 10 workers qui complètent des chapitres simultanément
    def complete_chapter(chapter_id):
        manager.mark_chapter_complete(chapter_id)

    threads = [
        threading.Thread(target=complete_chapter, args=(i,))
        for i in range(1, 11)
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Vérifier que tous les 10 chapitres sont là (pas de perte)
    checkpoint = manager.load_checkpoint()
    assert len(checkpoint['converted_chapters']) == 10
    assert set(checkpoint['converted_chapters']) == set(range(1, 11))


def test_get_pending_chapters(redis_client):
    """Test récupération chapitres en attente."""
    manager = DistributedCheckpointManager('test_session', redis_client)

    manager.save_checkpoint('audio_conversion_in_progress', {
        'total_chapters': 5,
        'converted_chapters': [1, 3, 5]
    })

    pending = manager.get_pending_chapters()
    assert pending == [2, 4]
```

3. **Exécuter tests**
```bash
pytest tests/test_distributed_checkpoint.py -v
```

#### Tests :
- ✅ Tous les tests passent
- ✅ Test concurrent prouve thread-safety
- ✅ Lock Redis fonctionne

---

## Phase 2 : Implémentation TTS distribué (Semaine 3)

### Étape 2.1 : Implémenter SharedStorageHandler

**Durée estimée** : 3 heures

#### Actions :

1. **Implémenter `lib/distributed/storage.py`**

Copier le code depuis `TECHNICAL_SPECIFICATIONS.md` section 1.6.

Commencer avec support NFS/local uniquement. S3 peut être ajouté plus tard.

2. **Tester upload/download**

Créer `tests/test_storage.py` :
```python
import pytest
import tempfile
import os
from pathlib import Path
from lib.distributed.storage import SharedStorageHandler


@pytest.fixture
def temp_storage():
    """Répertoire temporaire pour tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


def test_upload_download_filesystem(temp_storage):
    """Test upload et download local."""
    handler = SharedStorageHandler('local', temp_storage)

    # Créer fichier test
    test_file = '/tmp/test_audio.mp3'
    with open(test_file, 'wb') as f:
        f.write(b'fake audio data')

    # Upload
    shared_path = handler.upload_audio(test_file, 'session_123', 'chapter_1')
    assert os.path.exists(shared_path)
    assert 'session_123' in shared_path
    assert 'chapter_1.mp3' in shared_path

    # Download
    download_path = '/tmp/downloaded.mp3'
    handler.download_audio(shared_path, download_path)
    assert os.path.exists(download_path)

    # Vérifier contenu
    with open(download_path, 'rb') as f:
        assert f.read() == b'fake audio data'

    # Cleanup
    os.remove(test_file)
    os.remove(download_path)


def test_list_session_files(temp_storage):
    """Test listing fichiers session."""
    handler = SharedStorageHandler('local', temp_storage)

    # Upload 3 fichiers
    for i in range(3):
        test_file = f'/tmp/test_{i}.mp3'
        with open(test_file, 'wb') as f:
            f.write(b'data')
        handler.upload_audio(test_file, 'session_abc', f'chapter_{i}')
        os.remove(test_file)

    # Lister
    files = handler.list_session_files('session_abc')
    assert len(files) == 3


def test_cleanup_session(temp_storage):
    """Test cleanup session."""
    handler = SharedStorageHandler('local', temp_storage)

    # Upload fichier
    test_file = '/tmp/test.mp3'
    with open(test_file, 'wb') as f:
        f.write(b'data')
    handler.upload_audio(test_file, 'session_xyz', 'file')

    # Vérifier existence
    files = handler.list_session_files('session_xyz')
    assert len(files) == 1

    # Cleanup
    handler.cleanup_session('session_xyz')

    # Vérifier suppression
    files = handler.list_session_files('session_xyz')
    assert len(files) == 0

    os.remove(test_file)
```

3. **Exécuter tests**
```bash
pytest tests/test_storage.py -v
```

#### Tests :
- ✅ Upload/download fonctionnent
- ✅ Listing fichiers correct
- ✅ Cleanup supprime bien les fichiers

---

### Étape 2.2 : Implémenter la tâche Celery process_chapter

**Durée estimée** : 6 heures

#### Actions :

1. **Implémenter `lib/distributed/tasks.py`**

Copier le code depuis `TECHNICAL_SPECIFICATIONS.md` section 1.4.

**Important** : Pour les tests initiaux, créer une version simplifiée qui utilise un TTS mock.

2. **Créer TTS mock pour tests**

Créer `tests/mocks/tts_mock.py` :
```python
"""Mock TTS engine pour tests."""
import time
import random


class MockTTSEngine:
    """Simule un TTS engine."""

    def __init__(self, **kwargs):
        self.config = kwargs

    def convert_sentence2audio(self, sentence, output_file):
        """
        Simule conversion TTS.
        Génère un fichier MP3 vide et simule temps de traitement.
        """
        # Simuler temps de traitement (0.1-0.5s par phrase)
        time.sleep(random.uniform(0.1, 0.5))

        # Créer fichier vide
        with open(output_file, 'wb') as f:
            f.write(b'fake mp3 data for: ' + sentence.encode())

        return output_file
```

3. **Tester la tâche process_chapter**

Créer `tests/test_tasks.py` :
```python
import pytest
import tempfile
import os
from lib.distributed.tasks import process_chapter
from lib.distributed.checkpoint_manager import DistributedCheckpointManager
from lib.distributed.storage import SharedStorageHandler


@pytest.fixture
def test_config():
    """Config de test."""
    tmpdir = tempfile.mkdtemp()
    return {
        'session_id': 'test_session_123',
        'storage_path': tmpdir,
        'tts_config': {
            'model_name': 'mock',
            'voice_name': 'test',
            'language': 'en'
        }
    }


def test_process_chapter_basic(test_config):
    """Test traitement d'un chapitre simple."""
    # Préparer données
    chapter_id = 1
    sentences = [
        'This is sentence one.',
        'This is sentence two.',
        'This is sentence three.'
    ]

    # Exécuter tâche (synchrone pour test)
    result = process_chapter(
        chapter_id=chapter_id,
        sentences=sentences,
        session_id=test_config['session_id'],
        tts_config=test_config['tts_config']
    )

    # Vérifier résultat
    assert result['chapter_id'] == chapter_id
    assert result['num_sentences'] == 3
    assert 'audio_path' in result
    assert os.path.exists(result['audio_path'])

    # Vérifier checkpoint
    manager = DistributedCheckpointManager(
        test_config['session_id'],
        redis_client=None
    )
    checkpoint = manager.load_checkpoint()
    assert chapter_id in checkpoint.get('converted_chapters', [])


@pytest.mark.integration
def test_process_chapter_with_celery(test_config):
    """Test avec worker Celery réel."""
    from lib.distributed.tasks import process_chapter

    # Exécuter async
    task = process_chapter.delay(
        chapter_id=5,
        sentences=['Hello world.'],
        session_id=test_config['session_id'],
        tts_config=test_config['tts_config']
    )

    # Attendre résultat (max 30s)
    result = task.get(timeout=30)

    assert result['chapter_id'] == 5
    assert result['num_sentences'] == 1
```

4. **Exécuter tests**

Dans un terminal :
```bash
# Démarrer worker
celery -A lib.distributed.celery_app worker --loglevel=info
```

Dans un autre terminal :
```bash
# Tests unitaires
pytest tests/test_tasks.py::test_process_chapter_basic -v

# Test intégration (nécessite worker actif)
pytest tests/test_tasks.py::test_process_chapter_with_celery -v -m integration
```

#### Tests :
- ✅ Tâche s'exécute localement
- ✅ Tâche s'exécute via Celery worker
- ✅ Checkpoint mis à jour
- ✅ Fichier audio créé dans storage

---

### Étape 2.3 : Implémenter DistributedCoordinator

**Durée estimée** : 5 heures

#### Actions :

1. **Implémenter `lib/distributed/coordinator.py`**

Copier le code depuis `TECHNICAL_SPECIFICATIONS.md` section 1.3.

2. **Tester coordination**

Créer `tests/test_coordinator.py` :
```python
import pytest
from lib.distributed.coordinator import DistributedCoordinator


@pytest.fixture
def coordinator():
    """Coordinator de test."""
    return DistributedCoordinator(
        session_id='test_coord_123',
        num_workers=2,
        storage_type='local',
        storage_path='/tmp/test_storage'
    )


def test_distribute_book(coordinator):
    """Test distribution de chapitres."""
    chapters = [
        {'id': 1, 'sentences': ['Sentence 1.']},
        {'id': 2, 'sentences': ['Sentence 2.']},
        {'id': 3, 'sentences': ['Sentence 3.']}
    ]

    tts_config = {
        'model_name': 'mock',
        'voice_name': 'test',
        'language': 'en'
    }

    # Distribuer (retourne GroupResult)
    result = coordinator.distribute_book(chapters, tts_config)

    # Vérifier type
    from celery.result import GroupResult
    assert isinstance(result, GroupResult)

    # Vérifier nombre de tâches
    assert len(result) == 3


@pytest.mark.integration
def test_full_workflow(coordinator):
    """Test workflow complet."""
    chapters = [
        {'id': 1, 'sentences': ['Chapter one.', 'Second sentence.']},
        {'id': 2, 'sentences': ['Chapter two.']}
    ]

    tts_config = {
        'model_name': 'mock',
        'voice_name': 'test',
        'language': 'en'
    }

    # 1. Distribuer
    result = coordinator.distribute_book(chapters, tts_config)

    # 2. Attendre et agréger
    audio_paths = coordinator.wait_and_aggregate(result, timeout=60)

    # 3. Vérifier résultats
    assert len(audio_paths) == 2
    for path in audio_paths:
        assert os.path.exists(path)

    # 4. Vérifier progression
    progress = coordinator.get_overall_progress()
    assert progress['converted_chapters'] == 2
    assert progress['progress_percent'] == 100.0


def test_resume_workflow(coordinator):
    """Test resume après interruption."""
    chapters = [
        {'id': i, 'sentences': [f'Chapter {i}.']}
        for i in range(1, 6)
    ]

    tts_config = {'model_name': 'mock', 'voice_name': 'test', 'language': 'en'}

    # Simuler conversion partielle
    coordinator.checkpoint_manager.save_checkpoint('audio_conversion_in_progress', {
        'total_chapters': 5,
        'converted_chapters': [1, 2]  # 1 et 2 déjà faits
    })

    # Resume (ne doit traiter que 3, 4, 5)
    result = coordinator.distribute_book(chapters, tts_config, resume=True)

    assert len(result) == 3  # Seulement 3 tâches
```

3. **Exécuter tests**
```bash
# Démarrer worker d'abord
celery -A lib.distributed.celery_app worker --loglevel=info --concurrency=2

# Tests
pytest tests/test_coordinator.py -v
pytest tests/test_coordinator.py::test_full_workflow -v -m integration
```

#### Tests :
- ✅ Distribution fonctionne
- ✅ Workflow complet passe
- ✅ Resume ne traite que chapitres manquants
- ✅ Progression correcte

---

## Phase 3 : Intégration avec le code existant (Semaine 4)

### Étape 3.1 : Modifier lib/functions.py

**Durée estimée** : 4 heures

#### Actions :

1. **Ajouter paramètres distribués à convert_ebook()**

Éditer `lib/functions.py` :
```python
def convert_ebook(
    ebook_file,
    voice_name,
    language,
    ...,
    # NOUVEAUX PARAMÈTRES
    distributed_mode=False,
    num_workers=1,
    redis_url='redis://localhost:6379/0',
    storage_type='nfs',
    storage_path='/mnt/shared'
):
    """
    Convertit un ebook en audiobook.

    Args:
        ...
        distributed_mode: Si True, utilise le mode distribué
        num_workers: Nombre de workers attendus
        redis_url: URL Redis pour coordination
        storage_type: Type de stockage ('nfs', 's3', 'local')
        storage_path: Chemin du stockage partagé
    """

    # ... code existant jusqu'à extraction des chapitres ...

    # NOUVEAU : Branchement mode distribué
    if distributed_mode:
        logger.info(f"Using distributed mode with {num_workers} workers")

        from lib.distributed.coordinator import DistributedCoordinator

        # Initialiser coordinator
        coordinator = DistributedCoordinator(
            session_id=session_id,
            num_workers=num_workers,
            redis_url=redis_url,
            storage_type=storage_type,
            storage_path=storage_path
        )

        # Préparer config TTS
        tts_config = {
            'model_name': model_name,
            'voice_name': voice_name,
            'language': language,
            'custom_model': custom_model_path,
            'device': device
        }

        # Distribuer chapitres
        result = coordinator.distribute_book(chapters, tts_config)

        # Attendre et récupérer audios
        chapter_audio_paths = coordinator.wait_and_aggregate(result)

        # Combiner en fichier final
        final_audiobook = coordinator.combine_audio_files(
            chapter_audio_paths,
            output_audio_file
        )

    else:
        # MODE SÉQUENTIEL EXISTANT (inchangé)
        chapter_audio_paths = convert_chapters2audio(
            chapters, voice_name, language, ...
        )

        final_audiobook = combine_audio_files(
            chapter_audio_paths,
            output_audio_file
        )

    # ... suite du code existant ...
```

2. **Tester intégration**

Créer `tests/test_integration.py` :
```python
import pytest
from lib.functions import convert_ebook


@pytest.mark.integration
def test_convert_ebook_distributed():
    """Test conversion complète en mode distribué."""
    # Utiliser un mini ebook de test
    test_ebook = 'tests/fixtures/test_book.epub'

    # Lancer conversion
    result = convert_ebook(
        ebook_file=test_ebook,
        voice_name='test_voice',
        language='en',
        distributed_mode=True,
        num_workers=2,
        storage_type='local',
        storage_path='/tmp/test_distributed'
    )

    # Vérifier
    assert os.path.exists(result['output_file'])
    assert result['status'] == 'completed'


@pytest.mark.integration
def test_sequential_vs_distributed():
    """Compare mode séquentiel et distribué (résultats identiques)."""
    test_ebook = 'tests/fixtures/test_book.epub'

    # Mode séquentiel
    result_seq = convert_ebook(
        ebook_file=test_ebook,
        voice_name='test_voice',
        language='en',
        distributed_mode=False
    )

    # Mode distribué
    result_dist = convert_ebook(
        ebook_file=test_ebook,
        voice_name='test_voice',
        language='en',
        distributed_mode=True,
        num_workers=2
    )

    # Les deux doivent produire des audios de même durée
    duration_seq = get_audio_duration(result_seq['output_file'])
    duration_dist = get_audio_duration(result_dist['output_file'])

    assert abs(duration_seq - duration_dist) < 1.0  # Tolérance 1s
```

#### Tests :
- ✅ Conversion distribuée complète fonctionne
- ✅ Résultats similaires entre séquentiel et distribué

---

### Étape 3.2 : Ajouter arguments CLI

**Durée estimée** : 2 heures

#### Actions :

1. **Modifier app.py**

Éditer `app.py` :
```python
parser.add_argument(
    '--distributed',
    action='store_true',
    default=False,
    help='Enable distributed processing mode'
)

parser.add_argument(
    '--num-workers',
    type=int,
    default=1,
    help='Number of distributed workers (default: 1)'
)

parser.add_argument(
    '--redis-url',
    type=str,
    default='redis://localhost:6379/0',
    help='Redis URL for distributed coordination'
)

parser.add_argument(
    '--storage-type',
    type=str,
    choices=['nfs', 's3', 'local'],
    default='nfs',
    help='Shared storage type (default: nfs)'
)

parser.add_argument(
    '--storage-path',
    type=str,
    default='/mnt/shared',
    help='Shared storage path (default: /mnt/shared)'
)

parser.add_argument(
    '--worker-mode',
    action='store_true',
    default=False,
    help='Start as a distributed worker (not coordinator)'
)

# ... puis dans la fonction main ...

if args.worker_mode:
    # Démarrer comme worker Celery
    from lib.distributed.worker import start_worker
    start_worker(
        worker_id=os.getenv('WORKER_ID', 'worker_1'),
        gpu_id=os.getenv('CUDA_VISIBLE_DEVICES')
    )
else:
    # Mode normal (coordinator ou séquentiel)
    result = convert_ebook(
        ...,
        distributed_mode=args.distributed,
        num_workers=args.num_workers,
        redis_url=args.redis_url,
        storage_type=args.storage_type,
        storage_path=args.storage_path
    )
```

2. **Tester CLI**

```bash
# Test mode distribué via CLI
python app.py \
  --distributed \
  --num-workers 2 \
  --ebook tests/fixtures/test_book.epub \
  --voice test_voice \
  --language en \
  --script_mode headless

# Test mode worker
python app.py --worker-mode
```

#### Tests :
- ✅ Arguments parsés correctement
- ✅ Conversion lance via CLI
- ✅ Worker démarre via CLI

---

## Phase 4 : Docker et déploiement (Semaine 5-6)

### Étape 4.1 : Créer docker-compose.distributed.yml

**Durée estimée** : 4 heures

#### Actions :

1. **Créer le fichier**

Voir section suivante "Préparation des fichiers de configuration".

2. **Tester déploiement**

```bash
# Démarrer cluster (1 coordinator + 2 workers + Redis)
docker-compose -f docker-compose.distributed.yml up --scale worker=2

# Dans un autre terminal, vérifier
docker ps  # Doit montrer redis, coordinator, worker_1, worker_2, flower

# Accéder Flower
open http://localhost:5555

# Tester conversion
docker exec -it <coordinator_container> bash
python app.py --distributed --num-workers 2 --ebook /app/input/book.epub
```

#### Tests :
- ✅ Tous les containers démarrent
- ✅ Flower accessible et affiche workers
- ✅ Conversion fonctionne
- ✅ Fichiers créés dans volume partagé

---

### Étape 4.2 : Support multi-GPU

**Durée estimée** : 3 heures

#### Actions :

1. **Configurer isolation GPU**

Dans `docker-compose.distributed.yml` :
```yaml
worker:
  environment:
    - CUDA_VISIBLE_DEVICES=${WORKER_GPU_ID}
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

2. **Script de démarrage multi-GPU**

Créer `scripts/start_distributed_multi_gpu.sh` :
```bash
#!/bin/bash

# Détecter nombre de GPUs
NUM_GPUS=$(nvidia-smi -L | wc -l)

echo "Detected $NUM_GPUS GPUs"

# Démarrer 1 worker par GPU
for i in $(seq 0 $((NUM_GPUS - 1))); do
    echo "Starting worker for GPU $i"
    WORKER_GPU_ID=$i docker-compose -f docker-compose.distributed.yml up -d worker --scale worker=$((i+1))
done

echo "Started $NUM_GPUS workers"
```

3. **Tester**
```bash
chmod +x scripts/start_distributed_multi_gpu.sh
./scripts/start_distributed_multi_gpu.sh
```

#### Tests :
- ✅ Script détecte GPUs
- ✅ Un worker par GPU
- ✅ Chaque worker utilise son GPU dédié

---

## Phase 5 : Monitoring et optimisations (Semaine 7)

### Étape 5.1 : Configurer Flower

**Durée estimée** : 2 heures

Flower est déjà dans docker-compose, mais configurer:

1. **Authentification**

Éditer `docker-compose.distributed.yml` :
```yaml
flower:
  environment:
    - FLOWER_BASIC_AUTH=admin:secretpassword
```

2. **Métriques custom**

Dans `lib/distributed/tasks.py` :
```python
from celery.signals import task_success, task_failure
import prometheus_client

# Métriques Prometheus
CHAPTERS_COMPLETED = prometheus_client.Counter(
    'ebook2audio_chapters_completed',
    'Number of chapters completed'
)

CHAPTER_DURATION = prometheus_client.Histogram(
    'ebook2audio_chapter_duration_seconds',
    'Chapter processing duration'
)

@task_success.connect
def on_task_success(sender=None, result=None, **kwargs):
    CHAPTERS_COMPLETED.inc()
    if result and 'processing_time' in result:
        CHAPTER_DURATION.observe(result['processing_time'])

@task_failure.connect
def on_task_failure(sender=None, task_id=None, exception=None, **kwargs):
    logger.error(f"Task {task_id} failed: {exception}")
```

#### Tests :
- ✅ Flower affiche authentification
- ✅ Métriques visibles dans Flower

---

### Étape 5.2 : Benchmarks de performance

**Durée estimée** : 4 heures

#### Actions :

1. **Créer script de benchmark**

Créer `scripts/benchmark_distributed.py` :
```python
"""Benchmark mode séquentiel vs distribué."""
import time
import sys
from lib.functions import convert_ebook


def benchmark(ebook_path, num_workers=1, distributed=False):
    """Benchmark une conversion."""
    start = time.time()

    result = convert_ebook(
        ebook_file=ebook_path,
        voice_name='jenny',
        language='en',
        distributed_mode=distributed,
        num_workers=num_workers
    )

    elapsed = time.time() - start

    return {
        'mode': 'distributed' if distributed else 'sequential',
        'workers': num_workers,
        'duration_seconds': elapsed,
        'chapters': result['total_chapters']
    }


if __name__ == '__main__':
    test_book = sys.argv[1]

    # Sequential
    print("=== Sequential ===")
    seq_result = benchmark(test_book, distributed=False)
    print(f"Duration: {seq_result['duration_seconds']:.1f}s")

    # Distributed 2 workers
    print("\n=== Distributed (2 workers) ===")
    dist2_result = benchmark(test_book, num_workers=2, distributed=True)
    print(f"Duration: {dist2_result['duration_seconds']:.1f}s")
    print(f"Speedup: {seq_result['duration_seconds'] / dist2_result['duration_seconds']:.2f}x")

    # Distributed 4 workers
    print("\n=== Distributed (4 workers) ===")
    dist4_result = benchmark(test_book, num_workers=4, distributed=True)
    print(f"Duration: {dist4_result['duration_seconds']:.1f}s")
    print(f"Speedup: {seq_result['duration_seconds'] / dist4_result['duration_seconds']:.2f}x")
```

2. **Exécuter benchmark**
```bash
python scripts/benchmark_distributed.py /path/to/medium_book.epub
```

3. **Documenter résultats**

Créer `BENCHMARKS.md` avec tableaux de résultats.

#### Tests :
- ✅ Speedup linéaire (ou proche)
- ✅ Mode distribué 5x plus rapide avec 5 workers

---

## Phase 6 : Documentation et finalisation (Semaine 8)

### Étape 6.1 : Documentation utilisateur

**Durée estimée** : 4 heures

#### Actions :

1. **Créer README-DISTRIBUTED.md**

Avec sections :
- Quick start
- Configuration
- Troubleshooting
- FAQ

2. **Créer exemples**

Dans `examples/distributed/` :
- `docker-compose.example.yml`
- `start_local.sh`
- `start_cluster.sh`

#### Tests :
- ✅ Un utilisateur peut démarrer en suivant README

---

### Étape 6.2 : Tests end-to-end

**Durée estimée** : 6 heures

#### Actions :

1. **Test avec vrai livre**

```bash
# Télécharger un livre du domaine public
wget https://www.gutenberg.org/ebooks/84.epub.noimages -O alice.epub

# Convertir en distribué
docker-compose -f docker-compose.distributed.yml up -d
docker exec coordinator python app.py \
  --distributed \
  --num-workers 3 \
  --ebook /app/input/alice.epub \
  --voice jenny \
  --language en
```

2. **Vérifier qualité**
- Audio lisible
- Pas de coupures
- Durée correcte

3. **Test de panne**
- Tuer un worker pendant conversion
- Vérifier que tâches sont retriées
- Conversion se termine quand même

#### Tests :
- ✅ Livre complet converti
- ✅ Résistance aux pannes

---

## ✅ Checklist finale

Avant de considérer l'implémentation terminée :

- [ ] Tous les tests unitaires passent
- [ ] Tests d'intégration passent
- [ ] Benchmarks montrent amélioration performance
- [ ] Docker compose fonctionne
- [ ] Documentation complète
- [ ] Au moins 1 livre converti avec succès
- [ ] Test de résistance aux pannes
- [ ] Flower monitoring opérationnel
- [ ] Code reviewé et refactoré

---

## 🚀 Ordre recommandé d'implémentation

1. **Semaine 1-2** : Phases 1 (infrastructure)
2. **Semaine 3** : Phase 2 (TTS distribué)
3. **Semaine 4** : Phase 3 (intégration)
4. **Semaine 5-6** : Phase 4 (Docker)
5. **Semaine 7** : Phase 5 (monitoring)
6. **Semaine 8** : Phase 6 (doc + tests)

---

**Total estimé** : 8 semaines (temps plein) ou 16 semaines (mi-temps)

**Points de validation** : À la fin de chaque phase, faire une démo complète pour valider avant de passer à la suivante.
