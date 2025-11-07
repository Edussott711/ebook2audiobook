# Distributed Mode Deployment Scripts

These scripts help you quickly deploy ebook2audiobook in distributed mode across multiple machines using Docker.

## Architecture Overview

- **Coordinator**: Master machine that runs Redis, Flower dashboard, and coordinates the conversion
- **Workers**: GPU-equipped machines that process chapters in parallel
- **Redis**: Message broker and audio data transfer medium (no shared storage needed!)

## Quick Start

### Option 1: Interactive Setup (Recommended)

Run the interactive setup wizard:

```bash
./scripts/distributed/setup-cluster.sh
```

This will guide you through setting up either a coordinator or worker node.

### Option 2: Manual Setup

#### Step 1: Build Worker Image

On your development machine (or coordinator):

```bash
# Build worker image with CUDA support
./scripts/distributed/build-worker-image.sh

# Or specify CUDA version
TORCH_VERSION=cuda121 ./scripts/distributed/build-worker-image.sh
```

#### Step 2: Start Coordinator

On the coordinator machine:

```bash
# Start coordinator with default settings
./scripts/distributed/start-coordinator.sh

# Or with custom configuration
REDIS_PASSWORD=mysecret NUM_WORKERS=4 ./scripts/distributed/start-coordinator.sh
```

#### Step 3: Distribute Worker Image

Transfer the worker image to all worker machines:

```bash
# Save image
docker save ebook2audiobook-worker:latest | gzip > ebook2audiobook-worker.tar.gz

# Copy to worker machines
scp ebook2audiobook-worker.tar.gz user@worker1:/tmp/
scp ebook2audiobook-worker.tar.gz user@worker2:/tmp/

# On each worker machine, load the image
docker load < /tmp/ebook2audiobook-worker.tar.gz
```

Alternatively, push to a Docker registry:

```bash
docker tag ebook2audiobook-worker:latest your-registry/ebook2audiobook-worker:latest
docker push your-registry/ebook2audiobook-worker:latest

# On worker machines
docker pull your-registry/ebook2audiobook-worker:latest
docker tag your-registry/ebook2audiobook-worker:latest ebook2audiobook-worker:latest
```

#### Step 4: Start Workers

On each worker machine:

```bash
# Copy the start-worker.sh script to the worker machine
# Then run:

COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh

# Or with custom configuration
COORDINATOR_IP=192.168.1.10 \
REDIS_PASSWORD=mysecret \
GPU_ID=0 \
WORKER_ID=worker_gpu1 \
./scripts/distributed/start-worker.sh
```

## Script Reference

### `setup-cluster.sh`

Interactive wizard for setting up coordinator or worker nodes.

**Usage:**
```bash
./scripts/distributed/setup-cluster.sh
```

### `start-coordinator.sh`

Starts the coordinator with Redis and Flower monitoring dashboard.

**Environment Variables:**
- `REDIS_PASSWORD`: Password for Redis (optional)
- `NUM_WORKERS`: Expected number of workers (default: 2)
- `COORDINATOR_PORT`: Port for web UI (default: 7860)
- `FLOWER_PORT`: Port for Flower dashboard (default: 5555)

**Usage:**
```bash
./scripts/distributed/start-coordinator.sh

# With custom settings
REDIS_PASSWORD=secret NUM_WORKERS=4 ./scripts/distributed/start-coordinator.sh
```

### `start-worker.sh`

Starts a worker on a GPU-equipped machine.

**Environment Variables:**
- `COORDINATOR_IP`: IP address of coordinator machine (required)
- `REDIS_PASSWORD`: Redis password if configured (optional)
- `WORKER_ID`: Unique worker identifier (auto-generated if not set)
- `GPU_ID`: GPU device ID to use (default: 0)

**Usage:**
```bash
COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh

# Multi-GPU setup - start multiple workers
GPU_ID=0 WORKER_ID=worker_gpu0 COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh
GPU_ID=1 WORKER_ID=worker_gpu1 COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh
```

### `build-worker-image.sh`

Builds the Docker image for workers.

**Environment Variables:**
- `TORCH_VERSION`: PyTorch version to install (default: cuda124)
  - Options: `cuda124`, `cuda121`, `cuda118`, `rocm`, `cpu`
- `SKIP_XTTS_TEST`: Skip model download test (default: false)

**Usage:**
```bash
./scripts/distributed/build-worker-image.sh

# With custom CUDA version
TORCH_VERSION=cuda121 ./scripts/distributed/build-worker-image.sh

# Fast build (skip test)
SKIP_XTTS_TEST=true ./scripts/distributed/build-worker-image.sh
```

