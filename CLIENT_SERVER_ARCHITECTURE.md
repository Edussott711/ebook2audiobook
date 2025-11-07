# Architecture Client-Serveur pour Mode Distribué

## 📋 Vue d'ensemble

Architecture **Client-Serveur** simple et directe pour distribuer le traitement TTS sur plusieurs machines.

**Principe** : Le serveur (master) distribue les chapitres directement aux clients (workers) via HTTP, sans message broker intermédiaire.

---

## 🏗️ Architecture proposée

### Schéma global

```
┌─────────────────────────────────────────────────────────────────┐
│  SERVEUR (MASTER)                                               │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  MasterServer (FastAPI)                                   │  │
│  │  • Parse l'ebook en chapitres                             │  │
│  │  • Distribue aux workers via HTTP POST                    │  │
│  │  • Collecte les audios retournés                          │  │
│  │  • Assemble le livre final                                │  │
│  │  • Gère retry et timeouts                                 │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Configuration:                                                  │
│  WORKER_NODES=192.168.1.10:8000,192.168.1.11:8000              │
└────────────────┬─────────────────────────────────────────────────┘
                 │
                 │ HTTP POST /process_chapter
                 ├─────────────────┬───────────────────┐
                 ▼                 ▼                   ▼
┌──────────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ CLIENT 1 (WORKER)    │  │ CLIENT 2         │  │ CLIENT N         │
│ 192.168.1.10:8000    │  │ 192.168.1.11:8000│  │ 192.168.1.N:8000 │
│                      │  │                  │  │                  │
│ ┌──────────────────┐ │  │ ┌──────────────┐ │  │ ┌──────────────┐ │
│ │ WorkerServer     │ │  │ │ WorkerServer │ │  │ │ WorkerServer │ │
│ │ (FastAPI)        │ │  │ │ (FastAPI)    │ │  │ │ (FastAPI)    │ │
│ │                  │ │  │ │              │ │  │ │              │ │
│ │ POST /process    │ │  │ │ POST /process│ │  │ │ POST /process│ │
│ │ GET /health      │ │  │ │ GET /health  │ │  │ │ GET /health  │ │
│ │ GET /status      │ │  │ │ GET /status  │ │  │ │ GET /status  │ │
│ └────────┬─────────┘ │  │ └──────┬───────┘ │  │ └──────┬───────┘ │
│          │           │  │        │         │  │        │         │
│          ▼           │  │        ▼         │  │        ▼         │
│ ┌──────────────────┐ │  │ ┌──────────────┐ │  │ ┌──────────────┐ │
│ │ TTS Engine       │ │  │ │ TTS Engine   │ │  │ │ TTS Engine   │ │
│ │ (XTTSv2)         │ │  │ │ (XTTSv2)     │ │  │ │ (XTTSv2)     │ │
│ │ GPU 0            │ │  │ │ GPU 1        │ │  │ │ GPU N        │ │
│ └──────────────────┘ │  │ └──────────────┘ │  │ └──────────────┘ │
└──────────────────────┘  └──────────────────┘  └──────────────────┘
```

---

## 🔄 Flux de traitement

### Étape 1 : Initialisation

```
1. SERVEUR démarre
   ├─ Lit WORKER_NODES depuis env
   ├─ Parse : ["192.168.1.10:8000", "192.168.1.11:8000"]
   └─ Vérifie health de chaque worker (GET /health)

2. CLIENTS démarrent
   ├─ Lance WorkerServer sur port 8000
   ├─ Charge TTS model en mémoire GPU
   └─ Attend les requêtes du serveur
```

### Étape 2 : Distribution des chapitres

```
SERVEUR:
  1. Parse ebook.epub → 25 chapitres
  2. Pour chaque chapitre:
     ├─ Sélectionne worker disponible (round-robin ou status check)
     ├─ Envoie HTTP POST /process_chapter
     │  Body: {
     │    "chapter_id": 1,
     │    "sentences": ["Sentence 1.", "Sentence 2."],
     │    "tts_config": {...}
     │  }
     └─ Reçoit réponse avec audio en base64 ou URL

CLIENT (async):
  1. Reçoit POST /process_chapter
  2. Marque status = "busy"
  3. Pour chaque phrase:
     ├─ TTS conversion
     └─ Sauvegarde temp file
  4. Combine phrases avec FFmpeg
  5. Encode audio en base64 ou upload vers serveur
  6. Retourne réponse JSON
  7. Marque status = "idle"
```

