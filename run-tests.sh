#!/bin/bash
# Script pour lancer pytest dans Docker
# Usage: ./run-tests.sh [options]
# Exemples:
#   ./run-tests.sh                    # Tous les tests
#   ./run-tests.sh test_audio         # Tests audio uniquement
#   ./run-tests.sh quick              # Quick smoke test
#   ./run-tests.sh coverage           # Avec rapport de couverture

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 Pytest Docker Runner${NC}"
echo ""

# Build l'image
echo -e "${YELLOW}📦 Building Docker image...${NC}"
docker build -t ebook2audiobook . -q
echo -e "${GREEN}✅ Build complete${NC}"
echo ""

# Créer le dossier reports
mkdir -p reports

# Déterminer quels tests lancer
MODE="${1:-all}"

case "$MODE" in
  "audio")
    echo -e "${BLUE}🎵 Running audio tests...${NC}"
    docker run --rm ebook2audiobook pytest tests/test_audio/ -v --tb=short
    ;;

  "text")
    echo -e "${BLUE}📝 Running text tests...${NC}"
    docker run --rm ebook2audiobook pytest tests/test_text/ -v --tb=short
    ;;

  "ebook")
    echo -e "${BLUE}📚 Running ebook tests...${NC}"
    docker run --rm ebook2audiobook pytest tests/test_ebook/ -v --tb=short
    ;;

  "file")
    echo -e "${BLUE}📁 Running file tests...${NC}"
    docker run --rm ebook2audiobook pytest tests/test_file/ -v --tb=short
    ;;

  "core")
    echo -e "${BLUE}⚙️  Running core tests...${NC}"
    docker run --rm ebook2audiobook pytest tests/test_core/ -v --tb=short
    ;;

  "quick")
    echo -e "${BLUE}⚡ Running quick smoke test...${NC}"
    docker run --rm ebook2audiobook pytest tests/ --maxfail=1 -x -v --tb=line
    ;;

  "coverage")
    echo -e "${BLUE}📊 Running tests with coverage...${NC}"
    docker run --rm \
      -v $(pwd)/reports:/app/reports \
      ebook2audiobook \
      pytest tests/ \
        -v \
        --cov=lib \
        --cov-report=term-missing \
        --cov-report=html:reports/coverage \
        --junitxml=reports/junit.xml \
        --tb=short

    echo ""
    echo -e "${GREEN}✅ Tests completed!${NC}"
    echo -e "${BLUE}📊 Coverage report: ${YELLOW}reports/coverage/index.html${NC}"
    echo -e "${BLUE}📝 JUnit report: ${YELLOW}reports/junit.xml${NC}"
    ;;

  "parallel")
    echo -e "${BLUE}⚡ Running tests in parallel...${NC}"
    docker run --rm ebook2audiobook pytest tests/ -n auto -v --tb=short
    ;;

  "debug")
    echo -e "${BLUE}🐛 Running tests in debug mode...${NC}"
    docker run --rm -it ebook2audiobook pytest tests/ -vv -s --tb=long --pdb
    ;;

  "failed")
    echo -e "${BLUE}🔁 Re-running failed tests...${NC}"
    docker run --rm ebook2audiobook pytest tests/ --lf -v --tb=short
    ;;

  "all"|*)
    echo -e "${BLUE}🚀 Running all tests...${NC}"
    docker run --rm \
      -v $(pwd)/reports:/app/reports \
      ebook2audiobook \
      pytest tests/ \
        -v \
        --tb=short \
        --maxfail=10
    ;;
esac

echo ""
echo -e "${GREEN}✨ Done!${NC}"
