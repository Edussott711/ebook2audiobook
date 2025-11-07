# Mode Distribué Client-Serveur - Guide Rapide

## 🚀 Démarrage ultra-rapide (3 minutes)

### Prérequis
- Docker + Docker Compose
- GPU NVIDIA (optionnel mais recommandé)

### Installation

```bash
# 1. Cloner le repo (si pas déjà fait)
git clone https://github.com/yourusername/ebook2audiobook.git
cd ebook2audiobook

# 2. Démarrer le cluster (lance workers + master)
./scripts/start-client-server.sh

# 3. Accéder à l'interface web
open http://localhost:7860

# 4. Uploader un ebook et lancer la conversion !
```

C'est tout ! 🎉

---

## 📖 Qu'est-ce que le mode distribué ?

Le mode distribué permet de **paralléliser la conversion TTS** en utilisant plusieurs machines (ou GPUs).

### Sans mode distribué (séquentiel)
```
Livre de 100 chapitres → 10 heures ⏱️
```

### Avec mode distribué (3 workers)
```
Livre de 100 chapitres → 3.5 heures ⏱️  (3x plus rapide!)
```

---

## 🏗️ Architecture

```
┌────────────────┐
│  MASTER        │  Coordonne la conversion
│  (Serveur)     │  Distribue les chapitres
└───────┬────────┘
        │
        ├─────────┬─────────┬─────────┐
        ▼         ▼         ▼         ▼
    ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐
    │Worker│  │Worker│  │Worker│  │Worker│
    │  1   │  │  2   │  │  3   │  │  N   │
    │GPU 0 │  │GPU 1 │  │GPU 2 │  │GPU N │
    └──────┘  └──────┘  └──────┘  └──────┘
      TTS       TTS       TTS       TTS
```

**Fonctionnement** :
1. Master parse l'ebook en chapitres
2. Envoie chaque chapitre à un worker disponible (via HTTP)
3. Worker traite le TTS et retourne l'audio
4. Master assemble tous les chapitres en audiobook final

---

## 🎯 Cas d'usage

### Vous devriez utiliser le mode distribué si :
✅ Vous avez plusieurs GPUs (même machine ou différentes machines)
✅ Vous convertissez des livres longs (>10 chapitres)
✅ Vous voulez diviser le temps de traitement par N (N = nombre de workers)

### Restez en mode séquentiel si :
❌ Vous n'avez qu'1 seul GPU
❌ Vous convertissez de petits textes (<5 chapitres)
❌ Vous préférez la simplicité

---

## ⚙️ Configuration

### Configuration basique (Docker Compose)

Le fichier `docker-compose.client-server.yml` est déjà configuré pour 3 workers.

**Pour ajuster le nombre de workers** :
1. Éditer `docker-compose.client-server.yml`
2. Commenter/décommenter les sections `worker1`, `worker2`, `worker3`, etc.
3. Mettre à jour `WORKER_NODES` dans la section `master`

### Configuration multi-machines

**Sur la machine Master** :
```bash
# docker-compose.client-server.yml
environment:
  - WORKER_NODES=192.168.1.10:8000,192.168.1.11:8000,192.168.1.12:8000
```

**Sur chaque machine Worker** :
```bash
# Lancer le worker
docker run -d \
  --gpus all \
  -p 8000:8000 \
  -e WORKER_PORT=8000 \
  -e CUDA_VISIBLE_DEVICES=0 \
  ebook2audiobook:worker
```

---

## 📊 Monitoring

### Vérifier la santé des workers

```bash
# Worker 1
curl http://localhost:8001/health

# Réponse:
{
  "status": "healthy",
  "gpu_available": true,
  "model_loaded": true
}
```

### Voir le statut d'un worker

```bash
curl http://localhost:8001/status

# Réponse:
{
  "status": "idle",  # ou "busy"
  "current_chapter": null,
  "gpu_memory_free_mb": 15360,
  "uptime_seconds": 3600
}
```

### Logs en temps réel

```bash
# Master
docker logs -f ebook2audio-master

# Worker 1
docker logs -f ebook2audio-worker1
```

---

## 🐛 Troubleshooting

### Workers ne démarrent pas

**Symptôme** : `docker ps` ne montre pas les workers

**Solutions** :
1. Vérifier les logs : `docker logs ebook2audio-worker1`
2. Vérifier que les GPUs sont accessibles : `nvidia-smi`
3. Vérifier la configuration Docker GPU : `docker run --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi`

---

### Worker répond "503 Service Unavailable"

**Symptôme** : `curl http://localhost:8001/health` retourne 503

**Raison** : Worker est occupé à traiter un chapitre

**Solution** : Attendre que le chapitre se termine, ou ajouter plus de workers

---

### Conversion très lente

**Diagnostic** :
```bash
# Vérifier que les workers sont utilisés
docker logs ebook2audio-master | grep "Processing chapter"

# Doit montrer des logs comme:
# worker1: Processing chapter 1
# worker2: Processing chapter 2
# worker3: Processing chapter 3
```

**Si pas de parallélisme** :
- Vérifier que `--distributed` est passé à la commande
- Vérifier que `WORKER_NODES` est bien configuré dans master

---

### GPU out of memory

**Symptôme** :
```
RuntimeError: CUDA out of memory
```

**Solutions** :
1. Réduire le nombre de workers (1 worker = 1 GPU)
2. S'assurer que `CUDA_VISIBLE_DEVICES` est unique par worker
3. Utiliser un modèle TTS plus léger

---

## 🔧 Commandes utiles

```bash
# Démarrer le cluster
./scripts/start-client-server.sh

# Arrêter le cluster
docker-compose -f docker-compose.client-server.yml down

# Redémarrer un worker
docker-compose -f docker-compose.client-server.yml restart worker1

# Voir les containers
docker-compose -f docker-compose.client-server.yml ps

# Accéder au shell d'un worker
docker exec -it ebook2audio-worker1 bash

# Tester un worker manuellement
curl -X POST http://localhost:8001/process_chapter \
  -H "Content-Type: application/json" \
  -d '{
    "chapter_id": 1,
    "sentences": ["Hello world."],
    "tts_config": {"voice_name": "jenny", "language": "en", "model_name": "xtts"}
  }'
```

---

## 📚 Documentation complète

Pour plus de détails, consulter :

- **[CLIENT_SERVER_ARCHITECTURE.md](CLIENT_SERVER_ARCHITECTURE.md)** - Architecture détaillée
- **[ARCHITECTURE_COMPARISON.md](ARCHITECTURE_COMPARISON.md)** - Comparaison Celery vs Client-Serveur
- **[IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)** - Guide d'implémentation

---

## ❓ FAQ

**Q: Combien de workers puis-je avoir ?**
R: Autant que de GPUs disponibles. En pratique, 2-10 workers est optimal.

**Q: Puis-je mixer GPUs et CPUs ?**
R: Oui, mais les workers CPU seront beaucoup plus lents.

**Q: Les workers doivent-ils avoir le même GPU ?**
R: Non, mais les performances seront limitées par le GPU le plus lent.

**Q: Puis-je ajouter/retirer des workers pendant une conversion ?**
R: Non, pas dans cette version. Arrêtez et relancez le cluster.

**Q: Quelle est la consommation réseau ?**
R: Environ 1-5MB par chapitre (transfert audio). Négligeable sur réseau local.

---

## 🎉 Résultat attendu

Avec 3 workers GPU :
- Livre de 50 chapitres
- Mode séquentiel : ~6 heures
- **Mode distribué : ~2 heures** ⚡

**Gain : 3x plus rapide !**

---

**Bon audiobook ! 🎵**
