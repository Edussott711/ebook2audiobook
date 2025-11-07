#!/bin/bash
# Script de test pour vérifier la configuration du mode distribué
# Usage: ./scripts/distributed/test-setup.sh

set -e

echo "======================================"
echo "Test Configuration Mode Distribué"
echo "======================================"
echo ""

# Couleurs pour output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Fonction pour afficher succès
success() {
    echo -e "${GREEN}✓${NC} $1"
}

# Fonction pour afficher erreur
error() {
    echo -e "${RED}✗${NC} $1"
}

# Fonction pour afficher warning
warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

echo "1. Vérification Docker..."
if command -v docker &> /dev/null; then
    success "Docker installé ($(docker --version))"
else
    error "Docker n'est pas installé!"
    echo "  Installer Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

echo ""
echo "2. Vérification GPU (optionnel)..."
if command -v nvidia-smi &> /dev/null; then
    if nvidia-smi &> /dev/null; then
        GPU_COUNT=$(nvidia-smi --query-gpu=name --format=csv,noheader | wc -l)
        success "GPU détecté: $GPU_COUNT GPU(s)"
        nvidia-smi --query-gpu=index,name,memory.total --format=csv,noheader | while read line; do
            echo "    - GPU $line"
        done
    else
        warning "nvidia-smi trouvé mais ne fonctionne pas"
    fi
else
    warning "Pas de GPU NVIDIA détecté (workers tourneront en mode CPU)"
fi

echo ""
echo "3. Vérification Docker GPU support..."
if command -v nvidia-smi &> /dev/null; then
    if docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi &> /dev/null; then
        success "Docker GPU support OK"
    else
        error "Docker GPU support manquant"
        echo "  Installer nvidia-docker2: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
    fi
fi

echo ""
echo "4. Vérification images Docker..."

if docker image inspect ebook2audiobook-worker:latest &> /dev/null; then
    success "Image worker trouvée"
    SIZE=$(docker image inspect ebook2audiobook-worker:latest --format='{{.Size}}' | awk '{print $1/1024/1024/1024}')
    printf "    Taille: %.2f GB\n" $SIZE
else
    warning "Image worker pas encore construite"
    echo "  Build avec: ./scripts/distributed/build-worker-image.sh"
fi

if docker image inspect ebook2audiobook:latest &> /dev/null; then
    success "Image coordinator trouvée"
else
    warning "Image coordinator pas encore construite"
    echo "  Build avec: docker build -t ebook2audiobook:latest ."
fi

echo ""
echo "5. Vérification Redis..."

if docker ps | grep -q ebook2audio-redis; then
    success "Redis container tourne"

    # Test connexion
    if docker exec ebook2audio-redis redis-cli ping &> /dev/null; then
        success "Redis répond au ping"
    else
        error "Redis ne répond pas"
    fi
else
    warning "Redis container pas démarré"
    echo "  Démarrer avec: docker run -d --name ebook2audio-redis -p 6379:6379 redis:7-alpine"
fi

echo ""
echo "6. Vérification Workers actifs..."

WORKERS_RUNNING=$(docker ps --filter "name=ebook2audio-worker" --format "{{.Names}}" | wc -l)
if [ $WORKERS_RUNNING -gt 0 ]; then
    success "$WORKERS_RUNNING worker(s) actif(s):"
    docker ps --filter "name=ebook2audio-worker" --format "  - {{.Names}} ({{.Status}})"

    # Vérifier les logs d'un worker
    FIRST_WORKER=$(docker ps --filter "name=ebook2audio-worker" --format "{{.Names}}" | head -1)
    echo ""
    echo "  Dernières lignes de logs de $FIRST_WORKER:"
    docker logs --tail 5 $FIRST_WORKER 2>&1 | sed 's/^/    /'
else
    warning "Aucun worker actif"
    echo "  Démarrer avec: ./scripts/distributed/start-worker.sh"
fi

echo ""
echo "7. Vérification Flower (monitoring)..."

