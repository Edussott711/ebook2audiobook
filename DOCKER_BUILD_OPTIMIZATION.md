# 🚀 Docker Build Optimization Guide

This document explains how to build Docker images efficiently, avoiding re-downloads of large packages (like PyTorch ~887 MB).

## 🎯 Quick Start - Optimized Build Commands

### For CPU-only build (fastest):
```bash
DOCKER_BUILDKIT=1 docker build \
  --build-arg TORCH_VERSION=cpu \
  -t ebook2audiobook:latest .
```

### For CUDA build:
```bash
DOCKER_BUILDKIT=1 docker build \
  --build-arg TORCH_VERSION=cuda124 \
  -t ebook2audiobook:cuda .
```

### For build without XTTS test (faster development):
```bash
DOCKER_BUILDKIT=1 docker build \
  --build-arg SKIP_XTTS_TEST=true \
  -t ebook2audiobook:dev .
```

---

## 📚 How Cache Optimization Works

### 1. **BuildKit Cache Mount**
The Dockerfile uses `RUN --mount=type=cache,target=/root/.cache/pip` which:
- ✅ **Persists pip cache** between builds on your local machine
- ✅ **Shares downloaded packages** across different builds
- ✅ **No re-download** if package already in cache
- ✅ **Automatic cleanup** by Docker when space needed

**Example:** If you build for CPU, then build for CUDA:
- First build: Downloads PyTorch CPU (~887 MB) ⏱️ 5-15 min
- Second build: Reuses torch files from cache ⏱️ 30 sec

### 2. **Layer Caching**
The Dockerfile is organized to maximize Docker layer cache hits:

```dockerfile
# ✅ These layers are cached (rarely change):
1. System packages (apt-get)
2. Rust compiler
3. requirements.txt only
4. UniDic installation

# ⚠️ This layer invalidates on code change:
5. COPY . /app (your application code)
```

**Result:** When you modify Python code, only layer 5 rebuilds. Layers 1-4 are reused from cache!

### 3. **.dockerignore Optimization**
Excludes unnecessary files from build context:
- `.git/` (can be 100s of MB)
- `__pycache__/`
- `audiobooks/` outputs (can be GBs!)
- Session data
- IDE configs

**Before:** `docker build` sends 500 MB to daemon
**After:** `docker build` sends 50 MB to daemon
**Speed gain:** 10x faster context transfer!

---

## 🔄 Cache Behavior Examples

### Scenario 1: First Build
```bash
$ DOCKER_BUILDKIT=1 docker build -t ebook2audiobook:latest .
#1 [internal] load build definition
#2 [internal] load .dockerignore
#3 [base 1/5] FROM python:3.12
#4 [base 2/5] RUN apt-get update && ...          ⏱️ 2 min (new)
#5 [base 3/5] RUN curl --proto '=https' ...      ⏱️ 1 min (new)
#6 [base 4/5] COPY requirements.txt /app/        ⏱️ 1 sec (new)
#7 [base 5/5] RUN pip install unidic...          ⏱️ 30 sec (new)
#8 [pytorch] RUN pip install torch...            ⏱️ 15 min (downloading 887 MB)
#9 [pytorch] COPY . /app                         ⏱️ 5 sec (new)

Total: ~20 minutes
```

### Scenario 2: Rebuild After Code Change
```bash
$ # You modified lib/functions.py
$ DOCKER_BUILDKIT=1 docker build -t ebook2audiobook:latest .
#4 [base 2/5] RUN apt-get update && ...          ✅ CACHED
#5 [base 3/5] RUN curl --proto '=https' ...      ✅ CACHED
#6 [base 4/5] COPY requirements.txt /app/        ✅ CACHED
#7 [base 5/5] RUN pip install unidic...          ✅ CACHED
#8 [pytorch] RUN pip install torch...            ✅ CACHED (pip cache + layer cache!)
#9 [pytorch] COPY . /app                         ⏱️ 5 sec (changed)

Total: ~10 seconds! 🎉
```

### Scenario 3: Rebuild After requirements.txt Change
```bash
$ # You added a new package to requirements.txt
$ DOCKER_BUILDKIT=1 docker build -t ebook2audiobook:latest .
#4 [base 2/5] RUN apt-get update && ...          ✅ CACHED
#5 [base 3/5] RUN curl --proto '=https' ...      ✅ CACHED
#6 [base 4/5] COPY requirements.txt /app/        ⏱️ 1 sec (changed)
#7 [base 5/5] RUN pip install unidic...          ✅ CACHED
#8 [pytorch] RUN pip install torch...            ⏱️ 30 sec (reuses cached wheels!)
#9 [pytorch] COPY . /app                         ⏱️ 5 sec

Total: ~40 seconds (not 20 minutes!)
```

---

## 💡 Pro Tips

