#!/bin/bash
set -e

# Entrypoint script for development container

echo "========================================"
echo "eBook2Audiobook Development Environment"
echo "========================================"

# Ensure directories exist
mkdir -p /workspace/{audiobooks,ebooks,models,voices,tmp,logs}

# Install project dependencies if requirements.txt exists
if [ -f "/workspace/requirements.txt" ]; then
    echo "📦 Installing project dependencies..."
    pip install --user -r /workspace/requirements.txt
fi

# Install project in editable mode if setup.py exists
if [ -f "/workspace/setup.py" ]; then
    echo "📦 Installing project in editable mode..."
    pip install --user -e /workspace
fi

echo "✅ Development environment ready!"
echo ""
echo "Quick start commands:"
echo "  - Run tests: pytest"
echo "  - Format code: black ."
echo "  - Lint code: flake8 ."
echo "  - Type check: mypy ."
echo "  - Run app: python app.py"
echo ""

# Execute the command passed to the container
exec "$@"