if docker ps | grep -q ebook2audio-flower; then
    success "Flower dashboard actif"

    # Obtenir l'IP
    if command -v hostname &> /dev/null; then
        IP=$(hostname -I | awk '{print $1}')
        echo "  Accès: http://$IP:5555"
    else
        echo "  Accès: http://localhost:5555"
    fi
else
    warning "Flower dashboard pas démarré"
    echo "  Démarrer avec: docker run -d --name ebook2audio-flower -p 5555:5555 \\"
    echo "    -e CELERY_BROKER_URL=redis://localhost:6379/0 mher/flower:2.0"
fi

echo ""
echo "8. Vérification Firewall (si serveur)..."

if command -v ufw &> /dev/null; then
    if sudo ufw status | grep -q "6379.*ALLOW"; then
        success "Firewall: Port 6379 (Redis) ouvert"
    else
        warning "Firewall: Port 6379 (Redis) possiblement fermé"
        echo "  Ouvrir avec: sudo ufw allow 6379/tcp"
    fi
else
    warning "UFW firewall non détecté (skip)"
fi

echo ""
echo "9. Test de connexion Redis (réseau)..."

# Détecter IP locale
if command -v hostname &> /dev/null; then
    LOCAL_IP=$(hostname -I | awk '{print $1}')
    echo "  IP locale détectée: $LOCAL_IP"

    if command -v redis-cli &> /dev/null; then
        if redis-cli -h $LOCAL_IP ping &> /dev/null; then
            success "Redis accessible sur le réseau ($LOCAL_IP)"
        else
            warning "Redis pas accessible sur $LOCAL_IP (normal si pas configuré)"
        fi
    else
        warning "redis-cli pas installé (skip test réseau)"
    fi
fi

echo ""
echo "======================================"
echo "Résumé"
echo "======================================"

# Compter les composants prêts
READY=0
TOTAL=5

docker --version &> /dev/null && ((READY++))
docker image inspect ebook2audiobook-worker:latest &> /dev/null && ((READY++))
docker ps | grep -q ebook2audio-redis && ((READY++))
[ $WORKERS_RUNNING -gt 0 ] && ((READY++))
docker ps | grep -q ebook2audio-flower && ((READY++))

echo "Composants prêts: $READY/$TOTAL"

if [ $READY -eq $TOTAL ]; then
    echo ""
    success "Système complètement configuré et prêt!"
    echo ""
    echo "Prochaines étapes:"
    echo "  1. Vérifier Flower: http://localhost:5555"
    echo "  2. Lancer une conversion de test:"
    echo "     docker exec ebook2audio-coordinator python app.py --headless \\"
    echo "       --distributed --num_workers $WORKERS_RUNNING \\"
    echo "       --ebook /app/input/test.epub --language eng"
elif [ $READY -ge 3 ]; then
    echo ""
    warning "Système partiellement configuré"
    echo ""
    echo "Pour compléter l'installation:"
    [ ! $(docker image inspect ebook2audiobook-worker:latest &> /dev/null) ] && echo "  - Build image worker: ./scripts/distributed/build-worker-image.sh"
    [ ! $(docker ps | grep -q ebook2audio-redis) ] && echo "  - Démarrer Redis: docker run -d --name ebook2audio-redis -p 6379:6379 redis:7-alpine"
    [ $WORKERS_RUNNING -eq 0 ] && echo "  - Démarrer workers: ./scripts/distributed/start-worker.sh"
    [ ! $(docker ps | grep -q ebook2audio-flower) ] && echo "  - Démarrer Flower (optionnel): voir guide"
else
    echo ""
    error "Configuration incomplète"
    echo ""
    echo "Suivre le guide: GUIDE_DEMARRAGE_RAPIDE.md"
fi

echo ""
echo "Pour plus d'aide:"
echo "  - Guide complet: cat GUIDE_DEMARRAGE_RAPIDE.md"
echo "  - Documentation: docs/distributed/"
echo ""
