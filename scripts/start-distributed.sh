#!/bin/bash
# Script de démarrage rapide pour le mode distribué ebook2audiobook

set -e  # Exit on error

# Couleurs pour output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  ebook2audiobook - Mode Distribué${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Vérifier que docker et docker-compose sont installés
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker n'est pas installé${NC}"
    echo "Installer Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose n'est pas installé${NC}"
    echo "Installer Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}✓ Docker et Docker Compose détectés${NC}"

# Vérifier GPU (optionnel)
if command -v nvidia-smi &> /dev/null; then
    NUM_GPUS=$(nvidia-smi -L | wc -l)
    echo -e "${GREEN}✓ $NUM_GPUS GPU(s) détecté(s)${NC}"
    nvidia-smi -L
else
    echo -e "${YELLOW}⚠ Aucun GPU NVIDIA détecté (mode CPU sera utilisé)${NC}"
    NUM_GPUS=0
fi

echo ""

# Vérifier fichier .env.distributed
if [ ! -f ".env.distributed" ]; then
    echo -e "${YELLOW}⚠ Fichier .env.distributed non trouvé${NC}"
    echo "Copie depuis .env.distributed.example..."
    cp .env.distributed.example .env.distributed
    echo -e "${GREEN}✓ .env.distributed créé${NC}"
    echo -e "${YELLOW}Veuillez éditer .env.distributed et relancer le script${NC}"
    exit 0
fi

# Charger variables d'environnement
source .env.distributed

# Demander nombre de workers
if [ -z "$NUM_WORKERS" ] || [ "$NUM_WORKERS" -eq 0 ]; then
    if [ "$NUM_GPUS" -gt 0 ]; then
        DEFAULT_WORKERS=$NUM_GPUS
    else
        DEFAULT_WORKERS=2
    fi

    read -p "Nombre de workers à démarrer [$DEFAULT_WORKERS]: " WORKER_COUNT
    WORKER_COUNT=${WORKER_COUNT:-$DEFAULT_WORKERS}
else
    WORKER_COUNT=$NUM_WORKERS
fi

export NUM_WORKERS=$WORKER_COUNT

echo ""
echo -e "${GREEN}Configuration:${NC}"
echo "  - Workers: $WORKER_COUNT"
echo "  - Storage: $SHARED_STORAGE_TYPE"
echo "  - Redis: ${REDIS_URL:-redis://localhost:6379/0}"
echo ""

# Demander confirmation
read -p "Démarrer le cluster avec cette configuration? [Y/n] " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]] && [[ ! -z $REPLY ]]; then
    echo "Annulé."
    exit 0
fi

echo ""
echo -e "${GREEN}🚀 Démarrage du cluster...${NC}"

# Arrêter cluster existant si présent
if docker-compose -f docker-compose.distributed.yml ps | grep -q "Up"; then
    echo "Arrêt du cluster existant..."
    docker-compose -f docker-compose.distributed.yml down
fi

# Démarrer Redis d'abord
echo ""
echo "1️⃣  Démarrage Redis..."
docker-compose -f docker-compose.distributed.yml up -d redis

# Attendre Redis
echo "   Attente de Redis..."
sleep 5
if docker exec ebook2audio-redis redis-cli ping | grep -q "PONG"; then
    echo -e "   ${GREEN}✓ Redis prêt${NC}"
else
    echo -e "   ${RED}✗ Redis ne répond pas${NC}"
    exit 1
fi

# Démarrer Flower
echo ""
echo "2️⃣  Démarrage Flower (monitoring)..."
docker-compose -f docker-compose.distributed.yml up -d flower
sleep 3
echo -e "   ${GREEN}✓ Flower accessible sur http://localhost:5555${NC}"

# Démarrer workers
echo ""
echo "3️⃣  Démarrage des workers ($WORKER_COUNT workers)..."
docker-compose -f docker-compose.distributed.yml up -d --scale worker=$WORKER_COUNT worker

# Attendre que workers se connectent
echo "   Attente de la connexion des workers..."
sleep 10

# Vérifier workers via Flower API
ACTIVE_WORKERS=$(docker exec ebook2audio-redis redis-cli KEYS "celery-task-meta-*" | wc -l || echo "0")
echo -e "   ${GREEN}✓ Workers démarrés${NC}"

# Démarrer coordinator
echo ""
echo "4️⃣  Démarrage Coordinator..."
docker-compose -f docker-compose.distributed.yml up -d coordinator
sleep 5
echo -e "   ${GREEN}✓ Coordinator démarré${NC}"

# Vérifier statut
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Cluster démarré avec succès! 🎉${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Afficher statut des services
docker-compose -f docker-compose.distributed.yml ps

echo ""
echo -e "${GREEN}📊 Monitoring:${NC}"
echo "  Flower Dashboard: http://localhost:5555"
echo "  Login: ${FLOWER_USER:-admin} / ${FLOWER_PASSWORD:-admin}"
echo ""

echo -e "${GREEN}🎵 Pour lancer une conversion:${NC}"
echo ""
echo "  Option 1 - Via CLI:"
echo "  docker exec ebook2audio-coordinator python app.py \\"
echo "    --distributed \\"
echo "    --num-workers $WORKER_COUNT \\"
echo "    --ebook /app/input/mon_livre.epub \\"
echo "    --voice jenny \\"
echo "    --language fr \\"
echo "    --script_mode headless"
echo ""
echo "  Option 2 - Via Web UI:"
echo "  1. Accéder à http://localhost:7860"
echo "  2. Uploader votre ebook"
echo "  3. Configurer les options"
echo "  4. Lancer la conversion"
echo ""

echo -e "${GREEN}📋 Commandes utiles:${NC}"
echo ""
echo "  Voir les logs du coordinator:"
echo "  docker logs -f ebook2audio-coordinator"
echo ""
echo "  Voir les logs d'un worker:"
echo "  docker logs -f ebook2audiobook_worker_1"
echo ""
echo "  Arrêter le cluster:"
echo "  docker-compose -f docker-compose.distributed.yml down"
echo ""
echo "  Redémarrer un worker:"
echo "  docker-compose -f docker-compose.distributed.yml restart worker"
echo ""
echo "  Scale workers (ex: passer à 5):"
echo "  docker-compose -f docker-compose.distributed.yml up -d --scale worker=5 worker"
echo ""

echo -e "${YELLOW}💡 Astuce:${NC}"
echo "  Suivre la progression en temps réel dans Flower:"
echo "  http://localhost:5555/tasks"
echo ""

echo -e "${GREEN}✨ Bon audiobook! ✨${NC}"
