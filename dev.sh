#!/bin/bash
# Quick development environment launcher

set -e

echo "🚀 eBook2Audiobook - Development Environment Launcher"
echo "======================================================="

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${YELLOW}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}❌ docker-compose is not installed.${NC}"
    exit 1
fi

# Display menu
echo ""
echo "Choose an option:"
echo "  1) 🏗️  Build dev container"
echo "  2) ▶️  Start dev container"
echo "  3) ⏹️  Stop dev container"
echo "  4) 🔄 Rebuild dev container (no cache)"
echo "  5) 🐚 Open shell in container"
echo "  6) 📋 View container logs"
echo "  7) 🧹 Clean up (stop and remove volumes)"
echo "  8) ✅ Run tests"
echo "  9) 🎨 Format code"
echo "  10) 🔍 Run linters"
echo "  0) ❌ Exit"
echo ""

read -p "Enter your choice [0-10]: " choice

case $choice in
    1)
        echo -e "${BLUE}🏗️  Building dev container...${NC}"
        docker-compose -f docker-compose.dev.yml build
        echo -e "${GREEN}✅ Build complete!${NC}"
        ;;
    2)
        echo -e "${BLUE}▶️  Starting dev container...${NC}"
        docker-compose -f docker-compose.dev.yml up -d
        echo -e "${GREEN}✅ Container started!${NC}"
        echo ""
        echo "Access the container with: docker-compose -f docker-compose.dev.yml exec dev zsh"
        echo "Or use VSCode Dev Containers extension"
        ;;
    3)
        echo -e "${BLUE}⏹️  Stopping dev container...${NC}"
        docker-compose -f docker-compose.dev.yml down
        echo -e "${GREEN}✅ Container stopped!${NC}"
        ;;
    4)
        echo -e "${BLUE}🔄 Rebuilding dev container (no cache)...${NC}"
        docker-compose -f docker-compose.dev.yml build --no-cache
        echo -e "${GREEN}✅ Rebuild complete!${NC}"
        ;;
    5)
        echo -e "${BLUE}🐚 Opening shell in container...${NC}"
        docker-compose -f docker-compose.dev.yml exec dev zsh
        ;;
    6)
        echo -e "${BLUE}📋 Viewing container logs...${NC}"
        docker-compose -f docker-compose.dev.yml logs -f
        ;;
    7)
        echo -e "${YELLOW}🧹 Cleaning up...${NC}"
        read -p "This will remove all containers and volumes. Continue? [y/N]: " confirm
        if [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]]; then
            docker-compose -f docker-compose.dev.yml down -v
            echo -e "${GREEN}✅ Cleanup complete!${NC}"
        else
            echo "Cancelled."
        fi
        ;;
    8)
        echo -e "${BLUE}✅ Running tests...${NC}"
        docker-compose -f docker-compose.dev.yml exec dev pytest
        ;;
    9)
        echo -e "${BLUE}🎨 Formatting code...${NC}"
        docker-compose -f docker-compose.dev.yml exec dev black .
        docker-compose -f docker-compose.dev.yml exec dev isort .
        echo -e "${GREEN}✅ Code formatted!${NC}"
        ;;
    10)
        echo -e "${BLUE}🔍 Running linters...${NC}"
        docker-compose -f docker-compose.dev.yml exec dev flake8 .
        docker-compose -f docker-compose.dev.yml exec dev mypy .
        echo -e "${GREEN}✅ Linting complete!${NC}"
        ;;
    0)
        echo "Goodbye! 👋"
        exit 0
        ;;
    *)
        echo -e "${YELLOW}❌ Invalid choice. Please try again.${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}Done!${NC}"
