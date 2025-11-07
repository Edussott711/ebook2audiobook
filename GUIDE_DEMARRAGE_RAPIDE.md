# Guide Démarrage Rapide - Mode Distribué avec Docker

## 🎯 Tu veux tester ? Suis ce guide !

### Option A : Test Local (1 seule machine) - 5 minutes

Parfait pour tester que tout fonctionne avant de déployer sur plusieurs machines.

#### Étape 1 : Build les images Docker

```bash
cd /path/to/ebook2audiobook

# Build l'image worker (avec GPU)
docker build -f Dockerfile.worker -t ebook2audiobook-worker:latest \
  --build-arg TORCH_VERSION=cuda124 .

# Build l'image coordinator (normale)
docker build -t ebook2audiobook:latest .
```

**Temps** : ~10-15 minutes la première fois (télécharge PyTorch, etc.)

#### Étape 2 : Démarrer Redis

```bash
docker run -d \
  --name ebook2audio-redis \
  -p 6379:6379 \
  redis:7-alpine
```

#### Étape 3 : Démarrer un Worker

```bash
# Worker avec GPU
docker run -d \
  --name ebook2audio-worker-1 \
  --gpus device=0 \
  --restart unless-stopped \
  -e REDIS_URL=redis://172.17.0.1:6379/0 \
  -e WORKER_ID=worker_1 \
  -e CUDA_VISIBLE_DEVICES=0 \
  ebook2audiobook-worker:latest

# Voir les logs
docker logs -f ebook2audio-worker-1
# Tu devrais voir: "Loading TTS model... (device: cuda, GPU available: True)"
```

**Note** : `172.17.0.1` est l'IP du host Docker (fonctionne en local).

#### Étape 4 : Démarrer Flower (monitoring)

```bash
docker run -d \
  --name ebook2audio-flower \
  -p 5555:5555 \
  -e CELERY_BROKER_URL=redis://172.17.0.1:6379/0 \
  -e CELERY_RESULT_BACKEND=redis://172.17.0.1:6379/0 \
  mher/flower:2.0
```

**Ouvre Flower** : http://localhost:5555
- Tu devrais voir ton worker connecté !

#### Étape 5 : Tester une conversion

```bash
# Copier un ebook de test dans le container
docker cp test.epub ebook2audio-worker-1:/tmp/test.epub

# Lancer conversion en mode distribué
docker run --rm \
  --network host \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/test.epub:/app/input/test.epub \
  ebook2audiobook:latest \
  python app.py --headless \
    --distributed \
    --num_workers 1 \
    --redis_url redis://localhost:6379/0 \
    --ebook /app/input/test.epub \
    --language eng
```

**Regarde dans Flower** pendant la conversion !
- Tasks en cours
- Progression en temps réel

#### Étape 6 : Vérifier le résultat

```bash
ls output/
# Tu devrais voir: test.mp3 ou test_audiobook.mp3
```

✅ **Ça marche ?** → Passe au multi-machines !

---

### Option B : Déploiement Multi-Machines - Production

#### Architecture exemple :
- **Machine 1** (192.168.1.10) : Coordinator + Redis + Flower
- **Machine 2** (192.168.1.11) : Worker GPU
- **Machine 3** (192.168.1.12) : Worker GPU

---

### 🖥️ MACHINE 1 : Coordinator (192.168.1.10)

#### Étape 1 : Cloner le repo

```bash
git clone https://github.com/DrewThomasson/ebook2audiobook.git
cd ebook2audiobook
git checkout claude/distributed-parallelism-mode-011CUsL6fxY6ugbvLQN1LXBw
```

#### Étape 2 : Build l'image coordinator

```bash
docker build -t ebook2audiobook:latest .
```

#### Étape 3 : Démarrer les services

