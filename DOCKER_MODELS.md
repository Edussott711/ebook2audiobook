# Docker Model Management

This document explains how to manage TTS models with Docker using persistent volumes.

## Overview

By default, the Docker image for ebook2audiobook is built with `SKIP_XTTS_TEST: "true"`, which means models are **not** baked into the image to save space. Instead, models are downloaded on-demand when first used.

With the new **persistent volume** feature, you can:
- Download models once on first startup
- Store them in a persistent Docker volume
- Reuse them across container restarts without re-downloading

## Configuration

### Option 1: Download Models on First Startup (Recommended)

To enable automatic model download on first startup, edit `docker-compose.yml`:

```yaml
environment:
  - DOWNLOAD_MODELS_ON_STARTUP=true  # Change from false to true
```

### Option 2: Manual Model Management

Keep the default setting to download models on-demand:

```yaml
environment:
  - DOWNLOAD_MODELS_ON_STARTUP=false  # Default
```

## Persistent Volume

The `docker-compose.yml` includes a persistent volume for models:

```yaml
volumes:
  - ./:/app  # Maps the local directory to the container
  - ebook2audiobook_models:/app/models  # Persistent volume for TTS models
```

This named volume (`ebook2audiobook_models`) persists even when you:
- Stop and restart the container
- Rebuild the image
- Update the application

## Usage Examples

### Start with Model Download Enabled

1. Edit `docker-compose.yml` and set `DOWNLOAD_MODELS_ON_STARTUP=true`
2. Start the container:
   ```bash
   docker-compose up
   ```
3. On first startup, the base XTTS-v2 model will be downloaded automatically
4. Subsequent starts will reuse the cached models

### Clean Start (Remove Downloaded Models)

To clear all downloaded models and start fresh:

```bash
# Stop the container
docker-compose down

# Remove the models volume
docker volume rm ebook2audiobook_models

# Start again
docker-compose up
```

### Check Volume Size

To see how much space the models are using:

```bash
docker volume inspect ebook2audiobook_models
```

## What Models Are Downloaded?

When `DOWNLOAD_MODELS_ON_STARTUP=true`, the following base model is downloaded:

- **XTTS-v2** (Coqui TTS)
  - Repository: `coqui/XTTS-v2`
  - Files: `config.json`, `model.pth`, `vocab.json`, `ref.wav`, `speakers_xtts.pth`
  - Size: ~2-3 GB

Additional models (fine-tuned models, other TTS engines) are downloaded on-demand when you use them.

## Benefits

✅ **Faster Startup**: After first download, no waiting for models on subsequent starts
✅ **Bandwidth Savings**: Download once, reuse forever
✅ **Offline Operation**: Once downloaded, works without internet (for base model)
✅ **Easy Cleanup**: Remove volume to clear all models

## Troubleshooting

### Models Not Persisting

If models are being re-downloaded every time:
1. Check that the volume is properly mounted: `docker volume ls | grep ebook2audiobook_models`
2. Verify the volume is defined in `docker-compose.yml`
3. Make sure you're using `docker-compose up` (not `docker run`)

### Download Fails

If model download fails on startup:
1. Check your internet connection
2. Verify Hugging Face is accessible
3. The application will continue and download models on first use
4. Check logs: `docker-compose logs`

### Clear Cache

To force a fresh download:
```bash
docker-compose down
docker volume rm ebook2audiobook_models
docker-compose up
```

## Advanced: Custom Volume Location

To store models in a specific location on your host:

```yaml
volumes:
  - ./:/app
  - /path/to/your/models:/app/models  # Custom path on host
```

This gives you direct access to the models folder from your host system.
