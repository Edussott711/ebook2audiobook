# Mode Distribué - Guide Complet

## 🎯 Vue d'ensemble

Le mode distribué permet de **paralléliser la conversion TTS** en utilisant plusieurs machines équipées de GPU, réduisant significativement le temps de traitement.

**Architecture** : Celery + Redis

---

## 🚀 Quick Start (3 minutes)

### 1. Démarrer le cluster

```bash
# 1. Démarrer Redis
docker run -d -p 6379:6379 --name ebook2audio-redis redis:7-alpine

# 2. Démarrer les workers (1 par GPU)
# Terminal 1 - Worker 1
export WORKER_ID=worker_1
export CUDA_VISIBLE_DEVICES=0
python app.py --worker-mode

# Terminal 2 - Worker 2
export WORKER_ID=worker_2
export CUDA_VISIBLE_DEVICES=1
python app.py --worker-mode

# 3. Lancer la conversion (coordinator)
python app.py --headless \
  --distributed \
  --num-workers 2 \
  --ebook input/book.epub \
  --language en \
  --voice jenny
```

### 2. Avec Docker Compose (Recommandé)

```bash
# Démarrer tout le cluster
./scripts/start-distributed.sh

# Ou manuellement
docker-compose -f docker-compose.distributed.yml up -d --scale worker=3

# Lancer conversion
docker exec ebook2audio-coordinator python app.py \
  --headless --distributed --num-workers 3 \
  --ebook /app/input/book.epub
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
│ COORDINATOR  │  Distribue les chapitres
│  (Master)    │  via Celery tasks
└──────┬───────┘
       │
       ▼
┌──────────────┐
│    REDIS     │  Message Broker
│  Queue + KV  │  + Result Backend
└──────┬───────┘
       │
   ┌───┴────┬────────┬────────┐
   ▼        ▼        ▼        ▼
┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐
│Work1│  │Work2│  │Work3│  │WorkN│
│GPU0 │  │GPU1 │  │GPU2 │  │GPUN │
└─────┘  └─────┘  └─────┘  └─────┘
   │        │        │        │
   └────────┴────────┴────────┘
              │
              ▼
      ┌──────────────┐
      │ Shared       │
      │ Storage      │
      │ (NFS/S3)     │
      └──────────────┘
```

---

## ⚙️ Configuration

### Variables d'environnement

```bash
# Redis
export REDIS_URL=redis://localhost:6379/0

# Stockage partagé
export SHARED_STORAGE_TYPE=nfs  # ou s3, local
export SHARED_STORAGE_PATH=/mnt/shared

# Worker
export WORKER_ID=worker_1
export CUDA_VISIBLE_DEVICES=0
```

### Arguments CLI

```bash
python app.py --headless \
  --distributed \                    # Active le mode distribué
  --num-workers 4 \                  # Nombre de workers
  --redis-url redis://redis:6379/0 \ # URL Redis
  --storage-type nfs \               # Type de stockage
  --storage-path /mnt/shared \       # Chemin stockage
  --ebook book.epub
```

---

## 🐳 Docker Compose

### Configuration minimale

```yaml
# docker-compose.distributed.yml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  coordinator:
    build: .
    environment:
      - NUM_WORKERS=2
    volumes:
      - ./input:/app/input
      - ./output:/app/output
    depends_on:
      - redis
    command: python app.py --headless --distributed ...

  worker:
    build: .
    environment:
      - REDIS_URL=redis://redis:6379/0
    deploy:
      replicas: 2  # Nombre de workers
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    depends_on:
      - redis
    command: python app.py --worker-mode
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

**Q: Combien de workers puis-je avoir ?**
R: Autant que de GPUs. En pratique, 2-20 workers est optimal.

**Q: Puis-je mixer GPUs et CPUs ?**
R: Oui, mais les workers CPU seront beaucoup plus lents.

**Q: Quelle consommation réseau ?**
R: ~1-5MB par chapitre (transfert audio). Négligeable sur réseau local.

**Q: Puis-je reprendre après interruption ?**
R: Oui ! Le système de checkpoint distribué permet le resume.

---

## 🎉 Exemple complet

```bash
# 1. Démarrer le cluster (3 workers)
docker-compose -f docker-compose.distributed.yml up -d --scale worker=3

# 2. Vérifier les workers
docker-compose -f docker-compose.distributed.yml ps

# 3. Lancer conversion
docker exec ebook2audio-coordinator python app.py \
  --headless \
  --distributed \
  --num-workers 3 \
  --ebook /app/input/harry_potter.epub \
  --language en \
  --voice jenny

# 4. Suivre dans Flower
open http://localhost:5555

# 5. Résultat dans output/
ls output/
# harry_potter.mp3  (3x plus rapide qu'en séquentiel!)
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
