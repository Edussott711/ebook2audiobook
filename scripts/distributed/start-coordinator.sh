#!/bin/bash
# Start the coordinator with Redis and Flower monitoring
# This script should be run on the coordinator/master machine

set -e

# Configuration
REDIS_PASSWORD="${REDIS_PASSWORD:-}"
NUM_WORKERS="${NUM_WORKERS:-2}"
COORDINATOR_PORT="${COORDINATOR_PORT:-7860}"
FLOWER_PORT="${FLOWER_PORT:-5555}"

echo "====================================="
echo "Starting Distributed Mode Coordinator"
echo "====================================="
echo ""
echo "Configuration:"
echo "  - Redis Password: ${REDIS_PASSWORD:-<none>}"
echo "  - Expected Workers: $NUM_WORKERS"
echo "  - Coordinator Port: $COORDINATOR_PORT"
echo "  - Flower Dashboard: $FLOWER_PORT"
echo ""
echo "Coordinator will be accessible at:"
echo "  - Web UI: http://$(hostname -I | awk '{print $1}'):$COORDINATOR_PORT"
echo "  - Flower Dashboard: http://$(hostname -I | awk '{print $1}'):$FLOWER_PORT"
echo ""
echo "Workers should connect to:"
echo "  REDIS_URL=redis://:${REDIS_PASSWORD}@$(hostname -I | awk '{print $1}'):6379/0"
echo ""
echo "====================================="

# Start coordinator, redis, and flower
docker-compose -f docker-compose.distributed.yml up -d redis

echo "Waiting for Redis to be ready..."
sleep 5

docker-compose -f docker-compose.distributed.yml up -d flower coordinator

echo ""
echo "Services started successfully!"
echo ""
echo "View logs with:"
echo "  docker-compose -f docker-compose.distributed.yml logs -f"
echo ""
echo "Stop services with:"
echo "  docker-compose -f docker-compose.distributed.yml down"