```bash
# Méthode 1 : Script automatique (recommandé)
chmod +x scripts/distributed/start-coordinator.sh
./scripts/distributed/start-coordinator.sh

# Méthode 2 : Manuel
docker run -d --name ebook2audio-redis -p 6379:6379 redis:7-alpine

docker run -d \
  --name ebook2audio-flower \
  -p 5555:5555 \
  -e CELERY_BROKER_URL=redis://localhost:6379/0 \
  -e CELERY_RESULT_BACKEND=redis://localhost:6379/0 \
  mher/flower:2.0

docker run -d \
  --name ebook2audio-coordinator \
  -p 7860:7860 \
  -v $(pwd)/input:/app/input \
  -v $(pwd)/output:/app/output \
  -e REDIS_URL=redis://localhost:6379/0 \
  ebook2audiobook:latest
```

#### Étape 4 : Vérifier que tout tourne

```bash
docker ps
# Tu devrais voir 3 containers:
# - ebook2audio-redis
# - ebook2audio-flower
# - ebook2audio-coordinator (optionnel si tu utilises CLI)

# Tester Redis
docker exec ebook2audio-redis redis-cli ping
# Réponse: PONG

# Accéder à Flower
open http://192.168.1.10:5555
```

#### Étape 5 : Configurer le firewall

```bash
# Autoriser Redis (port 6379) pour les workers
sudo ufw allow 6379/tcp

# Autoriser Flower (optionnel)
sudo ufw allow 5555/tcp

# Autoriser Gradio UI (optionnel)
sudo ufw allow 7860/tcp
```

---

### 🖥️ MACHINE 2 : Worker 1 (192.168.1.11)

#### Étape 1 : Cloner et build

```bash
git clone https://github.com/DrewThomasson/ebook2audiobook.git
cd ebook2audiobook
git checkout claude/distributed-parallelism-mode-011CUsL6fxY6ugbvLQN1LXBw

# Build worker image
chmod +x scripts/distributed/build-worker-image.sh
./scripts/distributed/build-worker-image.sh
```

**Ou si tu as déjà l'image sur le coordinator** :

```bash
# Sur coordinator (192.168.1.10)
docker save ebook2audiobook-worker:latest | gzip > worker.tar.gz
scp worker.tar.gz user@192.168.1.11:/tmp/

# Sur worker (192.168.1.11)
docker load < /tmp/worker.tar.gz
```

#### Étape 2 : Démarrer le worker

```bash
# Méthode 1 : Script automatique (recommandé)
chmod +x scripts/distributed/start-worker.sh
COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh

# Méthode 2 : Manuel
docker run -d \
  --name ebook2audio-worker-gpu0 \
  --gpus device=0 \
  --restart unless-stopped \
  -e REDIS_URL=redis://192.168.1.10:6379/0 \
  -e WORKER_ID=worker_machine2_gpu0 \
  -e CUDA_VISIBLE_DEVICES=0 \
  ebook2audiobook-worker:latest
```

#### Étape 3 : Vérifier que le worker est connecté

```bash
# Voir les logs du worker
docker logs -f ebook2audio-worker-gpu0

# Tu devrais voir:
# "Loading TTS model... (device: cuda, GPU available: True)"
# "celery@worker_machine2_gpu0 ready."

# Vérifier dans Flower (depuis ton navigateur)
open http://192.168.1.10:5555
# Le worker "worker_machine2_gpu0" doit apparaître !
```

---

### 🖥️ MACHINE 3 : Worker 2 (192.168.1.12)

**Répète exactement les mêmes étapes que Machine 2** !

```bash
# Cloner, build ou charger l'image
git clone ...
cd ebook2audiobook
./scripts/distributed/build-worker-image.sh

# Démarrer worker
COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh

# Ou manuel
docker run -d \
  --name ebook2audio-worker-gpu0 \
  --gpus device=0 \
  -e REDIS_URL=redis://192.168.1.10:6379/0 \
  -e WORKER_ID=worker_machine3_gpu0 \
  -e CUDA_VISIBLE_DEVICES=0 \
  ebook2audiobook-worker:latest
```

