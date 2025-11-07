#!/bin/bash
# Start a worker node on any machine with GPU or CPU
# This script should be run on each worker machine

set -e

# Configuration
COORDINATOR_IP="${COORDINATOR_IP:-localhost}"
REDIS_PASSWORD="${REDIS_PASSWORD:-}"
WORKER_ID="${WORKER_ID:-worker_$(hostname)_$(date +%s)}"
USE_GPU="${USE_GPU:-auto}"  # auto, yes, no
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

# Detect GPU availability
GPU_AVAILABLE="no"
if command -v nvidia-smi &> /dev/null; then
    if nvidia-smi &> /dev/null; then
        GPU_AVAILABLE="yes"
    fi
fi

# Determine if we should use GPU
USE_GPU_FINAL="no"
if [ "$USE_GPU" = "yes" ]; then
    if [ "$GPU_AVAILABLE" = "yes" ]; then
        USE_GPU_FINAL="yes"
    else
        echo "Warning: GPU requested but not available, falling back to CPU"
    fi
elif [ "$USE_GPU" = "auto" ] && [ "$GPU_AVAILABLE" = "yes" ]; then
    USE_GPU_FINAL="yes"
fi

echo "Configuration:"
echo "  - Worker ID: $WORKER_ID"
echo "  - Coordinator IP: $COORDINATOR_IP"
echo "  - Redis URL: ${REDIS_URL}"
echo "  - GPU Available: $GPU_AVAILABLE"
echo "  - Using GPU: $USE_GPU_FINAL"
if [ "$USE_GPU_FINAL" = "yes" ]; then
    echo "  - GPU ID: $GPU_ID"
fi
echo ""
echo "====================================="

# Check if the image exists
if ! docker image inspect ebook2audiobook-worker:latest &> /dev/null; then
    echo "Error: Docker image 'ebook2audiobook-worker:latest' not found!"
    echo ""
    echo "Please build the worker image first:"
    echo "  cd /path/to/ebook2audiobook"
    if [ "$USE_GPU_FINAL" = "yes" ]; then
        echo "  ./scripts/distributed/build-worker-image.sh  # For GPU"
    else
        echo "  TORCH_VERSION=cpu ./scripts/distributed/build-worker-image.sh  # For CPU"
    fi
    echo ""
    exit 1
fi

# Build docker run command
DOCKER_CMD="docker run -d --name ebook2audio-worker-${WORKER_ID} --restart unless-stopped"

# Add GPU support if needed
if [ "$USE_GPU_FINAL" = "yes" ]; then
    DOCKER_CMD="$DOCKER_CMD --gpus device=${GPU_ID}"
    CUDA_VISIBLE="${GPU_ID}"
else
    # Force CPU mode by setting CUDA_VISIBLE_DEVICES to empty
    CUDA_VISIBLE=""
fi

# Add environment variables and image
DOCKER_CMD="$DOCKER_CMD \
    -e REDIS_URL=${REDIS_URL} \
    -e WORKER_ID=${WORKER_ID} \
    -e CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE} \
    ebook2audiobook-worker:latest"

# Start the worker
eval $DOCKER_CMD

echo ""
echo "Worker started successfully!"
echo ""
echo "View worker logs with:"
echo "  docker logs -f ebook2audio-worker-${WORKER_ID}"
echo ""
echo "Stop worker with:"
echo "  docker stop ebook2audio-worker-${WORKER_ID}"
echo "  docker rm ebook2audio-worker-${WORKER_ID}"
