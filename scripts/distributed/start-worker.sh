#!/bin/bash
# Start a worker node on any machine
# This script should be run on each worker machine with GPU

set -e

# Configuration
COORDINATOR_IP="${COORDINATOR_IP:-localhost}"
REDIS_PASSWORD="${REDIS_PASSWORD:-}"
WORKER_ID="${WORKER_ID:-worker_$(hostname)_$(date +%s)}"
GPU_ID="${GPU_ID:-0}"

# Construct Redis URL
if [ -z "$REDIS_PASSWORD" ]; then
    REDIS_URL="redis://${COORDINATOR_IP}:6379/0"
else
    REDIS_URL="redis://:${REDIS_PASSWORD}@${COORDINATOR_IP}:6379/0"
fi

echo "====================================="
echo "Starting Distributed Worker"
echo "====================================="
echo ""
echo "Configuration:"
echo "  - Worker ID: $WORKER_ID"
echo "  - GPU ID: $GPU_ID"
echo "  - Coordinator IP: $COORDINATOR_IP"
echo "  - Redis URL: ${REDIS_URL}"
echo ""
echo "====================================="

# Check if the image exists
if ! docker image inspect ebook2audiobook-worker:latest &> /dev/null; then
    echo "Error: Docker image 'ebook2audiobook-worker:latest' not found!"
    echo ""
    echo "Please build the worker image first:"
    echo "  cd /path/to/ebook2audiobook"
    echo "  docker build -f Dockerfile.worker -t ebook2audiobook-worker:latest --build-arg TORCH_VERSION=cuda124 ."
    echo ""
    echo "Or run: ./scripts/distributed/build-worker-image.sh"
    exit 1
fi

# Start the worker
docker run -d \
    --name "ebook2audio-worker-${WORKER_ID}" \
    --gpus "device=${GPU_ID}" \
    --restart unless-stopped \
    -e REDIS_URL="${REDIS_URL}" \
    -e WORKER_ID="${WORKER_ID}" \
    -e CUDA_VISIBLE_DEVICES="${GPU_ID}" \
    ebook2audiobook-worker:latest

echo ""
echo "Worker started successfully!"
echo ""
echo "View worker logs with:"
echo "  docker logs -f ebook2audio-worker-${WORKER_ID}"
echo ""
echo "Stop worker with:"
echo "  docker stop ebook2audio-worker-${WORKER_ID}"
echo "  docker rm ebook2audio-worker-${WORKER_ID}"