---

## 🎵 Lancer une Conversion Distribuée

### Depuis le Coordinator (192.168.1.10)

#### Méthode 1 : Via l'interface web Gradio

```bash
# Si tu as démarré le coordinator avec l'interface
open http://192.168.1.10:7860

# Upload ton ebook
# Sélectionne les options
# Clique "Convert"
```

#### Méthode 2 : Via CLI (recommandé)

```bash
# Sur le coordinator, copier un ebook
cd /path/to/ebook2audiobook
cp mon_livre.epub input/

# Lancer conversion
docker run --rm \
  --network host \
  -v $(pwd)/input:/app/input \
  -v $(pwd)/output:/app/output \
  ebook2audiobook:latest \
  python app.py --headless \
    --distributed \
    --num_workers 2 \
    --redis_url redis://localhost:6379/0 \
    --ebook /app/input/mon_livre.epub \
    --language eng \
    --voice jenny
```

**Ou si le coordinator tourne déjà** :

```bash
docker exec -it ebook2audio-coordinator python app.py --headless \
  --distributed \
  --num_workers 2 \
  --redis_url redis://localhost:6379/0 \
  --ebook /app/input/mon_livre.epub \
  --language eng
```

---

## 📊 Monitoring Pendant la Conversion

### Flower Dashboard

Ouvre http://192.168.1.10:5555

**Tu verras** :
- Nombre de workers actifs (2 dans notre exemple)
- Tasks en cours (processing chapters)
- Tasks complétées
- Durée de chaque task
- Graphiques en temps réel

### Logs Workers

```bash
# Sur Machine 2
docker logs -f ebook2audio-worker-gpu0

# Sur Machine 3
docker logs -f ebook2audio-worker-gpu0
```

Tu verras :
```
[Worker worker_machine2_gpu0] Processing chapter 0 (25 sentences)
Loading TTS model: xtts_jenny_cuda (device: cuda, GPU available: True)
Chapter 0 completed in 45.3s (duration: 180.2s)
```

### Logs Coordinator

```bash
# Sur Machine 1
docker logs -f ebook2audio-coordinator
```

Tu verras :
```
Distributed 30 chapters to workers
Waiting for all chapters to complete...
Chapter 0 received (4.5 MB, 180.2s)
Chapter 1 received (5.2 MB, 195.8s)
...
All 30 chapters completed successfully
Combining 30 audio files...
Final audiobook created at /app/output/mon_livre.mp3
```

---

## 🧪 Tests Rapides

### Test 1 : Vérifier Redis

```bash
# Depuis n'importe quelle machine
redis-cli -h 192.168.1.10 ping
# Réponse: PONG
```

### Test 2 : Health Check Workers

```bash
# Installer celery (sur coordinator ou ta machine)
pip install celery[redis]

# Vérifier workers
celery -A lib.distributed.celery_app inspect stats \
  -b redis://192.168.1.10:6379/0

# Ou via Python
python -c "
from celery import Celery
app = Celery(broker='redis://192.168.1.10:6379/0')
print(app.control.inspect().stats())
"
```

### Test 3 : Conversion Mini

```bash
# Créer un fichier texte de test
echo "This is a test sentence for TTS conversion." > test.txt

# Convertir
docker exec -it ebook2audio-coordinator python app.py --headless \
  --distributed \
  --num_workers 2 \
  --ebook /app/input/test.txt \
  --language eng
```

---

## 🔧 Troubleshooting

### Worker ne se connecte pas

**Symptôme** : Le worker n'apparaît pas dans Flower

**Solutions** :
```bash
# 1. Tester connectivité Redis
redis-cli -h 192.168.1.10 ping

# 2. Vérifier firewall coordinator
sudo ufw status
sudo ufw allow 6379/tcp

# 3. Voir les logs worker
docker logs ebook2audio-worker-gpu0
# Cherche les erreurs de connexion

# 4. Vérifier l'URL Redis
docker inspect ebook2audio-worker-gpu0 | grep REDIS_URL
```