### Étape 3 : Agrégation

```
SERVEUR:
  1. Collecte tous les audios des chapitres
  2. Sauvegarde dans /tmp/session_id/chapter_N.mp3
  3. Combine tous les chapitres avec FFmpeg
  4. Génère audiobook.mp3 final
  5. Déplace vers output/
```

---

## 🔌 Spécification de l'API

### API Client (Worker)

#### 1. POST /process_chapter

Traite un chapitre et retourne l'audio.

**Request:**
```json
{
  "chapter_id": 1,
  "sentences": [
    "This is the first sentence.",
    "This is the second sentence."
  ],
  "tts_config": {
    "voice_name": "jenny",
    "language": "en",
    "model_name": "xtts"
  }
}
```

**Response (Option A - Audio inline):**
```json
{
  "chapter_id": 1,
  "audio_base64": "UklGRiQAAABXQVZFZm10IBAAA...",
  "duration": 125.4,
  "num_sentences": 2
}
```

**Response (Option B - Upload URL):**
```json
{
  "chapter_id": 1,
  "audio_url": "http://worker-ip:8000/download/chapter_1.mp3",
  "duration": 125.4,
  "num_sentences": 2
}
```

**Statut codes:**
- 200: Succès
- 503: Worker occupé
- 500: Erreur traitement

---

#### 2. GET /health

Health check simple.

**Response:**
```json
{
  "status": "healthy",
  "gpu_available": true,
  "model_loaded": true
}
```

---

#### 3. GET /status

État détaillé du worker.

**Response:**
```json
{
  "status": "idle",  // "idle" | "busy"
  "current_chapter": null,  // ou chapter_id si busy
  "gpu_memory_free_mb": 15360,
  "uptime_seconds": 3600
}
```

---

#### 4. GET /download/{filename}

Télécharge un fichier audio généré.

**Response:**
- Content-Type: audio/mpeg
- Body: Binary audio data

---

### API Serveur (Master) - Optionnel

Le serveur expose aussi une API pour monitoring :

#### 1. GET /progress/{session_id}

Progression de la conversion.

**Response:**
```json
{
  "session_id": "abc123",
  "total_chapters": 25,
  "completed_chapters": 10,
  "progress_percent": 40.0,
  "estimated_time_remaining": 1200
}
```

---

## 💻 Implémentation technique

### Stack technologique

| Composant | Technologie | Justification |
|-----------|-------------|---------------|
| Serveur HTTP | **FastAPI** | Async, performant, simple |
| Client HTTP | **httpx** | Client async pour FastAPI |
| Validation | **Pydantic** | Validation automatique des données |
| Concurrence | **asyncio** | I/O non-bloquant |
| Audio encoding | **base64** ou **streaming** | Transfert des fichiers |

---

### Code du Worker (Client)

**`lib/distributed/worker_server.py`**

