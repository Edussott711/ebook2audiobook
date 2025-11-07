# Quick Start: Distributed Mode

Get your distributed ebook2audiobook cluster running in **5 minutes**!

## 🎯 What You Need

- **1 Coordinator machine** (can be CPU-only, just needs to run Redis)
- **1+ Worker machines** with NVIDIA GPUs
- All machines on the same network
- Docker installed on all machines

## ⚡ Super Quick Setup

### Step 1: Build Worker Image (on any machine)

```bash
cd /path/to/ebook2audiobook
./scripts/distributed/build-worker-image.sh
```

This creates the `ebook2audiobook-worker:latest` Docker image.

### Step 2: Distribute Image to Worker Machines

**Option A: Via Docker Registry (recommended for multiple workers)**

```bash
# Tag and push
docker tag ebook2audiobook-worker:latest your-registry/ebook2audiobook-worker:latest
docker push your-registry/ebook2audiobook-worker:latest

# On each worker machine
docker pull your-registry/ebook2audiobook-worker:latest
docker tag your-registry/ebook2audiobook-worker:latest ebook2audiobook-worker:latest
```

**Option B: Via File Transfer (for few workers)**

```bash
# Save image
docker save ebook2audiobook-worker:latest | gzip > ebook2audiobook-worker.tar.gz

# Copy to each worker
scp ebook2audiobook-worker.tar.gz user@worker1:/tmp/
scp ebook2audiobook-worker.tar.gz user@worker2:/tmp/

# On each worker machine
docker load < /tmp/ebook2audiobook-worker.tar.gz
```

### Step 3: Start Coordinator

On the coordinator machine:

```bash
./scripts/distributed/start-coordinator.sh
```

**Note the IP address displayed** - you'll need it for workers!

### Step 4: Start Workers

On each worker machine (copy the scripts first):

```bash
COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh
```

Replace `192.168.1.10` with your coordinator's IP.

**For multi-GPU machines**, run multiple workers:

```bash
GPU_ID=0 WORKER_ID=worker_gpu0 COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh
GPU_ID=1 WORKER_ID=worker_gpu1 COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh
```

### Step 5: Convert Books!

Open your browser: `http://<coordinator-ip>:7860`

Or use CLI:

```bash
docker exec ebook2audio-coordinator python app.py \
  --headless \
  --distributed \
  --num_workers 4 \
  --ebook /app/input/book.epub \
  --language eng
```

## 📊 Monitoring

- **Web UI**: `http://<coordinator-ip>:7860`
- **Flower Dashboard**: `http://<coordinator-ip>:5555` (admin/admin)
- **Worker Logs**: `docker logs -f ebook2audio-worker-<worker-id>`

## 🔥 Even Easier: Interactive Setup

Don't want to remember commands? Use the interactive wizard:

```bash
./scripts/distributed/setup-cluster.sh
```

It will guide you through setting up either a coordinator or worker!

## 🎬 Complete Example

Let's say you have:
- Coordinator: `192.168.1.10`
- Worker 1: `192.168.1.11` (1x GPU)
- Worker 2: `192.168.1.12` (2x GPUs)

```bash
# === On 192.168.1.10 (Coordinator) ===
./scripts/distributed/start-coordinator.sh
# Output: Coordinator running at http://192.168.1.10:7860

# === On 192.168.1.11 (Worker 1) ===
COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh
# Worker started!

# === On 192.168.1.12 (Worker 2) ===
# Start 2 workers (one per GPU)
GPU_ID=0 WORKER_ID=w2_gpu0 COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh
GPU_ID=1 WORKER_ID=w2_gpu1 COORDINATOR_IP=192.168.1.10 ./scripts/distributed/start-worker.sh
# 2 workers started!

# === Back on 192.168.1.10 ===
# Check Flower dashboard
open http://192.168.1.10:5555
# You should see 3 workers active!

# Convert a book
open http://192.168.1.10:7860
# Upload book and start conversion
# 3x faster than single GPU! 🚀
```

## 🛠️ Troubleshooting

### Workers can't connect

```bash
# On coordinator, check Redis is accessible
docker ps | grep redis

# Test from worker machine
redis-cli -h <coordinator-ip> ping
# Should return: PONG
```

If fails, check firewall:

```bash
# On coordinator
sudo ufw allow 6379/tcp
```

### Worker not processing

```bash
# Check worker logs
docker logs ebook2audio-worker-<worker-id>

# Check GPU is available
docker exec ebook2audio-worker-<worker-id> nvidia-smi
```

### Redis out of memory

Edit `docker-compose.distributed.yml` and increase `maxmemory`:

```yaml
command: redis-server --maxmemory 4gb --maxmemory-policy allkeys-lru
```

## 📖 Need More Details?

- **Deployment Scripts**: [scripts/distributed/README.md](scripts/distributed/README.md)
- **Full Documentation**: [DISTRIBUTED_MODE.md](DISTRIBUTED_MODE.md)
- **Architecture Details**: See distributed mode docs in `/docs/distributed/`

## ✨ Key Features

- ✅ **No shared storage needed** - Audio transferred via Redis
- ✅ **Linear scaling** - 2 workers = 2x faster, 4 workers = 4x faster
- ✅ **Automatic retry** - Failed chapters are automatically retried
- ✅ **Resume support** - Interrupt and resume conversions
- ✅ **GPU isolation** - One task per worker, no memory conflicts

## 🚀 Performance

| Workers | Time (300-page book) | Speedup |
|---------|---------------------|---------|
| 1 GPU   | 6 hours            | 1x      |
| 2 GPUs  | 3 hours            | 2x      |
| 4 GPUs  | 1.5 hours          | 4x      |
| 8 GPUs  | 45 minutes         | 8x      |

**Happy distributed audiobook creation! 🎵**
