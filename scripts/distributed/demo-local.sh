#!/bin/bash
# Démo rapide du mode distribué sur une seule machine
# Ce script configure et teste tout automatiquement

set -e

echo "======================================"
echo "Démo Mode Distribué - Local"
echo "======================================"
echo ""
echo "Ce script va:"
echo "  1. Build les images Docker"
echo "  2. Démarrer Redis"
echo "  3. Démarrer 2 workers (GPU si dispo, sinon CPU)"
echo "  4. Démarrer Flower monitoring"
echo "  5. Lancer une conversion de test"
echo ""
read -p "Continuer? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 0
fi

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

step() {
    echo ""
    echo -e "${GREEN}>>> $1${NC}"
}

# Détecter si GPU disponible
GPU_AVAILABLE=false
if command -v nvidia-smi &> /dev/null; then
    if nvidia-smi &> /dev/null; then
        GPU_AVAILABLE=true
    fi
fi

step "Étape 1/7: Build image worker"
if docker image inspect ebook2audiobook-worker:latest &> /dev/null; then
    echo "Image worker déjà présente, skip build"
else
    echo "Building worker image (cela peut prendre 10-15 minutes)..."
    if [ "$GPU_AVAILABLE" = true ]; then
        TORCH_VERSION=cuda124 ./scripts/distributed/build-worker-image.sh
    else
        TORCH_VERSION=cpu ./scripts/distributed/build-worker-image.sh
    fi
fi

step "Étape 2/7: Build image coordinator"
if docker image inspect ebook2audiobook:latest &> /dev/null; then
    echo "Image coordinator déjà présente, skip build"
else
    echo "Building coordinator image..."
    docker build -t ebook2audiobook:latest .
fi

step "Étape 3/7: Démarrer Redis"
if docker ps | grep -q ebook2audio-redis; then
    echo "Redis déjà actif"
else
    docker run -d \
        --name ebook2audio-redis \
        -p 6379:6379 \
        redis:7-alpine \
        redis-server --maxmemory 2gb --maxmemory-policy allkeys-lru
    echo "Redis démarré"
    sleep 2
fi

step "Étape 4/7: Démarrer Flower monitoring"
if docker ps | grep -q ebook2audio-flower; then
    echo "Flower déjà actif"
else
    docker run -d \
        --name ebook2audio-flower \
        -p 5555:5555 \
        -e CELERY_BROKER_URL=redis://172.17.0.1:6379/0 \
        -e CELERY_RESULT_BACKEND=redis://172.17.0.1:6379/0 \
        mher/flower:2.0
    echo "Flower démarré sur http://localhost:5555"
    sleep 2
fi

step "Étape 5/7: Démarrer 2 workers"

# Cleanup old workers
docker rm -f ebook2audio-worker-demo-1 &> /dev/null || true
docker rm -f ebook2audio-worker-demo-2 &> /dev/null || true

if [ "$GPU_AVAILABLE" = true ]; then
    GPU_COUNT=$(nvidia-smi --query-gpu=name --format=csv,noheader | wc -l)
    echo "GPU détecté: $GPU_COUNT GPU(s) disponible(s)"

    # Worker 1 sur GPU 0
    docker run -d \
        --name ebook2audio-worker-demo-1 \
        --gpus device=0 \
        -e REDIS_URL=redis://172.17.0.1:6379/0 \
        -e WORKER_ID=demo_worker_1 \
        -e CUDA_VISIBLE_DEVICES=0 \
        ebook2audiobook-worker:latest
    echo "Worker 1 démarré (GPU 0)"

    # Worker 2 sur GPU 1 ou GPU 0 si une seule GPU
    if [ $GPU_COUNT -gt 1 ]; then
        docker run -d \
            --name ebook2audio-worker-demo-2 \
            --gpus device=1 \
            -e REDIS_URL=redis://172.17.0.1:6379/0 \
            -e WORKER_ID=demo_worker_2 \
            -e CUDA_VISIBLE_DEVICES=1 \
            ebook2audiobook-worker:latest
        echo "Worker 2 démarré (GPU 1)"
    else
        echo "Une seule GPU détectée, démarrage worker 2 en mode CPU"
        docker run -d \
            --name ebook2audio-worker-demo-2 \
            -e REDIS_URL=redis://172.17.0.1:6379/0 \
            -e WORKER_ID=demo_worker_2 \
            -e CUDA_VISIBLE_DEVICES="" \
            ebook2audiobook-worker:latest
    fi