```python
"""
Worker server - Écoute les requêtes du master et traite les chapitres.
"""

import os
import base64
import asyncio
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import torch

# Import du TTS existant
from lib.classes.tts_manager import TTSManager

# ============================================================================
# Modèles Pydantic
# ============================================================================

class ProcessChapterRequest(BaseModel):
    chapter_id: int
    sentences: List[str]
    tts_config: Dict[str, Any]

class ProcessChapterResponse(BaseModel):
    chapter_id: int
    audio_base64: str
    duration: float
    num_sentences: int

class HealthResponse(BaseModel):
    status: str
    gpu_available: bool
    model_loaded: bool

class StatusResponse(BaseModel):
    status: str  # "idle" | "busy"
    current_chapter: int | None
    gpu_memory_free_mb: int
    uptime_seconds: int

# ============================================================================
# Worker Server
# ============================================================================

app = FastAPI(title="ebook2audiobook Worker")

# État global du worker
class WorkerState:
    def __init__(self):
        self.tts_manager = None
        self.is_busy = False
        self.current_chapter = None
        self.start_time = time.time()

worker_state = WorkerState()


@app.on_event("startup")
async def startup_event():
    """Charge le modèle TTS au démarrage."""
    print("🚀 Worker starting...")

    # Charger le modèle TTS
    worker_state.tts_manager = TTSManager(
        model_name=os.getenv('TTS_MODEL', 'xtts'),
        device='cuda' if torch.cuda.is_available() else 'cpu'
    )

    print(f"✅ TTS model loaded on {worker_state.tts_manager.device}")


@app.post("/process_chapter", response_model=ProcessChapterResponse)
async def process_chapter(request: ProcessChapterRequest):
    """
    Traite un chapitre : TTS + combine + retourne audio.
    """
    # Vérifier si worker est disponible
    if worker_state.is_busy:
        raise HTTPException(
            status_code=503,
            detail="Worker is busy processing another chapter"
        )

    worker_state.is_busy = True
    worker_state.current_chapter = request.chapter_id

    try:
        print(f"📖 Processing chapter {request.chapter_id} ({len(request.sentences)} sentences)")

        # 1. Convertir chaque phrase en audio
        sentence_audio_files = []
        for i, sentence in enumerate(request.sentences):
            output_file = f"/tmp/worker_ch{request.chapter_id}_s{i}.mp3"

            audio_file = worker_state.tts_manager.convert_sentence2audio(
                sentence=sentence,
                output_file=output_file,
                voice_name=request.tts_config.get('voice_name'),
                language=request.tts_config.get('language')
            )
            sentence_audio_files.append(audio_file)

        # 2. Combiner les phrases avec FFmpeg
        combined_file = f"/tmp/worker_chapter_{request.chapter_id}.mp3"
        _combine_audio_files(sentence_audio_files, combined_file)

        # 3. Lire et encoder en base64
        with open(combined_file, 'rb') as f:
            audio_bytes = f.read()
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')

        # 4. Calculer durée
        duration = _get_audio_duration(combined_file)

        # 5. Cleanup fichiers temporaires
        for f in sentence_audio_files + [combined_file]:
            os.remove(f)

        print(f"✅ Chapter {request.chapter_id} completed ({duration:.1f}s)")

        return ProcessChapterResponse(
            chapter_id=request.chapter_id,
            audio_base64=audio_base64,
            duration=duration,
            num_sentences=len(request.sentences)
        )

    except Exception as e:
        print(f"❌ Error processing chapter {request.chapter_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        worker_state.is_busy = False
        worker_state.current_chapter = None


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check du worker."""
    return HealthResponse(
        status="healthy",
        gpu_available=torch.cuda.is_available(),
        model_loaded=worker_state.tts_manager is not None
    )


@app.get("/status", response_model=StatusResponse)
async def get_status():
    """État détaillé du worker."""
    gpu_memory_free = 0
    if torch.cuda.is_available():
        gpu_memory_free = torch.cuda.mem_get_info()[0] // (1024 ** 2)

    return StatusResponse(
        status="busy" if worker_state.is_busy else "idle",
        current_chapter=worker_state.current_chapter,
        gpu_memory_free_mb=gpu_memory_free,
        uptime_seconds=int(time.time() - worker_state.start_time)
    )


def _combine_audio_files(audio_files: List[str], output_file: str):
    """Combine plusieurs fichiers audio avec FFmpeg."""
    import subprocess

    # Créer fichier liste
    list_file = output_file + '.txt'
    with open(list_file, 'w') as f:
        for audio_file in audio_files:
            f.write(f"file '{audio_file}'\n")

    # FFmpeg concat
    subprocess.run([
        'ffmpeg', '-f', 'concat', '-safe', '0',
        '-i', list_file, '-c', 'copy', output_file
    ], check=True, capture_output=True)

    os.remove(list_file)


def _get_audio_duration(audio_file: str) -> float:
    """Récupère la durée d'un fichier audio."""
    import subprocess
    import json

    result = subprocess.run([
        'ffprobe', '-v', 'quiet', '-print_format', 'json',
        '-show_format', audio_file
    ], capture_output=True, text=True)

    data = json.loads(result.stdout)
    return float(data['format']['duration'])


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv('WORKER_PORT', 8000))
    print(f"Starting worker on port {port}")

    uvicorn.run(app, host="0.0.0.0", port=port)
```

---

### Code du Master (Serveur)

**`lib/distributed/master_server.py`**

