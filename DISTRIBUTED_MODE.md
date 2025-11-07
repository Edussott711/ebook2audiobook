# Mode Distribué - Guide Complet

## 🎯 Vue d'ensemble

Le mode distribué permet de **paralléliser la conversion TTS** en utilisant plusieurs machines équipées de GPU, réduisant significativement le temps de traitement.

**Architecture** : Celery + Redis
**Stockage partagé** : ❌ **Pas nécessaire !** Audio transféré via Redis (base64)

---

## 🚀 Quick Start (3 minutes)

### Option 1: Script interactif (Recommandé)

```bash
# Setup automatique
./scripts/distributed/setup-cluster.sh

# Suivre les instructions pour configurer coordinator ou worker
```

### Option 2: Multi-machines avec Docker

```bash
# Machine 1 (Coordinator)
./scripts/distributed/start-coordinator.sh

# Machine 2+ (Workers - sur chaque machine avec GPU)
COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh

# Accéder à l'interface web
open http://192.168.1.10:7860
```

### Option 3: Machine locale avec plusieurs GPUs

```bash
# 1. Démarrer Redis
docker run -d -p 6379:6379 --name ebook2audio-redis redis:7-alpine

# 2. Démarrer les workers (1 par GPU)
# Terminal 1 - Worker 1
WORKER_ID=worker_1 CUDA_VISIBLE_DEVICES=0 python app.py --worker_mode

# Terminal 2 - Worker 2
WORKER_ID=worker_2 CUDA_VISIBLE_DEVICES=1 python app.py --worker_mode

# 3. Lancer la conversion (coordinator)
python app.py --headless \
  --distributed \
  --num_workers 2 \
  --ebook input/book.epub \
  --language eng \
  --voice jenny
```

---

## 📊 Performance

### Gains attendus

| Configuration | Temps | Speedup |
|---------------|-------|---------|
| Séquentiel (1 GPU) | 6h | 1x |
| **Distribué (2 workers)** | **3h** | **2x** |
| **Distribué (4 workers)** | **1.5h** | **4x** |
| **Distribué (8 workers)** | **45min** | **8x** |

**Scaling linéaire** jusqu'à 10-20 workers !

---

## 🏗️ Architecture

```
┌──────────────┐
│ COORDINATOR  │  1. Distribue les chapitres
│  (Master)    │     via Celery tasks
└──────┬───────┘  2. Reçoit audio base64
       │          3. Combine & sauvegarde
       ▼
┌──────────────────────────────┐
│         REDIS                │
│  • Message Broker (Celery)   │
│  • Result Backend            │
│  • Audio Transfer (base64)   │  ← Pas de NFS/S3 !
└──────┬───────────────────────┘
       │
   ┌───┴────┬────────┬────────┐
   ▼        ▼        ▼        ▼
┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐
│Work1│  │Work2│  │Work3│  │WorkN│
│GPU0 │  │GPU1 │  │GPU2 │  │GPUN │  ← Machines indépendantes
└─────┘  └─────┘  └─────┘  └─────┘
  TTS      TTS      TTS      TTS
   │        │        │        │
   └────────┴────────┴────────┘
       (Audio encodé base64
        et retourné via Redis)
```

**Avantages** :
- ✅ Aucun stockage partagé nécessaire (NFS/S3/etc.)
- ✅ Déploiement simplifié avec `docker run` sur chaque machine
- ✅ Workers complètement indépendants
- ✅ Audio transféré directement via Redis

---

## ⚙️ Configuration

### Variables d'environnement

```bash
# Redis (seule configuration nécessaire!)
export REDIS_URL=redis://localhost:6379/0

# Worker
export WORKER_ID=worker_1
export CUDA_VISIBLE_DEVICES=0
```

### Arguments CLI (Coordinator)

```bash
python app.py --headless \
  --distributed \                     # Active le mode distribué
  --num_workers 4 \                   # Nombre de workers
  --redis_url redis://redis:6379/0 \  # URL Redis
  --ebook book.epub
```

### Arguments CLI (Worker)

```bash
python app.py --worker_mode  # Lance en mode worker
# Utilise REDIS_URL, WORKER_ID et CUDA_VISIBLE_DEVICES des env vars
```

---

## 🐳 Docker Déploiement

### Option 1: Scripts automatiques (Recommandé)

```bash
# Sur la machine coordinator
./scripts/distributed/start-coordinator.sh

# Sur chaque machine worker
COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh
```

Voir [scripts/distributed/README.md](scripts/distributed/README.md) pour plus de détails.

### Option 2: Docker Compose (machine locale uniquement)

