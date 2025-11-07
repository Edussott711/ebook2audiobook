#!/bin/bash
# Script de démarrage rapide pour le mode client-serveur distribué

set -e  # Exit on error

# Couleurs pour output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

clear
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  ebook2audiobook - Mode Client-Serveur${NC}"
echo -e "${BLUE}========================================${NC}"
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
    echo -e "${GREEN}✓ $NUM_GPUS GPU(s) NVIDIA détecté(s)${NC}"
    nvidia-smi --query-gpu=index,name,memory.total --format=csv,noheader | nl
else
    echo -e "${YELLOW}⚠  Aucun GPU NVIDIA détecté (mode CPU sera utilisé)${NC}"
    NUM_GPUS=0
fi

echo ""

# Vérifier fichier .env
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠  Fichier .env non trouvé${NC}"
    if [ -f ".env.client-server.example" ]; then
        echo "Copie depuis .env.client-server.example..."
        cp .env.client-server.example .env
        echo -e "${GREEN}✓ .env créé${NC}"
    fi
fi

# Demander nombre de workers
if [ "$NUM_GPUS" -gt 0 ]; then
    DEFAULT_WORKERS=$NUM_GPUS
else
    DEFAULT_WORKERS=2
fi

echo -e "${BLUE}Configuration du cluster:${NC}"
read -p "Nombre de workers à démarrer [$DEFAULT_WORKERS]: " WORKER_COUNT
WORKER_COUNT=${WORKER_COUNT:-$DEFAULT_WORKERS}

# Générer la liste WORKER_NODES
WORKER_NODES=""
for i in $(seq 1 $WORKER_COUNT); do
    if [ $i -eq 1 ]; then
        WORKER_NODES="worker$i:8000"
    else
        WORKER_NODES="$WORKER_NODES,worker$i:8000"
    fi
done

export WORKER_NODES

echo ""
echo -e "${GREEN}Configuration finale:${NC}"
echo "  - Nombre de workers: $WORKER_COUNT"
echo "  - Worker nodes: $WORKER_NODES"
echo "  - Architecture: Client-Serveur (HTTP direct)"
echo ""

# Demander confirmation
read -p "Démarrer le cluster avec cette configuration? [Y/n] " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]] && [[ ! -z $REPLY ]]; then
    echo "Annulé."
    exit 0
fi

echo ""
echo -e "${GREEN}🚀 Démarrage du cluster client-serveur...${NC}"

# Arrêter cluster existant si présent
if docker-compose -f docker-compose.client-server.yml ps 2>/dev/null | grep -q "Up"; then
    echo "Arrêt du cluster existant..."
    docker-compose -f docker-compose.client-server.yml down
fi

# Construire les images si nécessaire
echo ""
echo -e "${BLUE}1️⃣  Construction des images Docker...${NC}"
docker-compose -f docker-compose.client-server.yml build --quiet

# Démarrer les workers d'abord
echo ""
echo -e "${BLUE}2️⃣  Démarrage des workers ($WORKER_COUNT workers)...${NC}"

# Créer un docker-compose temporaire avec le bon nombre de workers
TEMP_COMPOSE=$(mktemp)
cat docker-compose.client-server.yml > $TEMP_COMPOSE

# Démarrer les workers
for i in $(seq 1 $WORKER_COUNT); do
    echo "   Starting worker$i..."
    docker-compose -f $TEMP_COMPOSE up -d worker$i 2>/dev/null || echo "   worker$i already defined or skipped"
done

# Attendre que workers démarrent
echo "   Attente du démarrage des workers..."
sleep 10

# Vérifier santé des workers
echo "   Vérification de la santé des workers..."
HEALTHY_WORKERS=0
for i in $(seq 1 $WORKER_COUNT); do
    WORKER_NAME="ebook2audio-worker$i"
    if docker ps | grep -q $WORKER_NAME; then
        # Tenter health check
        HEALTH=$(docker exec $WORKER_NAME curl -s -f http://localhost:8000/health 2>/dev/null | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
        if [ "$HEALTH" = "healthy" ]; then
            echo -e "   ${GREEN}✓ worker$i is healthy${NC}"
            HEALTHY_WORKERS=$((HEALTHY_WORKERS + 1))
        else
            echo -e "   ${YELLOW}⚠  worker$i is starting...${NC}"
        fi
    else
        echo -e "   ${RED}✗ worker$i not running${NC}"
    fi
done

if [ $HEALTHY_WORKERS -eq 0 ]; then
    echo -e "${YELLOW}⚠  Aucun worker prêt pour l'instant (peut prendre 1-2 min pour charger les modèles)${NC}"
fi

# Démarrer le master
echo ""
echo -e "${BLUE}3️⃣  Démarrage du Master (Coordinator)...${NC}"
docker-compose -f $TEMP_COMPOSE up -d master
sleep 5

rm $TEMP_COMPOSE

# Vérifier statut final
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Cluster démarré avec succès! 🎉${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Afficher statut des services
docker-compose -f docker-compose.client-server.yml ps

echo ""
echo -e "${GREEN}📊 Services:${NC}"
echo "  Master:  http://localhost:7860 (Gradio UI)"
echo "  Workers:"
for i in $(seq 1 $WORKER_COUNT); do
    WORKER_IP=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' ebook2audio-worker$i 2>/dev/null || echo "N/A")
    echo "    - worker$i: $WORKER_IP:8000"
done

echo ""
echo -e "${GREEN}🎵 Pour lancer une conversion:${NC}"
echo ""
echo "  ${YELLOW}Option 1 - Via Web UI:${NC}"
echo "  1. Accéder à http://localhost:7860"
echo "  2. Uploader votre ebook"
echo "  3. Configurer les options"
echo "  4. Activer 'Mode distribué'"
echo "  5. Lancer la conversion"
echo ""
echo "  ${YELLOW}Option 2 - Via CLI:${NC}"
echo "  docker exec ebook2audio-master python app.py \\"
echo "    --distributed \\"
echo "    --ebook /app/input/mon_livre.epub \\"
echo "    --voice jenny \\"
echo "    --language fr \\"
echo "    --script_mode headless"
echo ""

echo -e "${GREEN}📋 Commandes utiles:${NC}"
echo ""
echo "  ${YELLOW}Voir les logs du master:${NC}"
echo "  docker logs -f ebook2audio-master"
echo ""
echo "  ${YELLOW}Voir les logs d'un worker:${NC}"
echo "  docker logs -f ebook2audio-worker1"
echo ""
echo "  ${YELLOW}Vérifier santé d'un worker:${NC}"
echo "  curl http://localhost:8001/health"
echo "  (Remplacer 8001 par le port du worker)"
echo ""
echo "  ${YELLOW}Arrêter le cluster:${NC}"
echo "  docker-compose -f docker-compose.client-server.yml down"
echo ""
echo "  ${YELLOW}Redémarrer un worker:${NC}"
echo "  docker-compose -f docker-compose.client-server.yml restart worker1"
echo ""
echo "  ${YELLOW}Voir le statut en temps réel:${NC}"
echo "  watch docker-compose -f docker-compose.client-server.yml ps"
echo ""

echo -e "${BLUE}💡 Astuces:${NC}"
echo "  • Les workers chargent le modèle TTS au démarrage (1-2 min)"
echo "  • Chaque worker traite un chapitre à la fois (isolation GPU)"
echo "  • Le master distribue automatiquement les chapitres (round-robin)"
echo "  • Les audios sont retournés directement via HTTP (pas de stockage partagé)"
echo ""

echo -e "${GREEN}✨ Cluster prêt! Bon audiobook! ✨${NC}"