```python
"""
Master server - Distribue les chapitres aux workers et agrège les résultats.
"""

import os
import base64
import asyncio
from typing import List, Dict, Any
import httpx
from dataclasses import dataclass

@dataclass
class Worker:
    """Représente un worker."""
    host: str
    port: int

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    async def is_healthy(self) -> bool:
        """Vérifie si le worker est en bonne santé."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/health",
                    timeout=5.0
                )
                return response.status_code == 200
        except Exception:
            return False

    async def is_idle(self) -> bool:
        """Vérifie si le worker est disponible."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/status",
                    timeout=5.0
                )
                if response.status_code == 200:
                    data = response.json()
                    return data['status'] == 'idle'
        except Exception:
            pass
        return False

    async def process_chapter(
        self,
        chapter_id: int,
        sentences: List[str],
        tts_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Envoie un chapitre au worker pour traitement.

        Returns:
            Dict avec chapter_id, audio_base64, duration, etc.
        """
        async with httpx.AsyncClient(timeout=3600.0) as client:  # 1h timeout
            response = await client.post(
                f"{self.base_url}/process_chapter",
                json={
                    "chapter_id": chapter_id,
                    "sentences": sentences,
                    "tts_config": tts_config
                }
            )
            response.raise_for_status()
            return response.json()


class MasterCoordinator:
    """
    Coordonne la distribution des chapitres aux workers.
    """

    def __init__(self, worker_nodes: str):
        """
        Args:
            worker_nodes: String format "host1:port1,host2:port2"
                         Ex: "192.168.1.10:8000,192.168.1.11:8000"
        """
        self.workers = self._parse_worker_nodes(worker_nodes)
        self.current_worker_idx = 0

    def _parse_worker_nodes(self, worker_nodes: str) -> List[Worker]:
        """Parse la config WORKER_NODES."""
        workers = []
        for node in worker_nodes.split(','):
            node = node.strip()
            if ':' in node:
                host, port = node.split(':')
                workers.append(Worker(host=host, port=int(port)))
        return workers

    async def check_workers_health(self) -> List[Worker]:
        """
        Vérifie la santé de tous les workers.

        Returns:
            Liste des workers en bonne santé
        """
        healthy_workers = []

        for worker in self.workers:
            if await worker.is_healthy():
                healthy_workers.append(worker)
                print(f"✅ Worker {worker.base_url} is healthy")
            else:
                print(f"❌ Worker {worker.base_url} is unreachable")

        return healthy_workers

    async def distribute_chapters(
        self,
        chapters: List[Dict[str, Any]],
        tts_config: Dict[str, Any]
    ) -> List[str]:
        """
        Distribue les chapitres aux workers et collecte les audios.

        Args:
            chapters: Liste de dicts avec 'id' et 'sentences'
            tts_config: Config TTS (voice, language, etc.)

        Returns:
            Liste des chemins audio des chapitres (ordonnés)
        """
        # Vérifier workers disponibles
        healthy_workers = await self.check_workers_health()

        if not healthy_workers:
            raise Exception("No healthy workers available")

        print(f"📊 Distributing {len(chapters)} chapters to {len(healthy_workers)} workers")

        # Distribuer les chapitres
        tasks = []
        for chapter in chapters:
            # Round-robin worker selection
            worker = healthy_workers[self.current_worker_idx % len(healthy_workers)]
            self.current_worker_idx += 1

            # Créer tâche async
            task = self._process_chapter_with_retry(
                worker, chapter, tts_config
            )
            tasks.append(task)

        # Exécuter en parallèle
        results = await asyncio.gather(*tasks)

        # Sauvegarder audios et retourner chemins
        audio_paths = []
        for result in results:
            chapter_id = result['chapter_id']
            audio_base64 = result['audio_base64']

            # Décoder et sauvegarder
            audio_bytes = base64.b64decode(audio_base64)
            audio_path = f"/tmp/chapter_{chapter_id}.mp3"

            with open(audio_path, 'wb') as f:
                f.write(audio_bytes)

            audio_paths.append(audio_path)

            print(f"✅ Chapter {chapter_id} received ({result['duration']:.1f}s)")

        # Trier par chapter_id
        audio_paths.sort(key=lambda p: int(p.split('_')[-1].replace('.mp3', '')))

        return audio_paths

    async def _process_chapter_with_retry(
        self,
        worker: Worker,
        chapter: Dict[str, Any],
        tts_config: Dict[str, Any],
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Traite un chapitre avec retry automatique.
        """
        for attempt in range(max_retries):
            try:
                result = await worker.process_chapter(
                    chapter_id=chapter['id'],
                    sentences=chapter['sentences'],
                    tts_config=tts_config
                )
                return result

            except Exception as e:
                print(f"⚠️  Chapter {chapter['id']} failed on attempt {attempt + 1}: {e}")

                if attempt == max_retries - 1:
                    raise Exception(f"Chapter {chapter['id']} failed after {max_retries} attempts")

                # Attendre avant retry (backoff exponentiel)
                await asyncio.sleep(2 ** attempt)
```

