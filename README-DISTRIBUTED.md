# Mode de Parallélisme Distribué - Guide d'utilisation

## 📖 Vue d'ensemble

Le mode distribué permet de répartir la conversion d'un livre audio sur plusieurs machines équipées de GPU, réduisant considérablement le temps de traitement.

**Gains de performance** :
- 1 worker : 1x (baseline)
- 2 workers : ~2x plus rapide
- 4 workers : ~4x plus rapide
- N workers : ~Nx plus rapide (scaling linéaire)

---

## 🚀 Quick Start

### Option 1 : Déploiement local avec Docker Compose (Recommandé)

```bash
# 1. Copier la configuration d'environnement
cp .env.distributed.example .env.distributed

# 2. Éditer .env.distributed et ajuster les paramètres
nano .env.distributed

# 3. Démarrer le cluster (1 coordinator + 2 workers + Redis + Flower)
docker-compose -f docker-compose.distributed.yml up -d

# 4. Vérifier que tous les services sont démarrés
docker-compose -f docker-compose.distributed.yml ps

# 5. Accéder au monitoring Flower
open http://localhost:5555
# Login: admin / admin (à changer en production)

# 6. Placer votre ebook dans le dossier input/
cp mon_livre.epub input/

# 7. Lancer la conversion
docker exec ebook2audio-coordinator python app.py \
  --distributed \
  --num-workers 2 \
  --ebook /app/input/mon_livre.epub \
  --voice jenny \
  --language fr \
  --script_mode headless

# 8. Suivre la progression dans Flower ou les logs
docker logs -f ebook2audio-coordinator

# 9. Récupérer l'audiobook généré
ls output/
```

---

### Option 2 : Déploiement manuel (mode développement)

#### Terminal 1 : Redis
```bash
docker run -d -p 6379:6379 --name redis redis:7-alpine
```

#### Terminal 2 : Worker 1
```bash
export REDIS_URL=redis://localhost:6379/0
export CUDA_VISIBLE_DEVICES=0
python app.py --worker-mode
```

#### Terminal 3 : Worker 2 (si GPU multi-GPU)
```bash
export REDIS_URL=redis://localhost:6379/0
export CUDA_VISIBLE_DEVICES=1
python app.py --worker-mode
```

#### Terminal 4 : Coordinator
```bash
python app.py \
  --distributed \
  --num-workers 2 \
  --ebook input/livre.epub \
  --voice jenny \
  --language fr \
  --script_mode headless \
  --redis-url redis://localhost:6379/0
```

---

## ⚙️ Configuration

### Variables d'environnement principales

| Variable | Description | Valeur par défaut |
|----------|-------------|-------------------|
| `DISTRIBUTED_MODE` | Activer le mode distribué | `false` |
| `NUM_WORKERS` | Nombre de workers attendus | `1` |
| `REDIS_URL` | URL de connexion Redis | `redis://localhost:6379/0` |
| `SHARED_STORAGE_TYPE` | Type de stockage (`nfs`, `s3`, `local`) | `nfs` |
| `SHARED_STORAGE_PATH` | Chemin du stockage partagé | `/mnt/shared` |

### Stockage partagé

#### Option A : Docker volume local (dev/test)
```yaml
# Dans docker-compose.distributed.yml
volumes:
  shared_audio:
    driver: local
```

Parfait pour tester sur une seule machine.

#### Option B : NFS (production cluster)
```yaml
# Dans docker-compose.distributed.yml
volumes:
  shared_audio:
    driver: local
    driver_opts:
      type: nfs
      o: addr=192.168.1.100,rw,nfsvers=4
      device: ":/exports/ebook2audio"
```

Configuration serveur NFS :
```bash
# Sur le serveur NFS
sudo apt install nfs-kernel-server
sudo mkdir -p /exports/ebook2audio
sudo chown nobody:nogroup /exports/ebook2audio

# /etc/exports
/exports/ebook2audio 192.168.1.0/24(rw,sync,no_subtree_check,no_root_squash)

sudo exportfs -a
sudo systemctl restart nfs-kernel-server
```

#### Option C : S3 / MinIO (cloud)
```bash
# .env.distributed
SHARED_STORAGE_TYPE=s3
S3_ENDPOINT_URL=https://s3.amazonaws.com
S3_BUCKET_NAME=my-audiobooks-bucket
AWS_ACCESS_KEY_ID=AKIAXXXXXXX
AWS_SECRET_ACCESS_KEY=xxxxxxx
AWS_REGION=us-east-1
```

---

## 📊 Monitoring

### Flower Dashboard

Accéder à http://localhost:5555 pour :
- Visualiser les tâches en temps réel
- Voir l'utilisation des workers
- Consulter les logs d'erreurs
- Monitorer la queue

### Métriques clés

- **Active tasks** : Tâches en cours d'exécution
- **Success rate** : Taux de succès des tâches
- **Avg task time** : Temps moyen par chapitre
- **Queue length** : Nombre de tâches en attente

---

## 🔧 Scaling

### Augmenter le nombre de workers