## Network Requirements

- **Port 6379**: Redis (must be accessible from workers to coordinator)
- **Port 7860**: Gradio Web UI (coordinator only)
- **Port 5555**: Flower dashboard (coordinator only)

### Firewall Configuration

On the coordinator machine, allow incoming connections:

```bash
# Ubuntu/Debian with ufw
sudo ufw allow 6379/tcp
sudo ufw allow 7860/tcp
sudo ufw allow 5555/tcp

# CentOS/RHEL with firewalld
sudo firewall-cmd --permanent --add-port=6379/tcp
sudo firewall-cmd --permanent --add-port=7860/tcp
sudo firewall-cmd --permanent --add-port=5555/tcp
sudo firewall-cmd --reload
```

## Monitoring

### Flower Dashboard

Access the Flower dashboard at `http://<coordinator-ip>:5555` (default credentials: admin/admin)

Features:
- Real-time worker status
- Task queue monitoring
- Task history and results
- Worker resource utilization

### Docker Logs

```bash
# Coordinator logs
docker-compose -f docker-compose.distributed.yml logs -f coordinator

# Redis logs
docker-compose -f docker-compose.distributed.yml logs -f redis

# Worker logs (on worker machine)
docker logs -f ebook2audio-worker-<worker-id>
```

## Troubleshooting

### Workers can't connect to Redis

1. Check firewall settings on coordinator
2. Verify coordinator IP address is correct
3. Test Redis connectivity:
   ```bash
   redis-cli -h <coordinator-ip> -p 6379 ping
   ```

### Worker not processing tasks

1. Check worker logs: `docker logs ebook2audio-worker-<id>`
2. Verify GPU is available: `docker exec ebook2audio-worker-<id> nvidia-smi`
3. Check Flower dashboard for worker status

### Audio files not being generated

1. Check Redis memory usage (may need to increase `maxmemory`)
2. Verify all workers are connected and active
3. Check coordinator logs for errors

### Performance issues

1. Increase Redis memory limit in docker-compose.distributed.yml
2. Ensure workers have adequate GPU memory
3. Monitor network bandwidth (audio transfer via Redis)

## Advanced Configuration

### Multiple GPUs per Worker Machine

Start multiple worker containers on the same machine:

```bash
for gpu_id in 0 1 2 3; do
    GPU_ID=$gpu_id \
    WORKER_ID="worker_$(hostname)_gpu${gpu_id}" \
    COORDINATOR_IP=192.168.1.10 \
    ./scripts/distributed/start-worker.sh
done
```

### Custom Redis Configuration

Edit `docker-compose.distributed.yml` to customize Redis settings:

```yaml
command: redis-server --appendonly yes --maxmemory 4gb --maxmemory-policy allkeys-lru
```

### Using with Docker Swarm or Kubernetes

For production deployments, consider using orchestration tools:
- Docker Swarm: Use `docker stack deploy` with the compose file
- Kubernetes: Convert compose file using kompose or write custom manifests

## Examples

### Example 1: 2-Machine Setup (1 Coordinator + 1 Worker)

**Coordinator (192.168.1.10):**
```bash
./scripts/distributed/start-coordinator.sh
```

**Worker (192.168.1.11):**
```bash
COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh
```

### Example 2: 1 Coordinator + 3 Workers with 2 GPUs each

**Coordinator (192.168.1.10):**
```bash
NUM_WORKERS=6 ./scripts/distributed/start-coordinator.sh
```

**Worker 1 (192.168.1.11):**
```bash
GPU_ID=0 WORKER_ID=worker1_gpu0 COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh
GPU_ID=1 WORKER_ID=worker1_gpu1 COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh
```

**Worker 2 (192.168.1.12):**
```bash
GPU_ID=0 WORKER_ID=worker2_gpu0 COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh
GPU_ID=1 WORKER_ID=worker2_gpu1 COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh
```

**Worker 3 (192.168.1.13):**
```bash
GPU_ID=0 WORKER_ID=worker3_gpu0 COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh
GPU_ID=1 WORKER_ID=worker3_gpu1 COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh
```

## Security Considerations

1. **Use Redis password** in production: Set `REDIS_PASSWORD`
2. **Firewall rules**: Only allow worker IPs to access coordinator
3. **Network isolation**: Use private network for cluster communication
4. **Change Flower credentials**: Edit `FLOWER_BASIC_AUTH` in docker-compose file
5. **TLS/SSL**: For production, configure Redis with TLS

## Support

For issues and questions:
- GitHub Issues: https://github.com/DrewThomasson/ebook2audiobook/issues
- Documentation: See `/docs/distributed/` folder