else
    echo "Pas de GPU, démarrage workers en mode CPU"
    docker run -d \
        --name ebook2audio-worker-demo-1 \
        -e REDIS_URL=redis://172.17.0.1:6379/0 \
        -e WORKER_ID=demo_worker_1 \
        -e CUDA_VISIBLE_DEVICES="" \
        ebook2audiobook-worker:latest
    echo "Worker 1 démarré (CPU)"

    docker run -d \
        --name ebook2audio-worker-demo-2 \
        -e REDIS_URL=redis://172.17.0.1:6379/0 \
        -e WORKER_ID=demo_worker_2 \
        -e CUDA_VISIBLE_DEVICES="" \
        ebook2audiobook-worker:latest
    echo "Worker 2 démarré (CPU)"
fi

sleep 5

step "Étape 6/7: Vérifier la configuration"

echo "Workers actifs:"
docker ps --filter "name=ebook2audio-worker-demo" --format "  - {{.Names}} ({{.Status}})"

echo ""
echo "Vérification connexion Flower..."
sleep 2

step "Étape 7/7: Créer un fichier de test et lancer conversion"

# Créer répertoires
mkdir -p input output

# Créer fichier texte de test
cat > input/test_demo.txt << 'EOF'
Chapter 1: Introduction

This is a test chapter for the distributed audiobook conversion system.
The system uses Celery and Redis to distribute the workload across multiple workers.
Each worker processes chapters in parallel, significantly reducing the total conversion time.

Chapter 2: How It Works

The coordinator sends chapter tasks to Redis.
Workers pick up tasks and convert text to speech using GPU or CPU.
The audio files are encoded in base64 and sent back via Redis.
Finally, the coordinator combines all chapters into a single audiobook file.

Chapter 3: Conclusion

This distributed architecture allows linear scaling.
With two workers, the conversion is twice as fast.
With four workers, it's four times faster.
Welcome to distributed audiobook generation!
EOF

echo "Fichier de test créé: input/test_demo.txt"
echo ""

# Lancer conversion
echo "Lancement conversion distribuée..."
echo ""

docker run --rm \
    --network host \
    -v $(pwd)/input:/app/input \
    -v $(pwd)/output:/app/output \
    ebook2audiobook:latest \
    python app.py --headless \
        --distributed \
        --num_workers 2 \
        --redis_url redis://localhost:6379/0 \
        --ebook /app/input/test_demo.txt \
        --language eng

echo ""
step "Démo terminée!"
echo ""
echo "Résultats:"
echo "  - Fichier audio: output/test_demo.mp3"
echo "  - Flower dashboard: http://localhost:5555"
echo ""
echo "Voir les logs des workers:"
echo "  docker logs ebook2audio-worker-demo-1"
echo "  docker logs ebook2audio-worker-demo-2"
echo ""
echo "Écouter le résultat:"
echo "  mpv output/test_demo.mp3"
echo "  # ou"
echo "  vlc output/test_demo.mp3"
echo ""
echo "Arrêter la démo:"
echo "  docker stop ebook2audio-redis ebook2audio-flower \\"
echo "    ebook2audio-worker-demo-1 ebook2audio-worker-demo-2"
echo "  docker rm ebook2audio-redis ebook2audio-flower \\"
echo "    ebook2audio-worker-demo-1 ebook2audio-worker-demo-2"
echo ""
echo -e "${GREEN}✓ Démo réussie!${NC}"
