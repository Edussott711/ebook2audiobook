# Mode Distribué avec Docker Compose

Guide ultra-simple pour lancer le mode distribué avec Docker Compose uniquement.

## 🚀 Setup Complet sur UNE Machine

Tout en une commande (Redis + Flower + 2 Workers + Interface Web) :

```bash
docker-compose -f docker-compose.distributed.yml up --build -d
```

**Accès** :
- Interface Web : http://localhost:7860
- Monitoring Flower : http://localhost:5555 (admin/admin)

**Logs** :
```bash
# Tous les services
docker-compose -f docker-compose.distributed.yml logs -f

# Seulement les workers
docker-compose -f docker-compose.distributed.yml logs -f worker1 worker2
```

**Arrêter** :
```bash
docker-compose -f docker-compose.distributed.yml down
```

---

## 🌐 Setup Multi-Machines (Production)

### Machine 1 : Coordinator

```bash
# Lancer Redis + Flower + Interface Web
docker-compose -f docker-compose.coordinator.yml up --build -d

# Voir l'IP de cette machine
hostname -I
# Exemple: 192.168.1.10
```

**Firewall** (autoriser workers à se connecter) :
```bash
sudo ufw allow 6379/tcp  # Redis
```

### Machine 2+ : Workers

1. **Créer fichier `.env`** :
```bash
echo "COORDINATOR_IP=192.168.1.10" > .env
```

2. **Lancer workers** :
```bash
docker-compose -f docker-compose.worker.yml up --build -d
```

3. **Vérifier connexion dans Flower** :
   - Ouvrir http://192.168.1.10:5555
   - Les workers doivent apparaître !

---

## ⚙️ Configuration

### Une Seule GPU ?

Éditer `docker-compose.distributed.yml` ou `docker-compose.worker.yml` :

```yaml
# Worker 2 - Changer device_ids de ['1'] à ['0']
worker2:
  environment:
    - CUDA_VISIBLE_DEVICES=0  # <-- Changer 1 en 0
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            device_ids: ['0']  # <-- Changer ['1'] en ['0']
```

### Mode CPU ?

Éditer le worker :

```yaml
worker1:
  build:
    args:
      TORCH_VERSION: cpu  # <-- Changer cuda124 en cpu
  environment:
    - CUDA_VISIBLE_DEVICES=""  # <-- Vide pour forcer CPU
  # Supprimer la section deploy.resources
```

### Plus de 2 GPUs ?

Dupliquer le service `worker2` et renommer en `worker3`, `worker4`, etc. :

```yaml
worker3:
  build:
    context: .
    dockerfile: Dockerfile.worker
    args:
      TORCH_VERSION: cuda124
      SKIP_XTTS_TEST: "true"
  container_name: ebook2audio-worker-3
  environment:
    - REDIS_URL=redis://redis:6379/0
    - CUDA_VISIBLE_DEVICES=2  # <-- GPU 2
    - WORKER_ID=worker_3
  volumes:
    - ./models:/app/models
  depends_on:
    redis:
      condition: service_healthy
  networks:
    - ebook2audio-net
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            device_ids: ['2']  # <-- GPU 2
            capabilities: [gpu]
  restart: unless-stopped
```

---

## 🎵 Lancer une Conversion

### Via Interface Web (Gradio)

1. Ouvrir http://localhost:7860 (ou http://<coordinator-ip>:7860)
2. Upload ton ebook
3. Configurer les options
4. Cliquer "Convert"
5. Suivre la progression dans Flower : http://localhost:5555

### Via CLI (Mode Headless)

```bash
# Copier ebook dans input/
cp mon_livre.epub input/

# Lancer conversion
docker exec ebook2audio-coordinator python app.py --headless \
  --distributed \
  --num_workers 2 \
  --ebook /app/input/mon_livre.epub \
  --language eng

# Résultat dans output/
ls output/
```

---

## 📊 Monitoring

### Flower Dashboard

http://localhost:5555 (ou http://<coordinator-ip>:5555)

**Login** : admin / admin