---

## 🐳 Configuration Docker

### Dockerfile.worker

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Installer dépendances système
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copier requirements
COPY requirements.txt requirements-distributed.txt ./
RUN pip install -r requirements.txt -r requirements-distributed.txt

# Copier code
COPY . .

# Exposer port worker
EXPOSE 8000

# Démarrer worker server
CMD ["python", "lib/distributed/worker_server.py"]
```

### docker-compose.client-server.yml

```yaml
version: '3.8'

services:
  # Master (Serveur)
  master:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: ebook2audio-master
    environment:
      - WORKER_NODES=worker1:8000,worker2:8000
    ports:
      - "7860:7860"  # Gradio UI
    volumes:
      - ./input:/app/input
      - ./output:/app/output
    networks:
      - ebook-net
    command: python app.py --script_mode gradio

  # Worker 1
  worker1:
    build:
      context: .
      dockerfile: Dockerfile.worker
    container_name: ebook2audio-worker1
    environment:
      - WORKER_PORT=8000
      - CUDA_VISIBLE_DEVICES=0
    networks:
      - ebook-net
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ['0']
              capabilities: [gpu]

  # Worker 2
  worker2:
    build:
      context: .
      dockerfile: Dockerfile.worker
    container_name: ebook2audio-worker2
    environment:
      - WORKER_PORT=8000
      - CUDA_VISIBLE_DEVICES=1
    networks:
      - ebook-net
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ['1']
              capabilities: [gpu]

networks:
  ebook-net:
    driver: bridge
```

---

## 🚀 Démarrage

### Option 1 : Docker Compose

```bash
# Démarrer le cluster
docker-compose -f docker-compose.client-server.yml up -d

# Vérifier les workers
curl http://localhost:8001/health
curl http://localhost:8002/health

# Lancer conversion
docker exec ebook2audio-master python app.py \
  --ebook /app/input/book.epub \
  --distributed \
  --script_mode headless
```

### Option 2 : Manuel (développement)

**Terminal 1 - Worker 1:**
```bash
export WORKER_PORT=8001
export CUDA_VISIBLE_DEVICES=0
python lib/distributed/worker_server.py
```

**Terminal 2 - Worker 2:**
```bash
export WORKER_PORT=8002
export CUDA_VISIBLE_DEVICES=1
python lib/distributed/worker_server.py
```

**Terminal 3 - Master:**
```bash
export WORKER_NODES=localhost:8001,localhost:8002
python app.py --ebook input/book.epub --distributed
```

---

## ✅ Avantages de cette architecture

| Avantage | Description |
|----------|-------------|
| **Simplicité** | Pas de Redis/Celery, communication HTTP directe |
| **Légèreté** | Moins de dépendances, plus facile à déployer |
| **Contrôle** | Maîtrise totale du flux de données |
| **Debugging** | Logs simples, requêtes HTTP traçables |
| **Cluster fixe** | Idéal si workers sont connus à l'avance |

## ⚠️ Limitations

| Limitation | Solution |
|------------|----------|
| Pas de queue persistence | Implémenter checkpoint manuel |
| Retry manuel | Implémenté dans `_process_chapter_with_retry` |
| Pas de monitoring intégré | Ajouter /metrics endpoint Prometheus |
| Scaling moins flexible | Ajouter discovery service si besoin |

---

## 📊 Performance attendue

Identique à l'approche Celery :
- **5 workers** → ~5x plus rapide
- **Utilisation GPU** → >80%
- **Overhead** → <5% (moins que Celery car pas de broker)

---

**Date** : 2025-11-06
**Version** : 2.0 - Architecture Client-Serveur
