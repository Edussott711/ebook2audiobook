#!/bin/bash
# Interactive setup script for distributed cluster
# Helps configure and start a distributed ebook2audiobook cluster

set -e

echo "====================================="
echo "Distributed Cluster Setup Wizard"
echo "====================================="
echo ""

# Detect role
echo "Select your role:"
echo "  1) Coordinator (master machine with Redis)"
echo "  2) Worker (processing machine with GPU)"
echo ""
read -p "Enter choice [1-2]: " role_choice

case $role_choice in
    1)
        echo ""
        echo "Setting up as COORDINATOR..."
        echo ""

        # Ask for Redis password
        read -p "Set Redis password (leave empty for no password): " redis_pass
        export REDIS_PASSWORD="$redis_pass"

        # Ask for number of workers
        read -p "Expected number of workers [2]: " num_workers
        export NUM_WORKERS="${num_workers:-2}"

        # Get coordinator IP
        coordinator_ip=$(hostname -I | awk '{print $1}')

        echo ""
        echo "Configuration:"
        echo "  - Coordinator IP: $coordinator_ip"
        echo "  - Redis Password: ${REDIS_PASSWORD:-<none>}"
        echo "  - Expected Workers: $NUM_WORKERS"
        echo ""

        # Build coordinator image if needed
        if ! docker image inspect ebook2audiobook:latest &> /dev/null; then
            echo "Building coordinator image..."
            docker build -t ebook2audiobook:latest .
        fi

        # Start coordinator
        echo "Starting coordinator services..."
        ./scripts/distributed/start-coordinator.sh

        echo ""
        echo "====================================="
        echo "Coordinator Setup Complete!"
        echo "====================================="
        echo ""
        echo "Workers should connect with this command:"
        echo ""
        if [ -z "$REDIS_PASSWORD" ]; then
            echo "  COORDINATOR_IP=$coordinator_ip ./scripts/distributed/start-worker.sh"
        else
            echo "  COORDINATOR_IP=$coordinator_ip REDIS_PASSWORD='$REDIS_PASSWORD' ./scripts/distributed/start-worker.sh"
        fi
        echo ""
        echo "Access the web UI at: http://$coordinator_ip:7860"
        echo "Access Flower dashboard at: http://$coordinator_ip:5555 (admin/admin)"
        ;;

    2)
        echo ""
        echo "Setting up as WORKER..."
        echo ""

        # Ask for coordinator IP
        read -p "Enter coordinator IP address: " coordinator_ip
        export COORDINATOR_IP="$coordinator_ip"

        # Ask for Redis password
        read -p "Enter Redis password (leave empty if none): " redis_pass
        export REDIS_PASSWORD="$redis_pass"

        # Ask for GPU ID
        read -p "GPU ID to use [0]: " gpu_id
        export GPU_ID="${gpu_id:-0}"

        # Generate worker ID
        worker_id="worker_$(hostname)_$(date +%s)"
        export WORKER_ID="$worker_id"

        echo ""
        echo "Configuration:"
        echo "  - Worker ID: $WORKER_ID"
        echo "  - Coordinator IP: $COORDINATOR_IP"
        echo "  - GPU ID: $GPU_ID"
        echo ""

        # Check if worker image exists
        if ! docker image inspect ebook2audiobook-worker:latest &> /dev/null; then
            echo "Worker image not found. Building..."
            read -p "Enter CUDA version (e.g., cuda124, cuda121) [cuda124]: " cuda_version
            export TORCH_VERSION="${cuda_version:-cuda124}"
            ./scripts/distributed/build-worker-image.sh
        fi

        # Start worker
        echo "Starting worker..."
        ./scripts/distributed/start-worker.sh

        echo ""
        echo "====================================="
        echo "Worker Setup Complete!"
        echo "====================================="
        echo ""
        echo "Worker is now connected to coordinator at $COORDINATOR_IP"
        echo ""
        echo "View logs with:"
        echo "  docker logs -f ebook2audio-worker-$WORKER_ID"
        ;;

    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac

echo ""
echo "Setup complete!"
