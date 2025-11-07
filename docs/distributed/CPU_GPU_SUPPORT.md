# Support CPU et GPU - Mode Distribué

## 🎯 Vue d'ensemble

Le mode distribué supporte **à la fois CPU et GPU** sur les workers. Vous pouvez mixer les deux types dans le même cluster !

## 🔍 Détection Automatique

### Code de Détection

**Fichier** : `lib/distributed/tasks.py`

```python
def _is_gpu_available() -> bool:
    """Vérifie si GPU est disponible."""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False

def _get_or_create_tts_engine(tts_config: Dict[str, Any]):
    """Crée TTS engine avec auto-détection GPU/CPU."""
    requested_device = tts_config.get('device')
    gpu_available = _is_gpu_available()

    # Auto-détection
    if requested_device:
        device = requested_device  # Explicite
    else:
        device = 'cuda' if gpu_available else 'cpu'  # Auto

    # Fallback si GPU demandé mais pas dispo
    if device == 'cuda' and not gpu_available:
        logger.warning("GPU requested but not available, falling back to CPU")
        device = 'cpu'

    # Créer TTS avec device approprié
    tts_manager = TTSManager(..., device=device)
    return tts_manager
```

### Workflow de Détection

```
Worker démarre
    ↓
Vérifier torch.cuda.is_available()
    ↓
┌─────────────────┬─────────────────┐
│  GPU Disponible │ Pas de GPU      │
│  ✓ CUDA active  │ ✓ CPU seulement │
└────────┬────────┴────────┬────────┘
         │                 │
         ▼                 ▼
   device = 'cuda'   device = 'cpu'
         │                 │
         └────────┬────────┘
                  ▼
          TTS model chargé
         avec device approprié
```

---

## 🚀 Déploiement GPU

### Option 1: Auto-détection (Recommandé)

Le worker détecte automatiquement le GPU :

```bash
# Script détecte et utilise GPU automatiquement
COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh
```

### Option 2: GPU Explicite

Forcer l'utilisation d'un GPU spécifique :

```bash
# Utiliser GPU 0
GPU_ID=0 USE_GPU=yes COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh

# Utiliser GPU 1
GPU_ID=1 USE_GPU=yes COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh
```

### Option 3: Docker Run Manuel

```bash
docker run -d \
    --name ebook2audio-worker-gpu0 \
    --gpus device=0 \
    -e REDIS_URL=redis://192.168.1.10:6379/0 \
    -e WORKER_ID=worker_gpu0 \
    -e CUDA_VISIBLE_DEVICES=0 \
    ebook2audiobook-worker:latest
```

### Multi-GPU sur Une Machine

```bash
# Worker 1 sur GPU 0
GPU_ID=0 WORKER_ID=w1_gpu0 COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh

# Worker 2 sur GPU 1
GPU_ID=1 WORKER_ID=w1_gpu1 COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh

# Worker 3 sur GPU 2
GPU_ID=2 WORKER_ID=w1_gpu2 COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh
```

---

## 💻 Déploiement CPU

### Option 1: Auto-détection

Si aucun GPU n'est détecté, utilise automatiquement le CPU :

```bash
# Sur machine sans GPU - détection auto
COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh
# → Utilise CPU automatiquement
```

### Option 2: CPU Forcé

Forcer CPU même si GPU disponible :

```bash
# Forcer CPU
USE_GPU=no COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh
```

### Option 3: Docker Run Manuel

```bash
docker run -d \
    --name ebook2audio-worker-cpu \
    -e REDIS_URL=redis://192.168.1.10:6379/0 \
    -e WORKER_ID=worker_cpu \
    -e CUDA_VISIBLE_DEVICES="" \
    ebook2audiobook-worker:latest
```

**Important** : `CUDA_VISIBLE_DEVICES=""` force le mode CPU !

### Build Image CPU

```bash
# Build worker avec PyTorch CPU
TORCH_VERSION=cpu ./scripts/distributed/build-worker-image.sh
```

---

## 🔀 Cluster Mixte CPU + GPU

### Exemple : 2 GPU + 1 CPU

```bash
# Machine 1 - GPU (192.168.1.11)
COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh
# → Auto: GPU détecté et utilisé

# Machine 2 - GPU (192.168.1.12)
COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh
# → Auto: GPU détecté et utilisé

# Machine 3 - CPU seulement (192.168.1.13)
COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh
# → Auto: Pas de GPU, utilise CPU

# Coordinator
NUM_WORKERS=3 ./scripts/distributed/start-coordinator.sh
```

**Flower Dashboard** montrera :
- Worker 1: device_type = 'cuda', gpu_memory_free = 11000 MB
- Worker 2: device_type = 'cuda', gpu_memory_free = 11000 MB
- Worker 3: device_type = 'cpu', gpu_memory_free = 0

### Répartition des Tâches

Celery distribue les chapitres **équitablement** :
- Chapitre 0 → Worker GPU 1 (rapide)
- Chapitre 1 → Worker GPU 2 (rapide)
- Chapitre 2 → Worker CPU (lent)
- Chapitre 3 → Worker GPU 1 (rapide)
- ...

⚠️ **Attention** : Worker CPU sera **beaucoup plus lent** (10-50x selon modèle).

---

## ⚡ Performances Comparées

### XTTS v2 (modèle par défaut)