### GPU non détecté

**Symptôme** : Logs montrent "device: cpu"

**Solutions** :
```bash
# 1. Vérifier nvidia-smi
nvidia-smi

# 2. Vérifier Docker GPU support
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi

# 3. Rebuild avec bon TORCH_VERSION
TORCH_VERSION=cuda124 ./scripts/distributed/build-worker-image.sh

# 4. Vérifier PyTorch dans container
docker exec ebook2audio-worker-gpu0 python -c "import torch; print(torch.cuda.is_available())"
```

### Conversion échoue

**Solutions** :
```bash
# 1. Voir logs coordinator
docker logs ebook2audio-coordinator

# 2. Voir tâches échouées dans Flower
open http://192.168.1.10:5555

# 3. Vérifier checkpoint Redis
redis-cli -h 192.168.1.10
> KEYS checkpoint:*
> HGETALL checkpoint:votre_session_id
```

---

## 🎯 Commandes Utiles

### Arrêter tout

```bash
# Sur Coordinator
docker stop ebook2audio-redis ebook2audio-flower ebook2audio-coordinator
docker rm ebook2audio-redis ebook2audio-flower ebook2audio-coordinator

# Sur chaque Worker
docker stop ebook2audio-worker-gpu0
docker rm ebook2audio-worker-gpu0
```

### Restart Worker

```bash
docker restart ebook2audio-worker-gpu0

# Ou rebuild et restart
docker stop ebook2audio-worker-gpu0
docker rm ebook2audio-worker-gpu0
COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh
```

### Voir utilisation GPU

```bash
# Sur machine worker
watch -n 1 nvidia-smi

# Pendant conversion, tu verras GPU usage ~90-100%
```

### Nettoyer Redis

```bash
# Supprimer tous les checkpoints
redis-cli -h 192.168.1.10 FLUSHDB

# Supprimer un checkpoint spécifique
redis-cli -h 192.168.1.10 DEL checkpoint:votre_session_id
```

---

## 🚀 Optimisations

### Multi-GPU sur une Machine

```bash
# Worker 1 sur GPU 0
docker run -d --name worker-gpu0 --gpus device=0 \
  -e REDIS_URL=redis://192.168.1.10:6379/0 \
  -e WORKER_ID=machine2_gpu0 \
  -e CUDA_VISIBLE_DEVICES=0 \
  ebook2audiobook-worker:latest

# Worker 2 sur GPU 1
docker run -d --name worker-gpu1 --gpus device=1 \
  -e REDIS_URL=redis://192.168.1.10:6379/0 \
  -e WORKER_ID=machine2_gpu1 \
  -e CUDA_VISIBLE_DEVICES=1 \
  ebook2audiobook-worker:latest
```

### Augmenter mémoire Redis

```bash
# Stop Redis
docker stop ebook2audio-redis

# Restart avec plus de mémoire
docker run -d \
  --name ebook2audio-redis \
  -p 6379:6379 \
  redis:7-alpine \
  redis-server --maxmemory 4gb --maxmemory-policy allkeys-lru
```

---

## ✅ Checklist Finale

**Coordinator prêt ?**
- [ ] Redis tourne (port 6379)
- [ ] Flower accessible (http://ip:5555)
- [ ] Firewall configuré (allow 6379)

**Workers prêts ?**
- [ ] Image worker built
- [ ] Worker connecté (visible dans Flower)
- [ ] GPU détecté (logs montrent "cuda")
- [ ] TTS model chargé (logs "TTS model loaded")

**Conversion OK ?**
- [ ] Fichier ebook dans /input
- [ ] Commande lancée avec --distributed
- [ ] Tasks visibles dans Flower
- [ ] Fichier final dans /output

🎉 **C'est parti !**
