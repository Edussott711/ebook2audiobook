#!/bin/bash
# Build the worker Docker image
# This image can then be distributed to all worker machines

set -e

# Configuration
TORCH_VERSION="${TORCH_VERSION:-cuda124}"
SKIP_XTTS_TEST="${SKIP_XTTS_TEST:-false}"

echo "====================================="
echo "Building Worker Docker Image"
echo "====================================="
echo ""
echo "Configuration:"
echo "  - PyTorch Version: $TORCH_VERSION"
echo "  - Skip XTTS Test: $SKIP_XTTS_TEST"
echo ""
echo "Building image..."
echo ""

# Build the worker image
docker build \
    -f Dockerfile.worker \
    -t ebook2audiobook-worker:latest \
    --build-arg TORCH_VERSION="${TORCH_VERSION}" \
    --build-arg SKIP_XTTS_TEST="${SKIP_XTTS_TEST}" \
    .

echo ""
echo "====================================="
echo "Build completed successfully!"
echo "====================================="
echo ""
echo "Image: ebook2audiobook-worker:latest"
echo ""
echo "To distribute this image to other machines:"
echo ""
echo "1. Save the image:"
echo "   docker save ebook2audiobook-worker:latest | gzip > ebook2audiobook-worker.tar.gz"
echo ""
echo "2. Copy to worker machine:"
echo "   scp ebook2audiobook-worker.tar.gz user@worker-machine:/path/to/destination/"
echo ""
echo "3. Load on worker machine:"
echo "   docker load < ebook2audiobook-worker.tar.gz"
echo ""
echo "Or push to a registry:"
echo "   docker tag ebook2audiobook-worker:latest your-registry/ebook2audiobook-worker:latest"
echo "   docker push your-registry/ebook2audiobook-worker:latest"
