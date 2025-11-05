#!/usr/bin/env python3
"""
Script to pre-download TTS models for ebook2audiobook.
This script downloads the base XTTS-v2 model to ensure it's available
in a persistent Docker volume on first startup.
"""

import os
import sys
from pathlib import Path

def download_base_models():
    """Download the base XTTS-v2 model files."""
    try:
        from huggingface_hub import hf_hub_download
        from lib.conf import tts_dir
        from lib.models import TTS_ENGINES, models, default_engine_settings

        print("=" * 60)
        print("Starting model download process...")
        print("=" * 60)

        # Ensure the models directory exists
        os.makedirs(tts_dir, exist_ok=True)

        # Download XTTS-v2 base model (the most commonly used)
        engine = TTS_ENGINES['XTTSv2']
        model_config = models[engine]['internal']

        print(f"\n📦 Downloading {engine} base model...")
        print(f"Repository: {model_config['repo']}")
        print(f"Cache directory: {tts_dir}")

        # Download all required files for XTTS-v2
        files_to_download = default_engine_settings[engine]['files']

        for idx, filename in enumerate(files_to_download, 1):
            print(f"\n[{idx}/{len(files_to_download)}] Downloading: {filename}")
            try:
                downloaded_path = hf_hub_download(
                    repo_id=model_config['repo'],
                    filename=filename,
                    cache_dir=tts_dir
                )
                print(f"✅ Downloaded to: {downloaded_path}")
            except Exception as e:
                print(f"⚠️  Warning: Could not download {filename}: {e}")
                # Continue with other files even if one fails

        print("\n" + "=" * 60)
        print("✅ Model download completed successfully!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n❌ Error during model download: {e}", file=sys.stderr)
        return False

def check_models_exist():
    """Check if models are already downloaded."""
    try:
        from lib.conf import tts_dir
        from lib.models import TTS_ENGINES, default_engine_settings

        # Check if the basic XTTS-v2 model files exist in cache
        if not os.path.exists(tts_dir):
            return False

        # Simple check: if the directory has content, assume models might be there
        # A more thorough check could verify specific files
        content = list(Path(tts_dir).rglob('*'))

        return len(content) > 10  # Arbitrary threshold for "has models"

    except Exception as e:
        print(f"⚠️  Warning: Could not check for existing models: {e}")
        return False

def main():
    """Main function to handle model downloading."""

    # Check if we should download models
    download_on_startup = os.environ.get('DOWNLOAD_MODELS_ON_STARTUP', 'false').lower()

    if download_on_startup not in ['true', '1', 'yes']:
        print("Model download on startup is disabled.")
        print("Set DOWNLOAD_MODELS_ON_STARTUP=true to enable.")
        return

    print("\n🚀 Checking for models...")

    # Check if models already exist
    if check_models_exist():
        print("✅ Models already exist in cache. Skipping download.")
        return

    print("📥 Models not found. Starting download...")

    # Download the models
    success = download_base_models()

    if success:
        print("\n✅ All done! Models are ready to use.")
        sys.exit(0)
    else:
        print("\n⚠️  Model download completed with some errors.")
        print("The application will download missing models on first use.")
        sys.exit(0)  # Don't fail the startup, just warn

if __name__ == '__main__':
    main()