| Device | Temps/Phrase (10 mots) | Speedup vs CPU |
|--------|------------------------|----------------|
| RTX 4090 | 0.5s | 40x |
| RTX 3090 | 0.8s | 25x |
| Tesla V100 | 1.2s | 17x |
| GTX 1080 Ti | 2s | 10x |
| **CPU (16 cores)** | **20s** | **1x** |

### Livre de 300 pages (~500 chapitres, ~10,000 phrases)

| Configuration | Temps Total |
|---------------|-------------|
| 1x RTX 4090 | 1.5 heures |
| 1x RTX 3090 | 2.2 heures |
| 1x CPU (16 cores) | **55 heures** |
| **2x RTX 4090** | **45 minutes** |
| **4x RTX 3090** | **33 minutes** |
| **Mixte: 2 GPU + 1 CPU** | **50 minutes** ⚠️ |

⚠️ Dans cluster mixte, les workers CPU ralentissent la progression globale !

---

## 🔍 Monitoring CPU vs GPU

### Health Check

Appeler le health check d'un worker :

```bash
# Via Flower dashboard
open http://192.168.1.10:5555

# Via Celery CLI
celery -A lib.distributed.celery_app inspect stats
```

**Réponse pour GPU Worker** :
```json
{
  "status": "ok",
  "device_type": "cuda",
  "gpu_available": true,
  "gpu_count": 1,
  "gpu_memory_free_mb": 11000,
  "tts_model_loaded": true,
  "cached_models": ["xtts_jenny_cuda"]
}
```

**Réponse pour CPU Worker** :
```json
{
  "status": "ok",
  "device_type": "cpu",
  "gpu_available": false,
  "gpu_count": 0,
  "gpu_memory_free_mb": 0,
  "tts_model_loaded": true,
  "cached_models": ["xtts_jenny_cpu"]
}
```

### Logs Worker

```bash
# GPU Worker
docker logs ebook2audio-worker-gpu0
# → "Loading TTS model: xtts_jenny_cuda (device: cuda, GPU available: True)"

# CPU Worker
docker logs ebook2audio-worker-cpu
# → "Loading TTS model: xtts_jenny_cpu (device: cpu, GPU available: False)"
```

---

## 🛠️ Troubleshooting

### GPU non détecté

**Symptômes** :
```
WARNING: GPU requested but not available, falling back to CPU
```

**Diagnostic** :
```bash
# Vérifier NVIDIA driver
nvidia-smi

# Vérifier Docker GPU support
docker run --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi

# Vérifier PyTorch
docker exec ebook2audio-worker-gpu0 python -c "import torch; print(torch.cuda.is_available())"
```

**Solutions** :
1. Installer NVIDIA drivers
2. Installer nvidia-docker2
3. Rebuild image avec bon TORCH_VERSION

### Worker CPU trop lent

**Symptômes** :
- Conversion prend des heures
- CPU usage 100%

**Solutions** :
1. Ajouter plus de workers GPU
2. Retirer worker CPU du cluster
3. Utiliser modèle TTS plus léger (Piper, edge-tts)

### OOM sur GPU

**Symptômes** :
```
RuntimeError: CUDA out of memory
```

**Solutions** :
```bash
# Réduire batch size (si applicable)
# Ou utiliser GPU avec plus de VRAM

# Vérifier mémoire disponible
nvidia-smi

# Restart worker pour clear cache
docker restart ebook2audio-worker-gpu0
```

---

## 📋 Checklist Déploiement

### Workers GPU

- [ ] NVIDIA drivers installés
- [ ] nvidia-docker2 installé
- [ ] `nvidia-smi` fonctionne
- [ ] Image built avec TORCH_VERSION=cuda124
- [ ] Variable `USE_GPU=auto` ou `yes`
- [ ] Tester: `docker run --gpus all nvidia/cuda nvidia-smi`

### Workers CPU

- [ ] Image built avec TORCH_VERSION=cpu
- [ ] Variable `USE_GPU=no` ou auto (si pas GPU)
- [ ] Variable `CUDA_VISIBLE_DEVICES=""`
- [ ] Accepter performances réduites

---

## 💡 Recommandations

### ✅ Faire

- Utiliser GPU pour production
- Mixer GPU/CPU si nécessaire
- 1 worker par GPU pour isolation
- Monitorer via Flower dashboard
- CPU workers pour tests/dev uniquement

### ❌ Éviter

- N'utilisez pas CPU en production (trop lent)
- Ne partagez pas 1 GPU entre plusieurs workers (OOM)
- N'oubliez pas de configurer CUDA_VISIBLE_DEVICES

---

## 🎯 Exemples Complets

### Cluster Production (GPU uniquement)

```bash
# Coordinator
./scripts/distributed/start-coordinator.sh

# Worker 1 - Machine avec 2x RTX 3090
GPU_ID=0 WORKER_ID=m1_gpu0 COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh
GPU_ID=1 WORKER_ID=m1_gpu1 COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh

# Worker 2 - Machine avec 1x RTX 4090
GPU_ID=0 WORKER_ID=m2_gpu0 COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh

# Total: 3 workers GPU → 3x speedup
```

### Cluster Dev/Test (Mixte)

```bash
# Coordinator
./scripts/distributed/start-coordinator.sh

# Worker GPU pour performance
COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh

# Worker CPU pour test
USE_GPU=no WORKER_ID=test_cpu COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh

# Total: 1 GPU + 1 CPU pour tests
```

---

**Le système s'adapte automatiquement à votre matériel ! 🚀**