```yaml
# docker-compose.distributed.yml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --maxmemory 2gb

  coordinator:
    build: .
    environment:
      - REDIS_URL=redis://redis:6379/0
      - NUM_WORKERS=2
    volumes:
      - ./input:/app/input
      - ./output:/app/output
    depends_on:
      - redis

  worker:
    build:
      dockerfile: Dockerfile.worker
    environment:
      - REDIS_URL=redis://redis:6379/0
      - CUDA_VISIBLE_DEVICES=0
    deploy:
      replicas: 2
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

**Usage** :
```bash
docker-compose -f docker-compose.distributed.yml up -d
```

---

## 📚 Documentation détaillée

### Planning et architecture
- [DISTRIBUTED_MODE_PLAN.md](DISTRIBUTED_MODE_PLAN.md) - Plan complet d'implémentation
- [ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md) - Diagrammes visuels
- [TECHNICAL_SPECIFICATIONS.md](TECHNICAL_SPECIFICATIONS.md) - Spécifications techniques

### Guides
- [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) - Guide d'implémentation (8 semaines)
- [README-DISTRIBUTED.md](README-DISTRIBUTED.md) - Guide utilisateur complet

### Index
- [DISTRIBUTED_MODE_INDEX.md](DISTRIBUTED_MODE_INDEX.md) - Navigation dans la documentation

---

## 🔧 Troubleshooting

### Workers ne démarrent pas

**Symptôme** : `celery worker` ne démarre pas

**Solutions** :
1. Vérifier que Redis est accessible : `redis-cli ping`
2. Vérifier les logs : `celery -A lib.distributed.celery_app inspect active`
3. Vérifier les dépendances : `pip install -r requirements-distributed.txt`

### Conversion bloquée

**Symptôme** : Aucune progression visible

**Diagnostic** :
```bash
# Flower monitoring
docker-compose up -d flower
open http://localhost:5555

# Vérifier queue Redis
redis-cli LLEN tts_queue
```

### GPU out of memory

**Solution** : 1 worker par GPU
```bash
# Chaque worker doit avoir son propre GPU
export CUDA_VISIBLE_DEVICES=0  # Worker 1
export CUDA_VISIBLE_DEVICES=1  # Worker 2
```

---

## 📈 Monitoring

### Flower Dashboard

```bash
# Démarrer Flower
docker-compose up -d flower

# Accéder au dashboard
open http://localhost:5555
```

**Features** :
- Tâches en temps réel
- Statistiques par worker
- Retry history
- Logs centralisés

---

## 🔐 Production

### Checklist sécurité

- [ ] Redis avec password : `REDIS_URL=redis://:password@host:6379/0`
- [ ] Redis avec TLS : `rediss://host:6379/0`
- [ ] Flower avec authentification
- [ ] Firewall pour limiter accès Redis
- [ ] S3 avec IAM roles (pas de credentials en clair)

---

## ❓ FAQ

**Q: Ai-je besoin d'un stockage partagé (NFS/S3) ?**
R: ❌ **Non !** Les fichiers audio sont transférés directement via Redis (base64). Chaque machine est complètement indépendante.

**Q: Combien de workers puis-je avoir ?**
R: Autant que de GPUs. En pratique, 2-20 workers est optimal.

**Q: Puis-je mixer GPUs et CPUs ?**
R: Oui, mais les workers CPU seront beaucoup plus lents.

**Q: Quelle consommation réseau ?**
R: ~1-10MB par chapitre (audio MP3 encodé base64 via Redis). Un livre de 50 chapitres = ~250MB transférés. Négligeable sur réseau local gigabit.

**Q: Redis peut-il gérer de gros fichiers audio ?**
R: Oui ! Redis 7 gère facilement des valeurs de 10-20MB. Configurez `maxmemory` selon vos besoins (voir docker-compose).

**Q: Puis-je reprendre après interruption ?**
R: Oui ! Le système de checkpoint distribué (stocké dans Redis) permet le resume.

**Q: Comment déployer sur plusieurs machines ?**
R: Utilisez `./scripts/distributed/setup-cluster.sh` ou suivez [scripts/distributed/README.md](scripts/distributed/README.md).

---

## 🎉 Exemple complet

### Scénario : 1 Coordinator + 3 Workers sur 4 machines

```bash
# === MACHINE 1 (Coordinator - 192.168.1.10) ===
./scripts/distributed/start-coordinator.sh
# Coordinator démarré sur http://192.168.1.10:7860
# Flower dashboard sur http://192.168.1.10:5555

# === MACHINE 2 (Worker 1 - GPU Tesla V100) ===
COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh

# === MACHINE 3 (Worker 2 - GPU RTX 3090) ===
COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh

# === MACHINE 4 (Worker 3 - 2x RTX 4090) ===
# Lancer 2 workers (1 par GPU)
GPU_ID=0 WORKER_ID=worker_m4_gpu0 COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh
GPU_ID=1 WORKER_ID=worker_m4_gpu1 COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh

# === Retour sur COORDINATOR ===
# Vérifier les workers dans Flower
open http://192.168.1.10:5555
# Vous devriez voir 4 workers actifs

# Lancer conversion via interface web
open http://192.168.1.10:7860
# Ou en CLI :
docker exec ebook2audio-coordinator python app.py \
  --headless \
  --distributed \
  --num_workers 4 \
  --ebook /app/input/harry_potter.epub \
  --language eng

# Résultat : 4x plus rapide qu'en séquentiel! 🚀
```

---

## 📞 Support

En cas de problème :
1. Consulter [README-DISTRIBUTED.md](README-DISTRIBUTED.md#troubleshooting)
2. Vérifier les logs : `docker logs ebook2audio-coordinator`
3. Ouvrir une issue : [GitHub Issues](https://github.com/yourusername/ebook2audiobook/issues)

---

**Bon audiobook distribué ! 🎵⚡**

**Créé le** : 2025-11-07
**Version** : 1.0