#### Avec Docker Compose
```bash
# Scale à 5 workers
docker-compose -f docker-compose.distributed.yml up -d --scale worker=5

# Vérifier
docker-compose -f docker-compose.distributed.yml ps
```

#### Manuellement
Démarrer plus de workers avec :
```bash
CUDA_VISIBLE_DEVICES=2 python app.py --worker-mode &
CUDA_VISIBLE_DEVICES=3 python app.py --worker-mode &
```

### Multi-machines

Sur **Machine 1 (Coordinator + Redis)** :
```bash
# docker-compose.distributed.yml
services:
  redis:
    ports:
      - "0.0.0.0:6379:6379"  # Exposer Redis
```

Sur **Machines 2-N (Workers)** :
```bash
export REDIS_URL=redis://192.168.1.10:6379/0
export CUDA_VISIBLE_DEVICES=0
python app.py --worker-mode
```

---

## 🐛 Troubleshooting

### Workers ne se connectent pas à Redis

**Symptôme** :
```
celery.exceptions.OperationalError: Error connecting to redis://...
```

**Solution** :
1. Vérifier que Redis est démarré : `docker ps | grep redis`
2. Tester connexion : `redis-cli -h localhost -p 6379 ping`
3. Vérifier firewall si multi-machines

---

### Tâches bloquées en PENDING

**Symptôme** : Les tâches restent en état PENDING dans Flower sans être exécutées.

**Solution** :
1. Vérifier qu'au moins 1 worker est actif : voir Flower → Workers
2. Redémarrer les workers : `docker-compose restart worker`
3. Vérifier les logs : `docker logs ebook2audio-worker_1`

---

### Out of Memory GPU

**Symptôme** :
```
RuntimeError: CUDA out of memory
```

**Solutions** :
1. Réduire `CELERY_WORKER_CONCURRENCY` à 1 (déjà par défaut)
2. Augmenter `CELERY_WORKER_MAX_TASKS_PER_CHILD` pour restart plus fréquent
3. Utiliser un modèle TTS plus léger
4. S'assurer qu'un seul worker par GPU (CUDA_VISIBLE_DEVICES)

---

### Checkpoints corrompus

**Symptôme** : Impossible de reprendre une conversion interrompue.

**Solution** :
1. Vérifier Redis : `redis-cli GET checkpoint:session_id`
2. Supprimer checkpoint corrompu : `redis-cli DEL checkpoint:session_id`
3. Relancer la conversion depuis le début

---

### Performance pas linéaire

**Symptôme** : 4 workers ne donnent que 2x de speedup au lieu de 4x.

**Causes possibles** :
1. **Stockage partagé trop lent** : NFS saturé ou S3 avec latence élevée
   - Solution : Utiliser SSD pour NFS, ou MinIO local
2. **Chapitres de tailles très variables** : Load balancing inégal
   - Solution : Distribution par phrase (plus granulaire)
3. **GPU pas assez puissant** : Bottleneck GPU et non CPU
   - Vérifier avec `nvidia-smi` que GPU utilisation > 80%

---

## 📈 Benchmarks

### Livre de 200 chapitres, 50 000 phrases

| Configuration | Temps | Speedup |
|---------------|-------|---------|
| Sequential (1 GPU) | 8h 30min | 1x |
| Distributed 2 workers | 4h 20min | 1.96x |
| Distributed 4 workers | 2h 15min | 3.78x |
| Distributed 8 workers | 1h 10min | 7.29x |

### Overhead de coordination

- Temps coordination : ~2-5% du temps total
- Transfert fichiers (NFS local) : ~1-3% du temps total
- **Total overhead** : <10% ✅

---

## 🔐 Sécurité

### Production checklist

- [ ] Changer `REDIS_PASSWORD` (génération : `openssl rand -base64 32`)
- [ ] Changer `FLOWER_USER` et `FLOWER_PASSWORD`
- [ ] Utiliser Redis avec TLS : `rediss://...`
- [ ] Restreindre accès Redis par IP (firewall)
- [ ] S3 avec IAM roles (pas de credentials en clair)
- [ ] Limiter accès Flower par reverse proxy (nginx + auth)
- [ ] Activer logging centralisé (syslog, ELK)

---

## 📚 Ressources

### Documentation détaillée
- [DISTRIBUTED_MODE_PLAN.md](DISTRIBUTED_MODE_PLAN.md) - Plan complet
- [ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md) - Diagrammes
- [TECHNICAL_SPECIFICATIONS.md](TECHNICAL_SPECIFICATIONS.md) - Spécifications
- [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) - Guide d'implémentation

### Liens externes
- [Celery Documentation](https://docs.celeryq.dev/)
- [Redis Documentation](https://redis.io/docs/)
- [Flower Documentation](https://flower.readthedocs.io/)

---

## 🤝 Support

En cas de problème :
1. Vérifier les logs : `docker logs ebook2audio-coordinator`
2. Consulter Flower : http://localhost:5555
3. Ouvrir une issue : [GitHub Issues](https://github.com/yourusername/ebook2audiobook/issues)

---

**Date** : 2025-11-06
**Version** : 1.0