Tu verras :
- Nombre de workers actifs
- Tasks en cours
- Tasks complétées
- Performance par worker
- Device type (cuda/cpu)

### Logs Workers

```bash
# Worker spécifique
docker logs -f ebook2audio-worker-1

# Tous les workers
docker-compose -f docker-compose.distributed.yml logs -f worker1 worker2
```

---

## 🔧 Commandes Utiles

### Rebuild après modification

```bash
docker-compose -f docker-compose.distributed.yml up --build -d
```

### Restart un worker

```bash
docker-compose -f docker-compose.distributed.yml restart worker1
```

### Voir les containers actifs

```bash
docker-compose -f docker-compose.distributed.yml ps
```

### Nettoyer tout

```bash
# Arrêter et supprimer containers + volumes
docker-compose -f docker-compose.distributed.yml down -v

# Supprimer aussi les images
docker-compose -f docker-compose.distributed.yml down -v --rmi all
```

---

## 🐛 Troubleshooting

### Workers n'apparaissent pas dans Flower

**Vérifier logs worker** :
```bash
docker logs ebook2audio-worker-1
```

**Vérifier connexion Redis** :
```bash
docker exec ebook2audio-redis redis-cli ping
# Doit répondre: PONG
```

**Sur worker distant, tester connexion** :
```bash
redis-cli -h <coordinator-ip> ping
```

### GPU non détecté

**Vérifier dans le container** :
```bash
docker exec ebook2audio-worker-1 nvidia-smi
```

**Vérifier logs** :
```bash
docker logs ebook2audio-worker-1 | grep "device:"
# Doit afficher: device: cuda
```

### Session Already Active

Si tu vois "Session is already active" :

1. **Fermer le navigateur complètement**
2. **Ou redémarrer le coordinator** :
   ```bash
   docker-compose -f docker-compose.distributed.yml restart coordinator
   ```

3. **Ou utiliser un nouveau navigateur / mode incognito**

---

## 📋 Fichiers Docker Compose

| Fichier | Usage |
|---------|-------|
| `docker-compose.distributed.yml` | **Setup complet sur 1 machine** |
| `docker-compose.coordinator.yml` | **Machine coordinator uniquement** |
| `docker-compose.worker.yml` | **Ajouter workers sur autres machines** |

---

## 🎯 Exemples Complets

### Exemple 1 : Test Local (1 Machine, 2 GPUs)

```bash
# Lancer tout
docker-compose -f docker-compose.distributed.yml up --build -d

# Attendre que les workers soient prêts (30s)
sleep 30

# Vérifier dans Flower
xdg-open http://localhost:5555

# Copier un ebook
cp test.epub input/

# Convertir
docker exec ebook2audio-coordinator python app.py --headless \
  --distributed --num_workers 2 \
  --ebook /app/input/test.epub --language eng

# Résultat
ls output/
```

### Exemple 2 : Production (1 Coordinator + 2 Machines Workers)

**Machine 1 (Coordinator - 192.168.1.10)** :
```bash
docker-compose -f docker-compose.coordinator.yml up --build -d
sudo ufw allow 6379/tcp
```

**Machine 2 (Worker - 2 GPUs)** :
```bash
echo "COORDINATOR_IP=192.168.1.10" > .env
docker-compose -f docker-compose.worker.yml up --build -d
```

**Machine 3 (Worker - 1 GPU)** :
```bash
echo "COORDINATOR_IP=192.168.1.10" > .env
# Éditer docker-compose.worker.yml : commenter worker2
docker-compose -f docker-compose.worker.yml up --build -d
```

**Vérifier** :
- Flower : http://192.168.1.10:5555
- 3 workers doivent apparaître !

**Convertir** (depuis machine 1) :
```bash
docker exec ebook2audio-coordinator python app.py --headless \
  --distributed --num_workers 3 \
  --ebook /app/input/livre.epub --language eng
```

---

## ✅ C'est Tout !

Pas de scripts bash complexes, juste Docker Compose ! 🎉

**Questions ?** Voir la documentation complète dans `docs/distributed/`