### Tip 1: Use BuildKit
**Always** use `DOCKER_BUILDKIT=1` or enable it globally:

```bash
# Enable BuildKit permanently (recommended)
echo 'export DOCKER_BUILDKIT=1' >> ~/.bashrc
source ~/.bashrc

# Or create daemon config
mkdir -p ~/.docker
cat > ~/.docker/daemon.json << 'EOF'
{
  "features": {
    "buildkit": true
  }
}
EOF
```

### Tip 2: Clean Build (When Needed)
If you need to force a complete rebuild without any cache:

```bash
DOCKER_BUILDKIT=1 docker build --no-cache -t ebook2audiobook:latest .
```

⚠️ **Warning:** This will re-download everything (PyTorch, all packages)!

### Tip 3: Check Cache Size
Docker automatically manages cache, but you can check its size:

```bash
# View BuildKit cache usage
docker builder du

# Prune old cache (keeps last 24h by default)
docker builder prune

# Aggressive cleanup (removes all cache)
docker builder prune --all
```

### Tip 4: Multi-Stage Build Strategy
If you modify code frequently, consider this workflow:

```bash
# 1. Build base image ONCE (includes all dependencies)
DOCKER_BUILDKIT=1 docker build \
  --target base \
  --build-arg TORCH_VERSION=cpu \
  -t ebook2audiobook:base .

# 2. For development, use this base
DOCKER_BUILDKIT=1 docker build \
  --build-arg BASE_IMAGE=ebook2audiobook:base \
  --build-arg SKIP_XTTS_TEST=true \
  -t ebook2audiobook:dev .
```

Now code changes only rebuild from the base, not from scratch!

---

## 📊 Performance Metrics

| Scenario | Without Optimization | With Optimization | Speed Gain |
|----------|---------------------|-------------------|------------|
| **First build** | 20 min | 20 min | Baseline |
| **Code change** | 20 min (full rebuild) | 10 sec | **120x faster** |
| **requirements.txt change** | 20 min | 40 sec | **30x faster** |
| **Clean build** | 20 min | 20 min | Same |

---

## 🐛 Troubleshooting

### Problem: "Cache not being used"
**Solution:** Make sure you're using `DOCKER_BUILDKIT=1`

```bash
# Check if BuildKit is active
docker buildx version

# If not available, update Docker
```

### Problem: "Still downloading PyTorch every time"
**Possible causes:**
1. Not using BuildKit → Add `DOCKER_BUILDKIT=1`
2. Using `--no-cache` flag → Remove it
3. Dockerfile changed before pip install → Check layer cache

### Problem: "Build context too large"
**Solution:** Improve `.dockerignore`

```bash
# Check context size
du -sh .

# Common culprits:
# - .git/ directory (can be 100s of MB)
# - audiobooks/ outputs (can be GBs!)
# - models/ downloaded at runtime
# - python_env/ virtual environments

# Make sure these are in .dockerignore!
```

### Problem: "Network timeout during build"
**Solution:** The Dockerfile now has automatic retry logic with 900s timeout.
If you still have issues:

```bash
# Increase timeout even more (30 minutes)
DOCKER_BUILDKIT=1 docker build \
  --build-arg PIP_DEFAULT_TIMEOUT=1800 \
  -t ebook2audiobook:latest .
```

---

## 🎓 Understanding BuildKit Cache Mount

Traditional Docker (without cache mount):
```dockerfile
RUN pip install torch  # Downloads 887 MB
# Package is deleted after build (--no-cache-dir)
# Next build: Download 887 MB again ❌
```

With BuildKit cache mount:
```dockerfile
RUN --mount=type=cache,target=/root/.cache/pip pip install torch
# Downloads 887 MB and stores in /root/.cache/pip
# Cache persists OUTSIDE the image
# Next build: Reuses cached wheels ✅
```

**Location of cache on your machine:**
```bash
# Linux
/var/lib/docker/buildkit/cache/

# macOS
~/Library/Containers/com.docker.docker/Data/vms/0/data/docker/buildkit/cache/

# Windows (WSL2)
\\wsl$\docker-desktop-data\data\docker\buildkit\cache\
```

---

## 🚀 Summary

1. ✅ **Always use** `DOCKER_BUILDKIT=1`
2. ✅ **requirements.txt is copied first** → Dependencies cached separately
3. ✅ **Cache mount persists** pip downloads between builds
4. ✅ **.dockerignore excludes** unnecessary files
5. ✅ **Layer order optimized** for maximum cache reuse

**Result:** Code changes = 10 second rebuilds, not 20 minute rebuilds! 🎉

---

## 📞 Need Help?

If builds are still slow:
1. Check `docker builder du` to see cache size
2. Verify `DOCKER_BUILDKIT=1` is set
3. Review `.dockerignore` for large excluded files
4. Check Docker version (20.10+ recommended)
